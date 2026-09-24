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

Publishes to <https://oceansensing.org/realtime-data-repo/> on its own cron,
and **since 2026-09-24 to Cloudflare R2 beside it** (`publish-r2`, below).
It also owns `pipeline/publish_r2.py`, which every data repository's R2
publish runs.
It owns `pipeline/orchestrate.py` — **the orchestrator every data repository
runs**: `espc-model-repo`, `espc-model-fields-repo`,
`mercator-model-currents-repo`, `mercator-model-fields-repo` and
`sentinel3-data-repo` each point it at their own workspace through
`PIPELINE_ROOT` (the two ECCOFS repositories are queued to) — plus `pipeline/products.toml`
for its own **nine** products, and the static half under `map/` that CI cannot
rebuild.

**Nine since 2026-08-31**, when the five Navy scalars left for
`espc-model-fields-repo`. This repository holds no ESPC product at all now.

The fetchers and the data contract live in `oceansensing.github.io` and are
checked out at run time, so a fetcher or `schema.ts` change lands here on the
**next run**, not on any push here.

Because the orchestrator is shared, **a change to it is a change to six
production pipelines** (as of 2026-09-01), and its unit suite — 53 cases —
is what stands between an edit and all of them. CI runs
`python3 pipeline/test_orchestrate.py` before every publish, here and in
every repository that runs it.

## 2026-09-24: every origin publishes to Cloudflare R2 beside Pages

For the Ocean Now app (its D23 and D24): the app's data moves to a private
R2 bucket, `oceannow-data`, served at data.oceannow.bluetao.com by a
Worker that checks every request, and **R2 must stand on its own** — the
owner: *"When operational R2 server should be able to function on its own
without GitHub. Cross check with GitHub is a feature but not
requirement."* So `publish-r2` needs only `build` and its publish decision
and runs beside the Pages deploy, never after it. `CLAUDE.md` has the rules.

- **The first run refused, safely.** sentinel3-data-repo's manual run of
  the first draft refused its tree before sending anything: the guard asked
  for a `map/manifest.json` no origin publishes. The Pages deploy beside it
  published as designed — the independence, seen working on the first try.
  The guard is `status/status.json` now, held by two mutants.
- **The first publishes**: sentinel3-data-repo 8 files; this repository
  201, all tagged with their spacing, and its next run **21 of 201** — only
  what changed; espc-model-fields-repo 799; espc-model-repo 1,667 (its
  next run 6); mercator-model-currents-repo 1,614; mercator-model-fields-repo
  1,165 (21:00 UTC). **All six origins are on R2** (2026-09-24), each run
  ending with the bucket listed again and equal to the built tree.
- **Every grid carries its spacing** (`deg` metadata: the smaller of its
  header's first `dx` and `dy`, or a tile index's `deg`), which the Worker
  reads to hold the app's line: finer than 0.25° is premium. Checked over
  the published files: Mercator's 1°, ESPC's 0.96°, the 0.25° globals and
  the wind chance's 0.5° free; the 1/12° tiles, ESPC's 0.16° Atlantic
  region, its tile index and chlorophyll's 0.05° premium.
- **Open**: sentinel3-data-repo's chlorophyll has been `held` since
  2026-09-22 (*"step color exit 1"*), and its tiles are not on either host.

## 2026-08-31: the five Navy scalars moved, and one subject is left

`sst-navy`, `sss-navy`, `sic-navy`, `sit-navy` and `ssh-navy` are published by
`espc-model-fields-repo` from 06:26Z. This repository holds **no ESPC product
at all** now — twelve products became nine, and the subject is observations.

**The ice was a live test set up on 2026-08-22 and it passed.** It stayed
behind then deliberately, to prove that moving one product between
repositories is a declaration rather than a rewrite. The consumer's side of
this move was **one line** in the site's `MAP_ORIGINS`.

**Three things had to move together, and the second is the one that would
have taken production down.**

The products go. The `fields` step gains `--only=oisst` — because
`fetch-ocean-fields.py` publishes ten families (`PRODUCTS` in `fetch-ocean-fields.py`) and left bare it would have
gone on writing `sst-navy.json` into a tree that no longer declares it, which
the write fence refuses **for the whole run, every product**. And both cache
Restore/Save pairs go, because no product here declares a cache any more and a
step reading a `cache-paths-*` output nothing emits fails on an empty path —
the fault this repository already met on 2026-08-22 when the currents left.

**The other repository met the step-scope fault from the opposite side, on its
first run**, and that is what caught it here before a cron did: its bare step
fetched OISST as well as its own three families and wrote three files nobody
there declared. **A product is the unit of OWNERSHIP; a step is the unit of
EXECUTION**, and splitting one script's families across repositories splits
the first without splitting the second.

Gated the same day in the site's `check:docs`, in both directions and across
every origin. Too wide is loud; too narrow is silent — the files are never
written and the previous copies carry forward frozen, which is the shape this
repository has three entries about.

**The anchor-following cron went too.** `18 0,3,6,9,12,15,18,21` existed
because the Navy fields take the last step of the currents' window, so the
hour they publish moves when the three-hourly anchor rolls. That reason is in
the other repository now, and it runs `22 0,3,6,...` there. Nothing left here
is ESPC-anchored: OISST is a daily analysis, ECMWF has its own cycles, the
observation products are continuous. Three attempts an hour is the whole
schedule.

**And the files cleaned themselves up, which was NOT what was expected.** The
plan was to remove 21 of them by hand from the `published` branch — 18 grids
and regional cuts under `map/`, three per-product manifests under `status/` —
on the strength of the 2026-08-21 lesson that a product which leaves takes its
files with it and that grids stay behind when they are not made to.

They did not need it, and the reason is a distinction that lesson does not
draw. **The two artifacts a run uploads are assembled differently.**
`branch-out`, which becomes the `published` branch, is built from the DECLARED
products — so undeclaring these three dropped their files from the bank on the
very first run, automatically, 06:49Z. `out`, which becomes the Pages tree, is
built from the STAGE, and the stage was seeded from the *previous* branch, so
it still carried the grids for exactly one run.

Measured at 06:52Z, and the split is precisely the one 2026-08-21 describes:
**the four tile tiers were already 404 while all five grids were still 200.**
Tiers are paired to their grid under `tiles.match` and nothing declared them,
so they went at once; grids have no such pairing and rode the stage one run
further. The next run, seeded from the cleaned branch, is what drops them.

**So undeclaring a whole product self-heals in two runs. Renaming a file
inside a live product does not heal at all** — that is what cost 32 files and
43.8 MB in August, and the difference is that the product still existed and
its `writes` glob still matched, so `branch-out` kept banking them. The lesson
is real; its scope is narrower than it reads.

## 2026-08-31: what the doctrine's trial run found here

The owner asked for one deliberate run of the six questions across all eight
repositories, as a trial of the process rather than as the tail of a change.
Two things here, both small, both the kind no gate in this repository could
see:

- **"Eleven-odd products" in "Where it stands", where there are twelve.** A
  present-tense claim about a number that `grep -c '^\[products\.'` answers,
  minus the two `.tiles` subsections. **The vagueness was the tell** —
  "eleven-odd" is what gets written when the number is not re-counted, and it
  survived every sweep since because it reads as an estimate rather than a
  claim.
- **The site's privacy switch, recorded separately above**, which the same
  trial surfaced from the other direction.

The three questions that fired across the whole sweep were 1, 3 and 6.
Nothing here needed a `CLAUDE.md` rule, a decision entry or a `docs/` change.

## 2026-08-31: this README described the site's privacy switch as pending, for two weeks

The owner's report, against the site's `LICENSE`; this repository had the same
fault in a second place. **"If the site repository ever goes private"** was a
section heading here until today. The site went private on **2026-08-17**, and
step 6 of the runbook under that heading still read *"Only then make the site
repository private, and watch the next scheduled run."*

**The corrected account was already in this repository, in the file next
door.** The checkout step's comment in the publish workflow has said since the
switch that anonymous read is now a 404, that the SSH path carries it, and
that a dispatched run checked the private repository out and published end to
end. **The workflow was right and the README was wrong**, which is the wrong
half of a repository to be the accurate one: a comment is read by whoever is
already editing that step, and the README is read by somebody deciding whether
they need to.

The section is kept, not deleted — it is the runbook for the next repository
that needs a read-only deploy key, and the ordering hazard it records (the
secret **arms** the SSH path the moment it exists, measured at 21:00 against a
key at 21:03) is the part worth having. What changed is that it now says the
switch is done and dates it, so nobody reads it as work outstanding.

**Nothing here gates prose**, and that is not a gap to be closed by copying
the site's checker: there is no `package.json`, no npm, and CI here is a
publish run. The mechanism for this repository is the doc doctrine's question
6, and this is a clean instance of it failing — the change that made the
sentence false happened in another repository, so nobody sweeping *this* one
had a reason to look.

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

**And one thing the move does not fix.** The ESPC hour rule spans twelve roots (five in `espc-model-repo`, seven in `espc-model-fields-repo`)
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

## 2026-09-01 — a vector file's failure was never attributable

`test-schema.mjs` names a component of a vector file as `cur.json[0]`, and
the contract attribution matched that whole token against the products'
namespace globs. No glob matches a name ending in `[0]`, so every vector
failure fell to `cannot map ... to a product` and the fatal branch -- the
deploy was held, correctly, with a diagnosis that said the product was
unknown when it was declared in plain sight. Seen on the first Mercator
depth-average roots to reach the contract: twelve failures, twelve `cannot
map` lines. The mapper strips the component index now, and the suite is 53
tests;
`test_contract_attributes_a_vector_component_token` pins it and its control
keeps an unknown file fatal. Found by mutation: with the strip reverted, the
test fails.

## 2026-09-02 — whose stale, published

The owner: "a lot of ESPC products are stale." Measured: every ESPC root's
newest frame was valid 03Z, 3.0–3.3 h from the reader against 2 h budgets
(heat content 6.3 against 6), both origins' fates all `fresh`, and HYCOM's
2026-09-01 12Z run carrying **7 steps** for the currents and **6** for
temperature and salinity where the two runs before it carried 65 each; sea
surface height and ice had no 09-01 run at all. The map's health line read
`stale` eight times. This orchestrator had already decided the split --
`currency: ice-navy 3.3 h — upstream, not us` is in every such run's log
since 2026-08-27 -- and left it there, so the one instrument a reader sees
could not say it.

**`staleCause` is published beside `stale`** now: `upstream` when the fetch
succeeded and nothing newer exists, `ours` when newer data was there and this
pipeline did not publish it, null within budget and always present. The map
reads `stale (upstream)`; the site's watchdog reads the field with the fate
rule as its fallback. Three mutations of the orchestrator -- the two causes
swapped, the field dropped, a cause published within budget -- each fail the
suite; 53 tests.

## 2026-09-11 — ten runs waited out the `fields` step's thirty minutes

Written 2026-09-19, from the run logs and GitHub's usage report, because the
owner read that report on 09-12 looking for a saving and found this
repository's minutes doubled instead.

**What happened.** From about 03:35Z to 12:00Z on 2026-09-11 every run took
33 to 52 minutes instead of five: 1,996 s, 2,399, 2,609, 2,374, 2,011,
3,138, 2,580, 1,067, 1,876 and 2,062, against 250–400 s either side of the
window. In each, `Fetch, validate, assemble` held the time (1,807 s in the
longest, run 34575908050, against 188 s in a normal run that evening), and
the log says why in two lines: the OISST fetcher's `! probe inconclusive
(The read operation timed out) — fetching`, repeated, and then `--- step
fields: timed out after 30 min` with `held  fields-oisst`. The upstream read
was stalling; nothing else in the run was slow, and every other product
published `fresh` each time. The day's wall time was 901 minutes against
about 313, and the usage report billed 758 minutes against about 385 — all
of it discounted, since this repository is public.

**The mechanism worth keeping.** An inconclusive probe falls through to the
fetch. That is the right default for a probe that merely could not tell, and
it is expensive when the reason it could not tell is that the host is not
answering: the fetch then waits on the same host until `[defaults]
timeout_minutes = 30` ends the step, and the next run, twenty minutes later,
does it again. OISST is a daily analysis with a 60 h budget (72 since
2026-09-21; see that entry), so nothing was
lost by the holds — the product was served from the last publish throughout
— and nothing was gained by the waiting either.

**What it was not.** Not the OOI collector added the day before (`ooi:` …
`19 sites, 8 KB`, under a second in the same logs), and not a change here.
The two runs GitHub shows as `cancelled` in the window never started a job:
the concurrency group keeps one pending run and replaces it when a newer one
queues, so they cost nothing.

**Levers, noted and not taken** (the minutes are free; the reason to pull
one would be politeness to a struggling host, or a plan that stops being
free): a timed-out probe could hold the product for the rest of the hour
instead of fetching; the `fields` step could carry a shorter timeout of its
own than the default. `espc-model-fields-repo` met the same shape the same
day against HYCOM, and its PLAN has that reading.

## 2026-09-19 — a tier its own step built was never reported as built

**Found the evening `sentinel3-data-repo`'s schedule came on**, by reading
the first scheduled run instead of its green tick. Thirty minutes after a
dispatched run had published the overpass of 2026-09-17T15:19Z, the
scheduled one logged `nothing new: newest overpass … is already published`
and then `tiles chl-s3: building (0 adrift, 1 missing)` — 232 s and the full
seven-day read from CoastWatch, to rebuild tiles the first run had made and
not kept. The first run's log has no `Cache saved` line: `Save chlorophyll
tiles` is conditional on `built-chl-tiles`, and this orchestrator set that
output only inside the branch that runs a product's `build` command. Every
sibling's tiles are built there. Sentinel-3's are not — its composite is one
expensive read, so `fetch-ocean-color.py` writes grids and tiles in a single
pass, the tier is already complete when `settle_tiles` looks, and the branch
never runs. **So every new overpass was fetched twice**, once by the run
that found it and once by the next, and nothing was red.

**The fix is a comparison across the steps, not a special case for one
repository.** `Run.__init__` snapshots each product's tile indexes
(`tile_index_times`: directory → `refTime`, or None) before any step; in
`settle_tiles`, a fresh product whose build command did not run and whose
indexes now differ from the snapshot — absent then, or another hour — is
reported built. Three boundaries, each with a test and a mutation that
fails it: a tier the cache restored and nothing touched is NOT saved again
(the mutation "any complete tier counts" fails it — without this the same
23 MB would upload three times a day for ever); a step-built tier over an
absent one and over an older one are both reported (the mutation "the branch
never fires" fails both); and a HELD product's tiles are never saved (the
mutation dropping the `fresh` guard survived the first three tests and is
why the fourth exists — a step can write its tiles and then be refused by
the physics check, and saving them would hand the next run, on a cache hit,
the tiles of data this pipeline had just rejected). 57 tests.

**Not yet read live.** The proof is two consecutive Sentinel-3 runs across a
new overpass: the first logs `tiles chl-s3: built by its own step — the
cache will be saved` and `Cache saved`, the second restores and stops on the
probe. `sentinel3-data-repo`'s PLAN carries the reading when it is taken.

## 2026-09-20 — every origin publishes its own schedule, because one budget for all of them hid a dead pipeline

**What was believed for a day, and was wrong.** When `sentinel3-data-repo`
turned out to have published nothing for nineteen days (its crons had never
been uncommented), the first reading was that the site's watchdog could not
see a pipeline that stops, because it reads the `stale` flag the last run
wrote. It can: it compares every origin's `generated` with now. It had been
saying so twice a day since 2026-08-31, in an issue with 39 comments.

**What actually happened.** The watchdog allowed every origin three hours of
silence and wrote, of each, "It publishes about three times an hour". That
is true of three origins. `mercator-model-fields-repo` publishes every six
hours, so it was reported at 4.4–4.7 h in 36 of the 39 comments; the issue
could never close; and the Sentinel-3 line beside it — 28.0 h on 09-02,
220.0 h on 09-10, 450-odd by 09-19 — read as more of the same. Once
Sentinel-3's eight-hourly schedule came on it began tripping the same
budget itself.

**The fix is that the origin says how often it is scheduled to speak.**
`publish_schedule()` reads the crons of the workflow under ROOT that runs
`orchestrate.py run` — commented lines do not match — and
`longest_gap_hours()` turns daily patterns into the longest wait between two
scheduled runs, across midnight: 0.33 h here and in both ESPC repositories,
6.0 for both Mercator repositories, 8.0 for Sentinel-3, read off the real
workflows. It rides in `status.json` as `schedule: {crons, longestGapHours}`;
no cron at all is `null`, which is what Sentinel-3 would have published for
nineteen days. The watchdog (site repository, same day) allows one and a
half gaps plus an hour with a floor of three, says the cadence in its
sentence, and reports an origin with no cron on sight. Three tests here and
four mutations, each failing the test that names it: a commented cron
counted, any workflow's cron counted, the gap across midnight dropped, a
weekly cron read as daily. 60 tests.

## 2026-09-20 — the status document says which edition of the contract the tree speaks

For the iOS port, which the owner ruled that day should find the data
contract versioned. The site states `CONTRACT = 1` in its `schema.ts` and its
checker answers `--contract` with that integer; `contract_edition()` asks once
a run and `write_record()` puts the answer at the top of `status.json`, beside
`schema`. One orchestrator serves six origins, so this is the whole change on
the publishing side and no `products.toml` moved.

**What the tests pin, and what each was mutated against.** Five new, 65 in
all. An edition the site states is published, second key after `schema`. A
site checkout from before the flag publishes no key — the fake tool now
answers `--contract` the way an old checker really does, with a page of
output and exit 0, which is the dangerous case; run by hand against the
site's own HEAD that evening it printed 98 lines and exited 1. `0`, `-1`,
`1.5`, `2 editions`, a `FAIL` line and empty output are all no edition. A
bare integer from a checker that exited non-zero is not believed. And the
second call leaves the gate's own `--owned=` argv alone. **Parsing the first
number found fails five of them; believing a failing checker fails the
sixth.**

**Order of deployment does not matter**, which was the design constraint:
this can reach a run before the site's half does, and then the key is simply
absent, which readers are required to take as "as you were built".

## 2026-09-21 — the OISST budget was a guess about when the analysis lands, and it was stale five hours a day

**Found by reading the watchdog's issue once it could finally close.** The
site's watchdog issue closed itself on 2026-09-21T01:43Z, its first closure
in three weeks — and the check before it, 13:25Z on 09-20, had stayed open
on one true, routine-looking line: `fields-oisst (61.4 h old)`. Read across
the whole issue, that line is in **all 20** afternoon checks from 09-01 to
09-20, at 61.1–61.4 h, and in **none** of the 21 night ones. An alarm on a
timer is a budget that is wrong.

**The arithmetic.** The analysis for day D is stamped D 00:00Z and lands on
D+1 at some time T, so just before it lands the newest frame is 48 h + T
old. `max_age_hours = 60`, set on 2026-08-14 beside the comment "lands
mid-morning UTC", is the claim "T is before 12:00Z".

**Measured.** Each run's log states the frame it holds (`probe: oisst: … run
already staged and complete`, or `base frame advanced to …`), so each day
was binary-searched for the run where it advanced: **fourteen days of
fourteen, 2026-09-07 to 09-20, in the run created between 16:31Z and
16:46Z.** PSL's own server agrees — `Last-Modified: Sun, 20 Sep 2026
16:34:15 GMT` on `sst.day.mean.2026.nc`, picked up here fourteen minutes
later. Never mid-morning, not once. Routine peak age about 64.9 h; stale
from 12:00Z to about 16:50Z every day; a day missed outright would reach
88.8 h.

**Moved to 72**, with the measurement written beside it in `products.toml`:
"yesterday's analysis has not arrived by the end of today". Seven hours of
slack over the measured landing; a missed day reported from 00:00Z. 66–68
was the tighter alternative and would alarm whenever PSL ran two hours late.
No test pinned the 60, which is part of how it survived five weeks. What
made it visible is worth keeping: while the watchdog's issue could never
close, a line that came and went on a twelve-hour timer looked like
everything else in it. **The next budget to read the same way is `assets`
(10 h)**, which the owner's screenshot of 2026-09-17 13:38Z also showed
stale.

## 2026-09-21 — the `assets` budget, measured: the number is about right and the CLOCK is the wrong one. Not changed.

Read the same day as the OISST budget, on the owner's ask, because his
screenshot of 2026-09-17 13:38Z showed `assets stale (upstream)`.

**The clock.** `assets` holds the storms, gliders, USVs and Argo floats, and
its `hour` is the only `refTime` among its roots: NHC's wind-speed
probabilities (`wsp34/50/64.json`), issued at 00/06/12/18Z. The budget of 10
is six for the cycle, three for issuance, one for margin.

**In an active tropics the number holds, thinly.** NHC's archive listing
carries a posting time for every cycle: since 2026-08-01 the median lag after
the synoptic hour is **3.38 h** and the 90th percentile is 3.38 h — the file
appears at :22–:23 past, like a clock. Picked up by the next run here, the
previous cycle is 9.5–9.8 h old when it is replaced. One scheduled run
dropped by GitHub makes it 10.1. The watchdog caught that once in 41 checks
(09-07 01:41Z, 13.2 h — a cycle late or missed).

**In a quiet tropics the product stops, and that is what the screenshot
was.** NHC issues wind-speed probabilities only while a tropical cyclone is
active. Thirteen consecutive cycles, 2026-09-16 06Z to 09-19 06Z, are absent
from its archive, and in the same directory it posted no storm advisory file
at all between EP15's last (09-16 02:32Z) and the next systems (AL06, EP16,
EP17, from 09-19); 38 of August's 124 cycles are absent the same way. For
those 3¼ days the newest product was the 09-16 00Z one, so `assets` read
`stale (upstream)` continuously — the watchdog named it in eight consecutive
checks, 13.4 h on 09-16 13:29Z to 85.3 h on 09-19 13:25Z — while every
glider, USV, float and storm record in the product was current. The fetcher
already knows a quiet ocean is not a broken fetch (`collect_wind_probability`
says so); the budget does not.

**Two consequences, the second not verified.** The health line and the
watchdog call the whole platform product stale for as long as the tropics are
quiet, which will be most of the winter. And the *Wind chance (NHC)* layer
probably goes on drawing the last storm's probabilities after the storm is
gone: nothing in the map was found that hides a wind-probability grid by its
age, and what NHC's `latest` archive holds during a gap was not read.

**Options, the owner's call.** (1) Leave it and accept a stale line through
every quiet spell. (2) Move 10 to 11, which absorbs one dropped run and does
nothing about quiet spells. (3) Make quiet a published state: when NHC lists
no active cyclone and `latest` has not moved, the fetcher writes empty grids
stamped with the current cycle — "as of this cycle there are no
probabilities" is a current statement, the clock keeps moving, and an old
storm's probabilities stop being drawn. (4) Split the probabilities into a
product of their own, so the platforms' currency is not the cyclone
product's. (3) is the smallest change that fixes both consequences; it needs
a rule for telling quiet from an NHC outage, which is the judgment in it.

## 2026-09-21 — `assets`: eleven, and a quiet tropics is published as a current statement

The owner's ruling on the four options in the entry above: **option 3, with
11.** Two changes, one here and one in the site's fetcher.

**Here: `max_age_hours` 10 → 11**, with the measured delay term written
beside it — NHC posts 3.38 h after the synoptic hour at the median and at
the 90th percentile, the previous cycle is 9.5–9.8 h old when replaced, and
one scheduled run dropped by GitHub made that 10.1. Eleven absorbs one.

**In the site (`scripts/fetch-ocean-assets.py`): quiet is a published
state.** `collect_storms` records what NHC's active list said — a count, or
None when it could not be read — and `wsp_quiet_stamp` decides: when NHC is
advising on no cyclone and the newest issuance in its bundle is older than
the cycle that would be up by now (`WSP_POSTED_AFTER_H = 3.5`), the three
grids are published EMPTY, every cell `null`, stamped with that cycle. "As
of 12Z there are no wind-speed probabilities" is a current statement; the
clock keeps moving, `assets` stops reading stale through every quiet spell,
and the *Wind chance* layer stops offering a dissipated storm's
probabilities. Three refusals keep it from hiding a fault: **unknown is not
quiet** (an unreadable list leaves the old product in place, stale and
saying so), **active is not quiet** (a cyclone with a late product is NHC
being late), and a product that IS current is published as it is. The empty
grids pass `test-schema.mjs` as they are — `null` already means "no value,
never zero" — and the map needs nothing: the field's scale is fixed at
0–100 and it draws only above 5 %.

**Held by the fetcher's `--self-test`** (run inside the site's
`test:probes`): the due cycle to the minute, each of the three refusals, the
issuance read off a member name, the empty grid's stamp, shape and nulls,
and the chain offline — NHC's list stubbed to answer nothing and then to
fail, a bundle holding a finished storm's product, a clock two days past
it. Eight mutations, each failing the case that names it: unknown read as
quiet, active read as quiet, a current product overwritten, a cycle due at
its own hour, zeros for nulls, the count never recorded, the collector
ignoring it, a failed list leaving the last answer standing. Run against
NHC's live bundle three ways the same night: advising on storms → the real
00Z product; two days on with the list unreadable → the real product, old;
two days on with no cyclone → three empty grids as of the due cycle.

**To read live:** the first quiet spell. The log line is `quiet tropics: NHC
lists no active cyclone … publishing empty grids as of …`, `assets` should
stay inside its budget through it, and the watchdog should stay silent.

**Read on the first run with both changes** (35558886353, created 03:50Z on
2026-09-21, green): NHC was advising on storms, so the real 00Z product was
published — 4,013, 2,232 and 1,705 points — with no quiet line, `assets`
fresh at 3.9 h under 11 and `fields-oisst` fresh at 51.9 h under 72.
