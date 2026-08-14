#!/usr/bin/env python3
"""The orchestrator. Everything between the fetch scripts and the publish.

Subcommands, in the order a run uses them:

  seed            copy the published branch's data into the stage, so every
                  fetcher starts from the last good publish
  plan            probe the model catalogs once, write plan.json, and emit
                  the tile cache keys for the workflow to restore against
  run             fetch, validate, resolve fates, build tiles, assemble the
                  candidate tree, write manifests and status, gate on the
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

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'                 # checkout of oceansensing.github.io
STAGE = SITE / 'public' / 'map'      # where the fetchers read and write
PUBLISHED = ROOT / 'published'       # checkout of the `published` branch
OUT = ROOT / 'out'                   # the candidate tree Pages deploys
BRANCH = ROOT / 'branch-out'         # what the next `published` commit holds
PLAN_FILE = ROOT / 'plan.json'

CACHE_VERSION = 'v1'  # bump alongside any change to what the tiles contain


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


def hour_of(product_spec):
    """The model hour a product currently presents, from its first root that
    carries a header. None for products whose files have none."""
    for root in product_spec['roots']:
        head = header_of(STAGE / root)
        if head and head.get('refTime'):
            return head['refTime']
    return None


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

    # -- group coherence -------------------------------------------------------

    def enforce_groups(self):
        groups = {}
        for name, spec in self.products.items():
            if 'group' in spec:
                groups.setdefault(spec['group'], []).append(name)
        for gname, members in groups.items():
            hours = {m: hour_of(self.products[m]) for m in members}
            if len(set(hours.values())) <= 1:
                continue
            stated = ', '.join(f'{m} at {h}' for m, h in hours.items())
            # Hold every fresh member back to the seed: the last publish
            # passed the contract, so the restored set agrees by
            # construction. Holding only the odd one out would need to know
            # which one is wrong, and "newest" is not the same as "right".
            for m in members:
                if self.fate[m] == 'fresh':
                    self.hold(m, f'group {gname} disagrees ({stated})')

    # -- tiles -----------------------------------------------------------------

    def settle_tiles(self):
        for name, spec in self.products.items():
            if 'tiles' not in spec:
                continue
            tiles = spec['tiles']
            states = {d: tile_dir_state(d, g) for d, g in tile_pairs(spec)}
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
                log(f'--- tiles {name}: {detail}')
                for stream in (out, err):
                    if stream.strip():
                        log(stream.rstrip())
                self.built[tiles['cache']] = ok
                if not ok:
                    self.notes.append(f'{name}: tile build failed ({detail})')
                states = {d: tile_dir_state(d, g) for d, g in tile_pairs(spec)}

            # Whatever is still not its grid's hour leaves the publish: a
            # removal, recorded. Absent degrades to the coarse grid; adrift
            # would be wrong data with no tell.
            self.withheld[name] = {}
            final = {}
            for d, (state, detail) in states.items():
                if state == 'ok':
                    final[d] = 'kept' if not self.built.get(tiles['cache']) else 'fresh'
                else:
                    shutil.rmtree(STAGE / d, ignore_errors=True)
                    self.withheld[name][d] = detail
                    final[d] = 'withheld'
                    log(f'withheld  {name}/{d}: {detail}')
            self.tile_state[name] = final

    # -- assembly and record ---------------------------------------------------

    def assemble(self):
        if OUT.exists():
            shutil.rmtree(OUT)
        (OUT / 'map').mkdir(parents=True)
        static = ROOT / 'map'
        if static.is_dir():
            shutil.copytree(static, OUT / 'map', dirs_exist_ok=True)
        shutil.copytree(STAGE, OUT / 'map', dirs_exist_ok=True)
        (OUT / '.nojekyll').touch()
        readme = ROOT / 'README.md'
        if readme.is_file():
            shutil.copy2(readme, OUT / 'index.md')

    def write_record(self):
        now = utcnow()
        status = {
            'schema': 1, 'generated': now, 'mode': self.mode,
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
                'hour': hour_of(spec),
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
            status['products'][name] = {
                'title': spec['title'],
                'fate': self.fate[name],
                'reason': self.reason.get(name),
                'checked': manifest['checked'],
                'updated': manifest['updated'],
                'hour': manifest['hour'],
                'stale': bool(
                    age_limit and manifest['updated']
                    and hours_since(manifest['updated']) > age_limit),
            }

        receipt = {
            'schema': 1, 'generated': now, 'mode': self.mode,
            'fates': dict(self.fate), 'reasons': dict(self.reason),
            'built': dict(self.built), 'withheld': dict(self.withheld),
            'deploy': self.deploy, 'notes': self.notes,
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

    def contract_gate(self):
        """The site's own schema check over the assembled tree, with one
        demote-and-retry: failures name files, files name products, and a
        product that cannot pass ships its previous version instead."""
        for attempt in (1, 2):
            ok, detail, out, err = run_cmd(
                self.cfg['contract']['check'] + [str(OUT / 'map')], SITE, 10,
                'contract')
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
            if attempt == 2 or unmapped or not fresh_culprits:
                for token in unmapped:
                    log(f'contract: cannot map {token} to a product')
                self.deploy = False
                self.notes.append('contract check failed; not deploying')
                return False
            for name in fresh_culprits:
                self.hold(name, 'failed the consumer contract')
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
    if declared != contract_roots:
        for extra in sorted(declared - contract_roots):
            log(f'ROOTS  {extra}: declared here, unknown to the contract')
        for missing in sorted(contract_roots - declared):
            log(f'ROOTS  {missing}: in the contract, declared by no product')
        return 2

    # The record is written last, after the gate and the guard have had
    # their say: a receipt describing what the run intended rather than what
    # it did is the predecessor's cache bug wearing a new hat.
    run = Run(cfg, plan)
    run.fetch_all()
    run.validate_products()
    run.enforce_groups()
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
