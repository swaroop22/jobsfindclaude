"""Exception hierarchy for jobtool.

Fetch failures against any single company/source should not abort a run that
spans many companies -- callers catch ``FetchError`` per-source, log it, and
continue with the rest.
"""


class JobToolError(Exception):
    """Base class for all jobtool errors."""


class FetchError(JobToolError):
    """Raised when a request to a job-board API/page fails or returns
    unusable data. Carries the source URL for logging/diagnostics."""

    def __init__(self, message: str, url: str | None = None) -> None:
        super().__init__(message)
        self.url = url


class InvalidCareersUrlError(JobToolError):
    """Raised when a configured careers URL doesn't match the expected
    format for its platform (e.g. a Workday URL missing the pod/tenant)."""
