# SIFTER Webserver Python 3 Migration

This repository contains the Python 3 / modern deployment version of the historical SIFTER webserver that serves `https://sifter.berkeley.edu`.

It is not the original large-scale SIFTER pipeline repository. This repo contains the web application, deployment configuration, and migration work needed to run the public SIFTER site on a modern Ubuntu server with Apache2, Gunicorn, Celery, Redis, Solr, and `uv`.

This webserver upgrade and deployment modernization were carried out at the direction of the current repository owner.

## Provenance

The Python 3 migration and deployment modernization in this repository were carried out on April 20, 2026 using OpenAI Codex in a local Codex CLI environment:

- Codex CLI version: `codex-cli 0.119.0`
- agent/runtime: GPT-5-based Codex coding agent
- working style: local repository edits, iterative validation, and live-site verification against `https://sifter.berkeley.edu`

For practical replication, the useful pieces are:

- the archival Python 2 baseline tag: `working-py2-2026-04-20`
- the Python 3 migration and deployment commits in this repository history
- the Ubuntu 24 deployment runbook in [`docs/deployment-ubuntu24.md`](docs/deployment-ubuntu24.md)
- the checked-in Apache and systemd service files under [`deploy/`](deploy)

The migration work preserved the historical SQLite-backed result databases and adapted the webserver to run on a modern Ubuntu stack using Apache2, Gunicorn, Celery, Redis, Solr, and `uv`.

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
