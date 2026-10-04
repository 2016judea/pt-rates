#!/usr/bin/env python3
"""Put a name on the TIN groups the roll-up cannot name.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request

HealthPartners publishes rates by individual NPI with the employer's TIN. When
no PT-taxonomy organisation NPI shares that TIN (health systems, hospital
rehab departments, big multi-specialty groups) the clinic would ship as
"Group of 298 therapists". This looks the group's modal NPPES practice address
up in the NPPES registry for ANY organisation (NPI-2) at that address and zip,
and writes pipeline/tin_names.json, which precompute.py reads.

Usage:  .venv/bin/python pipeline/name_tin_groups.py --db <duckdb> [--extra-db ...]
Only TINs not already in tin_names.json are looked up; delete an entry to redo it.
"""
import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import httpx

HERE = Path(__file__).resolve().parent
OUT = HERE / "tin_names.json"
API = "https://npiregistry.cms.hhs.gov/api/"


def norm(a):
    a = re.sub(r"[^A-Z0-9 ]", " ", (a or "").upper())
    a = re.sub(r"\b(SUITE|STE|UNIT|FLOOR|FL|BLDG)\b.*$", "", a)
    a = re.sub(r"\b(STREET)\b", "ST", a); a = re.sub(r"\b(AVENUE)\b", "AVE", a); a = re.sub(r"\b(ROAD)\b", "RD", a)
    a = re.sub(r"\b(DRIVE)\b", "DR", a); a = re.sub(r"\b(BOULEVARD)\b", "BLVD", a); a = re.sub(r"\b(NORTH)\b", "N", a)
    a = re.sub(r"\b(SOUTH)\b", "S", a); a = re.sub(r"\b(EAST)\b", "E", a); a = re.sub(r"\b(WEST)\b", "W", a)
    return re.sub(r"\s+", " ", a).strip()


def orgs_in_zip(client, zip5):
    out, skip = [], 0
    while True:
        r = client.get(API, params={"version": "2.1", "postal_code": zip5, "enumeration_type": "NPI-2", "limit": 200, "skip": skip})
        res = r.json().get("results", [])
        out.extend(res)
        if len(res) < 200 or skip >= 1000:
            return out
        skip += 200
        time.sleep(0.1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--extra-db", action="append", default=[])
    a = ap.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    parts = ["SELECT npi, tin FROM rates WHERE tin IS NOT NULL"]
    for i, e in enumerate(a.extra_db):
        con.execute(f"ATTACH '{e}' AS x{i} (READ_ONLY)")
        parts.append(f"SELECT npi, tin FROM x{i}.rates WHERE tin IS NOT NULL")
    rows = con.execute("SELECT DISTINCT TRIM(npi), tin FROM (" + " UNION ALL ".join(parts) + ")").fetchall()
    prov = {r[0]: r[1:] for r in con.execute("SELECT npi, provider_type, address_line1, city, zip FROM nppes_providers").fetchall()}
    by_tin = defaultdict(set)
    for npi, tin in rows:
        if npi in prov:
            by_tin[str(tin)].add(npi)
    unnamed = {t: n for t, n in by_tin.items() if not any(prov[x][0] == "Organization" for x in n)}
    known = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = {t: n for t, n in unnamed.items() if t not in known and len(n) >= 2}
    print(f"{len(unnamed)} TIN groups without a PT org NPI; {len(todo)} to look up ({len(known)} cached)")
    cache = {}
    with httpx.Client(timeout=60) as client:
        for tin, npis in sorted(todo.items(), key=lambda kv: -len(kv[1])):
            modal = Counter((norm(prov[n][1]), prov[n][3], prov[n][2]) for n in npis if prov[n][1] and prov[n][3]).most_common(1)
            if not modal:
                known[tin] = None; continue
            (addr, zip5, city), share = modal[0]
            if zip5 not in cache:
                cache[zip5] = orgs_in_zip(client, zip5)
            hits = []
            for r in cache[zip5]:
                loc = next((x for x in r.get("addresses", []) if x.get("address_purpose") == "LOCATION"), {})
                if norm(loc.get("address_1")) == addr:
                    hits.append((r["number"], r["basic"].get("organization_name", ""), (r.get("taxonomies") or [{}])[0].get("desc", "")))
            pick = None
            if hits:
                # prefer a rehab/therapy/clinic/hospital-sounding org; else the first
                pref = [h for h in hits if re.search(r"REHAB|THERAP|CLINIC|HOSPITAL|HEALTH|MEDICAL|ORTHO|SPORTS", h[1].upper())]
                pick = (pref or hits)[0]
            known[tin] = {"name": pick[1], "npi": pick[0], "taxonomy": pick[2], "addr": addr, "city": city, "zip": zip5,
                          "members": len(npis), "at_addr": share} if pick else None
            print(f"  TIN …{tin[-4:]} ({len(npis)} NPIs, {share} at {addr}, {city} {zip5}) -> {known[tin]['name'] if known[tin] else 'no org at that address'}")
            time.sleep(0.1)
    OUT.write_text(json.dumps(known, indent=1, sort_keys=True))
    named = sum(1 for v in known.values() if v)
    print(f"wrote {OUT}: {named}/{len(known)} named")


if __name__ == "__main__":
    main()
