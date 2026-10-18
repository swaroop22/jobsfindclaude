from jobtool import aggregate


def _job(**overrides):
    base = {
        "source": "workday",
        "company": "acme",
        "title": "Medical Coder",
        "location": "Dayton, OH",
        "url": "https://example.com/1",
        "id": "1",
        "description": "",
    }
    base.update(overrides)
    return base


def test_filter_entry_level_drops_senior_titles():
    jobs = [_job(title="Senior Medical Coder"), _job(title="Medical Coder")]
    result = aggregate.filter_entry_level(jobs)
    assert [j["title"] for j in result] == ["Medical Coder"]


def test_filter_entry_level_drops_level_ii_titles():
    result = aggregate.filter_entry_level([_job(title="Level II Coder")])
    assert result == []


def test_filter_entry_level_keeps_plain_titles():
    result = aggregate.filter_entry_level([_job(title="Medical Coder")])
    assert len(result) == 1


def test_filter_jobs_by_keyword_and_location():
    jobs = [
        _job(id="1", title="Medical Coder", location="Dayton, OH"),
        _job(id="2", title="Software Engineer", location="Dayton, OH"),
        _job(id="3", title="Medical Coder", location="Columbus, OH"),
    ]
    result = aggregate.filter_jobs(jobs, keywords=["coder"], location="dayton")
    assert [j["id"] for j in result] == ["1"]


def test_filter_part_time_matches_title_or_time_type():
    jobs = [
        _job(id="1", title="Part Time Teller"),
        _job(id="2", title="Teller", time_type="Part time"),
        _job(id="3", title="Full Time Teller"),
    ]
    result = aggregate.filter_part_time(jobs)
    assert {j["id"] for j in result} == {"1", "2"}


def test_filter_near_default_requires_ohio_state_code():
    jobs = [
        _job(id="1", location="Springfield, OH"),
        _job(id="2", location="Springfield, IL"),
    ]
    result = aggregate.filter_near(jobs)
    assert [j["id"] for j in result] == ["1"]


def test_filter_near_custom_cities_skip_state_check():
    jobs = [_job(id="1", location="Cincinnati, OH")]
    result = aggregate.filter_near(jobs, cities=["cincinnati"])
    assert [j["id"] for j in result] == ["1"]


def test_filter_recent_drops_jobs_with_unknown_age():
    jobs = [
        _job(id="1", posted_days_ago=2),
        _job(id="2", posted_days_ago=10),
        _job(id="3", posted_days_ago=None),
    ]
    result = aggregate.filter_recent(jobs, max_days_ago=7)
    assert [j["id"] for j in result] == ["1"]


def test_icims_days_ago_parses_iso8601():
    from datetime import datetime, timedelta, timezone

    posted = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
    assert aggregate._icims_days_ago(posted) == 3


def test_icims_days_ago_returns_none_for_missing_or_invalid():
    assert aggregate._icims_days_ago(None) is None
    assert aggregate._icims_days_ago("not-a-date") is None
