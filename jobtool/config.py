"""Runtime configuration: file locations, overridable via environment variables.

Centralizing these here (rather than deriving paths ad hoc in ``cli.py``) lets
the tool be deployed with data/config living outside the repo checkout --
e.g. a packaged install pointing ``JOBTOOL_DATA_DIR`` at a persistent volume.
"""
from __future__ import annotations

import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Directory holding mutable runtime data (the application tracker CSV).
#: Override with $JOBTOOL_DATA_DIR, e.g. to point at a persistent volume.
DATA_DIR = os.environ.get("JOBTOOL_DATA_DIR", os.path.join(_REPO_ROOT, "data"))

#: Path to the companies.json source list. Override with $JOBTOOL_COMPANIES_PATH.
COMPANIES_PATH = os.environ.get(
    "JOBTOOL_COMPANIES_PATH", os.path.join(_REPO_ROOT, "companies.json"))

#: Path to the CSV-backed application tracker. Override with $JOBTOOL_TRACKER_PATH.
TRACKER_PATH = os.environ.get(
    "JOBTOOL_TRACKER_PATH", os.path.join(DATA_DIR, "applications.csv"))
