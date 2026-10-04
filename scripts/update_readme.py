#!/usr/bin/env python3
"""Fill the README's payer table and dates from site/data/meta.json so the
README never carries a typed number. Run after precompute.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "site" / "data" / "meta.json").read_text())
rows = ["| Payer | Rate rows kept | Twin Cities PT clinics | Codes with 3+ clinics | File dated |", "|---|---|---|---|---|"]
for p in meta["payers"]:
    net = f" ({', '.join(p['networks'])})" if p.get("networks") and p["name"].startswith("BCBS") else ""
    rows.append(f"| {p['name']}{net} | {p['rows']:,} | {p['clinics']} | {p['codes']} | {p['last_updated'] or 'n/a'} |")
table = "\n".join(rows) + f"\n\n{meta['clinics_total']} clinics in the search box, from {meta['nppes_providers']:,} NPPES PT/PTA records. Built {meta['built']}."
dates = {p["name"]: p["last_updated"] for p in meta["payers"]}
readme = ROOT / "README.md"
s = readme.read_text()
s = re.sub(r"<!-- payer-table -->.*?<!-- /payer-table -->", "<!-- payer-table -->\n" + table + "\n<!-- /payer-table -->", s, flags=re.S)
s = s.replace("__PAYER_TABLE__", "<!-- payer-table -->\n" + table + "\n<!-- /payer-table -->")
s = s.replace("__UCARE_DATE__", f"file dated {dates.get('UCare', 'n/a')}").replace("__BCBS_DATE__", f"file dated {dates.get('BCBS Minnesota', 'n/a')}").replace("__BUILT__", meta["built"])
readme.write_text(s)
print(table)
