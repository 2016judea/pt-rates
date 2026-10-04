#!/bin/bash
# Rebuild the DuckDB from the payers' Transparency in Coverage files, then
# recompute the static slices the site reads. Idempotent: every ingest script
# skips files already logged in ingestion_log.
#
# grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request
#
# Usage:
#   pipeline/refresh.sh            # NPPES + HealthPartners + UCare + slices
#   pipeline/refresh.sh bcbs       # the slow BCBS group scan + ingest, then slices
#   pipeline/refresh.sh slices     # only recompute site/data from the existing DB
#
# The pipeline itself is Aidan's Physical-Therapy-Market-Analysis repo, cloned to
# $PIPE with the patches in pipeline/patches/ applied (see README "How to refresh").
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PIPE="${PIPE:-$HOME/Desktop/pt-rates-data}"
PY="$PIPE/.venv/bin/python"
mkdir -p "$PIPE/logs"
step="${1:-all}"

if [ "$step" = "all" ]; then
  [ -s "$PIPE/data/rates.duckdb" ] || (cd "$PIPE" && caffeinate -i -s "$PY" scripts/load_mn_nppes.py)
  (cd "$PIPE" && caffeinate -i -s "$PY" -u scripts/ingest_ucare.py)
  (cd "$PIPE" && caffeinate -i -s "$PY" -u scripts/ingest_healthpartners.py)
fi
if [ "$step" = "bcbs" ]; then
  [ -s "$PIPE/data/bcbs_npi_to_groups.json" ] || (cd "$PIPE" && caffeinate -i -s "$PY" -u scripts/scan_bcbs_groups.py)
  (cd "$PIPE" && caffeinate -i -s "$PY" -u scripts/ingest_bcbs_local.py)
fi
(cd "$HERE" && "$PY" pipeline/precompute.py --db "$PIPE/data/rates.duckdb")
