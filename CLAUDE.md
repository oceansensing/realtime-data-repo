# CLAUDE.md

Guidance for working in this repository. The **design** — why the pipeline
is shaped the way it is, what a product is, what the fates mean — lives in
`README.md` and is not repeated here, what has *happened* — measurements,
defects, open items — is in `PLAN.md`, and which one-way doors have closed is
`DECISIONS.md`. This file is the operator's and maintainer's half: what to
run, what must move together, and what has already gone wrong.

<!-- DOC-DOCTRINE v1 begin — identical in all ten repositories; `check:docs` holds them equal. Edit one, sync all. -->
## Where truth lives, and what "update docs" means

Ten repositories carry this project. The engine and the site:
`oceanlet.js`, `oceansensing.github.io` (the site, and every fetch script).
The orchestrator and the observations: `realtime-data-repo`. And the data
repositories, which since 2026-08-30 split **currents from fields** per model:
`espc-model-repo` (the ESPC currents — a legacy name, see below),
`espc-model-fields-repo`, `eccofs-model-currents-repo`,
`eccofs-model-fields-repo`, `mercator-model-currents-repo`,
`mercator-model-fields-repo`, and `sentinel3-data-repo` (ocean color, which
has no vector half to split). Each document answers exactly one question.

**`espc-model-repo` is the ESPC CURRENTS repository** despite its name — the
one exception to the convention, kept because its URL is a live origin and
GitHub Pages does not reliably redirect a renamed project site. Read it and
`eccofs-model-currents-repo` as the same kind of thing.

*(`eccofs-model-repo` was RENAMED to `eccofs-model-fields-repo` on 2026-08-30,
not superseded — GitHub redirects the old name, which is why a rename was
free there and is not free for `espc-model-repo`: that one has published
bytes behind a Pages URL, and Pages does not redirect what the API does.)*

**All ten carry the same four documents, and since 2026-08-31 a gate holds
them to it** — `check:docs` requires a `DECISIONS.md` tracked in git in every
repository. The last two landed that day, the site's and
`realtime-data-repo`'s, reconstructed from records that already existed:
nothing was missing but the file, which is how the site went seven weeks
without one and `realtime-data-repo` eighteen days. **This block asserted
otherwise from the day it was written** — byte-compared in the eight places there were then, and
false in two of them, because a gate on a text is a gate on the text. What it
cost is measurable: the engine promotion's own rehearsal listed *"a dated
entry in this repo's decisions and oceanlet's"* as its ninth step, and the
half with nowhere to go was simply not written.

| file | answers | tense | it is stale when |
| --- | --- | --- | --- |
| `README.md` | what this is, how to run it | present | a reader types a command or trusts a number and is wrong |
| `CLAUDE.md` | what must not be got wrong here | imperative | the next session is about to repeat a mistake |
| `PLAN.md` | what happened, measured, and what is open | dated past | "why is it like this?" has no answer here |
| `DECISIONS.md` | which one-way door closed, and when | dated | a reversal would cost a migration and nothing says so |
| `docs/` | contracts, ledgers and the guide | present | it describes an interface, a divergence or a concept that has moved on |

**`docs/` is a first-class part of "all docs", not an appendix** — the owner
asked for that explicitly on 2026-08-28, and the reason is that these are the
documents everything else points AT. A frozen contract, a divergence ledger
whose rows are pinned by tests, a guide that introduces the model: each is
the thing a reader is sent to when the short answer will not do, so each is
the worst place for a claim that has quietly stopped being true.

**"Update docs" means a sweep of all ten repositories, not the one in hand.**
Docs are part of the change, never a follow-up and never a separate ask. Six
questions, asked of every repository the change touched:

1. Did a command, a path, a script name or a number a reader would type or
   trust move? → `README.md`
2. Did a rule, a trap, or a things-that-must-move-together change or come to
   light? → `CLAUDE.md`
3. Did something *happen* — a measurement, a defect, a yield, a mechanism, an
   open question opened or answered? → `PLAN.md`
4. Did a one-way door close — **or has one already recorded stopped being
   fully true**? → `DECISIONS.md`, in **every** repository the change
   touched. All ten carry one, so this is no longer the
   engine's question with seven exemptions; the amendment half is here
   because two entries needed one within a day of being written.
5. Did an interface, a deliberate divergence, or a concept the guide explains
   move? → the matching file under `docs/`
6. **Does a document in another repository now say something false because of
   this change?** → fix it there, in the same sitting.

**Question 6 is the one that gets missed, and it is why this block is
identical in ten places.** Measured 2026-08-28: one tile-tier measurement
falsified `espc-model-repo`'s README, its `products.toml` header and the
site's README at once. Two were found; the third took a reminder from the
owner, who then asked for this doctrine.

**Two repositories are deliberately NOT in the list above, on opposite
grounds, and both are named because an exclusion nobody wrote down is
indistinguishable from an oversight.**

`ocean-now`, the iOS port, **consumes this system** — it mirrors the site's
published contract. It is not swept by these six questions and does not carry
this block; it has a lighter mechanism instead, a pending list in its parity
ledger, and the two repositories whose changes can reach it (the engine and
the site) each say so in their own section. It is named here because "four"
was read as "all of them" for two weeks while that ledger drifted 176 commits
behind with nothing noticing — question 6 failing at the granularity of a
whole repository rather than a document.

`hab-data-repo` is excluded on the opposite ground: **it does not touch the
ocean map at all** (the owner's call, 2026-08-31). It publishes the bloom
photographs for a different part of the website, reached through `HAB_DATA`
in `src/config.ts`, and carries no interface anything here codes against
beyond a URL and a filename convention. It needs no mechanism, not even a
lighter one — nothing in these ten can falsify a claim in it, and it cannot
falsify one here. Do not mix it in.

Adding a repository to the list above is therefore a real act: it buys the
sweep, and leaving one off **silently** costs exactly what `ocean-now` cost.

A number in prose is only as good as its anchor. `check:docs` gates every
claim it can tie to a source constant and nothing else, so when a figure has
no anchor — a measurement, a live reading, a byte count off a build log —
write **where it was measured and when**, or the next reader cannot tell a
fact from a guess that aged.
<!-- DOC-DOCTRINE v1 end -->

## The five Navy scalars have gone, and what their going left behind

**Moved 2026-08-31** to `espc-model-fields-repo`: `sst-navy`, `sss-navy`,
`sic-navy`, `sit-navy` and `ssh-navy`. This repository holds **no ESPC product
at all** now, and one subject: observations.

**The `fields` step is scoped, and it must stay scoped.**
`fetch-ocean-fields.py` publishes six families (2026-08-31) and this
repository owns one, so the step carries `--only=oisst`. Left bare it would fetch the Navy fields
again and write `sst-navy.json` into a tree that no longer declares it — and
the write fence would refuse the run, **every product, on the next cron**. Not
a slow degradation; an immediate stop.

**A product is the unit of OWNERSHIP; a step is the unit of EXECUTION.** They
are one change, never two. The site's `check:docs` holds this across every
origin now, in both directions, and the other repository met the same fault
from the opposite side on its first run.

**No cache steps here any more**, because no product declares a cache. A
Restore or Save reading a `cache-paths-*` output nothing emits fails on an
empty path — how a cache step outliving its product died with no reason in
August. A new tiled product here needs its pair back.

**Their files cleaned themselves up in two runs, and knowing why keeps the
next migration from either panicking or trusting too much.**

The two artifacts a run uploads are assembled differently. `branch-out` — the
`published` branch — is built from the DECLARED products, so undeclaring a
product drops its files from the bank on the first run. `out` — the Pages tree
— is built from the STAGE, which was seeded from the previous branch, so it
carries them one run longer. Measured 2026-08-31: the four tile tiers 404 at
once (tiers are paired to their grid under `tiles.match`), all five grids
still 200, gone the run after.

**That is only true for a product that LEAVES.** Rename a file inside a
product that still exists and its `writes` glob still matches, so `branch-out`
goes on banking it and nothing ever removes it — 32 files and 43.8 MB in
August, found only because somebody went looking. **Undeclaring self-heals;
renaming does not.**

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

  **That mapping is a regex over the consumer's own output, and it was
  silently missing most of it until 2026-08-29.** It read
  `^FAIL\s+(\S+?):` — a file name up to the first colon — which matches
  `FAIL  alpha.json: ...` and matches *nothing at all* in
  `FAIL  alpha.json asset sd1030: ...`, the shape every content check uses
  when it names WHICH record is wrong. A line that matches nothing yields no
  culprit **and no `unmapped` entry**, so the gate fell through to the fatal
  branch with no attribution, no demote, no retry, and not one word in the
  log saying why. Everything this file says about demoting one product was
  true only for whole-file failures.

  Cost: one Saildrone published `deployed: null`, and all twelve products
  froze for six hours. It now reads `^FAIL\s+([^\s:]+)` — stop at
  whitespace OR colon — and a token owning nothing still lands in `unmapped`
  and is still fatal, but says so. **When you touch a gate that parses
  another repository's output, test it against a real line from that
  repository**, not against the shape you have in mind.

- **"Which tiers does this product owe?" is answered from the GRIDS, never
  from a list of directory names.** `expected_tiers(spec)` is the only right
  answer; `tile_pairs` walks what exists and structurally cannot see an
  absent tier. Three separate call sites once read
  `[d for d, g in tiles['match'] if '*' not in d]`, which filters out every
  starred pattern — so a forecast frame's tier (`tiles-f*h`) was invisible to
  the build trigger, to the produced-nothing check AND to the withheld
  accounting. Live on 2026-08-29 the ESPC surface currents had no `tiles-f18h`
  for hours, `receipt.json` said the product had nothing withheld, and the map
  — which opens each layer on the frame nearest the reader — drew that frame
  at 0.24° instead of 0.08°. If you add a fourth place that needs the owed
  list, call `expected_tiers`.

- **`ageHours` is a magnitude; `nearestOffsetHours` carries the sign.**
  Positive is behind the reader, negative is ahead. Read the signed one when
  diagnosing: a forecast published too far into the future and data left
  behind report the same `ageHours`, and on 2026-08-29 that sent an
  investigation at the wrong half of the pipeline. `nearest_frame_age` is
  computed as `abs()` of the offset, never beside it, so the two cannot
  drift.

## Commands

```sh
python3 pipeline/test_orchestrate.py   # the unit suite; CI runs it before every publish
```

**Python 3.10 or newer, and on the sync machine that is not the default.**
`orchestrate.py` uses `str | None` annotations, so the system
`/usr/bin/python3` (3.9.6) fails at *import* — `TypeError: unsupported
operand type(s) for |` on a line that is correct — and it fails that way for
the suite AND for `orchestrate.py --help`, which makes it look like the file
is broken. Conda's is 3.13 but its init is in `~/.zshrc`, which only
interactive shells read, so a script or an agent shell will not have it:

```sh
PATH=/opt/anaconda3/bin:$PATH python3 pipeline/test_orchestrate.py
```

CI provisions its own and never meets this.

There is no other local entry point to memorize; the workflow runs
`orchestrate.py seed`, `plan`, then `run`, and each can be run by hand in
that order. A full local rehearsal against real upstreams:

```sh
git clone https://github.com/oceansensing/oceansensing.github.io site
python3 pipeline/orchestrate.py seed-published --from https://oceansensing.org/realtime-data-repo/map
cp -R branch-out published
python3 pipeline/orchestrate.py seed
python3 pipeline/orchestrate.py plan
python3 pipeline/orchestrate.py run
```

**A rehearsal is polite by the probe rather than by a mode now.** There was
a `--mode light` that fetched assets only and skipped the HYCOM tile
builds; it was retired on 2026-08-27 and `--mode` accepts only `full`. What
replaced it is better for a rehearsal anyway: the probe-first exits mean a
local run against real upstreams fetches only what has actually moved since
the seed, and the real contract still runs over the real assembled tree.
`site/`,
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
- **And the fix above was put inside the fresh-only branch, where a HELD
  product could not reach it.** 2026-08-28, HYCOM's `.das` timing out: the
  ESPC 50 m and depth-averaged currents held, their tile directories were
  gone, and their carried-forward grids advertised `tileIndex` against a
  404 for two hours. Surface stayed fresh, so its build ran and its tier
  was right — one layer correct and four wrong, which is what made it hard
  to see. **Rebuilding is for fresh products; accounting is for all of
  them.** The seeding is unconditional now. Note what the mutation test
  found on the way: dropping the `index.json` existence check *survived*,
  because `final` corrects the state back through the walk — the leak is
  the *reason*, into the manifest and the receipt's `withheld` map, both
  read as lists of what left. A control that only checks `state` cannot
  see it.

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

**Two more fields arrived after the shape was agreed**, and both were forced
by building the consumer rather than chosen:

- **`source`** — holding one model's products to one hour means knowing which
  products are one model. Grouping by the run is circular, and ECMWF and ESPC
  both publish 12Z runs, so unrelated products would collide. Hardcoding the
  ESPC list is the shape this repository has an entry about.
- **`hours`** — every hour a product publishes, not only its base. The rule is
  not "one model, one hour": the currents publish two frames and their base
  file is deliberately the earlier one, so a temperature at the later frame's
  hour is correct. A consumer given only the base compared single hours and
  reported that correct pairing as a fault on its very first comparison
  against live data. A simplified second copy of a rule disagreeing with the
  original — met by writing one.

`stamp_of` reads all four from one header, for the reason the first two are
one reading: a product's stamp must not be assembled from different files.

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
- ~~The ESPC hour-agreement rule reads a hardcoded product list.~~
  **Corrected 2026-08-31**: it is derived from each grid's own `source`
  header, so a product joins the check the day it publishes and cannot leave
  it by leaving a list. The pruning problem this list is about is unchanged;
  the reason it is ungated is one reason shorter.
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

## The engine is not the tree

`PIPELINE_ROOT` overrides where the orchestrator operates, defaulting to the
parent of its own file — so this repository behaves exactly as it always has
and nothing about it moved.

It exists so a **second data repository runs this orchestrator without owning
a copy of it**. `espc-model-repo` checks this repository out as its engine and
points the variable at its own workspace, which is the arrangement both
repositories already have with the site repository for the fetch scripts: the
code lives once, the schedule and the storage live per repository.

The alternative was copying 988 lines into every new data repository. That is
the shape this project has an entry about — a fault would have to be found
twice and fixed twice, or fixed once and left in the other — and three faults
were found in this file in a single day.

**`products.toml` follows the root, not the file**, and that is the whole
point rather than a detail. Each repository declares its own products; an
engine reading its neighbour's declaration would assemble and publish the
wrong repository's tree.

The test for it runs in a **subprocess with the variable actually set**, and
the first version did not: it asserted the paths hang off `ROOT` using the
already-imported module, where `PIPELINE_ROOT` is unset and `ROOT` is the
file's own parent — so a constant hardcoded straight back to
`Path(__file__).parent.parent` satisfied it exactly and the mutation walked
through. A value read at import can only be tested by a fresh import.

## How a run starts, and why a push does not

Two crons and `workflow_dispatch`. **No push trigger**, dropped 2026-08-21
after measuring what one cost.

**Every run is a full run as of 2026-08-27** — the light mode is gone, so
read the paragraphs below as the record of an incident rather than a
description of the machinery. It existed on the number they quote, 56
minutes against 5, and the probe-first exits removed it: a full run whose
probes all rested measured 3 min 59 s, faster than the light run it was
avoiding, because those minutes are the observation fetches a light run
performed anyway. What the split still cost was nine hours of stale Navy
fields, the runs GitHub delivered being the light ones, which skipped those
steps by construction. The conclusion below is unchanged and is still why
there is no push trigger.

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

**Making a push run *light* was the other candidate and was worse for the
case that matters.** A push here is usually a change to a fetcher or to the
orchestrator, and a light run performed one of the five steps — you would be
watching a run that did not do the thing you changed, which defeats the
deploy-and-watch habit rather than serving it. (Moot since the split was
retired, and kept because the reasoning applies to any future "cheap run"
proposal.)

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

**ESPC was 91% of the published tree**, and the currents MOVED on 2026-08-22
— this passage described the move in the future tense until the doc sweep of
2026-08-28. The figures it planned against (114 MB of grids, 505 MB of tiles)
predated the third depth cap and the second forecast lead; re-measured
2026-08-28 the tier is 738.7 MB and the grids 93 MB, and `espc-model-repo` is
832 MB of a 1 GB cap. **The four Navy field products did NOT go** — the
owner's call, on storage — so what is left here is those and the observing
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

