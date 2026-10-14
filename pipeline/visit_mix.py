#!/usr/bin/env python3
"""Medicare's own billing -> the visit mix the per-visit view prices (site/data/visit.json).

grounded: 2026-10-13 — the customer map (customer-lab/maps/pt-rates.json) found that the
people who negotiate PT contracts think in dollars per visit against their cost per visit
("If we can't get $81 per visit, then we're losing money"), not code by code.

What a "typical visit" is, and where each part comes from:
  * WHICH codes and in WHAT proportion: the share of timed treatment units each code
    takes in Medicare Part B billing by Twin Cities physical therapists in private
    practice, 2024 (CMS "Medicare Physician & Other Practitioners - by Provider and
    Service", pulled by pipeline/medicare_pull.py). Measured, not chosen.
  * HOW MANY units: a length the reader picks, converted with CMS's 8-minute rule
    (23-37 min = 2 units, 38-52 = 3, 53-67 = 4). Default 45 minutes = 3 units.
    Medicare's own data cannot pin units per visit: its 2024 Twin Cities rows bound it
    only to between 1.4 and 3.3 units (printed when run), because a visit that bills two codes
    is counted once per code.
  * The Medicare reference line: the units-weighted average Medicare ALLOWED amount per
    code for the same providers and year.

Nothing on the page is typed; the page reads this file and lets the reader edit the mix.
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "cache" / "medicare_mn_pt_2024.json"
OUT = HERE.parent / "site" / "data" / "visit.json"
ZIPS = ("550", "551", "552", "553", "554", "556")  # same as meta.json zip_prefixes
TIMED = ["97110", "97112", "97140", "97530", "97116", "97535"]  # >=99% of TC timed units
EVAL = "97161"

rows = [r for r in json.loads(SRC.read_text()) if r["Rndrng_Prvdr_Zip5"][:3] in ZIPS]
units, allowed = collections.Counter(), collections.defaultdict(float)
for r in rows:
    c, n = r["HCPCS_Cd"], float(r["Tot_Srvcs"])
    units[c] += n
    allowed[c] += n * float(r["Avg_Mdcr_Alowd_Amt"])

timed_total = sum(units[c] for c in TIMED)
all_timed = sum(v for c, v in units.items() if c.startswith("97") and c not in ("97161", "97162", "97163", "97164"))
by_npi = collections.defaultdict(dict)
for r in rows:
    by_npi[r["Rndrng_NPI"]][r["HCPCS_Cd"]] = float(r["Tot_Bene_Day_Srvcs"])
lo_visits = sum(max(v.values()) for v in by_npi.values())
hi_visits = sum(sum(v.values()) for v in by_npi.values())
total_units = sum(units.values())

out = {
    "source": "CMS, Medicare Physician & Other Practitioners - by Provider and Service, 2024",
    "source_url": "https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service",
    "who": "physical therapists in private practice, Twin Cities zips " + ", ".join(ZIPS),
    "providers": len(by_npi),
    "timed_units": int(timed_total),
    "coverage": round(timed_total / all_timed, 4),
    "codes": [{"code": c, "share": round(units[c] / timed_total, 4),
               "medicare": round(allowed[c] / units[c], 2)} for c in TIMED],
    "eval": {"code": EVAL, "medicare": round(allowed[EVAL] / units[EVAL], 2)},
    "minutes": [{"min": 30, "units": 2}, {"min": 45, "units": 3}, {"min": 60, "units": 4}],
    "minutes_rule": "CMS 8-minute rule: 23-37 minutes = 2 units, 38-52 = 3, 53-67 = 4",
    "default_minutes": 45,
    "units_per_visit_bounds": [round(total_units / hi_visits, 2), round(total_units / lo_visits, 2)],
    "example_cost": {
        "value": 81,
        "quote": "If we can't get $81 per visit, then we're losing money and we're not gonna do that.",
        "who": "Justin Stiver, rehab payer-contracting consultant, on StrataPT",
        "url": "https://www.stratapt.com/article/how-to-renegotiate-payer-contracts-for-rehab-therapy-clinics-ft-justin-stiver",
    },
}
OUT.write_text(json.dumps(out, indent=1))
print(f"{len(rows)} rows, {len(by_npi)} providers, timed units {int(timed_total):,} "
      f"({out['coverage']:.1%} of all timed PT units)")
print("mix:", {c["code"]: c["share"] for c in out["codes"]})
print("units per visit bounded to", out["units_per_visit_bounds"], "->", OUT)
