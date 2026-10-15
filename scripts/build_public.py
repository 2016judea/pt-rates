#!/usr/bin/env python3
"""Gate the data: site/ ships the market's aggregates only; every clinic's own rates go to the paid route.

    python3 scripts/build_public.py        # last step of pipeline/refresh.sh

Reads private/payers/<slug>.json (pipeline/precompute.py, gitignored): {payer, market, clinics: {id: {code: rate}}}.

Writes:
  site/data/market.json          per payer: the code medians (already aggregates) and the per-visit
                                 quantiles for each visit length the page offers. No clinic's own rate.
  private/bundle/full.json.gz    every payer file, served by /api/data behind the password and read by
                                 /api/preview for one clinic and its neighbours
  private/bundle/for.json        {token: clinic id} from outreach/round1/ledger.csv, so /for/<token>/
                                 opens on the recipient's own clinic without the list ever being public

scripts/deploy.py uploads private/bundle/ as api/_full/, readable by the functions only.
"""
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV, DATA, BUNDLE = ROOT / "private" / "payers", ROOT / "site" / "data", ROOT / "private" / "bundle"
LEDGER = ROOT / "outreach" / "round1" / "ledger.csv"
dump = lambda o: json.dumps(o, separators=(",", ":"))

meta = json.loads((DATA / "meta.json").read_text())
visit = json.loads((DATA / "visit.json").read_text())
payers = {p["slug"]: json.loads((PRIV / f"{p['slug']}.json").read_text()) for p in meta["payers"]}


def quant(s, p):  # same as quant() in site/index.html
    i = (len(s) - 1) * p
    lo, hi = int(i), -(-i // 1)
    hi = int(hi)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def per_visit(rates, units):
    t = 0.0
    for code, n in units.items():
        if not n:
            continue
        if rates.get(code) is None:
            return None
        t += n * rates[code]
    return t


market = {}
for slug, d in payers.items():
    vm = {}
    for m in visit["minutes"]:
        units = {k["code"]: m["units"] * k["share"] for k in visit["codes"]}
        vals = sorted(v for v in (per_visit(r, units) for r in d["clinics"].values()) if v is not None)
        if len(vals) >= 3:
            vm[str(m["min"])] = {"median": quant(vals, .5), "p25": quant(vals, .25), "p75": quant(vals, .75),
                                 "min": vals[0], "max": vals[-1], "n": len(vals)}
    market[slug] = {"payer": d["payer"], "market": d["market"], "visit_market": vm, "clinics_n": len(d["clinics"])}
(DATA / "market.json").write_text(dump(market))

BUNDLE.mkdir(parents=True, exist_ok=True)
(BUNDLE / "full.json.gz").write_bytes(gzip.compress(dump({"built": meta["built"], "payers": payers}).encode(), 9))

ids = {c["id"] for c in json.loads((DATA / "clinics.json").read_text())}
tokens = {}
if LEDGER.exists():
    for r in csv.DictReader(LEDGER.open()):
        if r.get("token") and r.get("record_id") in ids:
            tokens[r["token"]] = r["record_id"]
(BUNDLE / "for.json").write_text(dump(tokens))
assert not (DATA / "payers").exists(), "site/data/payers/ must not exist: the full rates never ship statically"
print(f"market.json: {len(market)} payers · bundle: {sum(len(d['clinics']) for d in payers.values())} clinic-payer rows · {len(tokens)} /for/ tokens")
