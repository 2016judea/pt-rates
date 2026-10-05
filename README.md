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
three-therapist, direct-access clinic. The page opens on Therapy Partners, Inc.
(Saint Paul; a large independent practice that appears in all three payers' files,
so every tab has an answer) with nothing typed; the search box is for any clinic.

The question this answers was first asked on 25 Jan 2026: *how do people find
out what a payer reimburses under Transparency in Coverage?* The answer became
three CSVs handed over on 2 Feb 2026 (clinic vs every local clinic per code,
payer medians per code, data coverage) plus a markdown list of codes where the
clinic sat below the market median. That last report is the product here. Its
three uses: anchor a fee-schedule negotiation with each payer, prove
underpayment against the local median per code, and show an employer or
workers'-comp case manager what the market actually pays.

## What is in, what is not

<!-- payer-table -->
| Payer | Rate rows kept | Twin Cities PT clinics | Codes with 3+ clinics | File dated |
|---|---|---|---|---|
| BCBS Minnesota (Aware Network) | 254,112 | 195 | 39 | 2026-07-27 |
| HealthPartners | 4,060,908 | 134 | 39 | 2026-10-01 |
| UCare | 235 | 23 | 5 | 2026-09-16 |

278 clinics in the search box, from 4,812 NPPES PT/PTA records. Built 2026-10-05.
<!-- /payer-table -->

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
- **Base prices only.** Each NPI/code carries the base rate plus modifier
  variants (`52`/`53` reduced service, `CO`/`CQ` assistant at 85%). Maverick's
  97012 under BCBS read as eight "rates" from $9.73 to $22.88 until the
  modifiers were separated. Modifier prices are tagged at ingest and dropped.
- **BCBS = the Aware network** (its broad commercial PPO, file group
  `000000011`, 31,950 plans cite it). The other 13 BCBS file groups are custom
  or narrow networks (Allina, PEIP, High Value, ...); they are in the DuckDB,
  tagged by network, and not on the page.
- **UCare's PT procedure codes are published as a percentage of charges**
  (65%, institutional), not dollars, so only its dollar-priced codes (97014 and
  the office-visit codes) appear. UCare is in, but it answers little.
- **Every number on the page comes from `site/data/`.** Nothing is typed.

## Data sources

| Source | What | Date |
|---|---|---|
| HealthPartners TiC in-network files (`mrfproddestinationdata.blob.core.windows.net/mrf-output/2026-10-01_HealthPartners_*_in-network-rates.zip`) | negotiated rates by individual NPI | file dated 2026-10-01 |
| UCare TiC table of contents (`ucm-p-001.sitecorecontenthub.cloud/.../ucare_toc.json`) | negotiated rates by org NPI | file dated 2026-09-16 |
| BCBS MN index (`mktg.bluecrossmn.com/mrf/2026/2026-01-01_..._index.json`, 645 "Local" files) | negotiated rates by provider group | file dated 2026-07-27 |
| NPPES registry API, taxonomies 225100000X / 225200000X, zips 550, 551, 552, 553, 554, 556 | the provider list and clinic names | pulled 2026-10-04 |
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

# 1. NPPES + UCare + HealthPartners (19 networks x 700 MB, ~5 min each), then the slices
~/Desktop/pt-rates/pipeline/refresh.sh

# 2. BCBS MN: 342 Local parts from the newest monthly index (~40 s each; Aware is the first 25)
~/Desktop/pt-rates/pipeline/refresh.sh bcbs

# 3. slices only (after any ingest finishes), check, README table, deploy
~/Desktop/pt-rates/pipeline/refresh.sh slices
python3 scripts/check_slices.py && python3 scripts/update_readme.py && VERCEL_TOKEN=... python3 scripts/deploy.py
```

The two big ingests stream with ijson in ~170 MB of memory
(`pipeline/ingest_stream.py`); the pipeline's own ingesters `json.loads()` whole
files and swap the machine. To run both payers at once, write BCBS to a side
file (`ingest_stream.py bcbs --db data/rates_bcbs.duckdb --nppes-db <copy of
rates.duckdb>`) and pass `--extra-db` to `precompute.py`: DuckDB allows one
writer per file. To build slices while an ingest is still writing, copy the
`.duckdb` and its `.wal` and point `--db` at the copy.

Build of 2026-10-04: HealthPartners networks 1–6 (the core Minnesota ones) and
BCBS Aware were in; HP networks 7–19 were still downloading. Step 3 folds them
in when they land.

If a HealthPartners URL 404s, bump the `YYYY-MM-01` prefix in
`config/payers.yaml` to the current month — the blob store keeps only the latest
month (Feb's files were gone by Oct 2026). If BCBS's index 403s, the newest
`mktg.bluecrossmn.com/mrf/2026/<YYYY-MM-01>_..._index.json` that answers 200 is
the one to pass as `--index` (2026-09-01 on 2026-10-04; the 2026-10-01 file was
not yet public).

## Not this

An AI intake agent for the clinic was considered and killed on 2026-08-23 for
four independent reasons. This page is rates only.

MIT.
