# PT Rates · Twin Cities

**Live:** https://pt-rates.vercel.app

**Competitive Market Analysis.** What everyone in your sector is charging for a given service.

— Aidan, [*Business Prototypes*](https://aidanjude.vercel.app/random/business-prototypes), 2026-10-12. Sibling instance of the same product: [Salon rates](https://github.com/2016judea/salon-rates) (live at https://salon-rates.vercel.app). This one is the physical-therapy sector, where the price is what each insurer pays a clinic per billing code.

A phone-first page for one kind of reader: the owner of an independent physical
therapy clinic, between patients, who wants to know whether an insurer pays them
less than it pays the clinic down the road. Type the clinic name or NPI and the
page says, per payer, *"paid below the market median on N of M codes,"* with the
code-by-code table underneath for the few who scroll.

`grounded: 2026-10-04 — built from Aidan's PT market analysis repo at his request`

## The contract (2026-10-24)

**Live:** https://pt-rates.vercel.app/contract/ · one page per recipient at `/contract/for/<token>/`

A fixed-price engagement for the private sector, off the work behind our AHRQ Healthcare Choice
submission: the buyer's fee schedule against the Minnesota market, per payer and per CPT code, the
dollar gap at their own volume, and a one-page renegotiation case per payer. One engagement = one
billing group (tax ID). BCBS Minnesota and HealthPartners in dollars, UCare in percent of charges;
Medica, UHC, Aetna and Cigna are named on the page as not covered (`DATA_MODEL.md`).

**$2,500, fixed. A hypothesis, set 2026-10-24.** The one published rate card found for the same
work: Contracting Providers charges $5,000 for a review of up to four payer contracts plus one
negotiation, and $2,500 per additional negotiation
(https://contractingproviders.com/services/payer-contract-negotiations, read 2026-10-24). This is
the review and the case without us sitting at the table, so it is priced at their per-contract
add-on. Against the buyer's side: a clinic under a payer's median sits about $4 a visit below it
(see Price below), about $5,000 a year per payer at 1,250 visits; two payers make the fee about a
quarter of one year's gap.

How it sells: `POST /api/checkout` with `{"offer":"contract"}` charges `offer.json` → `contract.price_usd`,
tags the session `metadata.kind=contract` (and `metadata.for=<token>`), and the existing webhook
emails the buyer what happens next plus the full-table password, and sends Aidan a `Sale: CONTRACT`
notice. Same Stripe router registration as the table (`metadata.product=pt-rates`).
Funnel events: `contract_open`, `checkout_open`, `paid` (all with `offer=contract`).

Recipients: `outreach/contract/ledger.csv` (gitignored; name, title, org, email + status, the
record quoted, token). `python3 scripts/build_contract.py` writes `private/bundle/contract.json`
(served one token at a time by `api/contract.js`, never static) and one draft per row to
`outreach/contract/drafts/`. Drafts are not sent from here.

## The paywall

Free: any clinic's own rates against the market, per payer, per code and per visit, plus
four neighbouring clinics; the market's medians and spreads. Paid: the full table, every
clinic and every payer side by side, and your own visit mix priced against all of them.
Same pattern as [msp-house-index](https://github.com/2016judea/msp-house-index).

`site/` ships only aggregates (`data/market.json`) and the clinic directory. Every clinic's own
rates live in `private/payers/` (gitignored); `scripts/build_public.py` bundles them into
`private/bundle/`, which `scripts/deploy.py` uploads as `api/_full/`, read by the functions only.

| route | does |
|---|---|
| `GET /api/preview?clinic=<id>` / `?for=<token>` | one clinic's own rates plus four neighbours' (the free slice) |
| `POST /api/checkout` | Stripe embedded Checkout at the price in `site/offer.json`; mints the buyer's password |
| `POST /api/stripe-webhook` | emails the password (Mailgun) once per session, and a sale notice to Aidan |
| `GET /api/session-status` | the return page's check; sends the password if the webhook has not |
| `GET /api/data` | password in `x-password`: the full table |

`/for/<token>/` opens on one clinic; tokens come from `outreach/round1/ledger.csv` (gitignored,
names and addresses never ship). Funnel events, to Vercel and PostHog: `preview_open`,
`lock_click`, `checkout_open`, `paid`, `unlock`. Lost password: `python3 scripts/fulfil.py <session>`;
a free copy: `python3 scripts/issue_password.py "comp:<label>"` (then redeploy so the label logs).
Vercel env: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ACCESS_SECRET`, `MAILGUN_*`, `SITE_URL`.

The per-clinic payer files were public in `site/data/payers/` until 2026-10-15 and are still in
this repo's git history before that commit.

## Price

**$500, once. A hypothesis, set 2026-10-15, not a finding.** A clinic under its payer's median sits
a median $2.67 (HealthPartners) to $5.02 (BCBS) a 45-minute visit below it (measured from
`private/payers/` that day). Call it $4. A three-therapist clinic sees about 7,500 visits a year
(3 x ~10 a day x 250 days); if one payer is a sixth of them, 1,250 visits x $4 = $5,000 a year from
closing the gap in one renegotiation. A tenth of that is $500. The sibling msp-house-index drew 10
checkouts and 0 payments at $100 (2026-10-11 to 10-12), so the price is the thing under test.

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

## Per visit (2026-10-13)

The headline is now **what each payer pays for a visit**, not code by code: the people
who negotiate PT contracts reason in dollars per visit against their own cost per visit
(*"If we can't get $81 per visit, then we're losing money"* — a payer-contracting
consultant on StrataPT, cited in `customer-lab/maps/pt-rates.json`). The page prices one
visit per clinic per payer, puts it beside the market's per-visit spread and Medicare, and
takes the owner's cost per visit (pre-filled with that $81 example) to show where a
contract loses money and how much it trails the market per 100 visits.

- **The mix is measured, not chosen.** Codes and proportions are the share of treatment
  units Twin Cities PTs billed Medicare in 2024 (`pipeline/medicare_pull.py` →
  `pipeline/visit_mix.py` → `site/data/visit.json`): 44% exercise, 23% neuromuscular
  re-ed, 15% manual, 14% therapeutic activities, 2% gait, 1% self-care (98% of units).
- **The length is the owner's.** Minutes become units by CMS's 8-minute rule (45 min = 3
  units, the default). Medicare's rows only bound a visit to 1.4–3.3 units, so no number
  is invented for it. Anyone can type their own units per code.
- UCare has no per-visit dollar (percent-of-charges); the page says so.
- Ideal model and what reality fills: `DATA_MODEL.md`. Distribution and sales rules:
  `GO_TO_MARKET.md`.

## What is in, what is not

<!-- payer-table -->
| Payer | Rate rows kept | Twin Cities PT clinics | Codes with 3+ clinics | File dated |
|---|---|---|---|---|
| BCBS Minnesota (Aware Network) | 254,112 | 195 | 39 | 2026-07-27 |
| HealthPartners | 4,060,908 | 134 | 39 | 2026-10-01 |
| UCare | 235 | 23 | 5 | 2026-09-16 |

278 clinics in the search box, from 4,812 NPPES PT/PTA records. Built 2026-10-14.
<!-- /payer-table -->

Not in, and why (each cost a day to learn in Feb 2026):

| Payer | Why not |
|---|---|
| UnitedHealthcare | NPIs appear in its files, but none are linked to PT rate entries. |
| Medica | HealthSparq portal with bot protection. |
| Aetna | HealthSparq portal; national file structure. |
| Cigna | CAPTCHA in front of the file list. |
| Humana | Bot protection and CAPTCHA. |
| Medicaid | Published separately by Minnesota DHS in another format. (Medicare is on the page as a per-visit reference line, from CMS's 2024 billing data.) |

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
| CMS Medicare Physician & Other Practitioners by Provider and Service (data.cms.gov dataset `92396110-…`) | the visit mix and the Medicare reference line | 2024 |

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
  - `private/payers/<payer>.json` — market stats per code + one rate per clinic per code (gitignored; served by `/api/data` behind the paywall, see "The paywall")
  - `site/data/market.json` — the public aggregates `scripts/build_public.py` derives from them
- `site/` is static plus five small functions (`site/api/`). No database at request time; the page fetches one payer
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

Build of 2026-10-04 (evening): all 19 HealthPartners networks and all 342 BCBS
parts are ingested. Networks 7–19 added rate rows but no new Twin Cities clinic;
the slices keep BCBS's Aware network only (see above), so the BCBS counts did
not move when the other 13 groups landed.

If a HealthPartners URL 404s, bump the `YYYY-MM-01` prefix in
`config/payers.yaml` to the current month — the blob store keeps only the latest
month (Feb's files were gone by Oct 2026). If BCBS's index 403s, the newest
`mktg.bluecrossmn.com/mrf/2026/<YYYY-MM-01>_..._index.json` that answers 200 is
the one to pass as `--index` (2026-09-01 on 2026-10-04; the 2026-10-01 file was
not yet public).

## Next build

The vision is *everyone in your sector*. Today that means Twin Cities PT clinics on three
payers; each new sector is a new instance of the same product (Salon rates is the second).
UnitedHealthcare, Medica, Aetna, Cigna and Humana are the PT gaps listed above.

## Not this

An AI intake agent for the clinic was considered and killed on 2026-08-23 for
four independent reasons. This page is rates only.

MIT.
