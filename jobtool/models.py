"""Shared type for a single normalized job posting.

Every fetcher (Greenhouse, Lever, Workday, iCIMS) builds one of these dicts
so downstream code (filters, tailoring, the tracker) has a single documented
shape to rely on regardless of source.
"""
from __future__ import annotations

from typing import TypedDict


class JobDict(TypedDict, total=False):
    source: str
    company: str
    title: str
    location: str
    url: str
    id: str
    description: str
    coverage_pct: float | str
    posted_days_ago: int | None
    time_type: str
    date_posted: str | None
