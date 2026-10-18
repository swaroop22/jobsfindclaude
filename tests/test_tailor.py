from jobtool import tailor


def test_analyze_full_coverage_when_all_keywords_present():
    resume = "Experienced medical coder skilled in icd-10 and cpc certification."
    job = "Medical coder icd-10 cpc certification."
    result = tailor.analyze(resume, job, top_n=5)
    assert result["coverage"] == 100.0
    assert result["missing"] == []


def test_analyze_reports_missing_keywords():
    resume = "General office administration experience."
    job = "Requires strong python programming and django experience."
    result = tailor.analyze(resume, job, top_n=5)
    assert "python" in result["missing"]
    assert result["coverage"] < 100.0


def test_analyze_empty_job_description_has_zero_coverage():
    result = tailor.analyze("anything", "")
    assert result["coverage"] == 0.0
    assert result["present"] == []
    assert result["missing"] == []


def test_extract_keywords_strips_html_and_stopwords():
    description = "<p>We need a <b>coder</b> for the team who can join and grow.</p>"
    keywords = tailor.extract_keywords(description)
    assert "coder" in keywords
    assert "the" not in keywords
    assert "team" not in keywords
