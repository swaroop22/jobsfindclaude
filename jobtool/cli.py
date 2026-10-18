"""Job search assistant CLI.

Aggregates postings from public Greenhouse/Lever boards, scores them against
your resume, and tracks status in a CSV. Submitting each application is left
to you -- this tool does not automate form-filling or login flows on any
platform.

Usage:
    python -m jobtool.cli search --keywords python backend --location remote
    python -m jobtool.cli status <job_id> applied --notes "referred by X"
    python -m jobtool.cli list --status found
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from jobtool import aggregate, tailor, tracker
from jobtool.logging_config import configure_logging
from jobtool.models import JobDict

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANIES_PATH = os.path.join(BASE_DIR, "companies.json")
TRACKER_PATH = os.path.join(BASE_DIR, "data", "applications.csv")

MEDICAL_CODING_KEYWORDS = [
    "medical coder", "medical coding", "coding specialist", "coding analyst",
    "coding auditor", "clinical coder", "cpc", "cca", "ccs", "ccs-p", "rhit", "rhia",
    "icd-10", "icd10", "cpt coding", "hcc coding", "risk adjustment coding",
    "outpatient coder", "inpatient coder", "him coder", "revenue cycle coder",
    "certified professional coder", "coding compliance", "coding auditor",
]


def load_companies() -> dict[str, list[str]]:
    with open(COMPANIES_PATH) as f:
        return json.load(f)


def cmd_search(args: argparse.Namespace) -> None:
    companies = load_companies()

    keywords = list(args.keywords)
    workday_search_texts: list[str] | None = None
    icims_search_texts: list[str] | None = None
    if args.medical_coding:
        keywords.extend(MEDICAL_CODING_KEYWORDS)
        # Workday/iCIMS search server-side per-tenant; run the narrower,
        # highest-signal terms as separate queries instead of one big OR.
        server_side_terms = ["medical coder", "medical coding", "coding specialist",
                              "cpc", "icd-10", "risk adjustment coding", "coding auditor"]
        workday_search_texts = server_side_terms
        icims_search_texts = server_side_terms
    elif keywords:
        # Without this, large tenants (e.g. national banks with hundreds of
        # open reqs) only return their first ~200 postings client-side,
        # which can silently miss every match. Search server-side instead.
        workday_search_texts = keywords
        icims_search_texts = keywords

    jobs: list[JobDict] = aggregate.fetch_all(
        companies, workday_search_texts=workday_search_texts,
        icims_search_texts=icims_search_texts,
        fetch_workday_descriptions=bool(args.resume),
        fetch_icims_dates=bool(args.posted_within_days))

    # Workday/iCIMS results are already server-side filtered by the search
    # texts above; re-filtering by title/description keywords would wrongly
    # drop matches whose title doesn't literally contain the search term.
    server_filtered_sources = {"workday", "icims"}
    server_filtered_jobs = [j for j in jobs if j["source"] in server_filtered_sources]
    other_jobs = aggregate.filter_jobs(
        [j for j in jobs if j["source"] not in server_filtered_sources],
        keywords=keywords, location=args.location)
    if args.location:
        server_filtered_jobs = aggregate.filter_jobs(server_filtered_jobs, location=args.location)
    jobs = other_jobs + server_filtered_jobs

    if args.entry_level:
        jobs = aggregate.filter_entry_level(jobs)

    if args.part_time:
        jobs = aggregate.filter_part_time(jobs)

    if args.near is not None:
        jobs = aggregate.filter_near(jobs, cities=args.near or None)

    if args.posted_within_days:
        jobs = aggregate.filter_recent(jobs, max_days_ago=args.posted_within_days)

    resume_text = ""
    if args.resume:
        with open(args.resume, encoding="utf-8") as f:
            resume_text = f.read()

    for j in jobs:
        if resume_text and j.get("description"):
            result = tailor.analyze(resume_text, j["description"])
            j["coverage_pct"] = result["coverage"]
        else:
            j["coverage_pct"] = ""

    added = tracker.upsert_jobs(TRACKER_PATH, jobs)
    print(f"\nFound {len(jobs)} matching jobs, added {added} new to tracker at {TRACKER_PATH}")

    if resume_text:
        jobs_sorted = sorted(jobs, key=lambda j: j.get("coverage_pct") or 0, reverse=True)
        print("\nTop matches by resume keyword coverage:")
        for j in jobs_sorted[:10]:
            print(f"  [{j['coverage_pct']}%] {j['title']} @ {j['company']} "
                  f"({j['source']}) - {j['url']}")


def cmd_tailor(args: argparse.Namespace) -> None:
    with open(args.resume, encoding="utf-8") as f:
        resume_text = f.read()
    with open(args.job_description, encoding="utf-8") as f:
        job_text = f.read()
    result = tailor.analyze(resume_text, job_text)
    print(tailor.format_report(result, job_title=args.title or "", company=args.company or ""))


def cmd_status(args: argparse.Namespace) -> None:
    ok = tracker.set_status(TRACKER_PATH, args.job_id, args.status, notes=args.notes)
    if ok:
        print(f"Updated {args.job_id} -> {args.status}")
    else:
        print(f"No job found with id {args.job_id}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    rows = tracker.load(TRACKER_PATH)
    if args.status:
        rows = [r for r in rows if r["status"] == args.status]
    for r in rows:
        print(f"[{r['id']}] {r['status']:10s} {r['title']} @ {r['company']} "
              f"({r.get('coverage_pct', '')}%) - {r['url']}")
    print(f"\n{len(rows)} jobs shown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job search assistant (no auto-submit)")
    parser.add_argument("--log-level", default=None,
                         help="Logging level (DEBUG, INFO, WARNING, ERROR); "
                              "defaults to $JOBTOOL_LOG_LEVEL or INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Fetch postings and score against your resume")
    p_search.add_argument("--keywords", nargs="*", default=[])
    p_search.add_argument("--location", default=None)
    p_search.add_argument("--resume", default=None, help="Path to resume text/markdown file")
    p_search.add_argument(
        "--medical-coding", action="store_true",
        help="Filter to medical coding roles (CPC, ICD-10, HCC, coding specialist, etc.)")
    p_search.add_argument("--entry-level", action="store_true",
                           help="Exclude titles with senior/lead/manager/director-level signals")
    p_search.add_argument("--part-time", action="store_true",
                           help="Keep only postings whose title/time-type indicates part-time")
    p_search.add_argument("--near", nargs="*", default=None,
                           help="Keep only postings whose location mentions one of these cities "
                                "(defaults to the Dayton, OH metro area if flag given with no "
                                "cities)")
    p_search.add_argument("--posted-within-days", type=int, default=None,
                           help="Keep only postings posted within this many days "
                                "(drops postings whose age can't be determined)")
    p_search.set_defaults(func=cmd_search)

    p_tailor = sub.add_parser("tailor", help="Compare one job description against your resume")
    p_tailor.add_argument("--resume", required=True)
    p_tailor.add_argument("--job-description", required=True)
    p_tailor.add_argument("--title", default=None)
    p_tailor.add_argument("--company", default=None)
    p_tailor.set_defaults(func=cmd_tailor)

    p_status = sub.add_parser("status", help="Update tracker status for a job")
    p_status.add_argument("job_id")
    p_status.add_argument(
        "status", choices=["found", "applied", "interview", "rejected", "offer", "skip"])
    p_status.add_argument("--notes", default=None)
    p_status.set_defaults(func=cmd_status)

    p_list = sub.add_parser("list", help="List tracked jobs")
    p_list.add_argument("--status", default=None)
    p_list.set_defaults(func=cmd_list)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()
