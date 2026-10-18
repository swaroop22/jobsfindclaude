"""Pull open job postings from public Greenhouse and Lever company job boards,
plus (via the workday/icims modules) Workday and iCIMS careers sites.

All sources are public, unauthenticated, read-only endpoints intended for
listing a company's own postings -- no ToS violation, no login involved.
"""
from __future__ import annotations

import datetime
import logging
import re

from jobtool.http import fetch_json
from jobtool.models import JobDict

logger = logging.getLogger(__name__)

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


def fetch_greenhouse(slug: str) -> list[JobDict]:
    data = fetch_json(GREENHOUSE_URL.format(slug=slug))
    if not data:
        return []
    jobs: list[JobDict] = []
    for j in data.get("jobs", []):
        jobs.append({
            "source": "greenhouse",
            "company": slug,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "id": str(j.get("id", "")),
            "description": j.get("content", ""),
        })
    return jobs


def fetch_lever(slug: str) -> list[JobDict]:
    data = fetch_json(LEVER_URL.format(slug=slug))
    if not data:
        return []
    jobs: list[JobDict] = []
    for j in data:
        cats = j.get("categories", {}) or {}
        jobs.append({
            "source": "lever",
            "company": slug,
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl", ""),
            "id": str(j.get("id", "")),
            "description": j.get("descriptionPlain", j.get("description", "")),
        })
    return jobs


def fetch_all(companies: dict[str, list[str]], workday_search_texts: list[str] | None = None,
              icims_search_texts: list[str] | None = None,
              fetch_workday_descriptions: bool = False,
              fetch_icims_dates: bool = False) -> list[JobDict]:
    """companies: {"greenhouse": [...], "lever": [...], "workday": [...], "icims": [...]}

    workday_search_texts / icims_search_texts: both platforms search server-side
    and don't return full descriptions in list results, so pass query terms
    (e.g. medical coding keywords) to search with directly rather than relying
    on client-side filtering.

    fetch_icims_dates: iCIMS list pages don't include a posting date, so this
    triggers one extra detail-page fetch per job (slower) to populate
    posted_days_ago for use with filter_recent().
    """
    all_jobs: list[JobDict] = []
    for slug in companies.get("greenhouse", []):
        logger.info("Fetching Greenhouse: %s", slug)
        all_jobs.extend(fetch_greenhouse(slug))
    for slug in companies.get("lever", []):
        logger.info("Fetching Lever: %s", slug)
        all_jobs.extend(fetch_lever(slug))
    workday_urls = companies.get("workday", [])
    if workday_urls:
        from jobtool import workday

        all_jobs.extend(workday.fetch_all(workday_urls, search_texts=workday_search_texts,
                                           fetch_descriptions=fetch_workday_descriptions))
    icims_urls = companies.get("icims", [])
    if icims_urls:
        from jobtool import icims

        icims_jobs = icims.fetch_all(icims_urls, search_texts=icims_search_texts,
                                      fetch_dates=fetch_icims_dates)
        for j in icims_jobs:
            j["posted_days_ago"] = _icims_days_ago(j.pop("date_posted", None))
        all_jobs.extend(icims_jobs)
    return all_jobs


def _icims_days_ago(iso_date_posted: str | None) -> int | None:
    if not iso_date_posted:
        return None
    try:
        posted = datetime.datetime.fromisoformat(iso_date_posted.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now - posted).days


SENIORITY_EXCLUDE_TERMS = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "manager", "supervisor",
    "director", "head of", "vp", "vice president", "chief", "level ii", "level iii",
    "level iv", "level 2", "level 3", "level 4",
]


def filter_entry_level(jobs: list[JobDict]) -> list[JobDict]:
    """Keep jobs whose title signals entry-level, or has no seniority signal at
    all (many postings say plainly "Medical Coder" with no level qualifier
    and are entry-level in practice); drop anything with a senior/lead/
    management signal in the title."""
    out = []
    for j in jobs:
        title = j["title"].lower()
        if any(term in title for term in SENIORITY_EXCLUDE_TERMS):
            continue
        out.append(j)
    return out


def filter_jobs(jobs: list[JobDict], keywords: list[str] | None = None,
                 location: str | None = None) -> list[JobDict]:
    keywords_lower = [k.lower() for k in (keywords or [])]
    location_lower = location.lower() if location else None
    out = []
    for j in jobs:
        if keywords_lower:
            hay = (j["title"] + " " + j.get("description", "")).lower()
            if not any(k in hay for k in keywords_lower):
                continue
        if location_lower and location_lower not in j.get("location", "").lower():
            continue
        out.append(j)
    return out


PART_TIME_TERMS = ["part time", "part-time", "part-timer", "pt ", "peak time", "peak-time"]
FULL_TIME_EXCLUDE_TERMS = ["full time", "full-time", "ft "]


def filter_part_time(jobs: list[JobDict]) -> list[JobDict]:
    """Workday's timeType facet is often blank on search results, so this
    matches the "Part Time"/"Peak Time" wording banks put directly in the
    job title instead."""
    out = []
    for j in jobs:
        hay = f"{j['title']} {j.get('time_type', '')}".lower()
        if any(term in hay for term in PART_TIME_TERMS):
            out.append(j)
    return out


# Cities in and immediately around the Dayton, OH metro area (Miamisburg is
# a Dayton suburb); postings are titled by city, not zip radius, so this
# curated list stands in for a real geo-distance lookup.
DAYTON_METRO_CITIES = [
    "miamisburg", "dayton", "kettering", "centerville", "west carrollton",
    "springboro", "franklin", "moraine", "beavercreek", "huber heights",
    "vandalia", "englewood", "trotwood", "west milton", "germantown",
    "carlisle", "oakwood", "riverside", "fairborn", "xenia", "middletown",
    "monroe", "springfield",
]


def filter_near(jobs: list[JobDict], cities: list[str] | None = None) -> list[JobDict]:
    """Keep jobs whose location text mentions one of the given cities.
    Defaults to the Dayton, OH metro area -- several of those city names
    (Springfield, Middletown, Monroe, ...) also exist in other states, so
    the default also requires "OH" in the location text to avoid matching
    e.g. Springfield, IL. Pass an explicit city list to search elsewhere
    without that state check."""
    require_ohio = cities is None
    cities_lower = [c.lower() for c in (cities or DAYTON_METRO_CITIES)]
    out = []
    for j in jobs:
        loc = j.get("location", "").lower()
        if not any(city in loc for city in cities_lower):
            continue
        if require_ohio and not re.search(r"\boh\b", loc):
            continue
        out.append(j)
    return out


def filter_recent(jobs: list[JobDict], max_days_ago: int = 7) -> list[JobDict]:
    """Keep jobs posted within max_days_ago. Jobs with no known posting
    age (posted_days_ago/date_posted absent) are dropped rather than
    assumed recent, since we can't verify the "last week" claim for them."""
    out = []
    for j in jobs:
        days = j.get("posted_days_ago")
        if days is None:
            continue
        if days <= max_days_ago:
            out.append(j)
    return out
