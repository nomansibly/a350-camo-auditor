# A350 Fleet Airworthiness Intelligence

A small Python and SQLite demonstration of continuing-airworthiness audit concepts for a fictional A350-900 fleet. It shows relational fleet records, engine EGT margin estimates, life-limited-part threshold checks, directive evidence tracking, composite repair inspection dates, and a terminal report.

## Important scope

All aircraft, engine, repair, directive, and engineering-order records in this project are synthetic examples. They do not describe Finnair or any real operator. Thresholds and maintenance intervals are illustrative placeholders, not certified limits or approved instructions. The project is for software-learning purposes only; it must not be used for maintenance planning, dispatch, release to service, or airworthiness decisions. Always use current approved technical data and the operator's authorized procedures.

## Run

Requires Python 3.10 or later. The demo uses only the Python standard library.

```bash
python a350_camo_auditor.py
```

Choose an audit date:

```bash
python a350_camo_auditor.py --as-of 2026-11-07
```

The script creates an in-memory SQLite database, loads synthetic sample records, checks them against clearly labeled demonstration thresholds, estimates example EGT threshold dates with a simple linear model, and prints a report. No persistent database or external service is required.

## Project structure

- `a350_camo_auditor.py` — runnable demonstration and SQLite schema
- `README.md` — project overview and usage

## Possible extensions

- Replace the in-memory demo data with a validated import pipeline.
- Add unit-aware data validation, audit history, and signed source references.
- Build an optional dashboard after defining an approved data model.
- Add automated checks once the project requirements and verified reference data are settled.

## License

This project is provided under the MIT License. See `LICENSE`.
