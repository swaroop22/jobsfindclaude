"""Central logging setup for the jobtool CLI.

Library modules just call ``logging.getLogger(__name__)`` and log at the
appropriate level; only the CLI entry point calls :func:`configure_logging`
to attach a handler and formatter.
"""
from __future__ import annotations

import logging
import os


def configure_logging(level: str | None = None) -> None:
    level_name = (level or os.environ.get("JOBTOOL_LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
