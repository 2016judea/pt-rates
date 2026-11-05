#!/usr/bin/env python3
"""Build the contract offer's per-recipient pages and the first-touch drafts.

Reads   outreach/contract/ledger.csv           (gitignored: names and emails)
        private/payers/*.json, site/data/market.json, site/data/visit.json
Writes  private/bundle/contract.json           token -> the slice /contract/for/<token>/ shows
                                                (uploaded as api/_full/contract.json, read by
                                                api/contract.js only, never a static file)
        outreach/contract/drafts/<NN>-<token>.txt  one email per DRAFT row; never sent from here
        the ledger's `fact` and `page_url` columns, so the draft and the page quote one number

Every number in a draft comes from the same files the page reads. Nothing is typed.
Run: python3 scripts/build_contract.py && python3 scripts/deploy.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "outreach" / "contract" / "ledger.csv"
DRAFTS = ROOT / "outreach" / "contract" / "drafts"
OUT = ROOT / "private" / "bundle" / "contract.json"
SITE = json.loads((ROOT / "site" / "offer.json").read_text())["site"]
PRICE = json.loads((ROOT / "site" / "offer.json").read_text())["contract"]["price_usd"]
SUBSTACK = "https://aidanjude.vercel.app/random/business-prototypes"
MINUTES = "45"

MARKET = json.loads((ROOT / "site" / "data" / "market.json").read_text())
VISIT = json.loads((ROOT / "site" / "data" / "visit.json").read_text())
UNITS = next(m["units"] for m in VISIT["minutes"] if str(m["min"]) == MINUTES)
MIX = {k["code"]: UNITS * k["share"] for k in VISIT["codes"]}  # the market's own code mix, as on /
PAYERS = {s: json.loads((ROOT / "private" / "payers" / f"{s}.json").read_text()) for s in ("bcbs-minnesota", "healthpartners")}
CLINICS = {c["id"]: c for c in json.loads((ROOT / "site" / "data" / "clinics.json").read_text())}


def visit(rates):
    if any(rates.get(c) is None for c in MIX):
        return None
    return sum(n * rates[c] for c, n in MIX.items())


def clinic_slice(cid):
    c = CLINICS[cid]
    payers = []
    for slug, d in PAYERS.items():
        r = d["clinics"].get(cid)
        vm = MARKET[slug].get("visit_market", {}).get(MINUTES)
        v = visit(r) if r else None
        if v is None or not vm:
            continue
        priced = [k for k in r if k in d["market"]]
        vals = [x for x in (visit(rr) for rr in d["clinics"].values()) if x is not None]
        payers.append({
            "payer": d["payer"], "slug": slug, "visit": round(v, 2), "median": round(vm["median"], 2),
            "codes": len(priced), "below": sum(1 for k in priced if r[k] < d["market"][k]["median"]),
            "clinics": vm["n"], "more": sum(1 for x in vals if x > v + 0.005), "same": sum(1 for x in vals if abs(x - v) < 0.005),
            "market": {k: round(vm[k], 2) for k in ("min", "p25", "median", "p75", "max")},
        })
    return {"id": cid, "name": c["name"], "city": c["city"], "payers": payers}


def money(x):
    return f"${x:,.2f}"


def fact_for(row, clinics):
    """One sentence our data adds about the reader's market, derived, never typed."""
    if clinics and clinics[0]["payers"]:
        c = clinics[0]
        p = min(c["payers"], key=lambda p: p["visit"] - p["median"])
        if abs(p["visit"] - p["median"]) < 0.005:
            return (f"In {p['payer']}'s own file, {c['name']} gets {money(p['visit'])} for a 45-minute visit, the same as "
                    f"{p['same'] - 1} other Twin Cities clinics. {p['more']} of the {p['clinics']} get more, and the top one gets {money(p['market']['max'])}.")
        side = "under" if p["visit"] < p["median"] else "over"
        return (f"In {p['payer']}'s own file, {c['name']} gets {money(p['visit'])} for a 45-minute visit. The median Twin Cities clinic gets "
                f"{money(p['median'])}, so that's {money(abs(p['visit'] - p['median']))} {side}, and {p['more']} of {p['clinics']} clinics get more.")
    hp = MARKET["healthpartners"]["visit_market"][MINUTES]
    return (f"In HealthPartners' own file, a 45-minute PT visit pays {money(hp['min'])} at the lowest Twin Cities clinic and "
            f"{money(hp['max'])} at the highest. The median is {money(hp['median'])}. Same visit, same payer, same metro.")


OFFER_LINE = {
    "rcm": ("If one of your clinics has a BCBS Minnesota or HealthPartners renewal coming, I'll build its case: their fee schedule "
            "against every clinic in the same insurer file, per code, and a one-page ask for each payer. ${price:,} fixed per clinic group, "
            "ten business days. The market is open to poke at, no login: {link}"),
    "group": ("I'll put your fee schedule against that market, per payer and per code, and write the case to bring each payer at renewal. "
              "${price:,} fixed, ten business days. Your page, no login: {link}"),
    "wc": ("When a clinic you work with wants its fee schedule checked against the market, I do that for one clinic group: per payer, "
           "per code, and the case for each renewal. ${price:,} fixed. The market's numbers are open, no login: {link}"),
}


def draft(row):
    first = row["name"].split()[0]
    body = [
        f"To: {row['email'] or 'NONE YET'}" + (f"   [{row['email_status']}]" if row["email_status"].startswith("CHECK") else ""),
        f"Subject: {row['subject']}",
        "",
        f"Hi {first},",
        "",
        row["opener"],
        "",
        row["fact"],
        "",
        OFFER_LINE[row["segment"]].format(price=PRICE, link=row["page_url"]),
        "",
        f"Why I build these: {SUBSTACK}",
        "",
        "Best,",
        "Aidan",
        "",
    ]
    return "\n".join(body)


def main():
    rows = list(csv.DictReader(LEDGER.open()))
    pages = {}
    DRAFTS.mkdir(parents=True, exist_ok=True)
    for old in DRAFTS.glob("*.txt"):
        old.unlink()
    n = 0
    for row in rows:
        ids = [i for i in row["clinic_ids"].split(";") if i]
        clinics = [clinic_slice(i) for i in ids if i in CLINICS]
        row["page_url"] = f"{SITE}/contract/for/{row['token']}/"
        row["fact"] = fact_for(row, clinics)
        pages[row["token"]] = {"org": row["org"].split(" (")[0], "segment": row["segment"], "clinics": clinics,
                               "headline": "The market your clients bill into" if row["segment"] == "rcm" else
                                           "The market your files bill into" if row["segment"] == "wc" else "The market you bill into"}
        if row["status"] == "DRAFT":
            n += 1
            (DRAFTS / f"{n:02d}-{row['segment']}-{row['token']}.txt").write_text(draft(row))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pages, separators=(",", ":")))
    with LEDGER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    by = {}
    for r in rows:
        k = (r["segment"], r["status"], r["email_status"].split(":")[0])
        by[k] = by.get(k, 0) + 1
    print(f"{len(pages)} pages -> {OUT.relative_to(ROOT)}; {n} drafts -> {DRAFTS.relative_to(ROOT)}/")
    for k in sorted(by):
        print("  ", *k, by[k])


if __name__ == "__main__":
    main()
