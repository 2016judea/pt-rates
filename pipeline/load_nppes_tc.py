#!/usr/bin/env python3
"""Load Twin Cities PTs / PTAs from the NPPES API into the pipeline's DuckDB.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request

Replaces the pipeline's scripts/load_mn_nppes.py for one reason: the NPPES API
silently clamps `skip` at 1000 and keeps returning the same 200 results, so the
original loader never terminates on a 3-digit zip prefix with more than 1,200
therapists (551 has that many). This pages by 4-digit prefix and splits to
5-digit zips when a query still hits the 1,200 ceiling.

Run from the pipeline clone:  .venv/bin/python <this file>
"""
import json
import sys
import time
from pathlib import Path

import httpx

PIPE = Path.home() / "Desktop" / "pt-rates-data"
sys.path.insert(0, str(PIPE))
from src.storage import RatesDatabase  # noqa: E402

API = "https://npiregistry.cms.hhs.gov/api/"
TAXONOMIES = [("225100000X", "Physical Therapist"), ("225200000X", "Physical Therapy Assistant")]
CEILING = 1200  # limit 200 x skip<=1000


def page(client, postal, tax_desc):
    out, skip = [], 0
    while True:
        r = client.get(API, params={"version": "2.1", "postal_code": postal, "taxonomy_description": tax_desc, "limit": 200, "skip": skip})
        res = r.json().get("results", [])
        out.extend(res)
        if len(res) < 200 or skip >= 1000:
            return out, len(out) >= CEILING
        skip += 200
        time.sleep(0.1)


def fetch(prefixes):
    providers = {}
    with httpx.Client(timeout=60) as client:
        for code, desc in TAXONOMIES:
            for p3 in prefixes:
                queue = [f"{p3}{d}*" for d in range(10)]
                while queue:
                    postal = queue.pop()
                    res, full = page(client, postal, desc)
                    if full and postal.endswith("*") and len(postal) < 6:
                        queue.extend(f"{postal[:-1]}{d}*" for d in range(10))
                        continue
                    for r in res:
                        npi = r["number"]
                        if npi in providers:
                            continue
                        basic = r.get("basic", {})
                        if r.get("enumeration_type") == "NPI-1":
                            name, ptype = f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(), "Individual"
                        else:
                            name, ptype = basic.get("organization_name", ""), "Organization"
                        loc = next((a for a in r.get("addresses", []) if a.get("address_purpose") == "LOCATION"), {})
                        taxes = r.get("taxonomies", [])
                        ptax = next((t for t in taxes if t.get("primary")), taxes[0] if taxes else {})
                        providers[npi] = (npi, name, ptype, ptax.get("code", code), ptax.get("desc", ""), loc.get("address_1", ""),
                                          loc.get("city", ""), loc.get("state", "MN"), (loc.get("postal_code") or "")[:5], loc.get("telephone_number", ""))
                print(f"  {desc} {p3}: {len(providers)} total", flush=True)
    return list(providers.values())


def main():
    cfg = json.loads((PIPE / "data" / "user_config.json").read_text())
    prefixes = cfg["zip_prefixes"]
    print("zip prefixes:", prefixes, flush=True)
    rows = fetch(prefixes)
    db = RatesDatabase()
    db.conn.execute("DELETE FROM nppes_providers")
    db.conn.executemany("INSERT INTO nppes_providers VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    n_org = db.query("SELECT COUNT(*) FROM nppes_providers WHERE provider_type='Organization'")[0][0]
    db.close()
    print(f"loaded {len(rows)} providers ({n_org} organisations)", flush=True)


if __name__ == "__main__":
    main()
