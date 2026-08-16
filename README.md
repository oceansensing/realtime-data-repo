# realtime-data-repo

The data pipeline behind the [C4PO ocean
map](https://oceansensing.org/visualization/) — the production service
since 2026-08-14. It fetches storms, gliders, USVs, Argo floats, currents,
temperature, salinity, ice, wind and waves from their upstream sources
through the hour and publishes them as static files at
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
   finally stood. The **static half** — the isobaths, the offline
   coastline, the borders, 135 MB the seafloor never changes and CI cannot
   rebuild — is committed in this repository under `map/` and copied in
   here; `[static]` in `products.toml` names what must be present and
   assemble refuses to run without it. Declared because it went missing
   silently once: the cutover carried every pipeline and no static file,
   and four lazily-fetched layers 404'd their way to nothing on the live
   map for a day.
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

### If the site repository ever goes private

**That checkout is the single thing standing between this pipeline and a dead
stop.** It works today on anonymous read: `actions/checkout` falls back to
this workflow's own `GITHUB_TOKEN`, which is scoped to *this* repository and
holds no grant on the site at all. Make the site private with nothing else in
place and the next run fails before it has fetched anything — not one product
going stale, every product, no data published at all.

The workflow already carries the plumbing, and it is **inert**:
`ssh-key: ${{ secrets.PIPELINES_SSH_KEY }}`. Verified against
`actions/checkout` at its pinned commit rather than assumed — `token`
defaults to `${{ github.token }}`, and the auth helper branches
`if (this.settings.sshKey) { … } else { // Configure HTTPS instead of SSH }`,
so an unset secret is an empty string, which is falsy, and the step behaves
exactly as it always has.

**A read-only deploy key, chosen on what this step actually needs.** It reads
one repository and writes nothing. A deploy key is scoped to a single
repository and read-only *by construction* rather than by configuration; it
does not expire, where a fine-grained PAT would stop this pipeline dead on
its expiry date; and it belongs to no person, so it survives somebody leaving
the org. A GitHub App would also clear those bars and costs more moving parts
for capabilities not wanted here.

**Do it in this order, and the order is the whole point.**

1. Generate a key pair with **no passphrase** — Actions cannot type one:

   ```sh
   ssh-keygen -t ed25519 -C "pipelines-checkout" -f pipelines_key -N ""
   ```

2. Put the **public** half (`pipelines_key.pub`) on the *site* repository:
   Settings → Deploy keys → Add deploy key. **Leave "Allow write access"
   unchecked** — it is the one control on that page that quietly turns a read
   credential into a write one.

3. Put the **private** half in a secret on **both** this repository *and*
   `ocean-data-repo`, straight from the file so a multi-line key never goes
   through a clipboard:

   ```sh
   gh secret set PIPELINES_SSH_KEY --repo oceansensing/realtime-data-repo < pipelines_key
   gh secret set PIPELINES_SSH_KEY --repo oceansensing/ocean-data-repo < pipelines_key
   ```

   Secrets do not cross repositories, and setting it only here leaves the
   standby broken in exactly the way this section is about. One key serves
   both: the public half sits once on the site repository.

4. `rm pipelines_key pipelines_key.pub`. Losing them costs two minutes and a
   new pair; keeping them lying about costs more.

5. **Dispatch a run and watch it go green while the site is still public.**
   This is the step people skip and the only one that proves anything: a key
   that is wrong fails here, harmlessly, with the pipeline still working
   underneath it. Do the same for `ocean-data-repo` — a standby that has not
   been shown to start is not a standby.

6. Only then make the site repository private, and watch the next scheduled
   run.

**Neither half is ever committed.** The private key lives in Actions secrets,
which is encrypted storage attached to the repository rather than content in
the tree — never in a diff, never in the published Pages output, masked if a
log ever echoes it. A secret in a *public* repository is still secret:
GitHub withholds secrets from workflows triggered by pull requests from
forks, and neither data repository has a `pull_request` or
`pull_request_target` trigger at all. The trust boundary is people with push
access here.

If the checkout does fail, the run says so in its own words rather than
leaving you with `Permission denied (publickey)`, which names the mechanism
and not the fix.

## How it compares to the predecessor, measured

The claims above are design; these are the differences that can be checked,
as measured at first publish (2026-08-14).

- **Blast radius of one product failing: everything → that product.**
  The night that prompted this repository, one flaky HTTP 500 on the ice
  froze every product for 16.5 hours, because the whole tree published or
  nothing did. This pipeline's *first run* held two products — and the
  other four published fresh, on schedule, with the holds' reason stated in
  the status file. Demonstrated, not projected.
- **Detection of a fault: hours → one page load.** The predecessor's only
  health signal was a timestamp on the map, which cannot distinguish a
  quiet upstream from a broken pipeline — the ambiguity that let the outage
  run 16 hours. `checked` versus `updated` in `status/status.json`
  separates exactly those two faults, per product, with the reason and the
  run URL beside them.
- **A poisoned cache: manual surgery → one automatic rebuild.** The
  predecessor trusted cache keys; an incomplete entry kept hitting and
  could not heal, and the repair took two hand-bumped key versions and a
  day of absent tiles. Here every restore is verified against the grid's
  own hour and rebuilt on mismatch.
- **Orchestration: 641 lines of bash-in-YAML → 204 lines of YAML with no
  decisions in it**, around an orchestrator of under 800 lines of
  standard-library Python with a unit suite that runs before every publish
  and mutation-tested load-bearing checks. It is debuggable on a laptop;
  the predecessor was debuggable only by pushing commits at CI. The suite
  caught its first real bug before the first publish.
- **Hand-kept lists: five → one declaration, self-checked.** Each of the
  predecessor's five lists drifted at least once, silently, on the newest
  product. The one list here is refused at run time if it disagrees with
  the consumer's contract.
- **Accumulated state: resident → durable.** Tracks and storm histories
  cannot be refetched; the predecessor kept them only in the live artifact
  and an evictable cache. The `published` branch banks them every run,
  including runs that cannot deploy.
- **Write-token exposure to third-party code: full → zero.** The
  predecessor's one job held Pages and OIDC tokens while running
  `pip install`; here the job with tokens runs only SHA-pinned first-party
  actions, and the job running third-party code can write nothing.

**And what is honestly not better.** The fetchers, the upstreams and their
fragility are identical — an outage now produces *labeled* staleness, not
less of it. Full-run wall time is roughly unchanged, since tile builds
dominate. A deploy is still whole-tree, because Pages is. There was also
one real regression at first publish: storms refreshed hourly here against
three times an hour on the predecessor. Closed the same day — light runs
are scheduled at :15 and :55 now, matching the predecessor's three
publishes an hour.

## License

Copyright (c) 2026 Donglai Gong and C4PO. All rights reserved — see
[LICENSE.md](LICENSE.md). The repository is public so the data can be
served from GitHub Pages; that is not a grant of any license. The
scientific data itself belongs to the bodies that produced it, each named
in the LICENSE and credited on the map.

## What is deliberately not here yet

- **Per-tile content addressing.** Tile builds are all-or-nothing per set;
  making the common case nearly free is queued, and contained.
- **Fetchers reading the plan.** They still decide their hour internally;
  the pipeline validates the outcome instead of dictating the input. Moving
  the decision into the plan entirely means teaching each fetcher a `--hour`
  flag, queued in the site repository's PLAN.md.
- **The predecessor's freeze.** Cutover happened on 2026-08-14 — `MAP_DATA`
  in the site's `src/config.ts` points here, after the development map ran
  against this pipeline first and proved it. The predecessor deliberately
  keeps publishing on its own crons for a few days as a warm standby
  (switching back is that one string again), and is then to be frozen in
  place: workflow disabled, nothing deleted, a readable record and a
  restartable fallback.
