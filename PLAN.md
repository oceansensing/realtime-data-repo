# realtime-data-repo — running record

What the orchestrator and this repository's products have done, measured, and
what is open. Started 2026-08-28, when the four repositories were given
document sets that were meant to match and did not — this repository's
`DECISIONS.md` did not arrive until 2026-08-31, and the sweep that noticed is
recorded below. **Records before 2026-08-28 live in
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

## 2026-08-31: a `DECISIONS.md`, eighteen days late, and what the gap was made of

The doctrine has said since 2026-08-28 that every repository carries four
documents. This one carried three. So did the site. The block asserting
otherwise was **byte-compared across eight copies the whole time** — held
equal, and false in two of them.

**That is the finding worth keeping, and it is not about this file.** A gate
on a text is a gate on the text. Eight identical copies of a sentence prove
the copies agree; they prove nothing about whether the sentence is true. The
same sweep found two README pointer sentences still saying the doctrine lives
"in all four" and "in all five" copies, sitting inches outside the compared
block — drifting freely while the block they point at could not.

**Ten entries, and only the last was written on the day it was taken.** The
rest are reconstructed, from `README.md`, from the commit log, and from the
site's `PLAN.md`, which carried this repository's history before 2026-08-28.
Each says so. The reconstruction is honest about its weakness in the file's
own preamble: **a commit message records what was done and almost never what
was rejected**, so where an alternative survives below it is because some
document happened to keep it.

What the reconstruction turned up that no single document held:

- **D4, the `published` branch, is the strongest one-way door here and was
  never written down as one.** One orphan commit, force-pushed every run.
  The durability argument is in `README.md`; the consequence is not — there
  is no history, yesterday's publish is unrecoverable, and the stage is
  seeded from that branch, so a bad publish propagates into the next run's
  starting point. Keeping history cannot be adopted retroactively.
- **D1 finished quietly.** The predecessor was to be a warm standby and then
  frozen. Its last run was 2026-08-17; nothing decided that, and this
  repository's own README described it as live for eleven days afterwards.
  **A fallback nobody exercises is a decision that completed without being
  taken**, which is a shape worth being able to name.
- **D7, the light/full split, is the only entry here of its kind** — a
  decision that removed a capability rather than closing a door. It is in the
  file because the argument for a light run is permanently attractive and the
  two measurements that killed it (56 min against 5; a rested full run at
  3 min 59 s) would otherwise have to be re-taken by whoever proposes it next.

**Gated the same day**, in the site's `check:docs`: every repository in the
doctrine must carry a `DECISIONS.md` **tracked in git**, not merely present
on disk. Content is deliberately unchecked — an empty file passes, because a
repository can honestly have closed no doors and a minimum entry count is a
number nobody chose. The discriminating mutation was a sibling's file left on
disk and removed from the index: `existsSync` passes it, git does not.

## 2026-08-30: the five Navy scalars are leaving — DECIDED, not yet moved

The owner decided the model repositories split two ways, along the axis that
costs bytes: **`<model>-model-currents-repo`** for the tiled vector fields
(expensive) and **`<model>-model-fields-repo`** for the scalars (cheap).
`espc-model-repo` keeps its legacy name as a knowing exception and is the
currents half; its `DECISIONS.md` D2 carries the reasoning.

**What leaves this repository**: `fields-navy` (`sst-navy.json`,
`sss-navy.json`), `ice-navy` (`sic-navy.json`, `sit-navy.json`) and
`ssh-navy` (`ssh-navy.json`) — five roots, to a new
**`espc-model-fields-repo`**, with an upper-ocean heat content layer expected
to join them later.

**Why they could not move before**, which is the whole reason they are here:
moving them into `espc-model-repo` as it stands lands at 982 MB, **96% of the
1 GB Pages cap** — less than one current frame of margin. The measurement is
in that repository's own `products.toml` header. Split off from the currents
instead, they sit at 150.3 MB (14.7%), or 195.3 MB with OHC.

**What this repository gains: one subject.** Observations, rather than
observations plus one model's output. That is the same argument that created
`espc-model-repo`, applied again — and the ice staying behind in 2026-08-22
was explicitly a live test that moving a product between repositories is
cheap. This is that test being cashed.

**Nothing has moved.** Recorded first, deliberately; the migration is a
separate sitting. When it happens, the two rules every such move has obeyed
still apply: every `roots` entry must be one the site's
`test-schema.mjs --roots` publishes, and **a product that leaves takes its
files with it** — the stage is seeded from what is already published, so a
withdrawn product lingers unless it is removed.

**And one thing the move does not fix.** The ESPC hour rule spans ten roots
and will still span two repositories afterwards; only the site, reading both
origins, can enforce it. The arrangement that would fix it — all ten in one
repository — is exactly what storage forbids.

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
a present tier carries no reason now. 51 tests.

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

## 2026-08-28: the attribution path's first live outage, and what `checked` said

**"The map is out of date" for the second time in two days, and a different
cause.** The first (above) was a model run eighteen hours late with every
signal healthy. This one was a single poisoned time step: HYCOM served
non-deterministic garbage below the surface at one valid hour, `espc-model-repo`'s
quality gate held `currents-50m` and `currents-caps`, and the depth layers
froze three hours behind the surface — 5.7 h old against the reader's clock
at the moment of the report, on the `+3h` frame the map actually opens on
rather than the `hour` in `status.json`. The full measurement is in that
repository's PLAN.
Two reports, the same four words, unrelated mechanisms — worth keeping
straight, because the instruments that would catch them are different.

**Fixed upstream of this repository the same evening**, on the owner's
instruction: the currents fetcher's step probe now reads every depth a run
reads instead of the surface alone, so a step corrupt below the surface is
walked past at selection rather than fetched and then held. All three ESPC
products move together to a step that serves at every depth, which means
this collision — a held depth product sitting at an older hour than its
fresh sibling — no longer arises from THIS cause. It can still arise from
any other per-domain hold, so the open item below stands.

**The escape hatch worked, and this is its first live exercise.** The held
products failed the consumer's ESPC hour rule — four `FAIL` lines, since a
held depth product sits at an older hour than the fresh surface — and the run
deployed anyway: `contract: failures attributable only to held currents-50m,
currents-caps — deploying the rest`, `run: deploy=True`. Before `58a7207`
that would have frozen the whole Pages tree, including the surface currents
that fetched cleanly. The open item below is unchanged — this shape still
cannot be *cured* by re-checking — but the tolerance is doing what it was
built to do, and the site's and espc's docs both claimed the old behavior
until this run falsified them.

**And one instrument lesson, which is a reading trap rather than a defect.**
The manifest writes `'checked': now if fresh else prev.get('checked')`, so a
product rejected every twenty minutes for six hours advertises a `checked`
six hours old. Reading the live document during this outage, the first
conclusion drawn from that field was "the pipeline has stopped running for
these products" — when it was running constantly and rejecting every time.

**The field is right and the reading was wrong.** `README.md` defines
`checked` as *the last time the pipeline successfully attempted the product*,
which is exactly what it did, and `CLAUDE.md` is careful to say `checked`
going quiet **across products** means the pipeline is not completing. What
neither says is the single-product case: one product's frozen `checked`
beside a current `generated` is the ordinary signature of a hold, not of a
stopped pipeline. `generated` at the top of the document is the run that
actually ran, and it is the field to read first.

Nothing changed in the code; the sentence is now in `espc-model-repo`'s
`CLAUDE.md` under "Reading a run", where somebody debugging a held ESPC
product will meet it.

## 2026-08-29: one null field froze all twelve products

The contract gate did what it is for and the cost was total. PMEL's ERDDAP
carried no `minTime` for `sd1030_hurricane_2026` — a Saildrone reporting
hourly — so `ocean-assets.json` published `deployed: null`, the site's
`test-schema.mjs` refused it, and this repository set `deploy=False` for
hours. Every one of the twelve products was `fresh`; eleven of them had
nothing wrong. The full diagnosis and the fix are in
`oceansensing.github.io`'s PLAN, which owns the fetchers and the contract.

**Two things this repository should take from it.**

**The escape hatch could not help, and correctly so.** It tolerates contract
failures attributable only to products this run already held — and nothing
was held. A fresh product publishing a malformed record is exactly the case
where refusing the tree is right, because the alternative is publishing data
a consumer has been promised is well-formed. The open item below is about the
*held* case and is unchanged.

**A frozen tree tells a stale story about itself.** `status/status.json` is
published with the tree, so while `deploy=False` holds, the document a reader
fetches is from the last run that succeeded — here reporting six products
`held` on `step assets exit 1` from 19:39Z, hours after that fault had
cleared and a different one had taken over. `espc-model-repo`'s `CLAUDE.md`
had just been given the sentence for this ("read the run log, not only the
published status, when the two could disagree") and this is its first
collection. Worth stating here too because this repository is where
`deploy=False` is decided: **when the tree is frozen, the run log is the only
current account of why.**

## 2026-08-29: the demote-and-retry was dead code for most failures

Asked after a night of instance-fixes: *why is the pipeline so brittle?* The
answer, for this repository, was not a missing capability. It was a regex.

`contract_gate` attributes each `FAIL` line to a product, demotes the fresh
culprits, reassembles and retries — so one bad file costs its own product and
the rest of the tree publishes. It is described that way in this file, in
`README.md`, in `CLAUDE.md` and in three tests. **For most failures it never
ran.**

The attribution read `^FAIL\s+(\S+?):`, non-whitespace up to the first
colon. The consumer emits two shapes:

```
FAIL  currents-50m.json: is valid ...            <- matched
FAIL  ocean-assets.json asset sd1030_...: ...    <- matched NOTHING
```

Every content check that names *which record* is wrong — assets, sondes,
tracks, the semicolon rule — uses the second. And a line matching nothing
produces no culprit **and no `unmapped` entry**, so the gate reached the
fatal branch with an empty culprit set, took `not fresh_culprits`, set
`deploy = False`, and logged nothing about why. Silent, and it looked exactly
like an ordinary contract failure.

Measured cost the night it was found: one Saildrone with `deployed: null`
froze all twelve products for six hours. Attributed, the same failure holds
`assets` alone — its previous file ships, the other eleven publish, and the
watchdog names it.

Now `^FAIL\s+([^\s:]+)`: stop at whitespace **or** colon. The whole-file
form keeps working (`\S+` alone would have captured the colon — a mutation
proves it), the record form attributes, and a token owning nothing still
lands in `unmapped` and is still fatal, now with the "cannot map" line it
always should have printed.

Two tests, three mutations killed: the old colon-only pattern, a greedy
`.+`, and `\S+` without the colon stop. The negative control — a
record-shaped failure naming a file no product owns must stay fatal — is
what stops this being "loosened" later until nothing is ever fatal again.

**The lesson is not about regexes.** A gate that parses another repository's
output is a contract with no compiler behind it, and this one was checked
against the shape someone imagined rather than a real line. Its own tests
used `FAIL  alpha.json: bad vibes` — the shape that worked — so the suite
agreed with the bug. Test a parser against output the other side actually
produced.

## 2026-08-29: this repository's tile tiers tolerate holes too

Ported from the currents in the same sitting. `fetch-ocean-fields.py` had the
identical all-or-nothing tile rule governing the SST, SSS, SSH and ice tiers:
one refused corner discarded the tier, and the build stopped at the first
failure because any failure abandoned the index anyway.

Both now use the shared `gap_budget()` (`TILE_GAP_MAX_FRACTION`, **6%** since
2026-08-29, applied per tier so each frame gets its own allowance, in
`espc_window.py` — one definition, because a tier policy that differs between
two pipelines reading the same flaky upstream is a difference nobody chose).
A tier publishes with `gaps` naming every refused corner; past the budget it
still refuses and keeps the previous complete set.

The measured case that prompted it was in the currents — an HTTP 500 on 1 of
162 corners costing all 161 others — and the full record is in the site's
PLAN.

**Not directly pinned here, and worth knowing:** this file writes its tile
index inline rather than through a function a self-test could drive, so the
shared `gap_budget` is tested and the contract validates the `gaps` shape,
but the publish-or-refuse branch itself is not. Extracting an index writer,
as `fetch-currents.py` has, is what would close it.

## 2026-08-29: a forecast frame's tier could not be seen to be missing

Reported as *"how come coarse resolution current data is still served"*, with
a share link at zoom 9 over the Chesapeake. The tile tiers had just been
restored and the base tier was complete, so the report looked wrong. It was
not.

The surface currents publish two frames — 03:00Z and 06:00Z — and the map
opens each layer on the one nearest the reader's clock. At 05:30Z that is the
**+18h** frame, and `tiles-f18h/index.json` was 404, so it fell back to
`currents-atlantic-f18h.json` at 0.24°. The browser's own resource timings
confirmed it: `tiles/20_-80.json` fetched for the base frame,
`tiles-f18h/index.json` asked for twice and `currents-atlantic-f18h.json`
loaded instead.

**Why that tier never built.** Three places asked "which tiers does this
product owe?", and all three read the same list:

```python
bases = [d for d, g in tiles['match'] if '*' not in d]
```

which filters out `tiles-f*h` **by construction**. So a forecast frame's tier
was invisible to the build trigger, to the produced-nothing check, and to the
withheld accounting. It could only ever be built as a side effect of the BASE
tier being missing in the same run — which is exactly why `tiles-50m-f18h`
existed (its base had been missing, and a build does every lead at once) and
`tiles-f18h` did not (the surface's base was cached and fine).

The accounting was the worst of the three: `receipt.json` reported
`"currents-surface": {}` — nothing withheld, nothing wrong — while that
product's forecast tier was absent and the map was drawing it coarse.

**`expected_tiers(spec)`** replaces all three. It is the counterpart to
`tile_pairs`, and the difference is the whole point: `tile_pairs` walks the
directories that EXIST, so it can call a tier adrift and can never call one
absent; `expected_tiers` walks the GRIDS and derives the directory each is
declared to owe. First match wins, same declaration order read the other way
round.

Two tests, three mutations killed: restore the unstarred-only list, derive a
tier for every file in the stage (the opposite failure, and costlier — an
endless build of directories nothing declares), and owe a tier where the grid
is absent.

**This is the 2026-08-16 lesson's third instalment**, and the pattern is
worth naming: *withholding must not walk the directories that exist* was
right, the fix computed the owed list from `match` instead — and that list
was still a list of directories, so it still could not contain a name with a
star in it. Deriving from the grids is what actually answers the question.

## 2026-08-30: `ageHours` has a sign now

It is a magnitude, so a forecast published seven hours AHEAD reported
identically to data left seven hours BEHIND. That is not hypothetical: at
20:16Z on 08-29 all three ESPC products read `stale: true, ageHours 7.15`
while publishing 2026-08-30T03:00Z. The report it produced — "the currents
are hours out" — was true, pointed the wrong way, and cost a full
investigation of the step picker rather than a glance at the status
document.

`nearestOffsetHours` is published beside it: **positive is behind the
reader, negative is ahead**. `ageHours` is unchanged, because it is what
`max_age_hours` compares against and staleness genuinely has no sign; what
changed is that `nearest_frame_age` is now computed as `abs()` of the offset
rather than independently, so no later edit can drift the pair apart.

The site's watchdog prints the direction — `7.2 h ahead` against `7.2 h old`
— and keeps the old rendering as a fallback for an origin that has not
published the new field yet, which is pinned by its own control.

Five cases here, four mutations: throw the sign away, pick the first frame
instead of the nearest, do not publish the field, and compute the age
independently. **The last is an equivalent mutant and is recorded as one** —
it gives the same number today, the reason to derive age from offset is
structural rather than behavioral, and no test can distinguish them. Saying
so is better than contriving one that seems to.

## Open

- ~~**`fetch-ocean-fields.py` memoises its step selection per PROCESS.**~~
  **CLOSED 2026-08-30**: the mechanism moved to `espc_window.py` and both
  fetchers share it, scoped so neither they nor the fields' six products can
  read each other's answer. Two pins that were not pins came out of it — a
  module imported by name only (every call would have raised `NameError`,
  and the suite passed because nothing exercised the new code) and a
  never-write mutation that survived until `memoized_frames` was extracted
  and driven with a counting stub. Record in the site's PLAN. The original
  entry follows.

- **`fetch-ocean-fields.py` memoises its step selection per PROCESS, and the
  orchestrator runs it many times per publish.** `forecast_frames` carries
  the same shape `fetch-currents.py` was fixed for on 2026-08-29: a memo
  scoped to a process, a docstring that already warns "two calls could
  disagree", and `--tile-key`, `--tiles` and `--namespace` invoking it
  separately per product — each re-probing upstream. There it produced three
  different tile keys in one run and left four tile tiers 404. Here the
  probe reads surface fields only, which is the cheap-probe case the
  currents were in before their depth probe landed, so it has been getting
  away with it. **Not fixed. If any probe in that file becomes costlier or
  stricter, do the memo first** — the fix is `frame_slot` /
  `read_frame_memo` / `write_frame_memo` in `fetch-currents.py`, about
  seventy lines, and its record is in the site's PLAN.


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
