#!/usr/bin/env python3
"""Sanity checks on site/data before a deploy. Exit non-zero on any failure.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request
"""
import json
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "site" / "data"
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


meta = json.loads((DATA / "meta.json").read_text())
clinics = json.loads((DATA / "clinics.json").read_text())
ids = {c["id"] for c in clinics}
check(meta["default_clinic"] in ids, "default clinic missing from clinics.json")
check(len(meta["payers"]) >= 1, "no payers")
total_bytes = 0
for p in meta["payers"]:
    f = DATA / "payers" / f"{p['slug']}.json"
    check(f.exists(), f"missing {f}")
    total_bytes += f.stat().st_size
    d = json.loads(f.read_text())
    check(set(d["clinics"]) <= ids, f"{p['name']}: clinic ids not in clinics.json")
    check(p["clinics"] == len(d["clinics"]), f"{p['name']}: meta clinic count {p['clinics']} != slice {len(d['clinics'])}")
    for code, m in d["market"].items():
        vals = sorted(v[code] for v in d["clinics"].values() if code in v)
        check(len(vals) == m["n"], f"{p['name']} {code}: n {m['n']} != {len(vals)}")
        check(abs(statistics.median(vals) - m["median"]) < 0.011, f"{p['name']} {code}: median mismatch")
        check(vals[0] == m["min"] and vals[-1] == m["max"], f"{p['name']} {code}: min/max mismatch")
        check(m["n"] >= 3, f"{p['name']} {code}: fewer than 3 clinics")
    # the clinic list must only promise payers that actually hold a rate
    for c in clinics:
        has = c["id"] in d["clinics"] and any(k in d["market"] for k in d["clinics"][c["id"]])
        check(has == (p["name"] in c["payers"]), f"{c['id']} payer flag for {p['name']} is wrong")
check(total_bytes < 3_000_000, f"payer slices total {total_bytes:,} bytes; split or trim")
for c in clinics:
    check(c["name"] and c["id"], f"clinic with empty name/id: {c}")

print(f"{len(clinics)} clinics, {len(meta['payers'])} payers, {total_bytes:,} bytes of payer slices")
if fails:
    print("\n".join("FAIL " + f for f in fails[:40]))
    sys.exit(1)
print("ok")
