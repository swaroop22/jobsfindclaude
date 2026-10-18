from jobtool import tracker


def _job(**overrides):
    base = {
        "id": "1",
        "source": "workday",
        "company": "acme",
        "title": "Medical Coder",
        "location": "Dayton, OH",
        "url": "https://example.com/1",
        "coverage_pct": 80.0,
    }
    base.update(overrides)
    return base


def test_load_returns_empty_list_for_missing_file(tmp_path):
    path = tmp_path / "applications.csv"
    assert tracker.load(str(path)) == []


def test_upsert_jobs_adds_new_and_skips_duplicates(tmp_path):
    path = str(tmp_path / "applications.csv")
    added_first = tracker.upsert_jobs(path, [_job(id="1"), _job(id="2")])
    added_second = tracker.upsert_jobs(path, [_job(id="2"), _job(id="3")])

    assert added_first == 2
    assert added_second == 1
    rows = tracker.load(path)
    assert {r["id"] for r in rows} == {"1", "2", "3"}
    assert all(r["status"] == tracker.DEFAULT_STATUS for r in rows)


def test_upsert_jobs_does_not_overwrite_existing_status(tmp_path):
    path = str(tmp_path / "applications.csv")
    tracker.upsert_jobs(path, [_job(id="1")])
    tracker.set_status(path, "1", "applied", notes="submitted via company site")

    tracker.upsert_jobs(path, [_job(id="1")])

    rows = tracker.load(path)
    row = next(r for r in rows if r["id"] == "1")
    assert row["status"] == "applied"
    assert row["notes"] == "submitted via company site"


def test_set_status_returns_false_for_unknown_id(tmp_path):
    path = str(tmp_path / "applications.csv")
    tracker.upsert_jobs(path, [_job(id="1")])
    assert tracker.set_status(path, "does-not-exist", "applied") is False
