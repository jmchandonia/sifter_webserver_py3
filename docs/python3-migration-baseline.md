# Python 3 Migration Baseline

This repository was tagged as the preserved Python 2 baseline at:

- tag: `working-py2-2026-04-20`
- commit: `c6ed76e`

## Live Site Baseline

Verified on April 20, 2026 against `https://sifter.berkeley.edu`:

- `/` returns `200`
- `/about/` returns `200`
- `/help/` returns `200`
- `/download/` returns `200`
- `/complexity/` returns `200`
- `/search_options/?q=9606` returns `302`

Observed response details:

- server header: `Apache/2.4.7 (Ubuntu)`
- content type: `text/html; charset=utf-8`
- TLS certificate chain is currently invalid and requires `curl -k` for inspection

The live homepage HTML matches the Django templates in this repository:

- Bootstrap-based UI
- `SIFTER Protein Function Prediction` page title
- routes and tabs for protein, species, function, and sequence searches

## Repository State

The copied source tree now includes the Django apps that were missing earlier:

- `term_db`
- `taxid_db`
- `weight_db`

The repository also contains substantial runtime data and artifacts:

- `db.sqlite3`
- `sifter_web/input/`
- `sifter_web/output/`
- `sifter_web/static/media/annotated_trees/`
- large tarballs and SQLite payloads under `sifter_web/static/media/`

These artifacts should not be treated as deployable application source.

## Secrets And Config

Hardcoded Django `SECRET_KEY` values were removed from tracked settings and replaced with:

- `DJANGO_SECRET_KEY`

Current example environment variables are captured in `.env.example`.

## Migration Priorities

1. Port the Django codebase from Python 2 / Django 1.7 idioms to Python 3.
2. Replace `djcelery` integration with modern Celery configuration.
3. Move filesystem paths for DBs and job artifacts behind environment variables.
4. Audit all pickle and compressed-blob usage before changing serialization.
5. Stand up Ubuntu 24.04 deployment using `uv`, Gunicorn, Apache2, and a broker such as Redis.

## Known Gaps

The external database bundle expected by the settings files has not yet been mapped to a final deploy path. The old settings refer to a sibling `my_dbs` directory, but that location has not yet been located in the copied tree.

Before the Python 3 port is runnable, we need to inventory:

- `term_db.sqlite3`
- `weight_db.sqlite3`
- `taxid_db_wP.sqlite3`
- `estimate.sqlite3`
- `idmap_db.sqlite3`
- `pfam_db.sqlite3`
- `sifter_results_cmp_*.sqlite3`
- `sifter_results_cmp_ready_*.sqlite3`

