#!/bin/bash
# Rebuild the DuckDB from the payers' Transparency in Coverage files, then
# recompute the static slices the site reads. Idempotent: every ingest skips
# files already logged in ingestion_log. DuckDB allows ONE writer, so stages
# run one after another; never start two of these at once.
#
# grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request
#
# Usage:
#   pipeline/refresh.sh            # NPPES + UCare + HealthPartners + slices  (~1.5 h, HP downloads)
#   pipeline/refresh.sh bcbs       # BCBS MN Local files + slices              (2-4 h)
#   pipeline/refresh.sh slices     # only recompute site/data from the existing DB
#
# The pipeline is Aidan's Physical-Therapy-Market-Analysis repo cloned to $PIPE
# with pipeline/patches/ applied (README "How to refresh"). The NPPES loader and
# the two big ingests are replaced by the streaming versions in this directory;
# the pipeline's own json.loads() ingesters do not fit in memory.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PIPE="${PIPE:-$HOME/Desktop/pt-rates-data}"
PY="$PIPE/.venv/bin/python"
mkdir -p "$PIPE/logs" "$PIPE/data"
[ -s "$PIPE/data/user_config.json" ] || cp "$HERE/pipeline/user_config.json" "$PIPE/data/"
step="${1:-all}"

if [ "$step" = "all" ]; then
  [ -s "$PIPE/data/rates.duckdb" ] || (cd "$PIPE" && caffeinate -i -s "$PY" -u "$HERE/pipeline/load_nppes_tc.py")
  (cd "$PIPE" && caffeinate -i -s "$PY" -u scripts/ingest_ucare.py)
  (cd "$PIPE" && caffeinate -i -s "$PY" -u "$HERE/pipeline/ingest_stream.py" hp)
fi
if [ "$step" = "bcbs" ]; then
  (cd "$PIPE" && caffeinate -i -s "$PY" -u "$HERE/pipeline/ingest_stream.py" bcbs)
fi
(cd "$HERE" && "$PY" pipeline/precompute.py --db "$PIPE/data/rates.duckdb")
(cd "$HERE" && python3 scripts/check_slices.py) || true
