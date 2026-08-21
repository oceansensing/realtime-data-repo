# CLAUDE.md

Guidance for working in this repository. The **design** — why the pipeline
is shaped the way it is, what a product is, what the fates mean — lives in
`README.md` and is not repeated here. This file is the operator's and
maintainer's half: what to run, what must move together, and what has
already gone wrong.

## The one relationship that explains everything else

The fetch scripts and the data contract live in
`oceansensing/oceansensing.github.io` and are checked out under `site/` at
run time. This repository owns everything around them: the declaration
(`pipeline/products.toml`), the orchestrator (`pipeline/orchestrate.py`),
the workflow, and the published record. Two consequences:

- A fetcher or `schema.ts` change lands on this repository's **next run**,
  not on any push here — and it lands on the predecessor
  (`ocean-data-repo`) the same way. Two pipelines, one copy of the scripts.
- Nothing in this repository may re-state a rule the contract owns.
  The orchestrator shipped with a copy of the ESPC hour-agreement rule and
  the copy was wrong on the very first live run — the currents' base file
  is deliberately the *earlier* of two frames, and cross-run raggedness is
  a note rather than a failure. The copy was deleted, not fixed: when the
  contract objects, the gate maps the failure to its product and demotes
  exactly that one. If a new cross-product rule is needed, it goes in
  `test-schema.mjs` in the site repository, never here.

## Commands

```sh
python3 pipeline/test_orchestrate.py   # the unit suite; CI runs it before every publish
```

There is no other local entry point to memorize; the workflow runs
`orchestrate.py seed`, `plan --mode <full|light>`, then `run`, and each can
be run by hand in that order. A full local rehearsal against real upstreams:

```sh
git clone https://github.com/oceansensing/oceansensing.github.io site
python3 pipeline/orchestrate.py seed-published --from https://oceansensing.org/realtime-data-repo/map
cp -R branch-out published
python3 pipeline/orchestrate.py seed
python3 pipeline/orchestrate.py plan --mode light
python3 pipeline/orchestrate.py run
```

Light mode is the polite rehearsal: one assets fetch, no HYCOM tile builds,
and the real contract still runs over the real assembled tree. `site/`,
`published/`, `out/`, `branch-out/` and `plan.json` are all gitignored
working state.

## Reading a run

Start with the data, not the Actions page:

```sh
curl -s https://oceansensing.org/realtime-data-repo/status/status.json | python3 -m json.tool
```

A held product's `reason` is one sentence; the `run.url` beside it links the
exact run, and `receipt.json` says what was built and withheld. `checked`
going quiet across products means the pipeline is not completing;
`updated` aging alone means an upstream is quiet — the two are different
faults with different owners, which is why both timestamps exist.

A **red run** is reserved for states where nothing can be trusted: the
orchestrator's own tests failing, the roots disagreeing with the contract,
or a fetcher writing outside every declared namespace (the write fence,
exit 3). Ordinary weather — a timeout, a bad grid, a contract objection —
ends green with fates recorded, because the publish it produces is still
correct. Do not "fix" a fence failure by widening a `writes` glob without
knowing what wrote the file; the fence exists because an unattributable
write means the restore logic can no longer reason about the stage.

## What must move together

- **`CACHE_VERSION` in orchestrate.py moves with tile *content or format*.**
  The caches are verified by `refTime`, so a wrong-hour restore heals
  itself — but a *format* change under the same hour would pass that check.
  That is exactly what the content check cannot see, so it is what the
  version constant is for. The light-run restore prefix is version-scoped
  for the same reason.
- **`products.toml` roots and `schema.ts` roots** are self-checked: the run
  refuses to start on a mismatch. Adding a root to one place means adding
  it to both, and the refusal is the reminder.
- **A tile `match` table lists exact names before starred ones** — a
  directory pairs with its first matching entry.
- **The fetchers' probe flags print the key to stdout and progress to
  stderr.** `run_cmd` keeps the streams separate because of it; a fetcher
  change that mixes them corrupts the cache key, not a log line.

## What has already gone wrong here

- **The record was written before the verdict.** The receipt once said
  `deploy: true` for runs the gate had refused — caught by the unit suite
  before first publish. `write_record` runs last, after the gate and the
  light-run guard, and must stay last: a receipt describing intent rather
  than outcome is the predecessor's cache bug wearing a new hat.
- **A copy of the contract's rule drifted on its first live encounter.**
  Above, under the relationship. The generalization: a copy of a rule is a
  list of one.
- **`index.md` is not a page.** Workflow-mode Pages runs no Jekyll, so the
  predecessor's `cp README.md out/index.md` had served a 404 at its root
  since launch — inherited here verbatim, found only when a summary linked
  the root. The landing page is a hand-written `index.html`, copied in by
  `assemble`. Verify a copied pattern in its *original* before trusting it
  in the copy.
- **The cutover carried every pipeline and no static file.** The isobaths,
  the offline coastline and the borders 404'd on the live map for a day —
  four lazily-fetched layers whose absence degrades to nothing, invisible
  to every gate. The static half lives in this repo's `map/` now, named in
  `[static]` in products.toml, and `assemble` refuses to run with any of it
  missing: a missing static is a defect here, not an upstream outage.
- **The roots check deadlocked on the seed it was guarding.** The site's
  `--roots` flag used to answer *after* its per-file checks ran — and the
  seed stages into the site checkout's own `public/map`, so the day a
  seeded storm carried a real contract fault (NHC published a null heading
  for a stationary system) the FAIL line's words were parsed as root names,
  the agreement check refused, and no run could publish the cure. The flag
  answers first now, and an unstated storm motion is published as absence
  rather than null. When a run fails at ROOTS with word-salad names, read
  the full log: those words are a check's failure line, and the fault is in
  the seeded data, not the declaration.

- **A build reported `ok` having produced nothing, and the record showed
  no trace of it.** 2026-08-16, with HYCOM returning 500s: the log read
  `tiles currents: building (0 adrift, 2 missing)` and then
  `--- tiles currents: ok`, 0.4 s apart, with both directories still
  missing — a sweep of 159 tiles across two depths takes minutes. Every
  pipeline here degrades by keeping the previous file and exiting 0, which
  is right and means **an exit code says "I did not fail", never "the
  tiles are there"**. Nothing was withheld and nothing recorded, because
  both walk the directories that *exist* and an absent one is in neither.
  `settle_tiles` re-reads the same `match` list afterwards, demotes a build
  that produced nothing, and records the absence with its reason — so the
  cache is not saved off it, which is what stops the incomplete-artifact
  trap this repository already has a note about.
- **A grid advertised a tier the publish had just withheld.** The same
  outage: `currents.json` went out carrying `tileIndex` while both tile
  directories had been dropped for being another hour, so every reader
  fetched a 404 per layer per view. The map catches it and the coarse grids
  stand — that fallback is right and is not the fault; the doomed request
  is. The withdrawal rewrites the header now, in the same place that
  removes the directory, because that is the only place that knows which
  grid was making the claim. Two shapes matter and one of them the
  integration fixture cannot show: the currents are a *list* of two grids,
  so touching only `doc[0]` leaves the second depth advertising, and it
  takes a direct test of `unadvertise_tiles` to catch it.

The unit suite's load-bearing checks — the write fence, the tile-drift
check, the held-product restore — are mutation-tested: plant the fault,
watch the suite go red, restore from git. Commit before running anything
that rewrites the tree.

## What `status/status.json` is for, and why it is one document

It began as a health statement and is the **routing document** as well since
schema 2 (2026-08-21). Each product entry now carries:

- **`roots`** — the files this origin serves. A consumer reads one document
  per origin and learns where every root lives, so moving a product between
  repositories costs nothing on the consumer's side.
- **`modelRun`** beside the existing `hour` — the pair the cross-origin hour
  rule compares. Same run with a different hour is this repository's own
  fault; a different run is upstream lag and only a note.

**One document rather than two, and the argument is not brevity.** Routing
and health have to agree: a *held* product is still served — its previous
files are published — so a consumer still needs to know which origin has
them. Two documents can disagree about which products exist; one cannot. It
is also already fetched by the map, and already a projection of
`products.toml` written in the process that reads it, rather than a second
list to keep in step.

**`origin` is deliberately absent.** The consumer knows where it fetched the
document from. Restating it would be a copy that can drift, which is the
shape this repository keeps paying for.

**The hour and the run are one reading**, taken from the first root that
carries a header — `stamp_of`, not two functions. Separately, the hour could
come from one root and the run from another, two facts about two files
reported as one product's stamp, and the distinction the hour rule turns on
would be meaningless.

**Bumping to 2 breaks nothing**, which is worth stating rather than assuming:
the map reads `fate` and `stale` and never looks at the version. A consumer
that wants to route treats a missing `roots` as "the default origin owns it",
which is what lets a reader land before any origin publishes the new shape.

## A published root the pipeline stops writing is never removed

Measured 2026-08-21, when the site's deep current layer moved from 60 m to
50 m. The tile directories went with it; **the grids did not**, and the
difference says exactly where the gap is.

Tiles are paired to their grid in `products.toml` under `tiles.match`, so
dropping `["tiles-60m", "currents-60m.json"]` from that list dropped the
directory. Grids have no such pairing. `orchestrate.py seed` fills the stage
from the last publish, each step writes into it, and a file no step writes
any more is simply carried — every run, forever.

Left behind: **32 files, 43.8 MB** — four regional grids and each of their
seven forecast frames — frozen at the hour of the last run that wrote them
and still served. Deleted by hand from `published` once the site was
confirmed to request none of them.

**Nothing catches it, and the reasons are worth knowing separately:**

- `--roots` and `products.toml` agree, because the file stopped being a root
  on both sides at once. The contract is about what *must* be published, not
  about what must not.
- The ESPC hour-agreement rule reads a hardcoded product list, so a grid that
  leaves the list also leaves the check — the very grid most likely to go
  stale is the one that stops being looked at.
- `max_age_hours` is per *product*, and the product is fresh. Its abandoned
  files are not the product.

So the file ages with nothing measuring it. The only reason this one was
found is that a person went looking after a rename.

**This is the move's largest risk, not a footnote.** `espc-model-repo` takes
a whole product set out of this repository — on today's behavior every grid
it takes stays here too, frozen and still served, which is 619 MB against the
1 GB cap that is the entire reason for moving. A prune has to exist before
the move, and the hard part is not the pruning: it is that a *partially
failed* step must never be read as "the product no longer writes these", or
the first flaky upstream deletes real data. That is the two-correct-components
shape this repository already has an entry about.

## How a run starts, and why a push does not

Three crons and `workflow_dispatch`. **No push trigger**, dropped 2026-08-21
after measuring what one cost.

It had run `full`, because the mode selector treats anything that is not the
light cron string as full — deliberately, since "a light run that was meant
to be full publishes an hour-old ocean with nothing saying so". The effect
was that a push changing one markdown file started a complete fetch of every
product: **56 minutes against a light run's 5**, and with
`concurrency: publish` and `cancel-in-progress: false` a new run cannot
cancel the one in flight, it queues — so each arrival cancelled the
previously queued one. Three consecutive scheduled runs were cancelled and
nothing published between 03:16 and 04:28, on a schedule that promises three
an hour. The map's staleness note needs three hours, so nothing said so.

**Making a push run *light* was the other candidate and is worse for the case
that matters.** A push here is usually a change to a fetcher or to the
orchestrator, and a light run performs one of the five steps — you would be
watching a run that did not do the thing you changed, which defeats the
deploy-and-watch habit rather than serving it.

So: **push freely, then dispatch when there is something to watch.**
`gh workflow run publish.yml` defaults to full for the same safe-direction
reason. Nothing is lost by waiting either way — the next scheduled run picks
up an unpushed change within about twenty minutes.

The site repository reached the same arrangement from the other side, where
`[skip ci]` keeps a push from deploying and a scheduled run carries it.

## Cutover, when it comes

Cutover happened on 2026-08-14: `MAP_DATA` in the site's `src/config.ts`
points at this repository, and every consumer — the production map, the
hurricane page, the build-time storm line, the dev map — follows that one
constant. Light crons run at `:15` and `:55` (enabled the same day), so
storm cadence matches the predecessor's three publishes an hour. A boundary
full run at `:02` after each six-hour window turns (added 2026-08-15) puts
the new window's frames up inside their own hour instead of the :35 cron's
~70–95 minutes later — the workflow header carries the measurements.

**What remains is the predecessor's freeze**, deliberately deferred a few
days: `ocean-data-repo` keeps publishing on its own crons as a warm
standby, so switching back is the one string in `src/config.ts`. The
freeze, when called, is `gh workflow disable` on its publish workflow and
nothing else — no deletions, no archive settings; the repository stays a
readable record and a restartable fallback. Until then a fetch-script
change still lands on both pipelines' next runs. The measured
old-versus-new ledger is in the README under "How it compares to the
predecessor".

## The tile encoding changes, reader first

Reader on the site 2026-08-20, writer 2026-08-21: `header.unitScale` says
what one unit in a grid's `data` is worth, absent meaning 1. **The currents
this repository publishes now carry `unitScale: 0.001`** — integer millimeters
per second. The ordering was deliberate rather than incidental.

This repository checks out `oceansensing.github.io@main` and runs its
pipelines three times an hour. The *site* deploys every six hours. So a change
to `scripts/fetch-currents.py` reaches production within twenty minutes while
the map that reads it can be six hours behind — and a grid written as integer
millimeters per second, read by a map that does not know it, draws the ocean
at a thousand times speed.

The reader shipped first for that reason, and the writer followed once the
served page reported the reader's own commit.

Measured on the first real run: the global grid went from 322 distinct values
to 2,111, from 2.47% of the wet field landing on exactly zero to 0.241%, and
from 684 KB to 565. The four regions came in 17-20% smaller.

**Both formats appear in one tree and that is the normal state.** The first
run after the writer landed degraded a forecast frame on a 500 from HYCOM and
kept the previous file, so new millimeter grids published beside an old
two-decimal one. Nothing coordinates them because nothing has to: the scale
rides in each file's own header.

**What the contract gate catches.** `test-schema.mjs` holds a declared scale
to a negative power of ten and to integers under it, and holds the *values*
to their declared step by their greatest common divisor — 1 for a field
genuinely quantized there, exactly the ratio for one rounded through a
coarser step. That last one is the important one: a writer that rounds to two
decimals and then scales by a thousand publishes valid integers under a valid
scale in a *smaller* file, so a byte count would call it a win. A FAIL naming
a file demotes its product to the previous version here, which is the right
outcome.

**And the gate's reach was an eighth of what it looked like.** Its vector half
picked files from a hardcoded list of the three *global* grids, so every
regional grid and every forecast frame this repository publishes was
unchecked — 26 of 30 currents files. It is derived from the tree now: 3 files
checked became 31. Worth knowing here because it means the contract gate has
been quieter than it appeared for as long as regional grids have existed.

## Coming: ESPC leaves this repository

Planned 2026-08-20 in the site repository's `PLAN.md`, to be built next
session. Recorded here because it is most of what this repository currently
carries and the change will be felt here first.

**ESPC is 91% of the published tree** — 114 MB of committed grids and 505 MB
of CI-built tiles, against 59 MB of everything else. It moves to
`espc-model-repo`, a public repository of its own, taking the currents and the
four Navy field products with it. What is left here is the observing
platforms, the storms, the buoys, the tides, the arrays, the vessels, the
sondes and the OISST fields: about 59 MB.

Two new products go to the new repository rather than this one: currents
**depth-integrated down to 200 m and down to 1000 m**, at the full 1/12° and
two frames each.

**And the tile encoding changes with the move** — integer millimeters per
second rather than decimal m/s, applied to the existing tiles as well as the
new ones. Shorter and ten times more precise at once, because the decimal
point and leading zero carry nothing. That is what makes the whole set fit
one cap: 670 MB against the 987 the current encoding would need.

Nothing about `products.toml`'s shape changes, but this repository's own
product list shrinks, and the **cross-repository contract gains a third
side**: `test-schema.mjs --roots` in the site repository has to agree with two
`products.toml` files rather than one. That agreement check already exits 2 on
disagreement and has stopped the publish before; a third side is the main risk
in the move.

