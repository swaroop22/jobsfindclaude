"""Compare a job description against a master resume and suggest keyword gaps.

This does not rewrite or auto-submit anything -- it highlights terms from the
posting that are missing or under-represented in the resume, so you can
decide how to phrase your own edits.
"""
from __future__ import annotations

import html
import re
from collections import Counter
from typing import TypedDict


def _strip_html(text: str) -> str:
    text = re.sub(r"<a\b[^>]*href=[\"'][^\"']*[\"'][^>]*>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


STOPWORDS = set("""
a an the and or but if in on at to for of with without from by as is are was
were be been being this that these those it its into over under about
than then so we you your our their they he she his her them will would
can could should must may might not no yes do does did have has had
who what when where why how all any each other some more most across
while within new work team link amp quot nbsp lsquo rsquo ldquo rdquo
join per per-year via etc using use used per get make made href note
please apply jobs grow businesses enterprises
""".split())  # noqa: SIM905 -- multi-line literal is more readable than one long list


def _tokenize(text: str) -> list[str]:
    text = _strip_html(text)
    words = re.findall(r"[a-zA-Z][a-zA-Z+\-.#]{1,}", text.lower())
    return [w.strip(".#-") for w in words if w not in STOPWORDS and len(w) > 2]


def extract_keywords(description: str, top_n: int = 25) -> list[str]:
    counts = Counter(_tokenize(description))
    return [w for w, _ in counts.most_common(top_n)]


class TailorResult(TypedDict):
    coverage: float
    present: list[str]
    missing: list[str]


def analyze(resume_text: str, job_description: str, top_n: int = 25) -> TailorResult:
    resume_terms = set(_tokenize(resume_text))
    job_keywords = extract_keywords(job_description, top_n=top_n)

    present = [k for k in job_keywords if k in resume_terms]
    missing = [k for k in job_keywords if k not in resume_terms]

    coverage = len(present) / len(job_keywords) if job_keywords else 0.0
    return {
        "coverage": round(coverage * 100, 1),
        "present": present,
        "missing": missing,
    }


def format_report(result: TailorResult, job_title: str = "", company: str = "") -> str:
    lines = []
    header = f"Tailoring report: {job_title} @ {company}".strip()
    lines.append(header)
    lines.append(f"Keyword coverage: {result['coverage']}%")
    lines.append(f"Matched ({len(result['present'])}): {', '.join(result['present']) or '-'}")
    lines.append(f"Missing ({len(result['missing'])}): {', '.join(result['missing']) or '-'}")
    lines.append("Suggestion: if a missing term reflects real experience you have, "
                  "work it into your resume/cover letter in your own words. "
                  "Do not add skills you don't actually have.")
    return "\n".join(lines)
