# Ubuntu 24 Deployment Runbook

This is the tested deployment shape for the migrated SIFTER site on Ubuntu 24.04 with Apache2, Gunicorn, Celery, Redis, Solr, and `uv`.

## Final Layout

- app checkout: `/data/sifter/app`
- env file: `/data/sifter/env/sifter.env`
- sqlite bundle: `/data/sifter/my_dbs`
- job inputs: `/data/sifter/input`
- job outputs: `/data/sifter/output`
- media assets: `/data/sifter/media`
- collected static: `/data/sifter/static`
- Solr home/logs: `/data/sifter/solr`
- uv cache: `/data/sifter/.cache/uv`

The legacy `/data_more/...` runtime tree should be folded into this layout by moving the old DB, input, output, and media files into the corresponding `/data/sifter/...` directories.

## Install Packages

```bash
sudo apt update
sudo apt install -y apache2 redis-server openjdk-21-jre-headless git curl
sudo a2enmod proxy proxy_http headers rewrite expires ssl
```

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo install -m 0755 "$HOME/.local/bin/uv" /usr/local/bin/uv
```

## Create Directories

```bash
sudo mkdir -p /data/sifter/{app,env,my_dbs,input,output,media,static,solr,.cache/uv}
sudo chown -R www-data:www-data /data/sifter
```

## Move Legacy Runtime Files

Move, do not copy, the old runtime files into the final layout:

```bash
sudo mv /old/path/to/my_dbs/* /data/sifter/my_dbs/
sudo mv /old/path/to/input/* /data/sifter/input/
sudo mv /old/path/to/output/* /data/sifter/output/
sudo mv /old/path/to/static/media/* /data/sifter/media/
sudo chown -R www-data:www-data /data/sifter
```

## Clone And Sync

```bash
cd /data/sifter
sudo -u www-data git clone https://github.com/jmchandonia/sifter_webserver_py3.git app
cd /data/sifter/app
sudo -u www-data env UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv sync --group migration
```

`--group migration` is required because `django-haystack`, `pysolr`, and `redis` are in the migration dependency group.

## Environment File

Create `/data/sifter/env/sifter.env`. Do not check secrets into git.

Minimal example:

```bash
DJANGO_SECRET_KEY=replace-me
DJANGO_SETTINGS_MODULE=sifter_web.settings_prod
ALLOWED_HOSTS=sifter.berkeley.edu,testserver,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://sifter.berkeley.edu
SIFTER_TRUSTED_PROXY_IPS=127.0.0.1,::1
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_PROXY_SSL_HEADER_NAME=HTTP_X_FORWARDED_PROTO
SECURE_PROXY_SSL_HEADER_VALUE=https
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=false
SECURE_HSTS_PRELOAD=false
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
SIFTER_DB_DIR=/data/sifter/my_dbs
SIFTER_INPUT_DIR=/data/sifter/input
SIFTER_OUTPUT_DIR=/data/sifter/output
STATIC_ROOT=/data/sifter/static
MEDIA_ROOT=/data/sifter/media
SIFTER_ENABLE_SOLR_SEARCH=true
SIFTER_SOLR_URL=http://127.0.0.1:8983/solr/sifter
SIFTER_BLAST_EXPECT=1e-2
SIFTER_BLAST_HITLIST_SIZE=100
SIFTER_BLAST_MAX_RETRIES=600
SIFTER_BLAST_RETRY_SLEEP=60
```

## Validate Before Services

```bash
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python tools/validate_runtime_layout.py'
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python manage.py check'
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python manage.py collectstatic --noinput'
```

## Eager Smoke Tests

Run smoke tests in eager mode before Redis/Celery are live:

```bash
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && export CELERY_TASK_ALWAYS_EAGER=true CELERY_TASK_EAGER_PROPAGATES=true CELERY_BROKER_URL=memory:// CELERY_RESULT_BACKEND=cache+memory:// && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python tools/smoke_test_sequence_replay.py'
```

The full local smoke test is useful, but in eager mode it can take a long time because the species-wide query runs inline:

```bash
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && export CELERY_TASK_ALWAYS_EAGER=true CELERY_TASK_EAGER_PROPAGATES=true CELERY_BROKER_URL=memory:// CELERY_RESULT_BACKEND=cache+memory:// && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python tools/smoke_test_local.py'
```

## Start Redis

```bash
sudo systemctl enable --now redis-server
sudo systemctl status redis-server
```

## Install Solr 9.10.1

Use the Apache binary release, not an Ubuntu package.

```bash
cd /tmp
curl -LO https://downloads.apache.org/solr/solr/9.10.1/solr-9.10.1.tgz
sudo tar -C /opt -xzf solr-9.10.1.tgz
sudo ln -sfn /opt/solr-9.10.1 /opt/solr
sudo mkdir -p /data/sifter/solr/logs
sudo mkdir -p /opt/solr-9.10.1/server/logs
sudo chown -R www-data:www-data /data/sifter/solr
sudo chown -R www-data:www-data /opt/solr-9.10.1/server/logs
sudo -u www-data env SOLR_LOGS_DIR=/data/sifter/solr/logs /opt/solr/bin/solr start -p 8983 -s /data/sifter/solr
sudo -u www-data env SOLR_LOGS_DIR=/data/sifter/solr/logs /opt/solr/bin/solr create_core -c sifter
```

Rebuild the index:

```bash
sudo -u www-data bash -lc 'cd /data/sifter/app && set -a && source /data/sifter/env/sifter.env && set +a && UV_CACHE_DIR=/data/sifter/.cache/uv /usr/local/bin/uv run python manage.py rebuild_index --noinput'
```

## Systemd Units

The checked-in examples live under `deploy/systemd/`.

- [deploy/systemd/sifter-gunicorn.service](/scratch/jmc/sifter/deploy/systemd/sifter-gunicorn.service:1)
- [deploy/systemd/sifter-celery.service](/scratch/jmc/sifter/deploy/systemd/sifter-celery.service:1)

Install them:

```bash
sudo cp /data/sifter/app/deploy/systemd/sifter-gunicorn.service /etc/systemd/system/
sudo cp /data/sifter/app/deploy/systemd/sifter-celery.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sifter-gunicorn
sudo systemctl enable --now sifter-celery
```

## Apache

The checked-in vhost example lives at `deploy/apache/sifter.conf`.

Important hardening note:

- do not publish `/data/sifter/output` directly through Apache
- `/downloads/...` should be proxied to Django so only the explicit text download endpoints are reachable

Install it:

```bash
sudo cp /data/sifter/app/deploy/apache/sifter.conf /etc/apache2/sites-available/sifter.conf
sudo a2dissite 000-default.conf
sudo a2ensite sifter.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

## Final Checks

```bash
curl -sS http://127.0.0.1:8983/solr/admin/info/system?wt=json | head
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1/
```

Then verify publicly:

- `/`
- `/search/?q=654924`
- `/predictions/?protein=001R_FRG3G`
- one real sequence submission to confirm outbound NCBI BLAST access

## Notes

- Sequence search still uses NCBI's remote BLAST service through BioPython, not a local BLAST install.
- The upgraded parser accepts both legacy GI-style hits and newer accession-style hits when those map through `idmap_db`.
- The upgraded app can fall back to direct ORM-backed search when Solr is unavailable, but keeping Solr enabled preserves the old site's search behavior more closely.
