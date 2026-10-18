# jobtool

A job search assistant. It does **not** auto-submit applications anywhere —
LinkedIn, Indeed, Monster, and Dice all prohibit automated form submission
in their Terms of Service, and doing so risks account bans and produces
low-quality, untailored applications. This tool instead speeds up the
parts of the process that are safe to automate: finding postings, scoring
them against your resume, and tracking status. You still click "Submit"
yourself on each platform.

## Setup

```
pip install -e ".[dev]"
```

(Or `pip install -r requirements.txt` for runtime-only, no dev tooling.)

### Development

```
pytest                # run the test suite
ruff check .          # lint
mypy jobtool          # type-check
```

Set `JOBTOOL_LOG_LEVEL=DEBUG` (or pass `--log-level DEBUG` to any command)
for verbose per-request logging.

Edit `companies.json` to list the companies you want to search:

- Greenhouse: slug from `https://boards.greenhouse.io/<slug>`
- Lever: slug from `https://jobs.lever.co/<slug>`
- Workday: the full careers URL, e.g. `https://r1rcm.wd1.myworkdayjobs.com/R1RCM`
  (visit the company's "Careers" page, click through to the job search page,
  and copy the URL -- it'll contain `.wdN.myworkdayjobs.com/<site>`)
- iCIMS: the base career-site URL, e.g. `https://careers-mrocorp.icims.com`
  (any `<something>.icims.com` careers page)

Most large healthcare employers and RCM/medical-coding firms (hospital
systems, R1 RCM, Ensemble Health Partners, MRO Corp, etc.) run on Workday or
iCIMS rather than Greenhouse/Lever, so those are the most useful sources for
medical coding roles specifically. Use `--medical-coding` on `search` to
filter to coding-related titles/keywords (CPC, ICD-10, HCC, coding
specialist, DRG auditor, etc.) across all sources. For Workday and iCIMS,
which search server-side, this also runs each keyword as a separate query
against their search API rather than filtering client-side.

## Commands

Search public job boards and score against your resume:

```
python -m jobtool.cli search --keywords python backend --location remote --resume resume.md
```

Add `--entry-level` to drop titles with senior/lead/principal/staff/manager/
supervisor/director-level signals (titles with no seniority signal, like a
plain "Medical Coder", are kept):

```
python -m jobtool.cli search --medical-coding --entry-level
```

Results are appended to `data/applications.csv` (status defaults to `found`).

Tailor-check a single job description against your resume:

```
python -m jobtool.cli tailor --resume resume.md --job-description job.txt --title "Backend Engineer" --company Acme
```

Update your tracker after you apply:

```
python -m jobtool.cli status <job_id> applied --notes "applied via company site"
```

List tracked jobs:

```
python -m jobtool.cli list --status found
```

## Notes

- Greenhouse and Lever both expose public, unauthenticated, read-only
  job-board APIs meant for listing a company's own postings -- this is
  within their intended use and does not require login or scraping
  HTML pages.
- The tailor command only reports keyword overlap; it will never
  invent skills or experience for you. Only add a suggested keyword to
  your resume if it reflects real experience.
