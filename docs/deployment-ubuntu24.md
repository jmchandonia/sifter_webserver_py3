# Ubuntu 24 Deployment Sketch

This is the target layout for the Python 3 migration deployment.

## Runtime Layout

- app code: `/srv/sifter/app`
- environment file: `/etc/sifter/sifter.env`
- data root: `/srv/sifter/data`
- sqlite bundle: `/srv/sifter/data/my_dbs`
- job inputs: `/srv/sifter/data/input`
- job outputs: `/srv/sifter/data/output`
- static collection: `/srv/sifter/static`
- logs: `/var/log/sifter`

## uv Workflow

Example bootstrap commands:

```bash
cd /srv/sifter/app
uv python install 3.12
uv sync
uv run python tools/validate_runtime_layout.py
```

## Services

Recommended service split:

- Apache2 as the public web server
- Gunicorn bound to localhost for Django
- Celery worker for background jobs
- Redis as the Celery broker
- Solr 9.10.x or 10.x if you want the legacy Haystack-backed search index
- outbound HTTPS access to NCBI if you want the legacy remote BLAST sequence search

The sample unit files and Apache vhost live under `deploy/`.

## Notes

- The current live site TLS chain is invalid; the replacement deployment should fix that.
- `my_dbs` must be fully copied and validated before Django startup testing is meaningful.
- The Python 2 baseline uses additional runtime artifacts under `sifter_web/static/media/`; those should be mounted or copied into `/srv/sifter/data/media` as needed rather than committed as source.
- The upgraded app will fall back to direct SQLite-backed ORM search when Solr is unavailable, so the core quick-search routes continue to work without a search daemon.
- Set `SIFTER_ENABLE_SOLR_SEARCH=true` and `SIFTER_SOLR_URL=...` to enable Solr-backed search/autocomplete on the new server.
- Sequence search still uses NCBI's remote BLAST service through BioPython rather than a local BLAST installation. The upgraded parser now accepts both legacy GI-style hits and modern accession-style hits when those can be mapped through `idmap_db`.
