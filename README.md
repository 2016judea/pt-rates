# PT Rates · Twin Cities

**Live:** https://pt-rates.vercel.app

A phone-first page for one kind of reader: the owner of an independent physical
therapy clinic, between patients, who wants to know whether an insurer pays them
less than it pays the clinic down the road. Type the clinic name or NPI and the
page says, per payer, *"paid below the market median on N of M codes,"* with the
code-by-code table underneath for the few who scroll.

`grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request`

## Who it was built for

Mason Richlen, DPT, co-owner of [Maverick Physiotherapy](https://www.google.com/search?q=Maverick+Physiotherapy+Saint+Paul)
(155 Eaton St, Saint Paul, inside Los Campeones Gym; org NPI 1073185393). A
three-therapist, direct-access clinic. The page opens on Maverick with nothing
typed; the search box is for the next clinic.

The question this answers was first asked on 25 Jan 2026: *how do people find
out what a payer reimburses under Transparency in Coverage?* The answer became
three CSVs handed over on 2 Feb 2026 (clinic vs every local clinic per code,
payer medians per code, data coverage) plus a markdown list of codes where the
clinic sat below the market median. That last report is the product here. Its
three uses: anchor a fee-schedule negotiation with each payer, prove
underpayment against the local median per code, and show an employer or
workers'-comp case manager what the market actually pays.

## What is in, what is not

__PAYER_TABLE__

Not in, and why (each cost a day to learn in Feb 2026):

| Payer | Why not |
|---|---|
| UnitedHealthcare | NPIs appear in its files, but none are linked to PT rate entries. |
| Medica | HealthSparq portal with bot protection. |
| Aetna | HealthSparq portal; national file structure. |
| Cigna | CAPTCHA in front of the file list. |
| Humana | Bot protection and CAPTCHA. |
| Medicare / Medicaid | Published separately by CMS and DHS in other formats. |

Rules the numbers obey:

- **The payer is always an axis.** In the Feb 2026 data HealthPartners' medians
  were the lowest and BCBS's the highest; a blended number would lie to everyone.
- **Clinic level before any median.** HealthPartners publishes rates by
  individual (Type 1) NPI only, UCare by organisation (Type 2) only, BCBS by
  both. Individuals are rolled up to a clinic first (override map → shared TIN →
  shared NPPES address → TIN group → solo), or a three-therapist clinic is
  counted three times. `pipeline/precompute.py` prints the roll-up tally.
- **One rate per clinic per code per payer** = the median of the distinct rates
  seen for that clinic's NPIs (the same fee schedule repeats across networks).
- **A market median needs at least 3 clinics**, otherwise the code is not shown.
- **Only `negotiated` / `fee schedule` professional rates** are kept.
- **Every number on the page comes from `site/data/`.** Nothing is typed.

## Data sources

| Source | What | Date |
|---|---|---|
| HealthPartners TiC in-network files (`mrfproddestinationdata.blob.core.windows.net/mrf-output/2026-10-01_HealthPartners_*_in-network-rates.zip`) | negotiated rates by individual NPI | file dated 2026-10-01 |
| UCare TiC table of contents (`ucm-p-001.sitecorecontenthub.cloud/.../ucare_toc.json`) | negotiated rates by org NPI | __UCARE_DATE__ |
| BCBS MN index (`mktg.bluecrossmn.com/mrf/2026/2026-01-01_..._index.json`, 645 "Local" files) | negotiated rates by provider group | __BCBS_DATE__ |
| NPPES registry API, taxonomies 225100000X / 225200000X, zips 550, 551, 552, 553, 554, 556 | the provider list and clinic names | pulled __BUILT__ |
| `config/cpt_codes.yaml` in the pipeline repo | the PT CPT codes | — |

Plain-language code names are in `pipeline/cpt_gloss.json`.

## How it is built

```
Physical-Therapy-Market-Analysis (DuckDB)  ──precompute.py──▶  site/data/*.json  ──deploy.py──▶  Vercel
```

- `pipeline/refresh.sh` drives Aidan's
  [Physical-Therapy-Market-Analysis](https://github.com/2016judea/Physical-Therapy-Market-Analysis)
  clone at `~/Desktop/pt-rates-data` (patches in `pipeline/patches/`), then runs
  `pipeline/precompute.py`, which writes:
  - `site/data/meta.json` — payers, counts, file dates, code gloss, the default clinic
  - `site/data/clinics.json` — the search list
  - `site/data/payers/<payer>.json` — market stats per code + one rate per clinic per code
- `site/` is static. No database at request time; the page fetches one payer
  slice at a time.
- `scripts/check_slices.py` recomputes every median from the per-clinic rates
  and fails if `meta.json` disagrees with a slice.
- `scripts/deploy.py` posts `site/` to Vercel over the REST API (project
  `pt-rates`). Needs `VERCEL_TOKEN`.

## How to refresh

```bash
# 0. one-time: the pipeline clone
git clone https://github.com/2016judea/Physical-Therapy-Market-Analysis ~/Desktop/pt-rates-data
cd ~/Desktop/pt-rates-data && uv venv .venv && VIRTUAL_ENV=$PWD/.venv uv pip install -e .
git apply ~/Desktop/pt-rates/pipeline/patches/*.patch        # Oct-2026 HP URLs, tolerant UCare TOC
cp ~/Desktop/pt-rates/pipeline/user_config.json data/        # Twin Cities zips, Maverick as primary

# 1. NPPES + HealthPartners + UCare, then the slices  (~1 h, mostly HP downloads)
~/Desktop/pt-rates/pipeline/refresh.sh

# 2. BCBS MN: provider-group scan then 645 Local files  (2–4 h; runs under caffeinate)
~/Desktop/pt-rates/pipeline/refresh.sh bcbs

# 3. check, deploy
python3 scripts/check_slices.py && VERCEL_TOKEN=... python3 scripts/deploy.py
```

If a HealthPartners URL 404s, bump the `YYYY-MM-01` prefix in
`config/payers.yaml` to the current month — the blob store keeps only the latest
month (Feb's files were gone by Oct 2026).

## Not this

An AI intake agent for the clinic was considered and killed on 2026-08-23 for
four independent reasons. This page is rates only.

MIT.
