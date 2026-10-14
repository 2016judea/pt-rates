# Go to market — PT Rates

`grounded: 2026-10-13` — written with the per-visit iteration, after the 10/04 batch (51
clinic gift emails, 0 replies) and the customer map `~/Desktop/customer-lab/maps/pt-rates.json`.

**What we are distributing:** a free page that prices a Twin Cities PT clinic's visit, per
payer, against every other clinic in that payer's file, against Medicare, and against the
clinic's own cost per visit. **Goal: visibility, not a sale** (distribution-channel rule 12:
there is no price; Aidan re-sets this if a paid packet appears). Nothing here is sent: every
touch below is a draft for Aidan to read (tenet 12).

## Plays, ranked

Ranked by what vouches for us (distribution-channel § The axiom), then by the forecaster
screen (`customer-lab/lab/screen.py`, AUC 0.86 on 419 real sends; `panel-backtest/RESULTS.md`).

| # | Play | Who vouches | Fan-out | Size | Screen |
|---|---|---|---|---|---|
| 1 | **APTA Minnesota Payor Advocacy Workgroup** — submit a payer issue to the inbox it runs | **Obligation + super user.** Its own page: "Bring your payor or payment issues to the workgroup emailing info@mnapta.org. A member of the workgroup will reply" and it "meets with payors in Minnesota" ([mnapta.org/payor-advocacy-workgroup](https://mnapta.org/payor-advocacy-workgroup/)). The map's owners ask their professional body to act on private rates (`e_a3117df700`). | every MN member clinic | 1 inbox | **P(reply) 10%**, P(click) 30% |
| 2 | **Payer-contracting consultants and PT billing firms** — open on their own published line | **Super user.** They renegotiate on clinics' behalf (`e_c298c1e103`) and sell "payer contract insights" (`e_d562fb610c`); each fronts dozens of clinics and gains a faster case. MN firms that list PT + payer contracting: Medwave (Twin Cities page), Billing Buddies, CapitalMed, Physician Practice Specialists. | 10s of clinics each | 15–25 | **P(reply) 10%**, P(click) 40% |
| 3 | **Independent clinic owners, touch 2** — open on a claim on their own site, then their own per-visit number | **Their own record** (rule 11). Touch 1 on 10/04 opened on the gift and got 0 of 51. | 1 | **≥50 delivered, 3 segments** | P(reply) 7%, P(click) 30% |
| 4 | **Owner communities and practice-management publishers** (Breakthrough, WebPT's blog, owner podcasts) — open on their own negotiation article | **Platform/super user**; owners learn negotiation from them (`e_ba8d71dff1`). National audiences, so the honest offer is "which metro next". | 1,000s | 5–10 | P(reply) 7%, P(click) 20% |

**Floor** (`~/.claude/BUSINESS.md` rule 4): 50 delivered recipients from at least 3 segments.
Play 3 carries it alone: solo/1–3-therapist practices, multi-site independents, and specialty
clinics (pediatric, vestibular, sports/performance). Plays 1, 2 and 4 are super users and are
counted as their own channels (distribution-channel procedure step 6); under 50 they are
**probes**, and silence from them is reported as a probe, never "the idea didn't land".
Spread sends over days: Mailgun allows 100 requests per rolling 24h across every campaign.

## Rules for selling and marketing this product

1. **Lead with dollars per visit against their cost, never "N of M codes".** *Why:* the
   people who negotiate think "If we can't get $81 per visit, then we're losing money"
   (`e_7cf9ef748c`) and track "total per visit costs" (`e_28c228ae55`); the map's surprise.
   The 10/04 batch led with code counts and got 0 of 51.
2. **The first two sentences quote the reader's own public record.** Their workgroup page,
   their podcast line, their own site's claim. *Why:* distribution-channel rule 11, all eight
   yeses ever received opened this way; ~210 touches that opened on us returned one "no".
3. **Every number in a touch is the payer's file times a stated mix, with the date.** Say
   "HealthPartners' October file", "a 45-minute visit", "Medicare allowed, 2024". Never a
   rounded "about", never a model's estimate. *Why:* the owner's open question is "can I show
   this to a payer?" (map, hypothesis); a number with its source is one they can.
4. **Say the mix is Medicare's and theirs to change.** *Why:* the visit mix is measured from
   CMS's Twin Cities PT billing, not commercial claims; Medicare's rows only bound a visit to
   1.4–3.3 units (`site/data/visit.json`). Overclaiming it is the one thing a billing expert
   will catch first.
5. **No price, no buy link, no "book a call" on the page or in a first touch.** A custom cut
   is offered by email only. *Why:* `feedback_price_is_negotiated_not_on_the_tool` (10/10)
   and Aidan's brief, 10/13.
6. **The super user gets their own gain in line one** (the workgroup: evidence for its payer
   meetings; the consultant: their floor tested against a payer's file). *Why:*
   distribution-channel rule 7; the broker pilot worked because the brief won the broker
   the listing.
7. **Independents only. No health systems, hospital outpatient, chiropractors or national
   chains.** *Why:* the 10/04 list sent to Allina, Hennepin Healthcare, NovaCare, Summit
   Orthopedics and four chiropractic offices (`bricks/data/outreach/pt_rates/tokens.csv`);
   they negotiate as systems and are not the customer (`project_pt_rates_prototype`).
8. **Never claim it fixes slow claims or raises a rate.** It shows where a rate sits. *Why:*
   job_map marks claim delays "none" and rate changes "partial".
9. **Three touches before silence counts, reply kinds logged.** Ledger:
   `~/Desktop/bricks/data/outreach/pt_rates/tokens.csv`. *Why:* distribution-channel rule 5.
   Touch 2 must not repeat touch 1 (the gift link + one sentence).
10. **Read use, not the inbox.** Per-clinic links carry `?clinic=`; PostHog + Vercel
    Analytics are on every page. *Why:* "Just because someone didn't respond to my email,
    doesn't mean they aren't using the thing" (`~/.claude/CLAUDE.md`, analytics).

## First-touch drafts (DRAFTS, nothing sent)

Files in `outreach/`. Scores from `screen.py --dry` (forecaster-v1, not logged; 417 scored
sends average 5.0%, so rank these against each other, not against 50%).

### Play 1 — APTA MN Payor Advocacy Workgroup · info@mnapta.org · **P(reply) 10%, P(click) 30%** (above 94% of scored sends)
Subject: A payor issue for the workgroup: what HealthPartners pays per visit
`outreach/1-apta-mn-workgroup.txt`

### Play 2 — Justin Stiver (StrataPT guest; address unverified) · **P(reply) 10%, P(click) 40%** (above 94%)
Subject: Your $81 floor, against HealthPartners' own file
`outreach/2-payer-contracting-consultant.txt`

### Play 3 — Christian, Flexed Mettle, Princeton · christian@flexedmettle.com · **P(reply) 7%, P(click) 30%** (above 82%)
Subject: HealthPartners pays Flexed Mettle less than Medicare for an hour
`outreach/3-clinic-owner.txt` — the template for the 50: line one is a claim from their own
site, line two their own per-visit number for the visit length that claim implies.

### Play 4 — Breakthrough (address unverified) · **P(reply) 7%, P(click) 20%** (above 82%)
Subject: Where $83 a visit lands in the Twin Cities
`outreach/4-owner-community.txt`

## What needs Aidan

Reading and sending. Addresses for plays 2 and 4 are unverified; play 3's 49 other rows need
a site claim each before they are sendable (rule 2).
