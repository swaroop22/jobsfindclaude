"""Pull open postings from public iCIMS career-site job search pages.

iCIMS doesn't expose a documented JSON API like Greenhouse/Lever/Workday, but
every career site publishes the same public, unauthenticated HTML "job
listings" search page (the one a browser loads client-side in an iframe).
This fetches that same page and parses the job cards out of the markup --
no login, no bypassing any access control.

Configure entries in companies.json as the career-site base URL, e.g.:

    "icims": ["https://careers-mrocorp.icims.com"]

(Find it from a company's "Careers" page -- iCIMS-hosted sites live at
<something>.icims.com.)
"""
from __future__ import annotations

import html
import logging
import re
import urllib.parse

from jobtool.http import fetch_html
from jobtool.models import JobDict

logger = logging.getLogger(__name__)

_JOB_CARD_RE = re.compile(
    r'<li class="iCIMS_JobCardItem">.*?</li>', re.S
)
_LOCATION_RE = re.compile(
    r'field-label">Location</span>\s*<span[^>]*>\s*([^<]*?)\s*</span>', re.S
)
_LINK_RE = re.compile(
    r'<a[^>]*href="([^"]*?/jobs/(\d+)/[^"]*)"[^>]*>\s*'
    r'<span class="sr-only field-label">Title</span>\s*<h3[^>]*>\s*([^<]*?)\s*</h3>',
    re.S,
)
_DESCRIPTION_RE = re.compile(
    r'class="col-xs-12 description">([^<]*)</div>', re.S
)
_DATE_POSTED_RE = re.compile(r'"datePosted"\s*:\s*"([^"]+)"')


def fetch_posted_date(job_url: str) -> str | None:
    """iCIMS list pages don't include a posted date; each job's detail page
    embeds one in a JSON-LD <script> block as an ISO 8601 timestamp."""
    page = fetch_html(job_url)
    if not page:
        return None
    m = _DATE_POSTED_RE.search(page)
    return m.group(1) if m else None


def fetch_icims(base_url: str, search_text: str = "", fetch_dates: bool = False) -> list[JobDict]:
    base_url = base_url.rstrip("/")
    company = urllib.parse.urlparse(base_url).netloc.split(".")[0].replace("careers-", "")

    params = {"ss": "1", "in_iframe": "1"}
    if search_text:
        params["searchKeyword"] = search_text
    query = urllib.parse.urlencode(params)
    url = f"{base_url}/jobs/search?{query}"

    page = fetch_html(url)
    if not page:
        return []

    jobs: list[JobDict] = []
    for card in _JOB_CARD_RE.findall(page):
        link_match = _LINK_RE.search(card)
        if not link_match:
            continue
        job_url, job_id, title = link_match.groups()
        job_url = html.unescape(job_url).replace("?in_iframe=1", "")
        loc_match = _LOCATION_RE.search(card)
        desc_match = _DESCRIPTION_RE.search(card)
        jobs.append({
            "source": "icims",
            "company": company,
            "title": html.unescape(title.strip()),
            "location": html.unescape(loc_match.group(1).strip()) if loc_match else "",
            "url": job_url,
            "id": job_id,
            "description": html.unescape(desc_match.group(1).strip()) if desc_match else "",
            "date_posted": fetch_posted_date(job_url) if fetch_dates else None,
        })
    return jobs


def fetch_all(base_urls: list[str], search_texts: list[str] | None = None,
              fetch_dates: bool = False) -> list[JobDict]:
    search_texts = search_texts or [""]
    all_jobs: list[JobDict] = []
    for url in base_urls:
        seen_ids: set[str] = set()
        for text in search_texts:
            logger.info("Fetching iCIMS: %s (search=%r)", url, text)
            for job in fetch_icims(url, search_text=text, fetch_dates=fetch_dates):
                if job["id"] in seen_ids:
                    continue
                seen_ids.add(job["id"])
                all_jobs.append(job)
    return all_jobs
