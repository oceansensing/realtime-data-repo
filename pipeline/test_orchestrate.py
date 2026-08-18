#!/usr/bin/env python3
"""Unit tests for the orchestrator. No network, no node: a fake fetch tool
and a fake contract stand in for the site checkout, and every fate path is
driven through them — fresh, held, carried, the write fence, the coherence
group, tile withholding, the demote loop and the light run's floor.

Run with:  python3 pipeline/test_orchestrate.py
"""

import json
import os
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrate  # noqa: E402

H0 = '2026-01-01T00:00:00Z'
H1 = '2026-01-02T00:00:00Z'

# One script, many hats: which hat is argv[1], and the ctl/ directory is the
# test's hand on the wheel. It stands where the fetchers and test-schema.mjs
# stand in production, so the orchestrator cannot tell the difference.
FAKE_TOOL = '''
import json, sys
from pathlib import Path
MAP = Path('public/map'); CTL = Path('ctl')
cmd = sys.argv[1]

def hour(name, default='2026-01-01T00:00:00Z'):
    f = CTL / ('hour-' + name)
    return f.read_text().strip() if f.is_file() else default

if cmd == 'fetch-alpha':
    if (CTL / 'fail-alpha').is_file():
        sys.exit(1)
    h = hour('alpha')
    extra = 'ghost.json' if (CTL / 'advertise-ghost').is_file() else 'alpha-extra.json'
    MAP.joinpath('alpha.json').write_text(json.dumps(
        {'header': {'refTime': h, 'tileIndex': '/map/atiles/index.json',
                    'details': [{'url': '/map/' + extra}]}}))
    MAP.joinpath('alpha-extra.json').write_text(json.dumps({'header': {'refTime': h}}))
    if (CTL / 'rogue').is_file():
        MAP.joinpath('rogue.json').write_text('{}')
elif cmd == 'fetch-beta':
    if (CTL / 'fail-beta').is_file():
        sys.exit(1)
    MAP.joinpath('beta.json').write_text(json.dumps({'header': {'refTime': hour('beta')}}))
elif cmd == 'tiles-alpha':
    if (CTL / 'fail-tiles').is_file():
        sys.exit(1)
    if (CTL / 'hollow-tiles').is_file():
        # Exits 0 having written nothing, which is what a real pipeline does
        # when its upstream is down: keep the previous file, do not block the
        # deploy. The orchestrator must not read that as tiles.
        sys.stderr.write('! alpha unavailable: pretending\\n')
        sys.exit(0)
    h = json.loads(MAP.joinpath('alpha.json').read_text())['header']['refTime']
    d = MAP / 'atiles'; d.mkdir(exist_ok=True)
    (d / 'index.json').write_text(json.dumps({'refTime': h}))
elif cmd == 'key-alpha':
    sys.stderr.write('probing the fake catalog...\\n')
    print('kA')
elif cmd == 'contract':
    fails = CTL / 'contract-fails'
    if fails.is_file():
        sys.stdout.write(fails.read_text())
        if (CTL / 'contract-oneshot').is_file():
            fails.unlink()
        sys.exit(1)
    print('ok  everything holds')
elif cmd == 'roots':
    print('alpha.json')
    if not (CTL / 'roots-short').is_file():
        print('beta.json')
'''

TEST_TOML = '''
[contract]
check = ["python3", "fake_tool.py", "contract"]
roots = ["python3", "fake_tool.py", "roots"]

[defaults]
timeout_minutes = 1

[steps.alpha]
cmd = ["python3", "fake_tool.py", "fetch-alpha"]
lane = "a"
light = true

[steps.beta]
cmd = ["python3", "fake_tool.py", "fetch-beta"]
lane = "b"

[products.alpha]
title = "Alpha"
step = "alpha"
roots = ["alpha.json"]
writes = ["alpha*.json"]
max_age_hours = 4

[products.alpha.tiles]
build = ["python3", "fake_tool.py", "tiles-alpha"]
key = ["python3", "fake_tool.py", "key-alpha"]
cache = "alpha-tiles"
match = [["atiles", "alpha.json"]]

[products.beta]
title = "Beta"
step = "beta"
roots = ["beta.json"]
writes = ["beta*.json"]
'''

PREV_CHECKED = '2025-12-31T23:00:00Z'
PREV_UPDATED = '2025-12-31T22:00:00Z'


class Env:
    """One disposable pipeline world per test."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='orchestrate-test-')
        root = Path(self.tmp)
        orchestrate.ROOT = root
        orchestrate.SITE = root / 'site'
        orchestrate.STAGE = orchestrate.SITE / 'public' / 'map'
        orchestrate.PUBLISHED = root / 'published'
        orchestrate.OUT = root / 'out'
        orchestrate.BRANCH = root / 'branch-out'
        orchestrate.PLAN_FILE = root / 'plan.json'
        (orchestrate.SITE / 'ctl').mkdir(parents=True)
        orchestrate.STAGE.mkdir(parents=True)
        (orchestrate.SITE / 'fake_tool.py').write_text(FAKE_TOOL)

        pm = orchestrate.PUBLISHED / 'map'
        pm.mkdir(parents=True)
        # Carries `tileIndex` like the fetched one, or the carried-`updated`
        # check below sees a header that differs and calls the product changed.
        pm.joinpath('alpha.json').write_text(json.dumps(
            {'header': {'refTime': H0, 'tileIndex': '/map/atiles/index.json',
                        'details': [{'url': '/map/alpha-extra.json'}]}}))
        pm.joinpath('alpha-extra.json').write_text(json.dumps({'header': {'refTime': H0}}))
        pm.joinpath('beta.json').write_text(json.dumps({'header': {'refTime': H0}}))
        ps = orchestrate.PUBLISHED / 'status'
        ps.mkdir()
        for name in ('alpha', 'beta'):
            ps.joinpath(f'{name}.json').write_text(json.dumps(
                {'checked': PREV_CHECKED, 'updated': PREV_UPDATED}))

        self.cfg = orchestrate.parse_config(TEST_TOML)
        self.set_mode('full')
        os.environ.pop('GITHUB_OUTPUT', None)

    def set_mode(self, mode):
        orchestrate.PLAN_FILE.write_text(json.dumps(
            {'schema': 1, 'mode': mode, 'products': {}}))

    def ctl(self, name, content=''):
        (orchestrate.SITE / 'ctl' / name).write_text(content)

    def run(self):
        orchestrate.cmd_seed(self.cfg)
        return orchestrate.cmd_run(self.cfg)

    def status(self):
        return json.loads((orchestrate.OUT / 'status' / 'status.json').read_text())

    def receipt(self):
        return json.loads((orchestrate.OUT / 'status' / 'receipt.json').read_text())

    def out_hour(self, name):
        doc = json.loads((orchestrate.OUT / 'map' / name).read_text())
        return doc['header']['refTime']

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class OrchestrateTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)

    def test_all_fresh(self):
        self.env.ctl('hour-alpha', H1)
        self.env.ctl('hour-beta', H1)
        self.assertEqual(self.env.run(), 0)
        st = self.env.status()
        self.assertEqual(st['products']['alpha']['fate'], 'fresh')
        self.assertEqual(st['products']['beta']['fate'], 'fresh')
        self.assertEqual(self.env.out_hour('alpha.json'), H1)
        tiles = json.loads(
            (orchestrate.OUT / 'map' / 'atiles' / 'index.json').read_text())
        self.assertEqual(tiles['refTime'], H1)
        self.assertTrue(self.env.receipt()['deploy'])
        self.assertTrue(self.env.receipt()['built']['alpha-tiles'])
        # updated advanced with the content, checked with the attempt
        self.assertEqual(st['products']['alpha']['updated'], st['generated'])
        for name in ('alpha.json', 'alpha-extra.json', 'beta.json'):
            self.assertTrue((orchestrate.BRANCH / 'map' / name).is_file())

    def test_step_failure_holds_and_restores(self):
        self.env.ctl('fail-beta')
        self.assertEqual(self.env.run(), 0)
        st = self.env.status()
        self.assertEqual(st['products']['beta']['fate'], 'held')
        self.assertIn('step beta', st['products']['beta']['reason'])
        self.assertEqual(self.env.out_hour('beta.json'), H0)
        self.assertEqual(st['products']['beta']['checked'], PREV_CHECKED)
        self.assertEqual(st['products']['alpha']['fate'], 'fresh')
        self.assertTrue(self.env.receipt()['deploy'])

    def test_checked_advances_while_updated_carries(self):
        # Both fetch the same bytes as the last publish: the attempt is
        # fresh, the content is not — the outage-visibility distinction.
        self.assertEqual(self.env.run(), 0)
        alpha = self.env.status()['products']['alpha']
        self.assertEqual(alpha['fate'], 'fresh')
        self.assertEqual(alpha['updated'], PREV_UPDATED)
        self.assertNotEqual(alpha['checked'], PREV_CHECKED)
        self.assertTrue(alpha['stale'])  # months-old content, said out loud

    def test_write_fence_is_fatal(self):
        self.env.ctl('rogue')
        orchestrate.cmd_seed(self.env.cfg)
        with self.assertRaises(SystemExit) as caught:
            orchestrate.cmd_run(self.env.cfg)
        self.assertEqual(caught.exception.code, 3)

    def test_advertised_but_missing_holds(self):
        self.env.ctl('advertise-ghost')
        self.env.ctl('hour-alpha', H1)
        self.env.ctl('hour-beta', H1)
        self.assertEqual(self.env.run(), 0)
        alpha = self.env.status()['products']['alpha']
        self.assertEqual(alpha['fate'], 'held')
        self.assertIn('ghost.json', alpha['reason'])
        self.assertEqual(self.env.out_hour('alpha.json'), H0)

    def test_contract_demotes_one_product(self):
        self.env.ctl('hour-alpha', H1)
        self.env.ctl('hour-beta', H1)
        self.env.ctl('contract-fails', 'FAIL  alpha.json: bad vibes\n')
        self.env.ctl('contract-oneshot')
        self.assertEqual(self.env.run(), 0)
        st = self.env.status()
        self.assertEqual(st['products']['alpha']['fate'], 'held')
        self.assertEqual(st['products']['alpha']['reason'],
                         'failed the consumer contract')
        self.assertEqual(st['products']['beta']['fate'], 'fresh')
        self.assertEqual(self.env.out_hour('alpha.json'), H0)
        self.assertEqual(self.env.out_hour('beta.json'), H1)
        self.assertTrue(self.env.receipt()['deploy'])

    def test_contract_still_failing_stops_the_deploy(self):
        self.env.ctl('contract-fails', 'FAIL  alpha.json: permanently bad\n')
        self.assertEqual(self.env.run(), 0)
        self.assertFalse(self.env.receipt()['deploy'])

    def test_light_run_carries_and_guards_the_tiles(self):
        self.env.set_mode('light')
        self.assertEqual(self.env.run(), 0)
        st = self.env.status()
        self.assertEqual(st['products']['alpha']['fate'], 'fresh')
        self.assertEqual(st['products']['beta']['fate'], 'carried')
        # No tiles restored, none built on a light run: deploy refused,
        # branch kept, so the fetch is banked rather than thrown away.
        self.assertFalse(self.env.receipt()['deploy'])
        self.assertTrue((orchestrate.BRANCH / 'map' / 'alpha.json').is_file())

    def test_light_run_with_restored_tiles_deploys(self):
        self.env.set_mode('light')
        orchestrate.cmd_seed(self.env.cfg)
        tiles = orchestrate.STAGE / 'atiles'
        tiles.mkdir()
        (tiles / 'index.json').write_text(json.dumps({'refTime': H0}))
        self.assertEqual(orchestrate.cmd_run(self.env.cfg), 0)
        self.assertTrue(self.env.receipt()['deploy'])
        manifest = json.loads(
            (orchestrate.OUT / 'status' / 'alpha.json').read_text())
        self.assertEqual(manifest['tiles']['atiles']['state'], 'kept')

    def test_adrift_tiles_are_withheld_when_the_build_cannot_fix_them(self):
        self.env.ctl('hour-alpha', H1)
        self.env.ctl('hour-beta', H1)
        self.env.ctl('fail-tiles')
        orchestrate.cmd_seed(self.env.cfg)
        tiles = orchestrate.STAGE / 'atiles'
        tiles.mkdir()
        (tiles / 'index.json').write_text(json.dumps({'refTime': H0}))
        self.assertEqual(orchestrate.cmd_run(self.env.cfg), 0)
        self.assertFalse((orchestrate.OUT / 'map' / 'atiles').exists())
        manifest = json.loads(
            (orchestrate.OUT / 'status' / 'alpha.json').read_text())
        self.assertEqual(manifest['tiles']['atiles']['state'], 'withheld')
        self.assertFalse(self.env.receipt()['built']['alpha-tiles'])
        self.assertTrue(self.env.receipt()['deploy'])

    def test_a_build_that_produced_nothing_is_not_a_success(self):
        """**An exit code says "I did not fail", never "the tiles are
        there".** Measured in production 2026-08-16: the log read
        `building (0 adrift, 2 missing)` and then `ok` 0.4 s apart, with both
        directories still missing, and the publish went out advertising a
        tier it did not carry. Nothing was withheld and nothing recorded,
        because both walk the directories that exist."""
        self.env.ctl('hollow-tiles')
        self.assertEqual(self.env.run(), 0)
        self.assertFalse((orchestrate.OUT / 'map' / 'atiles').exists())
        # The cache must not be saved off a build that produced nothing, or
        # the key hits for ever and the gap can never refill — the
        # incomplete-artifact trap this repository already has a note about.
        self.assertFalse(self.env.receipt()['built']['alpha-tiles'])
        self.assertTrue(any('produced nothing' in n
                            for n in self.env.receipt()['notes']))
        # And the absence is on the record with its reason, which is the half
        # that had no trace at all: a directory never written cannot be
        # withheld, so it has to be named rather than inferred.
        manifest = json.loads(
            (orchestrate.OUT / 'status' / 'alpha.json').read_text())
        self.assertEqual(manifest['tiles']['atiles']['state'], 'absent')
        self.assertEqual(manifest['tiles']['atiles']['reason'],
                         'build produced no tiles')

    def test_a_withheld_tier_stops_being_advertised(self):
        """**A grid must not point at a tier the publish has just dropped.**
        Measured in production 2026-08-16: `currents.json` went out carrying
        `tileIndex: /map/tiles/index.json` with both directories withheld for
        being another hour, so every reader fetched a 404 per layer per view.
        The map catches it and the coarse grids stand — that fallback is
        right and is not the problem; the doomed request is."""
        self.env.ctl('hour-alpha', H1)
        self.env.ctl('hour-beta', H1)
        self.env.ctl('fail-tiles')
        orchestrate.cmd_seed(self.env.cfg)
        tiles = orchestrate.STAGE / 'atiles'
        tiles.mkdir()
        (tiles / 'index.json').write_text(json.dumps({'refTime': H0}))
        self.assertEqual(orchestrate.cmd_run(self.env.cfg), 0)
        head = json.loads(
            (orchestrate.OUT / 'map' / 'alpha.json').read_text())['header']
        self.assertNotIn('tileIndex', head)
        # Everything else about the grid survives: this drops one claim, not
        # the header it lives in.
        self.assertIn('details', head)
        self.assertEqual(head['refTime'], H1)

    def test_a_kept_tier_is_still_advertised(self):
        """The positive control, and the reason it is not optional: a change
        that stripped `tileIndex` unconditionally would satisfy the check
        above and quietly cost every reader the fine tier on a healthy run."""
        self.assertEqual(self.env.run(), 0)
        head = json.loads(
            (orchestrate.OUT / 'map' / 'alpha.json').read_text())['header']
        self.assertEqual(head.get('tileIndex'), '/map/atiles/index.json')
        self.assertTrue(
            (orchestrate.OUT / 'map' / 'atiles' / 'index.json').is_file())

    def test_unadvertising_reaches_every_grid_in_the_file(self):
        """**The currents are a list of two grids, and the integration
        fixture is a single object.** So the shape where this fails — the
        second depth keeping a `tileIndex` the first just lost — cannot be
        exhibited there at all: planting "only touch `doc[0]`" leaves every
        test above green. A pure function on a file is cheap to ask
        directly, so it is asked directly."""
        path = orchestrate.STAGE / 'pair.json'
        path.write_text(json.dumps([
            {'header': {'refTime': H0, 'tileIndex': '/map/t/index.json'}},
            {'header': {'refTime': H0, 'tileIndex': '/map/t/index.json'}},
        ]))
        self.assertTrue(orchestrate.unadvertise_tiles(path))
        for body in json.loads(path.read_text()):
            self.assertNotIn('tileIndex', body['header'])

        one = orchestrate.STAGE / 'one.json'
        one.write_text(json.dumps({'header': {'refTime': H0,
                                              'tileIndex': '/map/t/index.json'}}))
        self.assertTrue(orchestrate.unadvertise_tiles(one))
        self.assertNotIn('tileIndex',
                         json.loads(one.read_text())['header'])

        # Nothing to drop is not a change — the caller logs on the return
        # value, and a grid that never advertised must not report that it
        # stopped.
        self.assertFalse(orchestrate.unadvertise_tiles(one))
        # An unreadable file is not a crash: the publish has bigger problems
        # and this is not the place to raise them.
        self.assertFalse(orchestrate.unadvertise_tiles(orchestrate.STAGE / 'nope.json'))

    def test_roots_disagreement_refuses_to_run(self):
        self.env.ctl('roots-short')
        orchestrate.cmd_seed(self.env.cfg)
        self.assertEqual(orchestrate.cmd_run(self.env.cfg), 2)

    def test_plan_writes_keys_from_stdout_only(self):
        out = Path(self.env.tmp) / 'gh-output'
        os.environ['GITHUB_OUTPUT'] = str(out)
        try:
            self.assertEqual(orchestrate.cmd_plan(self.env.cfg, 'full'), 0)
        finally:
            os.environ.pop('GITHUB_OUTPUT', None)
        text = out.read_text()
        # Derived from the constant, never a literal: the version is bumped
        # whenever what the tiles contain changes, and an assertion carrying
        # its own copy has to be hand-edited every time — which is an
        # assertion that will eventually be edited to match a mistake. What
        # this is about is the *composition*: cache name, version, probe key.
        self.assertIn(
            f'cache-key-alpha-tiles=alpha-tiles-{orchestrate.CACHE_VERSION}-kA\n', text)
        self.assertIn('site/public/map/atiles', text)
        plan = json.loads(orchestrate.PLAN_FILE.read_text())
        self.assertEqual(plan['products']['alpha']['tile_key'], 'kA')


if __name__ == '__main__':
    unittest.main(verbosity=2)
