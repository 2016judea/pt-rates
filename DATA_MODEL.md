# Data model — PT Rates, per visit

`grounded: 2026-10-13` — written from the need (BUSINESS.md rule 5) when the customer map
(`customer-lab/maps/pt-rates.json`) showed contract negotiators reason in dollars per visit
against their own cost per visit, not code by code.

## The ideal model (written from the need, before the data)

| Entity | Fields | Question it answers for the owner |
|---|---|---|
| Clinic | id, name, city, NPIs rolled up | Which practice is this? |
| Payer | name, network, file date | Who am I comparing? |
| Rate | clinic × payer × code → $ | What does this payer pay me for this code? |
| Visit mix | code → units per visit, source | What does a typical visit bill? |
| Visit price | clinic × payer → Σ units × rate | What does this payer pay me for a visit? |
| Market | payer → per-visit distribution across clinics (median, quartiles, n) | What does this payer pay everyone else for the same visit? |
| Reference | Medicare per visit, same mix | Am I at 106% or 173% of Medicare? |
| Cost | clinic → $ per visit (owner brings it) | Where do I lose money? |
| Volume | clinic × payer → visits a year (owner brings it) | Which contract costs me the most dollars? |

## Reality, field by field

| Field | Source | Fillable? |
|---|---|---|
| Rate | payer TiC files: BCBS MN (Aware), HealthPartners, UCare | Yes for 3 payers. UHC, Medica, Aetna, Cigna, Humana: no (README). UCare: PT codes are % of charges, so no dollar. |
| Visit mix | CMS Medicare by Provider and Service 2024, Twin Cities PTs (`pipeline/visit_mix.py`) | Proportions yes. Units per visit: Medicare only bounds it to 1.4–3.3, so the owner picks the length (CMS 8-minute rule) or types units. It is Medicare's mix, not commercial; editable for that reason. |
| Visit price, Market | derived in the page from the two rows above | Yes. Spread exists: HealthPartners $61.57–$235.86 for a 45-min visit, median $81.63. |
| Reference | same CMS file, Avg_Mdcr_Alowd_Amt | Yes. |
| Cost | owner input; example $81 is a quoted consultant floor, cited on the page | Owner-supplied by design. |
| Volume | owner input | Not built: shown as dollars per 100 visits instead. |

Verdict: the model fills for the payers we can read. The missing five payers are the
standing gap (README "Next build"); not a reframe.
