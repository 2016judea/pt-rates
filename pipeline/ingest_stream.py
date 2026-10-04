#!/usr/bin/env python3
"""Stream-ingest Transparency in Coverage in-network files into the pipeline's DuckDB.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request

Replaces the pipeline's whole-file json.loads() ingesters, which pushed this
24 GB Mac 11 GB into swap on the first 700 MB HealthPartners network. Streams
with ijson (yajl2_c) in two passes per file:

  pass A  provider_references  -> {group_id: [(npi, tin), ...]} for TARGET NPIs only
  pass B  in_network           -> rates for TARGET codes whose groups hit pass A

Each pass stops as soon as the parser leaves its section. Peak memory is one
in_network item.

Payers:
  hp     HealthPartners: 19 network zips (one .json member each) from config/payers.yaml,
         URLs re-dated to the current month (the blob store keeps only the latest).
  bcbs   BCBS Minnesota: the "Local" .json.gz parts listed in the newest monthly index at
         mktg.bluecrossmn.com/mrf/2026/<YYYY-MM-01>_..._index.json. Since the 2026-09-01
         index these files carry provider_references INLINE (integer ids, NPIs in the
         file), so the pipeline's 27k-file provider-group scan is no longer needed.

Run from the pipeline clone:
  .venv/bin/python <this file> hp [--only N]
  .venv/bin/python <this file> bcbs [--index URL] [--only N]
"""
import argparse
import gzip
import json
import sys
import time
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import ijson

PIPE = Path.home() / "Desktop" / "pt-rates-data"
sys.path.insert(0, str(PIPE))
from src.config import load_cpt_codes, load_payers_config  # noqa: E402
from src.parser import get_target_npis  # noqa: E402
from src.storage import RateRecord, RatesDatabase  # noqa: E402

TMP = PIPE / "data" / "tmp"
BCBS_INDEX_DEFAULT = "https://mktg.bluecrossmn.com/mrf/2026/2026-09-01_Blue_Cross_and_Blue_Shield_of_Minnesota_index.json"
TARGET: set = set()


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def download(url, dest):
    with httpx.stream("GET", url, timeout=httpx.Timeout(30.0, read=900.0), follow_redirects=True) as r:
        r.raise_for_status()
        n = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                n += len(chunk)
    return n


def section_events(stream, section):
    """Yield ijson parse events while inside `section`; stop at the next top-level key."""
    seen = False
    for prefix, event, value in ijson.parse(stream, use_float=True, buf_size=1 << 20):
        if prefix == section or prefix.startswith(section + "."):
            seen = True
            yield prefix, event, value
        elif seen and "." not in prefix and prefix:
            return


def header(stream):
    lu = None
    for prefix, event, value in ijson.parse(stream, use_float=True):
        if prefix == "last_updated_on":
            lu = value
        if prefix in ("provider_references", "in_network"):
            break
    try:
        return date.fromisoformat(lu) if lu else None
    except (ValueError, TypeError):
        return None


def tin_of(pg):
    t = pg.get("tin", {})
    return t.get("value") if isinstance(t, dict) else None


def pass_provider_refs(stream):
    groups = {}
    for pref in ijson.common.items(section_events(stream, "provider_references"), "provider_references.item"):
        gid = pref.get("provider_group_id")
        hits = [(str(n), tin_of(pg)) for pg in pref.get("provider_groups", []) for n in pg.get("npi", []) if str(n) in TARGET]
        if hits and gid is not None:
            groups[gid] = hits
    return groups


def pass_in_network(stream, groups, target_cpts, payer, last_updated, file_source):
    for item in ijson.common.items(section_events(stream, "in_network"), "in_network.item"):
        code = item.get("billing_code", "")
        if code not in target_cpts:
            continue
        for nr in item.get("negotiated_rates", []):
            provs = [p for ref in nr.get("provider_references", []) for p in groups.get(ref, ())]
            if not provs:
                provs = [(str(n), tin_of(pg)) for pg in nr.get("provider_groups", []) for n in pg.get("npi", []) if str(n) in TARGET]
            if not provs:
                continue
            for price in nr.get("negotiated_prices", []):
                rate = price.get("negotiated_rate")
                if rate is None:
                    continue
                sc = price.get("service_code") or []
                for npi, tin in provs:
                    yield RateRecord(payer_name=payer, last_updated=last_updated, billing_code=code,
                                     billing_code_type=item.get("billing_code_type", "CPT"), negotiated_rate=Decimal(str(rate)),
                                     negotiated_type=price.get("negotiated_type", ""), billing_class=price.get("billing_class", ""),
                                     place_of_service=sc[0] if sc else None, npi=npi, tin=tin, file_source=file_source)


def ingest_member(open_stream, db, payer, src, target_cpts):
    """open_stream() returns a fresh binary stream of the JSON each call."""
    log_id = db.log_ingestion_start(payer, src)
    try:
        with open_stream() as f:
            lu = header(f)
        t1 = time.time()
        with open_stream() as f:
            groups = pass_provider_refs(f)
        t2 = time.time()
        batch, inserted = [], 0
        with open_stream() as f:
            for rec in pass_in_network(f, groups, target_cpts, payer, lu, src):
                batch.append(rec)
                if len(batch) >= 20000:
                    inserted += db.insert_rates(batch); batch = []
        if batch:
            inserted += db.insert_rates(batch)
        db.log_ingestion_complete(log_id, inserted)
        log(f"  {len(groups)} groups ({t2-t1:.0f}s) -> {inserted:,} rates ({time.time()-t2:.0f}s)")
        return inserted
    except Exception as e:  # noqa: BLE001
        db.log_ingestion_error(log_id, str(e))
        log("  ERROR", repr(e))
        return 0


def run_hp(db, target_cpts, only):
    cfg = next(p for p in load_payers_config().payers if p.name == "HealthPartners")
    urls = [cfg.index_url] + list(cfg.additional_files or [])
    urls = urls[:only] if only else urls
    total = 0
    for i, url in enumerate(urls, 1):
        name = url.rsplit("/", 1)[-1]
        if db.is_file_ingested(url):
            log(f"network {i}/{len(urls)} skip (ingested) {name}"); continue
        zpath = TMP / "hp.zip"
        t0 = time.time()
        n = download(url, zpath)
        log(f"network {i}/{len(urls)} {name}: {n/1e6:.0f} MB in {time.time()-t0:.0f}s")
        got = 0
        with zipfile.ZipFile(zpath) as zf:
            for m in [m for m in zf.namelist() if m.endswith(".json")]:
                src = f"{url}#{m}"
                if not db.is_file_ingested(src):
                    got += ingest_member(lambda: zf.open(m), db, "HealthPartners", src, target_cpts)
        db.log_ingestion_complete(db.log_ingestion_start("HealthPartners", url), got)
        zpath.unlink(missing_ok=True)
        total += got
    return total


def bcbs_local_urls(index_url):
    r = httpx.get(index_url, timeout=120, follow_redirects=True)
    r.raise_for_status()
    d = r.json()
    urls = sorted({f["location"] for rs in d.get("reporting_structure", []) for f in rs.get("in_network_files", [])
                   if "Local" in f.get("description", "") and f.get("location", "").startswith("http")})
    return urls


def run_bcbs(db, target_cpts, only, index_url):
    urls = bcbs_local_urls(index_url)
    log(f"BCBS index {index_url.rsplit('/',1)[-1]}: {len(urls)} Local files")
    urls = urls[:only] if only else urls
    total = 0
    for i, url in enumerate(urls, 1):
        name = url.rsplit("/", 1)[-1]
        if db.is_file_ingested(url):
            continue
        gz = TMP / "bcbs.json.gz"
        t0 = time.time()
        try:
            n = download(url, gz)
        except Exception as e:  # noqa: BLE001
            db.log_ingestion_error(db.log_ingestion_start("BCBS Minnesota", url), f"download: {e}")
            log(f"file {i}/{len(urls)} {name}: download failed {e!r}"); continue
        log(f"file {i}/{len(urls)} {name}: {n/1e6:.1f} MB in {time.time()-t0:.0f}s")
        total += ingest_member(lambda: gzip.open(gz, "rb"), db, "BCBS Minnesota", url, target_cpts)
        gz.unlink(missing_ok=True)
    return total


def main():
    global TARGET
    ap = argparse.ArgumentParser()
    ap.add_argument("payer", choices=["hp", "bcbs"])
    ap.add_argument("--only", type=int, default=0)
    ap.add_argument("--index", default=BCBS_INDEX_DEFAULT)
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    TARGET = get_target_npis() or set()
    cpts = load_cpt_codes()
    log(f"{len(TARGET)} target NPIs, {len(cpts)} codes")
    db = RatesDatabase()
    total = run_hp(db, cpts, a.only) if a.payer == "hp" else run_bcbs(db, cpts, a.only, a.index)
    log(f"done: {total:,} rates added; total rows {db.get_rate_stats()['total_rates']:,}")
    db.close()


if __name__ == "__main__":
    main()
