"""Pull open postings from public Workday careers-site search APIs.

Workday's job-search endpoint (wday/cxs/<tenant>/<site>/jobs) is the same
public, unauthenticated JSON API that powers the "Search Jobs" box on a
company's own Workday careers page -- no login, no scraping of rendered
HTML, just the same request the browser already makes.

Each Workday tenant lives on a numbered pod (wd1, wd3, wd5, ...). Configure
entries in companies.json as full careers URLs, e.g.:

    "workday": [
        "https://r1rcm.wd1.myworkdayjobs.com/R1RCM"
    ]

The tenant, pod, and site are parsed out of that URL automatically.
"""
from __future__ import annotations

import logging
import re

from jobtool.exceptions import InvalidCareersUrlError
from jobtool.http import fetch_json
from jobtool.models import JobDict

logger = logging.getLogger(__name__)

_POSTED_RE = re.compile(r"Posted\s+(Today|Yesterday|(\d+)\+?\s*Days?\s*Ago)", re.IGNORECASE)

_URL_RE = re.compile(
    r"https?://(?P<tenant>[\w-]+)\.(?P<pod>wd\d+)\.myworkdayjobs\.com/(?:\w\w-\w\w/)?(?P<site>[\w-]+)"
)

PAGE_SIZE = 20


def parse_posted_days(text: str) -> int | None:
    """Parse Workday's postedOn text ("Posted Today", "Posted 3 Days Ago",
    "Posted 30+ Days Ago") into an approximate integer days-ago. Returns
    None if unparseable."""
    if not text:
        return None
    m = _POSTED_RE.search(text)
    if not m:
        return None
    label = m.group(1).lower()
    if label == "today":
        return 0
    if label == "yesterday":
        return 1
    return int(m.group(2))


def parse_careers_url(url: str) -> tuple[str, str, str]:
    m = _URL_RE.search(url)
    if not m:
        raise InvalidCareersUrlError(f"Not a recognizable Workday careers URL: {url}")
    return m.group("tenant"), m.group("pod"), m.group("site")


def fetch_workday(careers_url: str, search_text: str = "", max_pages: int = 10,
                   fetch_descriptions: bool = False) -> list[JobDict]:
    tenant, pod, site = parse_careers_url(careers_url)
    api_url = f"https://{tenant}.{pod}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[JobDict] = []
    offset = 0
    for _ in range(max_pages):
        data = fetch_json(
            api_url, method="POST",
            payload={"limit": PAGE_SIZE, "offset": offset, "searchText": search_text})
        if not data:
            break
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for p in postings:
            path = p.get("externalPath", "")
            description = fetch_job_detail(careers_url, path) if fetch_descriptions and path else ""
            jobs.append({
                "source": "workday",
                "company": tenant,
                "title": p.get("title", ""),
                "location": p.get("locationsText", ""),
                "url": f"https://{tenant}.{pod}.myworkdayjobs.com/{site}{path}",
                "id": path.rsplit("_", 1)[-1] if "_" in path else path,
                "description": description,
                "posted_days_ago": parse_posted_days(p.get("postedOn", "")),
                "time_type": p.get("timeType", ""),
            })
        total = data.get("total", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break
    return jobs


def fetch_job_detail(careers_url: str, external_path: str) -> str:
    """Fetch full description for one posting (Workday search results omit it).
    The detail endpoint is a GET, unlike the search endpoint's POST."""
    tenant, pod, site = parse_careers_url(careers_url)
    api_url = f"https://{tenant}.{pod}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{external_path}"
    data = fetch_json(api_url, headers={"Accept": "application/json"})
    if not data:
        return ""
    return (data.get("jobPostingInfo") or {}).get("jobDescription", "")


def fetch_all(careers_urls: list[str], search_texts: list[str] | None = None,
              fetch_descriptions: bool = False) -> list[JobDict]:
    """search_texts: list of queries to run per tenant (Workday's search API takes
    one query string at a time); results are merged and de-duplicated by id.
    fetch_descriptions: also fetch each posting's full description via a
    per-job detail call (slower -- one extra request per unique posting)."""
    search_texts = search_texts or [""]
    all_jobs: list[JobDict] = []
    for url in careers_urls:
        seen_ids: set[str] = set()
        for text in search_texts:
            logger.info("Fetching Workday: %s (search=%r)", url, text)
            for job in fetch_workday(url, search_text=text, fetch_descriptions=fetch_descriptions):
                if job["id"] in seen_ids:
                    continue
                seen_ids.add(job["id"])
                all_jobs.append(job)
    return all_jobs
