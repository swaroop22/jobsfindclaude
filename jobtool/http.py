"""Shared HTTP plumbing for the Greenhouse/Lever/Workday/iCIMS fetchers.

All four sources are public, unauthenticated, read-only endpoints -- this
module only centralizes the request/SSL/error-handling boilerplate that was
previously duplicated in each fetcher.
"""
from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Any

from jobtool.exceptions import FetchError

logger = logging.getLogger(__name__)

USER_AGENT = "jobtool/1.0"
DEFAULT_TIMEOUT = 15


def _build_ssl_context() -> ssl.SSLContext | None:
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        logger.warning("Neither truststore nor certifi is installed; using system SSL defaults")
        return None


SSL_CONTEXT = _build_ssl_context()


def fetch_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None) -> Any | None:
    """GET or POST a URL and parse the JSON response.

    Returns None (and logs a warning) on any HTTP/network error, rather than
    raising, so a single unreachable tenant doesn't abort a multi-company run.
    The JSON payload shape varies by API (Greenhouse/Workday return an object,
    Lever returns a top-level array), so the return type is left as Any.
    """
    req_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    data = None
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning("%s -> HTTP %s", url, e.code)
        return None
    except urllib.error.URLError as e:
        logger.warning("%s -> %s", url, e.reason)
        return None
    except json.JSONDecodeError as e:
        raise FetchError(f"Invalid JSON from {url}: {e}", url=url) from e


def fetch_html(url: str, *, headers: dict[str, str] | None = None) -> str | None:
    """GET a URL and return the response body as text, or None on error."""
    req_headers = {"User-Agent": f"Mozilla/5.0 ({USER_AGENT})", **(headers or {})}
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT, context=SSL_CONTEXT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        logger.warning("%s -> HTTP %s", url, e.code)
        return None
    except urllib.error.URLError as e:
        logger.warning("%s -> %s", url, e.reason)
        return None
