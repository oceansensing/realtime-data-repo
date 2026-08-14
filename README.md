# realtime-data-repo

The second-generation data pipeline for the [C4PO ocean
map](https://oceansensing.org/visualization/). It fetches storms, gliders,
USVs, Argo floats, currents, temperature, salinity, ice, wind and waves from
their upstream sources every hour and publishes them as static files at
`https://oceansensing.org/realtime-data-repo/map/`, with a machine-readable
health record beside them at `/status/status.json`.

It is the successor to
[`ocean-data-repo`](https://github.com/oceansensing/ocean-data-repo), designed
after a night in which five separate faults each produced a plausible-looking
state rather than an error, and one flaky HTTP 500 froze every product for
sixteen hours. The post-mortem's one-line diagnosis — **everything was
detected late where it could have been impossible by construction** — is the
design brief for this repository. The fetch scripts themselves are unchanged
and live in the site repository; what is rebuilt here is everything around
them.

## The shape

**One declaration.** `pipeline/products.toml` says everything the pipeline
knows about a product: which files are its roots, which filenames it is
allowed to write, which tile directories belong to which grids, which upstream
it leans on, how stale is too stale. The orchestrator derives the fetch steps,
the validation, the manifests, the cache keys and the publish from it. The
predecessor kept that knowledge in five hand-maintained lists (a seed list, two
cache path lists, a gap-guard list, a quarantine map), and every one of them
drifted — always silently, always on the newest product. A list that is
derived cannot fall behind, and the one list that remains (the roots) is
checked against the consumer's contract on every run.

**The product is the unit of build, validation and fate.** A product is a set
of files that are true together — a grid, its regions, its forecast frames,
its tiles. Each one is fetched, validated and published as a unit, and each
one carries its own fate for the run:

- **fresh** — fetched, validated, published.
- **held** — the fetch or validation failed; the previous version ships
  *whole*, and the reason is recorded. This is a *disclaimer*: nothing is
  removed, and what is given up is only the claim of being current.
- **carried** — not attempted on this kind of run, by design. The distinction
  from `held` matters: one is a failure, the other is a schedule.

A tile directory that cannot be brought into agreement with its grid is
**withheld** — deleted from the candidate tree, a *removal* in the strict
sense: bytes leave the publish, and the map degrades to the coarse grid it
draws at low zoom anyway. Absent is a shape the map handles honestly; a tile
tier six hours adrift of its grid is a lie with no tell. The predecessor used
one word, "withdrawal", for both of these operations, and a guard that could
not know which had happened misread a deliberate removal as damage.

**Stage, validate, swap.** Fetchers write into a stage seeded from the last
publish. Nothing reaches the candidate tree until it validates, and a product
that fails is restored from the last publish before anything downstream can
read the wreckage. The predecessor mutated its tree in place, which is why a
mid-run failure needed keep-the-previous-file logic scattered through every
script, and why a grid and its tiles could tear.

**The plan is decided once and written down.** Before anything is fetched, the
orchestrator probes the model catalogs once and writes `plan.json`: which
model run, which hours, which cache keys. The predecessor derived the hour in
four places; three of them disagreed in one night. The plan is published under
`/status/plan.json`, so the run's intent is public before its outcome.

**Content outranks bookkeeping.** The tile caches are transport, not truth:
whatever `actions/cache` restores is believed only if each tile index's
`refTime` matches the grid it would sit under, and rebuilt otherwise. The
predecessor trusted cache keys, and a cache that stored an incomplete artifact
under a key claiming completeness could not heal — the key kept hitting, the
build kept being skipped, and every subsequent run looked healthy.

**Cross-product rules belong to the contract, and only to it.** The currents
and the Navy fields come from the same model, and the map's contract requires
a Navy grid from the currents' run to sit at one of the currents' published
hours — a rule with real subtlety in it: the currents' base file is by design
the *earlier* of two frames, and a grid from a different model run is a note
rather than a failure, because upstream raggedness is the ordinary state.
The orchestrator carried its own simplified copy of that rule for exactly one
run, and the copy was wrong — it held two healthy products with a loud reason,
which is the safe direction, and it is also why the copy is gone. When the
contract objects, the gate maps the failure to its product and demotes just
that one. The OISST fields are their own product for the same spirit of
isolation: a daily analysis from a different source, so a Navy outage cannot
touch it even though one script fetches both.

**Two tiers of storage, each doing the one thing it is good at.**

- The **`published` branch** holds every small product and the status record:
  a single orphan commit, force-pushed each run, so history does not grow.
  This is what makes the accumulated state — glider tracks, USV tracks, storm
  histories, files that cannot be refetched from anywhere — durable rather
  than resident in a cache that can evict. It is also what seeds the stage,
  at clone speed, replacing the predecessor's re-download of the last publish
  over HTTP on every run.
- **`actions/cache`** carries only the tile trees (~500 MB that changes four
  times a day), keyed from the plan, saved only when this run built them, and
  verified by content on every restore.

**Fate is loud.** `status/status.json` records, per product: its fate this
run, the reason if held, the model hour it represents, and two timestamps
whose difference is the whole point — **`checked`**, the last time the
pipeline successfully attempted the product, and **`updated`**, the last time
its bytes changed. A quiet upstream and a broken pipeline look identical in
`updated`; they are day and night in `checked`. During the sixteen-hour
outage the map showed a fifteen-hour-old timestamp that nobody read because a
timestamp is arithmetic; the status file is a statement, and the map can say
"currents: held since 03:00 (HYCOM timeout)" instead of leaving the reader to
subtract.

**Two jobs, least privilege.** The build job holds no write permission at
all: it runs the fetchers, `pip install` and the contract check, and uploads
what it assembled. The publish job holds `contents: write`, `pages: write`
and `id-token: write`, and runs nothing but pinned first-party actions and
ten lines of git. A compromised transitive dependency in the build finds no
token worth stealing in its environment.

## What publishes where

```
oceansensing.org/realtime-data-repo/
  map/          the data — same layout, same files, same bytes as the
                predecessor, so a consumer retargets by changing one base URL
  status/
    status.json one object per product: fate, reason, checked, updated, hour
    plan.json   what this run intended before it started
    receipt.json  what it actually did: fates, builds, durations, sizes
```

The `map/` layout is the contract defined by `schema.ts` in the site
repository, and the site's own `test-schema.mjs` runs over the assembled tree
before anything deploys. If the tree fails the contract, the failing files are
mapped back to their products, those products are demoted to held, and the
check runs once more; only a tree that passes is published. The contract is
the consumer's, deliberately: this repository validates what it builds, but
the map's own gate has the last word.

## The run, step by step

1. **Seed** — the `published` branch is checked out and copied into the
   stage, so every fetcher starts from the last good publish.
2. **Plan** — one probe per model catalog; `plan.json` and the cache keys
   fall out. The tile caches restore into the stage.
3. **Fetch** — every step from `products.toml`, concurrently across
   upstreams, serially within one (two HYCOM reads should queue, not
   compete). A step failing marks its products held and restores their
   namespaces from the seed. A step writing outside every declared namespace
   fails the run outright — that is a bug, not weather.
4. **Validate** — per product: roots parse, and every file the headers
   advertise exists.
5. **Tiles** — restored tiles verified by content; wrong or missing tiers
   rebuilt for fresh products only; still-incoherent tiers withheld.
6. **Assemble and gate** — static seeds + the stage become the candidate,
   the site's contract check runs over it, and a failure demotes the
   product it names rather than the tree; manifests and status record what
   finally stood.
7. **Publish** — the small products and status force-push to `published`;
   the whole tree deploys to Pages. A light run that would deploy a tree
   without tiles skips the deploy but still pushes the branch, so nothing
   fetched is ever thrown away.

## Operating it

- **Dispatch a run**: Actions → *Publish realtime ocean data* → Run workflow.
  `mode: light` fetches only the products marked `light` (the storms and
  platforms) and carries the rest.
- **Read the health**: `curl -s https://oceansensing.org/realtime-data-repo/status/status.json | python3 -m json.tool`
- **First-time setup** (already done, recorded for the next repo like this):
  seed `map/` static files from the predecessor, run
  `pipeline/orchestrate.py seed-published --from <old live site>` once and
  push the result as the `published` branch, enable Pages in workflow mode.
- **The fetchers** live in
  [`oceansensing.github.io/scripts/`](https://github.com/oceansensing/oceansensing.github.io/tree/main/scripts)
  and are checked out at run time, pinned to `main` — one copy, one contract.
  Their reasoning lives in that repository's `CLAUDE.md` files.
- **Unit tests**: `python3 pipeline/test_orchestrate.py` — no network, no
  node; fake fetchers exercise every fate path. CI runs them before every
  publish, so a broken orchestrator refuses to run rather than publishing
  something strange.

## What is deliberately not here yet

- **Per-tile content addressing.** Tile builds are all-or-nothing per set;
  making the common case nearly free is queued, and contained.
- **Fetchers reading the plan.** They still decide their hour internally;
  the pipeline validates the outcome instead of dictating the input. Moving
  the decision into the plan entirely means teaching each fetcher a `--hour`
  flag, queued in the site repository's PLAN.md.
- **Cutover.** The predecessor keeps publishing on its own schedule; the
  production map still reads it. This repository runs hourly at :35 while it
  bakes in, read by the development map at `/dev/visualization/`. Cutover is
  a one-line change to `MAP_DATA` in the site's `src/config.ts`, and
  retiring the predecessor's crons is the other half.
