import pytest

from jobtool import workday
from jobtool.exceptions import InvalidCareersUrlError


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Posted Today", 0),
        ("Posted Yesterday", 1),
        ("Posted 3 Days Ago", 3),
        ("Posted 30+ Days Ago", 30),
        ("", None),
        (None, None),
        ("garbage", None),
    ],
)
def test_parse_posted_days(text, expected):
    assert workday.parse_posted_days(text) == expected


def test_parse_careers_url_extracts_tenant_pod_site():
    tenant, pod, site = workday.parse_careers_url(
        "https://pnc.wd5.myworkdayjobs.com/External")
    assert (tenant, pod, site) == ("pnc", "wd5", "External")


def test_parse_careers_url_handles_locale_prefix():
    tenant, pod, site = workday.parse_careers_url(
        "https://ensemblehp.wd5.myworkdayjobs.com/en-US/EnsembleHealthPartnersCareers")
    assert (tenant, pod, site) == ("ensemblehp", "wd5", "EnsembleHealthPartnersCareers")


def test_parse_careers_url_rejects_non_workday_url():
    with pytest.raises(InvalidCareersUrlError):
        workday.parse_careers_url("https://example.com/jobs")
