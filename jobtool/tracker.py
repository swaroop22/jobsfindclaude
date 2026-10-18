"""CSV-backed application tracker."""
from __future__ import annotations

import csv
import logging
import os

from jobtool.models import JobDict

logger = logging.getLogger(__name__)

FIELDS = ["id", "source", "company", "title", "location", "url",
          "coverage_pct", "status", "notes"]

#: Valid values for the tracker's "status" column; shared with the CLI's
#: `status` subcommand so the two can't drift out of sync.
STATUSES = ["found", "applied", "interview", "rejected", "offer", "skip"]

DEFAULT_STATUS = STATUSES[0]

TrackerRow = dict[str, str]


def load(path: str) -> list[TrackerRow]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path: str, rows: list[TrackerRow]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})


def upsert_jobs(path: str, jobs: list[JobDict]) -> int:
    """Add newly-seen jobs to the tracker without duplicating or overwriting status."""
    rows = load(path)
    existing_ids = {r["id"] for r in rows}
    added = 0
    for j in jobs:
        if j["id"] in existing_ids:
            continue
        rows.append({
            "id": j["id"],
            "source": j["source"],
            "company": j["company"],
            "title": j["title"],
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "coverage_pct": str(j.get("coverage_pct", "")),
            "status": DEFAULT_STATUS,
            "notes": "",
        })
        added += 1
    save(path, rows)
    logger.info("Added %d new job(s) to tracker at %s", added, path)
    return added


def set_status(path: str, job_id: str, status: str, notes: str | None = None) -> bool:
    rows = load(path)
    updated = False
    for r in rows:
        if r["id"] == job_id:
            r["status"] = status
            if notes is not None:
                r["notes"] = notes
            updated = True
    if updated:
        save(path, rows)
    return updated
