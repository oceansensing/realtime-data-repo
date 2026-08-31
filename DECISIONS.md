# Decisions

Dated, irreversible-leaning decisions, one entry each, newest last. The
design lives in `README.md` and the reasoning in `PLAN.md`; this file is the
index of what was decided and when, so a future reader never re-derives
whether a door was walked through.

**Started 2026-08-31**, eighteen days after this repository itself — the
doctrine says every repository carries one and two did not. Every entry
before that date is **reconstructed**, from `README.md`, from the commit log,
and from `oceansensing.github.io/PLAN.md`, which carried this repository's
history before it had a record of its own. They are marked as such.

**A reconstruction is weaker than a decision written the day it was taken**,
and the weakness is specific: a commit message records what was done and
almost never what was rejected. Where the alternative survives below it is
because some document happened to keep it, not because the reconstruction
recovered it.

**What counts as one-way here.** Three shapes, the same ones the model
repositories use, since this is one of them: a decision that puts bytes in
readers' hands under a shape they will code against; a decision about which
repository owns a product, since moving one costs a migration in two places;
and a decision that forecloses an upstream or a fallback. Tuning a threshold
is none of those.

A fourth, particular to a pipeline: **a decision that removes a capability**,
where re-proposing it costs a rebuild and a measurement somebody already
took. D7 is the only one of those so far, and it is here because the argument
for what it removed is genuinely attractive and genuinely settled.

## D1 — 2026-08-14 — Rebuild rather than repair, and the predecessor goes cold

*(Reconstructed 2026-08-31 from `README.md` and the site's `PLAN.md`.)*

This repository replaces `ocean-data-repo`, designed after a night in which
five separate faults each produced a plausible-looking state rather than an
error, and one flaky HTTP 500 froze every product for **16.5 hours**. The
post-mortem's one-line diagnosis — *everything was detected late where it
could have been impossible by construction* — is the design brief, and
`README.md` is where it is spent.

Cutover was 2026-08-14: `MAP_DATA` in the site's `src/config.ts` points here,
after the development map ran against this pipeline first and proved it.

**One-way through disuse rather than through machinery, which is the part
worth recording.** The predecessor was to keep publishing on its own crons as
a warm standby and then be frozen. Its last run was **2026-08-17** and it has
served no status document since, so switching back is still one string in the
site's config — against a tree that gets a day colder every day. This
repository's own README described that standby as live for eleven days after
it had stopped; the doc sweep of 2026-08-28 caught it. **A fallback nobody
exercises is a decision that finished quietly**, and this file exists partly
so the next one does not.

## D2 — 2026-08-14 — Public repository, all rights reserved, and the data was never ours to license

*(Reconstructed 2026-08-31 from `LICENSE.md` and its commit.)*

**This repository is public so the data can be served from GitHub Pages, and
that is not a grant of any license.** The code here is all rights reserved;
the scientific data belongs to the bodies that produced it, each named in
`LICENSE.md` and credited on the map.

Two doors, and neither reopens the same way it closed. Publishing a
repository puts its history somewhere a person can hold a copy of, and
un-publishing it does not retrieve that copy. Granting a license cannot be
withdrawn from anybody who already relied on it, which is why the
conservative half was chosen first and deliberately.

**It is the odd one of its family and the reason is worth stating**: the site
and the engine are private repositories, and this one is not. The distinction
is not a posture, it is what the hosting needed at the time — and it means
anything written here is written in the open, which is a different standard
from the one two of its siblings are held to.

## D3 — 2026-08-14 — The code is the site's; this repository holds declarations and the orchestrator

*(Reconstructed 2026-08-31. Reaffirmed at the rebuild rather than taken
then — the fetch scripts already lived in the site repository, and keeping
them there was a choice made by not making it.)*

The fetchers and the data contract (`schema.ts`) live in
`oceansensing.github.io` and are checked out at run time, pinned to `main`.
This repository owns `pipeline/orchestrate.py`, `pipeline/products.toml`, and
the static half under `map/` that CI cannot rebuild.

**What it buys**: one copy of every fetcher, one contract, and a fetcher fix
that lands on the **next run** rather than on a push here. The rejected
alternative is vendoring, which forks the scripts — and one contract with two
copies drifting apart is exactly the shape the predecessor's five
hand-maintained lists had.

**What it cost, and the cost was paid in full on 2026-08-16**: the checkout
became load-bearing on a repository this workflow holds no grant over. Making
the site private with nothing else in place would fail the next run before it
had fetched anything — not one product going stale, every product. A
read-only deploy key carries it, chosen over a PAT (which would stop this
pipeline dead on its expiry date) and over a GitHub App (more moving parts
for capabilities not wanted here). The ordering trap in `README.md` — the
secret arms the SSH path the moment it exists, so half-configured is worse
than either end — was measured, not reasoned about.

## D4 — 2026-08-14 — The `published` branch is one orphan commit, force-pushed every run

*(Reconstructed 2026-08-31 from `README.md`.)*

Every small product and the status record live on a `published` branch as a
**single orphan commit, force-pushed each run**, so history does not grow.
This is what makes the accumulated state durable — glider tracks, USV tracks,
storm histories, files that cannot be refetched from anywhere — rather than
resident in a cache that can evict, and it is what seeds the stage at clone
speed instead of re-downloading the last publish over HTTP.

**The cost was accepted and is the one-way half: there is no history.**
Yesterday's publish is not recoverable from this repository, and the stage is
seeded from that branch, so a bad publish propagates into the next run's
starting point until something overwrites it.

It is one-way in the strictest sense a git repository offers. Keeping history
cannot be adopted retroactively — the history that was not kept is gone, and
every run since 2026-08-14 has spent it.

## D5 — 2026-08-21 — `status/status.json` is the routing document, at schema 2

*(Reconstructed 2026-08-31 from the commit log — `97ffb23`, `815b721`,
`be96754`.)*

The status document stopped being only a health record and became the thing
the consumer routes on: **`roots` and `modelRun`, at schema 2**, with the
manifest naming every hour a product publishes rather than just its base, and
naming the model, because the site's hour rule cannot group products without
knowing which model they came from.

**Bytes in readers' hands under a shape they code against**, which is the
first of the three tests: the site reads it to learn what this origin serves,
the watchdog reads it to judge whose fault a staleness is, and the map's own
health line reads it too. A schema bump is a migration across every origin at
once, and it lands on readers holding a bundle from before the change.

The general design behind it is the site's D5 — the contract knows *origins*,
not products, and an origin publishes a manifest naming what it serves. This
entry is that decision's obligation on this side.

## D6 — 2026-08-22 — The ESPC currents leave, and the ice stays as a live test

*(Reconstructed 2026-08-31. The full record is `espc-model-repo`'s D1.)*

The ESPC currents move out of this repository into their own: **one upstream,
one fault domain, one gigabyte.** A HYCOM outage must not hold back the
observations, and the observations' failures must not hold back the currents.

**The Navy temperature and salinity stayed behind on storage** — measured
rather than estimated, the combined figure landing at 96% of the 1 GB Pages
cap. **The ice stayed behind deliberately**, as a live test that moving one
product between repositories is cheap.

One-way in the practical sense: cheap in machinery, expensive in everything
that points at it — roots in the contract, origins in the site's config, the
union `check:docs` holds across origins. D10 is that test being cashed.

## D7 — 2026-08-27 — One kind of run: the light/full split is retired

*(Reconstructed 2026-08-31 from `README.md` and `a595e68`.)*

There is one kind of run, and it fetches everything whose upstream has moved.

**The split existed on a real number**: a full run cost 56 minutes against a
light run's 5. The probe-first exits removed that number — a fully-rested
full run measured **3 min 59 s**, faster than the light run it was avoiding,
because those four minutes are the observation fetches a light run performed
anyway.

**What the split still cost on the day it went was nine hours of stale Navy
fields**, and the mechanism is why it could not be tuned instead: the runs
GitHub actually delivered were the light ones, which skip those steps by
construction. A schedule that is mostly the cheap variant is a schedule that
mostly does not fetch.

The fourth shape of one-way, and the only entry here that is: **the argument
for a light run is permanently attractive** — it is cheaper, it is obvious,
and somebody will propose it again. Re-proposing it costs a rebuild and the
two measurements above, which is why they are written here rather than left
in a commit message.

Three full runs an hour, at :03, :23 and :43, so the storms keep the cadence
they had on the predecessor and the fields ride along.

## D8 — 2026-08-27 — A contract failure attributable only to held products no longer stops the deploy

*(Reconstructed 2026-08-31 from `58a7207` and `PLAN.md`.)*

The contract gate attributes each `FAIL` line to a product, demotes the fresh
culprits, reassembles and retries — and **tolerates a failure attributable
only to products this run already held**, deploying the rest.

**It weakens a guarantee readers had, which is what makes it a door.** Before
this, a published tree either satisfied every cross-product rule or did not
exist. Now a tree can publish while one product's held copy sits at an older
hour than its fresh sibling, and the reader is told which by the credit
lines rather than by the tree's absence. Going back means readers lose a
partial availability they now have, on a pipeline whose ordinary state is
upstream raggedness.

First live exercise 2026-08-28: four `FAIL` lines from two held depth
products, and `run: deploy=True`. Before this the surface currents — which
had fetched cleanly — would have been frozen with them.

**One exclusion is deliberate and stays**: a product demoted in the *same*
run still fails the deploy, pinned by
`test_contract_still_failing_stops_the_deploy`. The 2026-08-27/28 hour
collision slips through it, and separating "held because the data was judged
bad" from "held because the fetch failed and the carried copy is merely
older" is a real design that is not started. It is in `PLAN.md`'s open
section, not here, because it is a door nobody has walked through yet.

## D9 — 2026-08-27 — Currency is measured and gated, not merely reported

*(Reconstructed 2026-08-31 from `cd2ba0c` and `README.md`.)*

Every other check here asks whether the tree is CORRECT. None asked whether
it was CURRENT, and on 2026-08-27 that gap cost a day: both origins reported
`stale: false` on every product while the Navy fields sat nine hours behind
and OISST forty-three, with **twenty of twenty runs green**. Both were found
by a person looking at the map.

**The bug was the quantity.** `stale` compared when the pipeline last
PUBLISHED against `max_age_hours` — which answers "did we run recently?" and
not "is what we serve current?". A pipeline republishing a nine-hour-old
field every hour is perfectly live and completely stale. It measures the
nearest published frame against the reader's clock now, and publishes it as
`ageHours` beside the flag.

**Whose fault it is decides how loud it gets**, and that half is as
load-bearing as the measurement: old with a fate of `fresh` means upstream
has nothing newer, and is a note. Old with any other fate goes in `behind`
and the workflow FAILS on it — **after the deploy, never instead**, because
refusing to publish would leave the reader something older still, which is
the one response to staleness that makes it worse.

One-way for the same reason as D5: these are published fields that two
instruments in another repository read. **`nearestOffsetHours` joined them on
2026-08-29** — signed, positive behind and negative ahead — because a
forecast published seven hours into the future and data left seven hours
behind reported identically without it, and the report that produced cost a
full investigation pointed the wrong way.

## D10 — 2026-08-30 — The five Navy scalars leave for `espc-model-fields-repo`

The owner's call, and the first entry here written on the day it was taken.

Every model repository splits two ways along the axis that costs bytes:
`<model>-model-currents-repo` for the tiled vector fields, expensive, and
`<model>-model-fields-repo` for the scalars, cheap. `espc-model-repo` keeps
its legacy name as a knowing exception and is the currents half; that
repository's D2 carries the reasoning and the measurements.

**What leaves here**: `fields-navy` (`sst-navy.json`, `sss-navy.json`),
`ice-navy` (`sic-navy.json`, `sit-navy.json`) and `ssh-navy`
(`ssh-navy.json`) — five roots, with an upper-ocean heat content layer
expected to join them later.

**Why they could not move before**, which is the whole reason they were here:
into `espc-model-repo` as it stands they land at 982 MB, 96% of the cap.
Split off from the currents they sit at 150.3 MB, or 195.3 MB with the heat
content.

**What this repository gains is one subject** — observations, rather than
observations plus one model's output. That is D6's argument applied again,
and D6's live test being cashed.

**Nothing has moved.** Recorded first, deliberately; the migration is a
separate sitting. Two rules every such move has obeyed still apply: every
`roots` entry must be one the site's `test-schema.mjs --roots` publishes, and
**a product that leaves takes its files with it** — the stage is seeded from
what is already published, so a withdrawn product lingers unless it is
removed.

**And one thing it does not fix.** The ESPC hour rule spans ten roots and
will still span two repositories afterwards; only the site, reading both
origins, can enforce it. That is the site's D10, and it is permanent rather
than transitional.
