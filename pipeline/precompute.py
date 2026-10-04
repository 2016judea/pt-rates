#!/usr/bin/env python3
"""DuckDB -> the static JSON slices the site reads.

grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request

Every number on the page comes out of here. Nothing is typed by hand downstream.

Rules carried over from the Feb 2026 work (they cost a week):
  * HealthPartners bills by Type 1 (individual) NPI only; UCare by Type 2 (org)
    only; BCBS MN by both.  Everything is rolled up to a CLINIC before any
    median is taken, or a three-DPT clinic is counted three times.
  * The payer is always an axis.  No blended number is ever produced.
  * Clinic rate = median of the DISTINCT negotiated rates seen for that clinic's
    NPIs, per payer, per code (the same fee schedule repeats across networks).

Clinic roll-up, in order:
  1. pipeline/npi_groups.json overrides (individual NPI -> org NPI)
  2. an organisation NPI that shares the individual's TIN in the rate files
  3. an organisation NPI at the same NPPES practice address (line 1 + zip)
  4. otherwise the TIN itself is the clinic (a group with no PT-taxonomy org NPI)
  5. otherwise the individual is a solo clinic under their own name
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "site" / "data"
PIPE = Path.home() / "Desktop" / "pt-rates-data"

DEFAULT_CLINIC = "1073185393"  # Maverick Physiotherapy, Saint Paul

# What the pipeline cannot ingest, and why. Static because it describes the
# absence of data; the README repeats it.
EXCLUDED = [
    {"payer": "UnitedHealthcare", "why": "NPIs appear in its files but none are linked to PT rate entries."},
    {"payer": "Medica", "why": "Files sit behind a HealthSparq portal with bot protection."},
    {"payer": "Aetna", "why": "HealthSparq portal; national file structure."},
    {"payer": "Cigna", "why": "CAPTCHA in front of the file list."},
    {"payer": "Humana", "why": "Bot protection and CAPTCHA."},
    {"payer": "Medicare / Medicaid", "why": "Published separately by CMS and DHS in other formats."},
]

KEEP_TYPES = ("negotiated", "fee schedule")
KEEP_CLASS = ("professional",)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def titlecase(name):
    if not name:
        return name
    if name.isupper() or name.islower():
        small = {"of", "and", "the", "for", "at", "in", "on", "llc", "pllc", "pa", "pc", "ltd", "inc"}
        words = []
        for w in name.lower().split():
            if w in {"llc", "pllc", "pa", "pc", "ltd", "inc", "pt", "dpt", "ot"}:
                words.append(w.upper())
            elif w in small and words:
                words.append(w)
            else:
                words.append(w.capitalize())
        return " ".join(words)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(PIPE / "data" / "rates.duckdb"))
    ap.add_argument("--pipe", default=str(PIPE))
    args = ap.parse_args()
    pipe = Path(args.pipe)

    codes_cfg = yaml.safe_load((pipe / "config" / "cpt_codes.yaml").read_text())["cpt_codes"]
    codes = list(dict.fromkeys(codes_cfg))  # config order, duplicates dropped
    gloss = json.loads((HERE / "cpt_gloss.json").read_text())
    overrides = json.loads((HERE / "npi_groups.json").read_text()) if (HERE / "npi_groups.json").exists() else {}

    con = duckdb.connect(args.db, read_only=True)

    types = con.execute("SELECT negotiated_type, billing_class, COUNT(*) FROM rates GROUP BY 1,2 ORDER BY 3 DESC").fetchall()
    print("negotiated_type x billing_class:", types)

    prov = {r[0]: {"name": r[1], "type": r[2], "addr": (r[3] or "").strip().upper(), "city": r[4], "zip": r[5]}
            for r in con.execute("SELECT npi, provider_name, provider_type, address_line1, city, zip FROM nppes_providers").fetchall()}

    rows = con.execute(f"""
        SELECT payer_name, TRIM(npi), billing_code, negotiated_rate, tin, last_updated, file_source
        FROM rates
        WHERE billing_code IN ({",".join("?" * len(codes))})
          AND lower(coalesce(negotiated_type,'negotiated')) IN {KEEP_TYPES}
          AND (billing_class IS NULL OR billing_class = '' OR lower(billing_class) IN {KEEP_CLASS})
    """, codes).fetchall()
    print(f"{len(rows):,} rate rows kept")

    # --- TIN per NPI (most common), orgs per TIN, orgs per address -------------
    tin_votes = defaultdict(Counter)
    for payer, npi, code, rate, tin, lu, src in rows:
        if tin:
            tin_votes[npi][str(tin)] += 1
    npi_tin = {n: c.most_common(1)[0][0] for n, c in tin_votes.items()}
    orgs_by_tin = defaultdict(set)
    for n, t in npi_tin.items():
        if prov.get(n, {}).get("type") == "Organization":
            orgs_by_tin[t].add(n)
    orgs_by_addr = defaultdict(set)
    for n, p in prov.items():
        if p["type"] == "Organization" and p["addr"] and p["zip"]:
            orgs_by_addr[(p["addr"], p["zip"])].add(n)

    def pick_org(cands):
        # the org with the most rate rows, else lowest NPI, for determinism
        return sorted(cands, key=lambda n: (-rate_rows_per_npi.get(n, 0), n))[0]

    rate_rows_per_npi = Counter(r[1] for r in rows)

    clinic_of = {}
    how = Counter()
    for npi in {r[1] for r in rows}:
        p = prov.get(npi)
        if npi in overrides:
            clinic_of[npi] = overrides[npi]; how["override"] += 1; continue
        if p and p["type"] == "Organization":
            clinic_of[npi] = npi; how["org"] += 1; continue
        t = npi_tin.get(npi)
        if t and orgs_by_tin.get(t):
            clinic_of[npi] = pick_org(orgs_by_tin[t]); how["tin->org"] += 1; continue
        if p and p["addr"] and orgs_by_addr.get((p["addr"], p["zip"])):
            clinic_of[npi] = pick_org(orgs_by_addr[(p["addr"], p["zip"])]); how["addr->org"] += 1; continue
        if t:
            clinic_of[npi] = "t" + hashlib.sha1(t.encode()).hexdigest()[:10]; how["tin-group"] += 1; continue
        clinic_of[npi] = npi; how["solo"] += 1
    print("roll-up:", dict(how))

    # --- distinct rates per clinic / payer / code -----------------------------
    seen = defaultdict(set)      # (payer, clinic, code) -> set(rate)
    members = defaultdict(set)   # clinic -> npis
    payer_meta = {}
    for payer, npi, code, rate, tin, lu, src in rows:
        c = clinic_of[npi]
        seen[(payer, c, code)].add(float(rate))
        members[c].add(npi)
        m = payer_meta.setdefault(payer, {"rows": 0, "last_updated": None, "files": set(), "npis": set()})
        m["rows"] += 1
        m["npis"].add(npi)
        m["files"].add(src.split("#")[0].rsplit("/", 1)[-1].split("?")[0])
        if lu and (m["last_updated"] is None or lu > m["last_updated"]):
            m["last_updated"] = lu

    clinic_rate = {(p, c, k): statistics.median(v) for (p, c, k), v in seen.items()}

    # --- clinic directory -----------------------------------------------------
    def clinic_record(c):
        ms = sorted(members[c])
        p = prov.get(c)
        if p and p["type"] == "Organization":
            kind, name, city, z = "org", titlecase(p["name"]), p["city"], p["zip"]
        elif c.startswith("t"):
            cities = Counter(prov[n]["city"] for n in ms if n in prov)
            city = cities.most_common(1)[0][0] if cities else ""
            z = Counter(prov[n]["zip"] for n in ms if n in prov).most_common(1)[0][0] if cities else ""
            kind, name = "group", f"Group of {len(ms)} therapists"
        else:
            kind, name, city, z = "solo", titlecase(p["name"]) + ", PT" if p else c, (p or {}).get("city", ""), (p or {}).get("zip", "")
        payers = sorted({pp for (pp, cc, kk) in clinic_rate if cc == c})
        return {"id": c, "name": name, "city": titlecase(city or ""), "zip": z or "", "kind": kind,
                "n": len(ms), "npis": ms if kind != "group" else [], "payers": payers}

    clinics = [clinic_record(c) for c in members]
    clinics.sort(key=lambda r: (r["kind"] != "org", r["name"]))
    clinic_ids = {c["id"] for c in clinics}

    # --- per-payer slice --------------------------------------------------------
    payers_out = []
    for payer in sorted(payer_meta):
        market = {}
        by_clinic = defaultdict(dict)
        for (p, c, k), r in clinic_rate.items():
            if p != payer:
                continue
            by_clinic[c][k] = round(r, 2)
        for k in codes:
            vals = sorted(v[k] for v in by_clinic.values() if k in v)
            if len(vals) < 3:
                continue
            q = statistics.quantiles(vals, n=4, method="inclusive")
            market[k] = {"median": round(statistics.median(vals), 2), "p25": round(q[0], 2), "p75": round(q[2], 2),
                         "min": vals[0], "max": vals[-1], "n": len(vals)}
        s = slug(payer)
        (OUT / "payers").mkdir(parents=True, exist_ok=True)
        (OUT / "payers" / f"{s}.json").write_text(json.dumps({"payer": payer, "market": market, "clinics": by_clinic}, separators=(",", ":")))
        m = payer_meta[payer]
        payers_out.append({"name": payer, "slug": s, "rows": m["rows"], "npis": len(m["npis"]), "clinics": len(by_clinic),
                           "codes": len(market), "last_updated": m["last_updated"].isoformat() if m["last_updated"] else None,
                           "files": len(m["files"])})
        print(f"{payer}: {m['rows']:,} rows, {len(m['npis'])} NPIs, {len(by_clinic)} clinics, {len(market)} codes with >=3 clinics")

    meta = {
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "default_clinic": DEFAULT_CLINIC if DEFAULT_CLINIC in clinic_ids else None,
        "zip_prefixes": json.loads((pipe / "data" / "user_config.json").read_text()).get("zip_prefixes", []),
        "codes": [{"code": k, "short": gloss.get(k, {}).get("short", k), "long": gloss.get(k, {}).get("long", "")} for k in codes],
        "payers": payers_out,
        "excluded": EXCLUDED,
        "clinics_total": len(clinics),
        "nppes_providers": len(prov),
        "rollup": dict(how),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    (OUT / "clinics.json").write_text(json.dumps(clinics, separators=(",", ":")))
    print(f"wrote {OUT}: {len(clinics)} clinics, {len(payers_out)} payers, default={meta['default_clinic']}")


if __name__ == "__main__":
    main()
