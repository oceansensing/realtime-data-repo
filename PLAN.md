# realtime-data-repo — running record

What the orchestrator and this repository's products have done, measured, and
what is open. Started 2026-08-28, when the four repositories were given
matching document sets; **records before that date live in
`oceansensing.github.io/PLAN.md`**, which carried this repository's history
while it had no record of its own — the fates design, the write fence, the
cache-key faults, the currency budgets and the quality hook are all there and
are not copied here.

## Where it stands

Publishes to <https://oceansensing.org/realtime-data-repo/> on its own cron.
It owns `pipeline/orchestrate.py` — **the orchestrator both data repositories
run**, `espc-model-repo` pointing it at its own workspace through
`PIPELINE_ROOT` — plus `pipeline/products.toml` for its own eleven-odd
products, and the static half under `map/` that CI cannot rebuild.

The fetchers and the data contract live in `oceansensing.github.io` and are
checked out at run time, so a fetcher or `schema.ts` change lands here on the
**next run**, not on any push here.

Because the orchestrator is shared, **a change to it is a change to both data
repositories**, and its unit suite is what stands between an edit and two
production pipelines. CI runs `python3 pipeline/test_orchestrate.py` before
every publish, in this repository and in `espc-model-repo`.

## 2026-08-28: rebuilding is for fresh products, accounting is for all of them

`settle_tiles` recomputed what a product still owes only
`if self.fate[name] == 'fresh'`. A **held** product skipped it: nothing seeded
`withheld`, `final` came out empty, and its carried-forward grid went on
advertising a tier the publish did not carry.

Live for two hours: four of the five ESPC current layers naming `tileIndex`
against a 404 while surface, which stayed fresh, was correct throughout — one
layer right and four wrong, which is what made the shape hard to see from
outside. The seeding is unconditional now, with `setdefault` on the inner key
so a build that ran and produced nothing keeps its more specific reason, and
the reason names the product's actual fate rather than assuming `held`.

**This is this repository's own 2026-08-16 fix placed one branch too deep.**
That fix taught that withholding must not walk the directories that *exist*,
and computed the owed list from `match` instead — then put it inside the
fresh-only branch, where a held product could not reach it.

**The mutation that survived is the part worth keeping.** Dropping the
`index.json` existence check changed nothing visible: `final` corrects the
state back through the walk. What leaks is the *reason*, into the manifest and
the receipt's `withheld` map, both of which are read as lists of what left. A
control that checks only `state` cannot see it; the kept-tier control asserts
a present tier carries no reason now. 45 tests.

## 2026-08-28: what the first doc sweep found here

Three claims, none of which any gate could anchor:

- **The workflow described light runs in the present tense** — a mode
  selector that no longer exists, a `:15`/`:55` schedule that no longer runs,
  and a pointer to "the light path in `pipeline/orchestrate.py`" that is gone.
  Rewritten to keep the reason three runs an hour is still right (the NHC does
  not publish on our schedule) without claiming the machinery.
- **`CLAUDE.md` described the ESPC move in the FUTURE tense**, six days after
  it happened, and said the four Navy field products were going with it. They
  are not — the owner's call, on storage — and its planning figures (114 MB of
  grids, 505 MB of tiles) predated the third depth cap and the second lead.
- **The predecessor was described as a live warm standby.**
  `ocean-data-repo` last ran 2026-08-17 and serves no status document, so the
  freeze is effectively in place; the README had been eleven days stale, and
  the workflow still noted the two pipelines overlapping four times a day
  with it.

## Deferred feature: the model run has an age and nothing watches it

**Proposed 2026-08-28, and the owner held off — logged so it is not lost.**

The report that raised it: the owner found the ESPC currents "out of date"
while every signal read healthy — `fate=fresh`, `stale=false`,
`ageHours=0.61`. Both were true. HYCOM's own `time_run` axis, probed
directly, offered nothing newer than the **2026-08-26T12:00:00Z** run at
03:39Z on 08-28, so the map was drawing a **+39 h forecast** whose valid time
was an hour old. Picking the frame nearest the reader's clock is right — a
late run should degrade into a forecast about the present, not a
confidently-labeled past — and the map's credit line named the run, which is
how the owner spotted it.

**What is missing is the alarm, not the display.** `ageHours` measures the
distance from the reader's clock to the nearest VALID TIME. Nothing measures
the distance to the MODEL RUN, so "upstream stopped running for two days" is
invisible to the currency gate and to the watchdog. The instruments did not
catch this; a person reading a credit line did.

The shape, if it is built: `runAgeHours` beside `ageHours` in
`status/status.json`, a per-product `max_run_age_hours` in the declaration
(30 h for a daily model — one missed cycle of slack), and a watchdog NOTE
rather than a red run. Old run with a fate of `fresh` is upstream's, and
refusing to publish a +39 h forecast would leave the reader nothing at all,
which is the one response to staleness that makes it worse.

Note the map already carries the reasoning, beside its `credit()` call: a
forecast valid an hour from now "is worthless if it came from a run three
days old... which is how the currents sat two days stale while looking
current". The display was fixed then. This is the same sentence asked of the
gate.

## Open

- **Product budgets are still being learned from live runs.** `assets` was
  sized wrong twice (4 → 8 → 10 hours) before the real cause was named: its
  `hour` is a synoptic time, not an issuance time, so the budget was
  measuring the wrong quantity. The upstream fix is recorded and not built.
- **The escape hatch for a partial outage.** The contract gate tolerates
  failures attributable only to products it held — except ones it demoted in
  the same run, which is deliberate and pinned by
  `test_contract_still_failing_stops_the_deploy`. The 2026-08-27/28 shape
  slips through that exclusion: a hold cannot cure an hour disagreement, so
  re-checking after the hold can only fail again. Separating "held because
  the data was judged bad" from "held because the fetch failed and the
  carried-forward copy is merely older" is a real design and is not started.
