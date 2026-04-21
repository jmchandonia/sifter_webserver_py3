# SIFTER Webserver Python 3 Migration

This repository contains the Python 3 / modern deployment version of the historical SIFTER webserver that serves `https://sifter.berkeley.edu`.

It is not the original large-scale SIFTER pipeline repository. This repo contains the web application, deployment configuration, and migration work needed to run the public SIFTER site on a modern Ubuntu server with Apache2, Gunicorn, Celery, Redis, Solr, and `uv`.

## What This Repository Contains

- the migrated Django web application for the SIFTER website
- compatibility code for preserved historical SQLite databases and result artifacts
- deployment examples for Apache2 and systemd
- local validation and smoke-test scripts

## Upstream Brenner Lab SIFTER Repository

The original Brenner Lab SIFTER pipeline repository is:

- https://github.com/BrennerLab/SIFTER

That upstream repository contains the large-scale SIFTER pipeline itself. This repository is focused on the webserver and deployment environment used to publish and serve precomputed SIFTER predictions.

## Live Site

- https://sifter.berkeley.edu

## Deployment Notes

The current deployment runbook for Ubuntu 24 is in:

- [`docs/deployment-ubuntu24.md`](docs/deployment-ubuntu24.md)

Example Apache and systemd files are in:

- [`deploy/apache/sifter.conf`](deploy/apache/sifter.conf)
- [`deploy/systemd/sifter-gunicorn.service`](deploy/systemd/sifter-gunicorn.service)
- [`deploy/systemd/sifter-celery.service`](deploy/systemd/sifter-celery.service)

## Important Scope

This repository intentionally does not include runtime secrets or the large production data bundle. The deployed site depends on preserved runtime data such as:

- SQLite databases under `my_dbs`
- job input/output artifact directories
- legacy media/download assets

Those runtime files should be managed on the deployment host, not committed here.
