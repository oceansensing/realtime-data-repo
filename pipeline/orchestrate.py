#!/usr/bin/env python3
"""The orchestrator. Everything between the fetch scripts and the publish.

Subcommands, in the order a run uses them:

  seed            copy the published branch's data into the stage, so every
                  fetcher starts from the last good publish
  plan            probe the model catalogs once, write plan.json, and emit
                  the tile cache keys for the workflow to restore against
  run             fetch, validate, judge quality, resolve fates, build tiles,
                  assemble the candidate tree, write manifests and status, gate on the
                  consumer's contract, and say what may publish
  seed-published  one-time bootstrap: pull the current publish from the old
                  live site into branch-out/, ready to push as `published`

Standard library only, like the fetchers it drives. The declaration it works
from is products.toml, next to this file; the design it implements is the
repository README. The fetchers live in the site repository and are checked
out under site/ — this file never reimplements what they know, it only
decides what becomes of what they wrote.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import tomllib
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# **The tree this operates on, which is not necessarily the one it lives in.**
#
# `PIPELINE_ROOT` exists so a second data repository can run this orchestrator
# without owning a copy of it. `espc-model-repo` checks this repository out as
# its engine and points the variable at its own workspace, exactly as both
# repositories already check out the site repository for the fetchers — the
# code lives once, the schedule and the storage live per repository.
#
# The alternative was copying 988 lines into every new data repository, which
# is the shape this project has an entry about: a fix would have to be made
# twice or not at all, and three faults were found in this file in one day.
#
# It defaults to the parent of this file, so a repository holding its own
# copy — this one — behaves exactly as before and nothing about it moved.
#
# **`products.toml` follows the root, not the file.** That is the whole point:
# each repository declares its own products, and an engine reading its own
# neighbor's declaration would publish the wrong repository's tree.
ROOT = Path(os.environ.get('PIPELINE_ROOT') or Path(__file__).resolve().parent.parent)
SITE = ROOT / 'site'                 # checkout of oceansensing.github.io
STAGE = SITE / 'public' / 'map'      # where the fetchers read and write
PUBLISHED = ROOT / 'published'       # checkout of the `published` branch
OUT = ROOT / 'out'                   # the candidate tree Pages deploys
BRANCH = ROOT / 'branch-out'         # what the next `published` commit holds
PLAN_FILE = ROOT / 'plan.json'

# Bump alongside any change to what the tiles *contain* — a format change is
# exactly when yesterday's tiles under today's refTime would fool the content
# check.
#
# **And a change to the tile *paths* orphans every existing entry whether this
# is bumped or not**, which is worth knowing before reading a miss as a bug.
# `actions/cache` computes a version of its own from the `path` inputs, and
# only matches entries with the same one — so the restore-keys prefix, which
# looks like a safety net, does not reach across a path change either.
# Measured 2026-08-21, splitting the Navy fields into two products: the
# `field-tiles` match list went from four tile directories to two, and the
# next light run reported `Cache not found for input keys:
# field-tiles-v2-…, field-tiles-v2-` against an entry with exactly that
# prefix sitting in the cache. The currents restored from an exact key in the
# same run, which is the control — their paths did not move.
#
# **Confirmed by the timestamps, after being doubted on a partial reading.**
# Every miss is before the first save under the new paths and every hit is
# after it: 22:43:39 `Cache not found`, 23:02:36 the save that created the
# two-product entries, 23:04:03 `Cache restored from key: field-tiles-v2-…`.
# The 21:24 miss is the one that carries the argument — a *light* run, so the
# `field-tiles-v2-` prefix was supplied and is listed in its own error, with
# an entry carrying exactly that prefix sitting in the cache since 18:54.
# Nothing but the path version explains it.
#
# So a `tiles.match` edit costs one cold rebuild, and the light-gap guard
# turns that into a withheld deploy for one cycle. That is the guard being
# right; the thing to do is expect it, not to widen the guard. Bumping this
# does not prevent the miss — it makes it legible, which is the whole reason
# to bump on the way in rather than to explain it afterwards.
CACHE_VERSION = 'v2'


def utcnow():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(msg):
    print(msg, flush=True)


def gh_output(name, value):
    """Hand a value to the workflow, if there is one listening."""
    path = os.environ.get('GITHUB_OUTPUT')
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as fh:
        if '\n' in value:
            fh.write(f'{name}<<__ORCHESTRATE__\n{value}\n__ORCHESTRATE__\n')
        else:
            fh.write(f'{name}={value}\n')


def load_config():
    return parse_config((ROOT / 'pipeline' / 'products.toml').read_text())


def parse_config(text):
    cfg = tomllib.loads(text)
    default_timeout = cfg.get('defaults', {}).get('timeout_minutes', 30)
    for step in cfg['steps'].values():
        step.setdefault('timeout_minutes', default_timeout)
        step.setdefault('light', False)
    for name, product in cfg['products'].items():
        if product['step'] not in cfg['steps']:
            raise SystemExit(f'products.toml: {name} names unknown step {product["step"]}')
    return cfg


# --- the stage, measured by content ----------------------------------------
# Change detection is by hash rather than mtime, because a fetcher re-writing
# the same bytes is the ordinary case mid-window, and `updated` claiming a
# change that did not happen would make the one honest timestamp a liar.

def scan_stage():
    if not STAGE.is_dir():
        return {}
    out = {}
    for f in sorted(STAGE.iterdir()):
        if f.is_file():
            out[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def match_any(name, globs):
    from fnmatch import fnmatch
    return any(fnmatch(name, g) for g in globs)


def owners_of(name, products):
    """Which products claim this top-level filename."""
    return [p for p, spec in products.items() if match_any(name, spec['writes'])]


# --- reading the data's own statements --------------------------------------

def header_of(path):
    """The header of a published grid, or None for the files that carry none
    (the asset and float lists are plain feature collections)."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    body = doc[0] if isinstance(doc, list) and doc else doc
    if isinstance(body, dict):
        head = body.get('header')
        if isinstance(head, dict):
            return head
    return None


def advertised(head):
    """Every file a header links to, as bare names — the same walk the
    predecessor's backfill used, here as a completeness check."""
    for detail in head.get('details', []) or []:
        yield detail['url'].rsplit('/', 1)[-1]
    for frame in head.get('forecast', []) or []:
        yield frame['url'].rsplit('/', 1)[-1]


def closure(roots):
    """All files reachable from these roots through their headers."""
    seen = []
    queue = list(roots)
    visited = set()
    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        seen.append(name)
        head = header_of(STAGE / name)
        if head:
            queue.extend(advertised(head))
    return seen


def stamp_of(product_spec):
    """The model hour, run and source a product currently presents.

    **One function because they are one reading.** Taken separately, the hour
    could come from the first root carrying a `refTime` and the run from a
    different root carrying a `modelRun` — two facts about two files,
    reported as one product's stamp. The pair is what the cross-origin hour
    rule compares: same run and a different hour is a fault, a different run
    is upstream lag and only a note, and answering those from different files
    would make the distinction meaningless.

    **`source` is here because the hour rule cannot be applied without it.**
    Holding one model's products to one hour across origins means knowing
    which products are one model, and the manifest is all a consumer has. The
    alternatives were both bad: grouping by the run is circular, since the run
    is half of what is being compared, and ECMWF and ESPC both publish 12Z
    runs, so unrelated products would collide. Hardcoding the ESPC product
    list is the shape this repository has an entry about.

    **`hours` is every hour the product publishes, not just the base**, and
    that distinction was found by running the check against live data. The
    rule is not "one model, one hour" — the currents publish two frames and
    their *base* file is deliberately the earlier of them, so a temperature
    at the later frame's hour is correct and a check comparing single hours
    calls it a fault. `test-schema.mjs` has always read the frame list; a
    manifest carrying only the base cannot express the same rule, and a
    consumer that tried would be a simplified copy disagreeing with the
    original — which is what happened, on the first comparison it ever made.

    `(None, None, None, [])` for products whose files carry no header at all.
    """
    for root in product_spec['roots']:
        head = header_of(STAGE / root)
        if head and head.get('refTime'):
            hours = [head['refTime']] + [
                f['valid'] for f in (head.get('forecast') or [])
                if isinstance(f, dict) and f.get('valid')
            ]
            # Ordered, deduplicated: the base is usually the first frame too.
            seen = list(dict.fromkeys(hours))
            return head['refTime'], head.get('modelRun'), head.get('source'), seen
    return None, None, None, []


def hour_of(product_spec):
    """Just the hour. Kept for the callers that only want it."""
    return stamp_of(product_spec)[0]


# --- tile directories, matched to the grids they must agree with ------------

def split_glob(pattern):
    """One `*` at most, by declaration."""
    if '*' not in pattern:
        return pattern, None
    prefix, suffix = pattern.split('*', 1)
    return prefix, suffix


def tile_pairs(spec):
    """(directory, grid file) pairs for every tile directory now in the
    stage, resolved through the declaration's match table. A directory is
    paired with its *first* matching entry, so the exact names must precede
    the starred ones in products.toml."""
    from fnmatch import fnmatch
    pairs = []
    if not STAGE.is_dir():
        return pairs
    dirs = sorted(d.name for d in STAGE.iterdir() if d.is_dir())
    for dirname in dirs:
        for dglob, gpattern in spec['tiles']['match']:
            if not fnmatch(dirname, dglob):
                continue
            prefix, suffix = split_glob(dglob)
            if suffix is None:
                grid = gpattern
            else:
                star = dirname[len(prefix):len(dirname) - len(suffix)]
                grid = gpattern.replace('*', star)
            pairs.append((dirname, grid))
            break
    return pairs


def tile_dir_state(dirname, grid):
    """How a tile directory stands relative to its grid: ('ok', refTime),
    ('orphan', ...) when the grid is gone, or ('adrift', why)."""
    head = header_of(STAGE / grid)
    index = STAGE / dirname / 'index.json'
    if head is None:
        return ('orphan', f'{grid} absent or unreadable')
    try:
        idx = json.loads(index.read_text())
    except (OSError, ValueError):
        return ('adrift', 'no readable index.json')
    if idx.get('refTime') != head.get('refTime'):
        return ('adrift', f'tiles {idx.get("refTime")} under grid {head.get("refTime")}')
    return ('ok', head.get('refTime'))


def unadvertise_tiles(path):
    """Drop `tileIndex` from a grid's header(s). Returns True if it changed.

    **A grid must not advertise a tier the publish has just withheld.** The
    writers bake `tileIndex` into every header, which is right when the tiles
    go out beside it and a false claim the moment the quarantine drops them —
    and the publish knows it is false at the instant it makes it.

    Measured 2026-08-16: `currents.json` went out carrying
    `tileIndex: /map/tiles/index.json` while both tile directories had been
    withheld for being another hour, so every reader fetched a 404 per layer
    per view. The map catches that and the regional grids stand, which is the
    intended degradation and is not the problem; the doomed request is.

    Both file shapes, because the currents are a list of two grids and the
    scalars a single object — `header_of` reads the first of a list, and this
    has to reach *all* of them or the second depth keeps advertising."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    bodies = doc if isinstance(doc, list) else [doc]
    changed = False
    for body in bodies:
        if isinstance(body, dict) and isinstance(body.get('header'), dict):
            if body['header'].pop('tileIndex', None) is not None:
                changed = True
    if changed:
        path.write_text(json.dumps(doc))
    return changed


# --- restoring a product from the seed ---------------------------------------

def restore_namespace(spec):
    """Put a product's namespace back the way the last publish had it: the
    published copies over the stage, and staged files with no published
    counterpart removed. Exact by construction — the globs are the list."""
    from fnmatch import fnmatch
    src = PUBLISHED / 'map'
    published = set()
    if src.is_dir():
        for f in src.iterdir():
            if f.is_file() and match_any(f.name, spec['writes']):
                shutil.copy2(f, STAGE / f.name)
                published.add(f.name)
    for f in list(STAGE.iterdir()) if STAGE.is_dir() else []:
        if f.is_file() and match_any(f.name, spec['writes']) and f.name not in published:
            f.unlink()


# --- subprocesses ------------------------------------------------------------

def run_cmd(cmd, cwd, timeout_min, label):
    """Run one command. Returns (ok, detail, stdout, stderr) — the streams
    stay separate because the tile-key probes print progress to stderr and
    the key to stdout, and a merged read would pollute the key."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, timeout=timeout_min * 60,
            capture_output=True, text=True)
    except subprocess.TimeoutExpired as exc:
        return (False, f'timed out after {timeout_min} min',
                (exc.stdout or ''), (exc.stderr or ''))
    except OSError as exc:
        return False, str(exc), '', ''
    if proc.returncode != 0:
        return False, f'exit {proc.returncode}', proc.stdout, proc.stderr
    return True, 'ok', proc.stdout, proc.stderr


# --- subcommands -------------------------------------------------------------

def cmd_seed(cfg):
    STAGE.mkdir(parents=True, exist_ok=True)
    src = PUBLISHED / 'map'
    if not src.is_dir():
        log('seed: no published branch checkout — starting cold')
        return 0
    count = 0
    for f in src.rglob('*'):
        if f.is_file():
            dest = STAGE / f.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            count += 1
    log(f'seed: {count} files from the last publish')
    return 0


def caches_without_a_consumer(caches):
    """Declared tile caches that no workflow step in this repository reads.

    **The hardcoded-list shape, in YAML, where nothing can derive it away.**
    `cmd_plan` emits `cache-key-<name>` for every product declaring tiles;
    the workflow needs one `actions/cache/restore` and one
    `actions/cache/save` per name, written out by hand because a matrix
    would need separate jobs. So a product that brings a new cache gets no
    caching at all until somebody remembers two steps — and that failure is
    **invisible**: the tiles are simply rebuilt from scratch every run and
    the published output is correct.

    Reported rather than fatal, and the severity is why. A roots mismatch
    publishes a tree the map cannot read; this publishes the right tree
    slowly. A gate that stops a publish over minutes is one that gets
    switched off.

    Read from ROOT, not from beside this file: the orchestrator is checked
    out as an engine by other repositories, and it is *their* workflow that
    has to carry the steps.
    """
    d = ROOT / '.github' / 'workflows'
    text = ''
    for f in sorted(d.glob('*.yml')) + sorted(d.glob('*.yaml')):
        try:
            text += f.read_text()
        except OSError:
            pass
    # No workflows readable at all is not evidence of a missing step — it is
    # this check being unable to see, which is a different claim. Say
    # nothing rather than name every cache.
    if not text:
        return [], []
    return ([c for c in caches if f'cache-key-{c}' not in text],
            sorted({c for c in re.findall(r'cache-key-([a-z0-9-]+)', text)}
                   - set(caches)))


def cmd_plan(cfg, mode):
    plan = {'schema': 1, 'generated': utcnow(), 'mode': mode, 'products': {}}
    for name, spec in cfg['products'].items():
        if 'tiles' not in spec:
            continue
        tiles = spec['tiles']
        ok, detail, out, err = run_cmd(tiles['key'], SITE, 5, f'plan:{name}')
        if err.strip():
            log(err.rstrip())
        key = out.strip().splitlines()[-1].strip() if ok and out.strip() else ''
        if not ok:
            log(f'plan: {name} probe failed ({detail}) — tiles unplanned this run')
        plan['products'][name] = {'tile_key': key}
        cache_key = f'{tiles["cache"]}-{CACHE_VERSION}-{key or "unplanned"}'
        gh_output(f'cache-key-{tiles["cache"]}', cache_key)
        # Version-scoped, so a light run's prefix restore can never reach
        # across a CACHE_VERSION bump — a format change is exactly when
        # yesterday's tiles under today's refTime would fool the content
        # check.
        gh_output(f'cache-prefix-{tiles["cache"]}',
                  f'{tiles["cache"]}-{CACHE_VERSION}-')
        paths = '\n'.join(f'site/public/map/{d}' for d, _ in tiles['match'])
        gh_output(f'cache-paths-{tiles["cache"]}', paths)
        log(f'plan: {name} -> {cache_key}')
    unread, unfed = caches_without_a_consumer(
        [s['tiles']['cache'] for s in cfg['products'].values() if 'tiles' in s])
    for cache in unread:
        log(f'plan: nothing reads cache-key-{cache} — this workflow has no'
            f' Restore/Save pair for it, so those tiles rebuild every run')
    # **The inverse, and it is fatal rather than wasteful.** A workflow step
    # naming a cache no product declares gets an *empty* key, and
    # `actions/cache` refuses that with `Input required and not supplied:
    # key` — a message that names neither the cache nor the reason. Measured
    # 2026-08-22: removing a product from espc-model-repo's products.toml
    # left its two steps behind and the next run died there, before fetching
    # anything.
    #
    # Reported here because `plan` runs before those steps, so the log says
    # why moments before the cryptic failure. Exiting non-zero as well would
    # only move the failure earlier without making it clearer, and `plan`
    # succeeding is what lets the run reach a step whose own error the reader
    # can now interpret.
    for cache in unfed:
        log(f'plan: this workflow reads cache-key-{cache} and no product'
            f' declares that cache — the Restore step will fail with "Input'
            f' required and not supplied: key". Remove the Restore/Save pair,'
            f' or give a product a [tiles] block naming it.')
    PLAN_FILE.write_text(json.dumps(plan, indent=1))
    gh_output('mode', mode)
    return 0


def previous_manifest(name):
    f = PUBLISHED / 'status' / f'{name}.json'
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


class Run:
    """One publish run's state: fates, reasons, and what got built."""

    def __init__(self, cfg, plan):
        self.cfg = cfg
        self.plan = plan
        self.mode = plan['mode']
        self.products = cfg['products']
        self.steps = cfg['steps']
        self.fate = {}      # product -> fresh | held | carried
        self.reason = {}    # product -> why, when held
        self.built = {}     # cache name -> bool
        self.withheld = {}  # product -> {dir: why}
        self.tile_state = {}  # product -> {dir: state}
        self.notes = []
        # Products serving old data that newer data existed for — ours to
        # answer for, and what turns the run red. See the note by
        # `nearest_frame_age`.
        self.behind = []
        self.deploy = True
        self.changed = set()

    # -- fetch ---------------------------------------------------------------

    def fetch_all(self):
        before = scan_stage()
        lanes = {s['lane']: threading.Lock() for s in self.steps.values()}
        print_lock = threading.Lock()
        outcomes = {}

        def one(sname, step):
            with lanes[step['lane']]:
                ok, detail, out, err = run_cmd(
                    step['cmd'], SITE, step['timeout_minutes'], sname)
            with print_lock:
                log(f'--- step {sname}: {detail}')
                for stream in (out, err):
                    if stream.strip():
                        log(stream.rstrip())
            return ok, detail

        to_run = {
            sname: step for sname, step in self.steps.items()
            if self.mode != 'light' or step['light']
        }
        with ThreadPoolExecutor(max_workers=max(1, len(lanes))) as pool:
            futures = {sname: pool.submit(one, sname, step)
                       for sname, step in to_run.items()}
            for sname, future in futures.items():
                outcomes[sname] = future.result()

        after = scan_stage()
        self.changed = ({n for n in after if before.get(n) != after[n]}
                        | {n for n in before if n not in after})

        # The write fence. A changed file no product claims means a fetcher
        # is writing outside every declared namespace — a bug in the
        # declaration or the fetcher, and either way nothing downstream can
        # attribute it, so nothing downstream should run.
        unclaimed = sorted(n for n in self.changed if not owners_of(n, self.products))
        contested = sorted(n for n in self.changed
                           if len(owners_of(n, self.products)) > 1)
        if unclaimed or contested:
            for n in unclaimed:
                log(f'FENCE  {n}: written by no declared namespace')
            for n in contested:
                log(f'FENCE  {n}: claimed by more than one product')
            raise SystemExit(3)

        for name, spec in self.products.items():
            sname = spec['step']
            if sname not in to_run:
                self.fate[name] = 'carried'
            elif outcomes[sname][0]:
                self.fate[name] = 'fresh'
            else:
                self.hold(name, f'step {sname} {outcomes[sname][1]}')

    def hold(self, name, why):
        self.fate[name] = 'held'
        self.reason[name] = why
        restore_namespace(self.products[name])
        log(f'held  {name}: {why}')

    # -- what a product no longer owns ---------------------------------------

    def survey_namespaces(self):
        """Report staged files a fresh product's own pipeline no longer names.

        **The stage is seeded from the last publish, so a file no step writes
        any more is carried for ever.** Measured 2026-08-21 on the site's
        60 m to 50 m rename: the tile directories went, because `tiles.match`
        pairs a directory to its grid; the grids stayed, 32 files and 43.8 MB,
        frozen and still served. Nothing caught it — `--roots` and
        `products.toml` agree once a file stops being a root on both sides,
        the ESPC hour rule reads a hardcoded product list, and
        `max_age_hours` is per product while the product is fresh.

        **Intent, not outcome.** The obvious rule is "prune what the step did
        not write this run", and it would be catastrophic: `fetch-currents.py`
        keeps the previous files and exits 0 when HYCOM is down, so a
        degrading run writes nothing and the rule would delete the product.
        A product declares a `namespace` command instead — a set of glob
        patterns derived from its own constants, answered without the network
        so a bad afternoon cannot look like an empty namespace.

        **Reporting only, deliberately, and this is the first version of a
        thing that will eventually delete published data at 3 a.m. on a
        flaky upstream.** It names what it would drop and drops nothing. Arm
        it once real runs have shown it naming the right files and only
        those; the failure it must never have is the one this repository has
        already paid for three times, where two correct components leave a
        state that reads as deliberate and was an accident.

        Two answers are kept apart on purpose. A probe that **fails** is
        reported and prunes nothing — an absent answer is not an empty
        namespace, which is the conflation `collect_erddap` and the tropical
        outlook were both fixed for. And a file the step **wrote this run**
        that matches no pattern is a *fault*, not an abandonment: the
        pipeline is writing outside its own declared namespace, which is the
        write fence one level down.
        """
        for name, spec in self.products.items():
            cmd = spec.get('namespace')
            if not cmd or self.fate[name] != 'fresh':
                continue
            ok, detail, out, err = run_cmd(cmd, SITE, 2, f'{name} namespace')
            if not ok:
                log(f'namespace {name}: probe failed ({detail}) — nothing surveyed. '
                    'An answer that did not arrive is not an empty namespace.')
                continue
            patterns = [line.strip() for line in out.splitlines() if line.strip()]
            if not patterns:
                log(f'namespace {name}: probe answered with no patterns — nothing '
                    'surveyed, since a product owning nothing would own nothing to fetch')
                continue
            staged = sorted(f.name for f in STAGE.iterdir()
                            if f.is_file() and match_any(f.name, spec['writes']))
            stray = [n for n in staged if not match_any(n, patterns)]
            wrote_stray = sorted(n for n in stray if n in self.changed)
            if wrote_stray:
                # Not abandonment. The step is writing names its own namespace
                # does not describe, so the declaration and the writer
                # disagree and neither can be trusted to say which is right.
                for n in wrote_stray:
                    log(f'FENCE  {n}: written by {name} this run but outside its '
                        'own declared namespace')
                raise SystemExit(3)
            if stray:
                total = sum((STAGE / n).stat().st_size for n in stray)
                log(f'namespace {name}: {len(stray)} carried file(s) it no longer '
                    f'names, {total / 1e6:.1f} MB — reporting only, nothing removed')
                for n in stray:
                    log(f'ABANDONED  {n}')

    # -- validation ----------------------------------------------------------

    def validate_products(self):
        for name, spec in self.products.items():
            if self.fate[name] != 'fresh':
                continue
            problem = self.validate_one(spec)
            if problem:
                self.hold(name, problem)

    def validate_one(self, spec):
        for root in spec['roots']:
            path = STAGE / root
            if not path.is_file():
                return f'root {root} missing'
            try:
                json.loads(path.read_text())
            except ValueError as exc:
                return f'root {root} unreadable: {exc}'
        for name in closure(spec['roots']):
            if not (STAGE / name).is_file():
                return f'advertises {name}, which is not in the stage'
        return None

    # -- data quality ----------------------------------------------------------

    def quality_products(self):
        """A product's own physics check, run against what its fetch staged.

        **Why this exists: 2026-08-26, HYCOM served depth as stripes.** For
        one three-hour step the upstream returned fields constant down every
        column for every depth below ~20 m, with HTTP 200 throughout. The
        fetchers kept-previous-on-error as designed — but there was no error,
        so five corrupt current products published and the site drew them
        faithfully for hours until the owner's eye caught it. Structural
        validation cannot see this: the files were well-formed JSON with the
        right shapes. Only the product knows what its own field should look
        like, so the check is a command the product declares, beside its
        `namespace` and `tiles` commands, living with the fetcher it checks.

        Runs AFTER structural validation (a physics check on an unreadable
        file would report physics) and BEFORE `settle_tiles` — a hold here
        keeps the seeded previous publish, tiles included, which is exactly
        the fallback the fetchers' own kept-previous discipline provides for
        upstream OUTAGES, extended to upstream LIES.

        The command's contract: exit 0 to accept; non-zero to reject, with
        the reason on the last non-empty line of stdout. A missing command
        means no check — products opt in."""
        for name, spec in self.products.items():
            if self.fate[name] != 'fresh':
                continue
            cmd = spec.get('quality')
            if not cmd:
                continue
            ok, detail, out, err = run_cmd(
                cmd, SITE, spec.get('timeout_minutes', 10), f'quality:{name}')
            for stream in (out, err):
                if stream.strip():
                    log(stream.rstrip())
            if not ok:
                lines = [l for l in out.strip().splitlines() if l.strip()]
                why = lines[-1] if lines else detail
                self.hold(name, f'quality: {why}')

    # -- tiles -----------------------------------------------------------------

    def settle_tiles(self):
        for name, spec in self.products.items():
            if 'tiles' not in spec:
                continue
            tiles = spec['tiles']
            pairs = tile_pairs(spec)
            states = {d: tile_dir_state(d, g) for d, g in pairs}
            adrift = [d for d, (s, _) in states.items() if s != 'ok']
            bases = [d for d, g in tiles['match'] if '*' not in d]
            missing = [d for d in bases
                       if header_of(STAGE / dict(tiles['match'])[d]) is not None
                       and not (STAGE / d / 'index.json').is_file()]

            if (self.fate[name] == 'fresh' and self.mode != 'light'
                    and (adrift or missing)):
                log(f'tiles {name}: building ({len(adrift)} adrift, '
                    f'{len(missing)} missing)')
                ok, detail, out, err = run_cmd(
                    tiles['build'], SITE,
                    tiles.get('timeout_minutes', 60), f'tiles:{name}')
                for stream in (out, err):
                    if stream.strip():
                        log(stream.rstrip())
                # **A build is believed by what it produced, not by what it
                # returned.** Every pipeline here degrades the same way: when
                # its upstream is down it keeps the previous file and exits 0,
                # so a deploy is never blocked by somebody else's outage. That
                # is right, and it means an exit code says "I did not fail",
                # never "the tiles are there".
                #
                # Measured 2026-08-16, with HYCOM returning 500s: the log read
                # `tiles currents: building (0 adrift, 2 missing)` and then
                # `--- tiles currents: ok`, 0.4 s apart, with both directories
                # still missing — a sweep of 159 tiles across two depths takes
                # minutes. Nothing was withheld, because withholding walks the
                # directories that *exist*; nothing was recorded, because the
                # record is built from the same walk. The publish went out
                # advertising a tier it did not carry.
                #
                # So the same list that decides `missing` above decides it
                # again afterwards. No new concept, and no new source of
                # truth: `match` already says which directories this product
                # owes.
                unbuilt = [d for d in bases
                           if header_of(STAGE / dict(tiles['match'])[d]) is not None
                           and not (STAGE / d / 'index.json').is_file()]
                if ok and unbuilt:
                    ok = False
                    detail = (f'{detail}, but produced nothing for '
                              f'{", ".join(unbuilt)}')
                log(f'--- tiles {name}: {detail}')
                self.built[tiles['cache']] = ok
                if not ok:
                    self.notes.append(f'{name}: tile build failed ({detail})')
                # Absent is a fate worth recording, and it was the one state
                # that left no trace. A directory that was never written
                # cannot be withheld — there is nothing to remove — so it is
                # named here, with its reason, exactly as an adrift one is.
                # The light-run guard and `status.json` both read this, and a
                # tier missing for a reason reads very differently from a tier
                # missing for none.
                for d in unbuilt:
                    self.withheld.setdefault(name, {})[d] = 'build produced no tiles'
                pairs = tile_pairs(spec)
                states = {d: tile_dir_state(d, g) for d, g in pairs}

            # Whatever is still not its grid's hour leaves the publish: a
            # removal, recorded. Absent degrades to the coarse grid; adrift
            # would be wrong data with no tell.
            # Seeded above when a build produced nothing, so this keeps
            # rather than clears — an absent directory has a reason too.
            self.withheld.setdefault(name, {})
            final = {d: 'absent' for d in self.withheld[name]}
            for d, (state, detail) in states.items():
                if state == 'ok':
                    final[d] = 'kept' if not self.built.get(tiles['cache']) else 'fresh'
                else:
                    shutil.rmtree(STAGE / d, ignore_errors=True)
                    self.withheld[name][d] = detail
                    final[d] = 'withheld'
                    log(f'withheld  {name}/{d}: {detail}')
            # And the grid stops advertising what just left. Paired with the
            # removal rather than done in `assemble`, because this is the one
            # place that knows *which* directory went and therefore which
            # grid was making the claim.
            # Resolved through the pairs captured before the removal, not
            # through `match` directly: a forecast frame's directory is
            # `tiles-f57h` and its entry is the glob `tiles-f*h`, so a lookup
            # by name finds nothing and the frame goes on advertising. The
            # base directories fall back to `match`, since an absent one was
            # never in the stage to be paired.
            grid_of = dict(pairs)
            for d, state in final.items():
                if state in ('withheld', 'absent'):
                    grid = grid_of.get(d) or dict(tiles['match']).get(d)
                    if grid and unadvertise_tiles(STAGE / grid):
                        log(f'unadvertised  {name}/{grid}: no {d} to point at')
            self.tile_state[name] = final

    # -- assembly and record ---------------------------------------------------

    def assemble(self):
        if OUT.exists():
            shutil.rmtree(OUT)
        (OUT / 'map').mkdir(parents=True)
        static = ROOT / 'map'
        # Every declared static must be present before anything is
        # published. This directory was silently empty for the first day of
        # production and four lazy layers 404'd their way to nothing on the
        # live map — a missing static is a defect in this repository, so
        # the correct fate is a loud failure, not a quieter tree.
        missing = [name for name in self.cfg.get('static', {}).get('required', [])
                   if not (static / name).exists()]
        if missing:
            raise SystemExit(f'assemble: static file(s) missing from map/: '
                             f'{", ".join(missing)}')
        if static.is_dir():
            shutil.copytree(static, OUT / 'map', dirs_exist_ok=True)
        shutil.copytree(STAGE, OUT / 'map', dirs_exist_ok=True)
        (OUT / '.nojekyll').touch()
        # index.html, not index.md: workflow-mode Pages runs no Jekyll, so
        # markdown at the root is a file, not a page — the predecessor's
        # root has 404'd behind exactly that mistake since it launched.
        landing = ROOT / 'index.html'
        if landing.is_file():
            shutil.copy2(landing, OUT / 'index.html')

    def write_record(self):
        now = utcnow()
        # **schema 2 adds `roots` and `modelRun` to each product**, and the
        # bump is honest rather than defensive: consumers that read neither
        # are unaffected, and the map is one of them — it reads `fate` and
        # `stale` and never looks at the version. A consumer wanting to route
        # treats a missing `roots` as "the default origin owns it", which is
        # what lets a reader land before any origin publishes the new shape.
        status = {
            'schema': 2, 'generated': now, 'mode': self.mode,
            'run': {
                'id': os.environ.get('GITHUB_RUN_ID', ''),
                'url': (f"{os.environ.get('GITHUB_SERVER_URL', '')}/"
                        f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
                        f"{os.environ.get('GITHUB_RUN_ID', '')}"
                        if os.environ.get('GITHUB_RUN_ID') else ''),
            },
            'products': {},
        }
        for d in (OUT / 'status', BRANCH / 'map', BRANCH / 'status'):
            d.mkdir(parents=True, exist_ok=True)

        for name, spec in self.products.items():
            prev = previous_manifest(name)
            hour, run, source, hours = stamp_of(spec)
            fresh = self.fate[name] == 'fresh'
            files = {}
            for f in sorted(STAGE.iterdir()):
                if f.is_file() and match_any(f.name, spec['writes']):
                    entry = {'bytes': f.stat().st_size}
                    if f.name in spec['roots']:
                        entry['sha256'] = hashlib.sha256(f.read_bytes()).hexdigest()
                    files[f.name] = entry
            changed_here = fresh and any(
                n in self.changed for n in files)
            manifest = {
                'schema': 1,
                'product': name,
                'title': spec['title'],
                'fate': self.fate[name],
                'reason': self.reason.get(name),
                'checked': now if fresh else prev.get('checked'),
                'updated': now if changed_here else prev.get('updated'),
                'hour': hour,
                'modelRun': run,
                'source': source,
                'hours': hours,
                'files': files,
            }
            if 'tiles' in spec:
                manifest['tiles'] = {
                    d: {'state': state,
                        'reason': self.withheld.get(name, {}).get(d)}
                    for d, state in self.tile_state.get(name, {}).items()
                }
            for dest in (OUT / 'status', BRANCH / 'status'):
                (dest / f'{name}.json').write_text(json.dumps(manifest, indent=1))
            age_limit = spec.get('max_age_hours')
            age = nearest_frame_age(manifest['hours'])
            overdue = bool(age_limit and age is not None and age > age_limit)
            if overdue:
                # **Whose fault it is decides how loud this gets, and the
                # two cases are genuinely different.** A product whose fetch
                # SUCCEEDED and is still old means upstream has nothing
                # newer — ESPC skipped two daily runs this week and the map
                # correctly showed the newest thing that exists. That is a
                # note. A product that is old while its fate is anything but
                # `fresh` means the newer data was there and this pipeline
                # did not publish it: on 2026-08-27 the Navy fields were
                # `carried` at nine hours while upstream had 18:00Z waiting,
                # because the full runs the scheduler owed simply never
                # arrived. That is ours, and it is what the run should go
                # red for.
                if self.fate[name] == 'fresh':
                    self.notes.append(
                        f'{name}: nearest frame is {age:.1f} h old, past its '
                        f'{age_limit} h budget — upstream has nothing newer')
                    log(f'currency: {name} {age:.1f} h — upstream, not us')
                else:
                    self.behind.append(f'{name} ({age:.1f} h, {self.fate[name]})')
                    # An Actions annotation, so it is visible on the run
                    # without opening the log.
                    log(f'::error title=Stale data::{name}: nearest published '
                        f'frame is {age:.1f} h old against a {age_limit} h '
                        f'budget, and its fate is {self.fate[name]} — newer '
                        f'data was available and was not published')
            status['products'][name] = {
                'title': spec['title'],
                # **Which files this origin serves.** The routing half of the
                # N-repository contract: a consumer reads one document per
                # origin and learns where every root lives, so moving a
                # product between repositories costs no configuration in the
                # consumer at all. A projection of `products.toml`, written
                # in the same process that reads it, rather than a second
                # list to keep in step.
                'roots': list(spec['roots']),
                'fate': self.fate[name],
                'reason': self.reason.get(name),
                'checked': manifest['checked'],
                'updated': manifest['updated'],
                'hour': manifest['hour'],
                'modelRun': manifest['modelRun'],
                'source': manifest['source'],
                'hours': manifest['hours'],
                # The READER's distance from the data, which is what the
                # credit-line light shows. `updated` is still published
                # above for anyone asking when the pipeline last ran; it is
                # no longer mistaken for currency.
                'stale': overdue,
                'ageHours': None if age is None else round(age, 2),
            }

        receipt = {
            'schema': 1, 'generated': now, 'mode': self.mode,
            'fates': dict(self.fate), 'reasons': dict(self.reason),
            'built': dict(self.built), 'withheld': dict(self.withheld),
            'deploy': self.deploy, 'notes': self.notes,
            # Products serving old data that newer data existed for. In the
            # receipt as well as the workflow output, so a test can read the
            # same answer the schedule fails on.
            'behind': self.behind,
        }
        for dest in (OUT / 'status', BRANCH / 'status'):
            (dest / 'status.json').write_text(json.dumps(status, indent=1))
            (dest / 'receipt.json').write_text(json.dumps(receipt, indent=1))
            if PLAN_FILE.is_file():
                shutil.copy2(PLAN_FILE, dest / 'plan.json')

        for f in sorted(STAGE.iterdir()):
            if f.is_file() and owners_of(f.name, self.products):
                shutil.copy2(f, BRANCH / 'map' / f.name)
        (BRANCH / 'README.md').write_text(
            '# published\n\nMachine-written by every publish run: the small '
            'products and the status record, one commit, force-pushed. '
            'Nothing here is authored by hand and nothing should be built '
            'on this branch.\n')

    # -- the consumer's gate ---------------------------------------------------


    def owned(self):
        """`--owned=` for the contract check: the roots this tree answers for.

        **The contract is every file the map reads, from every origin; this
        repository publishes a share of it.** `test-schema.mjs` fails on a
        required root that is absent — deliberately, because deriving the
        list from what is present turns a product that stopped publishing
        into a check that quietly tests less, and this project has been
        bitten by that twice. That is the right rule and it asks a question
        only one origin could answer while one origin published everything.

        Measured on the two trees the ESPC split produces, built from live
        published data: unscoped, the ESPC tree fails six required roots and
        the remaining tree fails four, each naming exactly what the *other*
        repository owns. Scoped, both pass. So this is not tidiness — no
        origin can publish without it.

        Derived from the same `roots` the agreement gate compares against, so
        it cannot drift from what this repository actually fetches.
        """
        roots = sorted({r for spec in self.products.values() for r in spec['roots']})
        return '--owned=' + ','.join(roots)
    def contract_gate(self):
        """The site's own schema check over the assembled tree, with one
        demote-and-retry: failures name files, files name products, and a
        product that cannot pass ships its previous version instead.

        A failure attributable only to products this run already HELD is a
        note rather than a stop — see the block below for why, and for what
        is still fatal."""
        demoted_here: set[str] = set()
        for attempt in (1, 2):
            ok, detail, out, err = run_cmd(
                self.cfg['contract']['check'] + [str(OUT / 'map'), self.owned()],
                SITE, 10, 'contract')
            log(out.rstrip() if out.strip() else f'contract: {detail}')
            if err.strip():
                log(err.rstrip())
            if ok:
                return True
            culprits = set()
            unmapped = []
            for m in re.finditer(r'^FAIL\s+(\S+?):', out, re.M):
                token = m.group(1)
                top = token.split('/', 1)[0]
                owners = owners_of(top, self.products)
                if not owners:
                    owners = [
                        name for name, spec in self.products.items()
                        if 'tiles' in spec and any(
                            match_any(top, [dglob])
                            for dglob, _ in spec['tiles']['match'])]
                if len(owners) == 1:
                    culprits.add(owners[0])
                else:
                    unmapped.append(token)
            fresh_culprits = [c for c in sorted(culprits)
                              if self.fate[c] == 'fresh']
            held_culprits = [c for c in sorted(culprits)
                             if self.fate[c] != 'fresh']

            # **Every failure attributable to a product this run HELD is that
            # hold's own consequence, and does not stop the deploy.**
            #
            # The case, live on 2026-08-27: the currents split into three
            # fault domains so a clean surface could publish while a corrupt
            # depth held — and then the consumer's ESPC hour rule failed the
            # tree, because a held `currents-caps` at 21Z sits beside a fresh
            # `currents-surface` advanced to 00Z of the SAME model run. The
            # culprit was already held, so `not fresh_culprits` sent this
            # gate down the fatal path and froze the WHOLE Pages tree — the
            # good surface included — for as long as the upstream stayed
            # broken. That is the fault-domain split defeating itself: the
            # case it exists for is the case that stopped every deploy.
            #
            # The justification is not "the hour rule is unimportant" — this
            # gate deliberately knows nothing about which rule failed, and
            # parsing the consumer's messages to find out is how two copies
            # of a rule start drifting. It is that NOTHING THIS RUN FETCHED
            # IS IMPLICATED: every product refreshed this run passed, and the
            # disagreement is between those and data carried forward from a
            # previous publish, which is the ordinary state of a partial
            # outage. The tree is not made worse by shipping it, and the
            # alternative — freezing every product until the sick one heals —
            # is what the split was built to stop.
            #
            # Deliberately NOT tolerated: an unmapped failure (nothing to
            # attribute it to) or a failure with no culprits at all. Those
            # still stop the deploy, because an unexplained contract failure
            # is exactly the shape that publishes a tree the map cannot read.
            # ...but NOT a product this gate itself demoted a moment ago.
            # If the contract failed on it, we held it, and it fails again,
            # then the version carried forward is itself unacceptable — the
            # case `test_contract_still_failing_stops_the_deploy` pins, and
            # the one shape where a hold does NOT make the tree safe. That
            # test caught this exact over-reach when the tolerance was first
            # written to trust every hold.
            if (not unmapped and culprits and not fresh_culprits
                    and not (culprits & demoted_here)):
                who = ', '.join(held_culprits)
                self.notes.append(
                    f'contract failed only on held product(s) {who}; '
                    f'deploying anyway — nothing fetched this run is implicated')
                log(f'contract: failures attributable only to held '
                    f'{who} — deploying the rest')
                return True

            if attempt == 2 or unmapped or not fresh_culprits:
                for token in unmapped:
                    log(f'contract: cannot map {token} to a product')
                self.deploy = False
                self.notes.append('contract check failed; not deploying')
                return False
            for name in fresh_culprits:
                self.hold(name, 'failed the consumer contract')
                demoted_here.add(name)
            self.settle_tiles()
            self.assemble()
        return False

    # -- the light run's floor -------------------------------------------------

    def light_gap_guard(self):
        """A light run must not deploy a tree without its tiles: Pages
        replaces everything, so an absent directory here is a deletion
        there. The branch still pushes — nothing fetched is thrown away."""
        if self.mode != 'light':
            return
        for name, spec in self.products.items():
            for d, _ in spec.get('tiles', {}).get('match', []):
                if '*' in d:
                    continue
                if not (OUT / 'map' / d / 'index.json').is_file():
                    self.deploy = False
                    self.notes.append(
                        f'light run without {d}; deploy skipped, branch kept')
                    log(f'light gap: {d} absent — skipping deploy')
                    return


# A published root is a bare lowercase filename. Used only as a positive
# control on the contract's own answer — see cmd_run.
ROOT_NAME = re.compile(r'^[a-z0-9-]+\.json$')


def cmd_run(cfg):
    if not PLAN_FILE.is_file():
        log('run: no plan.json — run `orchestrate.py plan` first')
        return 2
    plan = json.loads(PLAN_FILE.read_text())

    declared = set()
    for spec in cfg['products'].values():
        declared.update(spec['roots'])
    ok, detail, out, err = run_cmd(cfg['contract']['roots'], SITE, 5, 'roots')
    if not ok:
        log(f'run: cannot read the contract roots ({detail})')
        return 2
    contract_roots = set(out.split())
    # **A positive control on the interface, before believing a word of it.**
    # `--roots` once answered mid-file, after the per-file checks, so a
    # failing check printed a FAIL line and this parser read that line's own
    # words as root names — `FAIL`, `storm`, `should`, `be`, `a`, `number,`.
    # The site fixed its half by answering before any real work can print;
    # this is the other half, so a caller can never again mistake an error
    # message for a contract. It matters more now that the comparison below
    # is one-directional: a garbage answer would otherwise report every
    # declared root as unknown, which names the wrong subject entirely.
    if not contract_roots or not all(ROOT_NAME.match(n) for n in contract_roots):
        shown = ' '.join(sorted(contract_roots)[:4])
        log(f'run: the contract roots did not answer with a root list ({shown}…)')
        return 2
    stray = sorted(declared - contract_roots)
    if stray:
        for extra in stray:
            log(f'ROOTS  {extra}: declared here, unknown to the contract')
        return 2
    # **The other direction is not this repository's question any more.**
    # With several origins publishing into one contract, a root this
    # repository does not declare is the ordinary case — it belongs to
    # another origin's products.toml, which this run cannot see and should
    # not have to fetch. Failing on it would stop *this* repository's
    # publish over a gap in *another* one's.
    #
    # The check has not been dropped, it has moved to the only place with a
    # global view: `check:docs` in the site repository reads every origin in
    # MAP_ORIGINS and holds their declarations against `--roots` in both
    # directions at once, so a root nobody fetches still fails, and before a
    # push rather than after it. The measured cost of getting this wrong is
    # the reason it is worth saying twice: one undeclared root cost three
    # consecutive failed runs and two hours with nothing published at all.
    #
    # The count is logged because a run should say what it is *not*
    # covering. A repository that suddenly declares far fewer roots than it
    # used to has had something taken from it, and the number is the tell.
    elsewhere = len(contract_roots - declared)
    if elsewhere:
        log(f'roots: {len(declared)} of {len(contract_roots)} declared here;'
            f' {elsewhere} belong to other origins')

    # The record is written last, after the gate and the guard have had
    # their say: a receipt describing what the run intended rather than what
    # it did is the predecessor's cache bug wearing a new hat.
    #
    # There is deliberately no cross-product agreement check here. There was
    # one — a "coherence group" comparing the ESPC members' base hours — and
    # it was wrong on the very first live run: the currents' base file is by
    # design the *earlier* of two frames, the contract measures the Navy
    # fields against the currents' full set of published hours, and a
    # different model run is a note rather than a failure because upstream
    # raggedness is the ordinary state. Rules about how products relate are
    # the consumer's contract's to own, and duplicating one here is how two
    # copies drift. The gate below already maps a contract failure back to
    # its product and demotes exactly that one; the cost is that a doomed
    # product may build tiles before the gate speaks, which settle_tiles
    # then withholds — wasted minutes in a case the fetchers' own selection
    # already refuses, against a rule that cannot drift.
    run = Run(cfg, plan)
    run.fetch_all()
    run.survey_namespaces()
    run.validate_products()
    run.quality_products()
    run.settle_tiles()
    run.assemble()
    run.contract_gate()
    run.light_gap_guard()
    run.write_record()

    gh_output('deploy', 'true' if run.deploy else 'false')
    for cache, built in run.built.items():
        gh_output(f'built-{cache}', 'true' if built else 'false')
    log(f'run: fates {run.fate}')
    log(f'run: deploy={run.deploy}')
    # **Handed to the workflow rather than returned, because a stale tree
    # must still DEPLOY.** Refusing the publish would leave the reader with
    # something older still — the one response to staleness that makes it
    # worse. So the tree goes out and the run is failed afterwards, which
    # is what puts a red mark on the schedule and sends the notification
    # GitHub already knows how to send. Nothing here needs new plumbing.
    gh_output('behind', ', '.join(run.behind))
    if run.behind:
        log(f'run: BEHIND — {", ".join(run.behind)}')
    return 0


def cmd_seed_published(cfg, base):
    """Pull the predecessor's current publish into branch-out/, one time."""
    base = base.rstrip('/')
    (BRANCH / 'map').mkdir(parents=True, exist_ok=True)

    def grab(name):
        dest = BRANCH / 'map' / name
        if dest.exists():
            return True
        try:
            with urllib.request.urlopen(f'{base}/{name}', timeout=120) as r:
                dest.write_bytes(r.read())
            return True
        except OSError as exc:
            log(f'seed-published: no {name} ({exc})')
            return False

    got = []
    for name, spec in cfg['products'].items():
        for root in spec['roots']:
            if grab(root):
                got.append(root)
    # The closure, walked over what just landed: frames first, then what the
    # frames themselves advertise.
    queue = list(got)
    visited = set()
    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        head = header_of(BRANCH / 'map' / name)
        if not head:
            continue
        for linked in advertised(head):
            if grab(linked):
                queue.append(linked)
    now = utcnow()
    (BRANCH / 'status').mkdir(parents=True, exist_ok=True)
    for name, spec in cfg['products'].items():
        (BRANCH / 'status' / f'{name}.json').write_text(json.dumps({
            'schema': 1, 'product': name, 'title': spec['title'],
            'fate': 'carried', 'reason': 'seeded from the predecessor',
            'checked': now, 'updated': now, 'hour': None, 'files': {},
        }, indent=1))
    log(f'seed-published: {len(visited)} files in branch-out/map')
    return 0


def hours_since(stamp):
    try:
        then = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0.0
    return (datetime.now(timezone.utc) - then).total_seconds() / 3600


def nearest_frame_age(hours):
    """Hours between now and the NEAREST published valid time, or None.

    **The reader's own distance from the data**, and that is the quantity
    this pipeline was not measuring. `stale` compared `updated` — when the
    pipeline last PUBLISHED — against `max_age_hours`, which answers "did
    we run recently?" and not "is what we serve current?". A pipeline
    republishing a nine-hour-old field every hour is perfectly live and
    completely stale, and on 2026-08-27 that is exactly what happened:
    every product on both origins reported `stale: false` while the Navy
    fields sat nine hours behind and OISST forty-three. Both were found by
    the owner looking at the map, twice in one day, with every suite green.

    NEAREST rather than the base hour, because the map opens each layer on
    whichever published frame is closest to the reader's clock — a product
    publishing 15:00Z and 18:00Z at 17:00Z is an hour off, not two.
    """
    ages = [abs(hours_since(h)) for h in (hours or []) if h]
    return min(ages) if ages else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('seed')
    p_plan = sub.add_parser('plan')
    p_plan.add_argument('--mode', choices=['full', 'light'], default='full')
    sub.add_parser('run')
    p_boot = sub.add_parser('seed-published')
    p_boot.add_argument('--from', dest='base', required=True)
    args = parser.parse_args()

    cfg = load_config()
    if args.cmd == 'seed':
        return cmd_seed(cfg)
    if args.cmd == 'plan':
        return cmd_plan(cfg, args.mode)
    if args.cmd == 'run':
        return cmd_run(cfg)
    if args.cmd == 'seed-published':
        return cmd_seed_published(cfg, args.base)


if __name__ == '__main__':
    sys.exit(main())
