#!/usr/bin/env python3
"""publish_r2's rules, with no bucket: what a sync would upload and delete,
whose keys it may touch, and the refusals that come before anything is sent.
Run by the R2 publish job before it publishes, and by hand: python3 pipeline/test_publish_r2.py"""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import publish_r2  # noqa: E402


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


class PublishR2Tests(unittest.TestCase):
    def test_a_prefix_is_the_repository_name_with_its_slash(self):
        self.assertEqual(publish_r2.prefix_for('oceansensing/espc-model-repo'), 'espc-model-repo/')
        self.assertEqual(publish_r2.prefix_for('sentinel3-data-repo'), 'sentinel3-data-repo/')
        for bad in ('', '/', 'oceansensing/', '..', 'a b'):
            with self.assertRaises(ValueError, msg=bad):
                publish_r2.prefix_for(bad)

    def test_another_repositorys_keys_are_never_ours(self):
        listing = [{'Key': 'espc-model-repo/status/status.json', 'ETag': '"aa"'},
                   {'Key': 'espc-model-fields-repo/status/status.json', 'ETag': '"bb"'},
                   {'Key': 'espc-model-repo/', 'ETag': '"cc"'}]
        self.assertEqual(publish_r2.remote_tree(listing, 'espc-model-repo/'), {'status/status.json': 'aa'})

    def test_only_what_changed_is_uploaded_and_what_left_is_deleted(self):
        local = {'status/status.json': md5('new'), 'map/sst.json': md5('same'), 'map/tiles/0_0.json': md5('t')}
        remote = {'status/status.json': md5('old'), 'map/sst.json': md5('same'), 'map/gone.json': md5('x')}
        uploads, deletes = publish_r2.plan(local, remote)
        self.assertEqual(uploads, ['map/tiles/0_0.json', 'status/status.json'])
        self.assertEqual(deletes, ['map/gone.json'])
        self.assertEqual(publish_r2.plan(local, dict(local)), ([], []))

    def test_the_local_tree_is_every_file_with_its_md5(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'map/tiles').mkdir(parents=True)
            Path(d, 'status').mkdir()
            Path(d, 'status/status.json').write_text('{}')
            Path(d, 'map/tiles/0_0.json').write_text('[1]')
            self.assertEqual(publish_r2.local_tree(d),
                             {'status/status.json': md5('{}'), 'map/tiles/0_0.json': md5('[1]')})

    def test_a_tree_without_its_manifest_is_refused_before_anything_is_sent(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'index.html').write_text('<html>')
            with mock.patch.object(subprocess, 'run', side_effect=AssertionError('sent something')):
                self.assertEqual(publish_r2.main(['publish_r2.py', d, 'oceansensing/realtime-data-repo']), 2)
                self.assertEqual(publish_r2.main(['publish_r2.py', d, '..']), 2)

    def test_a_bucket_that_still_differs_fails_the_job(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'status').mkdir()
            Path(d, 'status/status.json').write_text('{}')
            # The bucket never takes the upload: the second listing still
            # lacks the file, and the job must say so rather than pass.
            with mock.patch.object(publish_r2, 'list_remote', return_value=[]), \
                 mock.patch.object(publish_r2, 'upload'), mock.patch.object(publish_r2, 'delete'), \
                 mock.patch.object(subprocess, 'run'), mock.patch.dict('os.environ', {'R2_ENDPOINT': 'x'}):
                self.assertEqual(publish_r2.main(['publish_r2.py', d, 'realtime-data-repo']), 1)
            listing = [{'Key': 'realtime-data-repo/status/status.json', 'ETag': f'"{md5("{}")}"'}]
            with mock.patch.object(publish_r2, 'list_remote', return_value=listing), \
                 mock.patch.object(publish_r2, 'upload'), mock.patch.object(publish_r2, 'delete'), \
                 mock.patch.object(subprocess, 'run'), mock.patch.dict('os.environ', {'R2_ENDPOINT': 'x'}):
                self.assertEqual(publish_r2.main(['publish_r2.py', d, 'realtime-data-repo']), 0)

    def test_a_grid_is_tagged_with_its_own_spacing(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'map/tiles-sst').mkdir(parents=True)
            # A coarse grid names a finer region in its header: its own dx
            # comes first and is what it is.
            Path(d, 'map/sst.json').write_text('[{"header":{"nx":360,"dx":1.0,"dy":1.0,'
                                               '"regions":[{"deg":0.08}]},"data":[1]}]')
            Path(d, 'map/tiles-sst/0_0.json').write_text('[{"header":{"dx":0.08333333333333333,"dy":0.08333333333333333},"data":[]}]')
            Path(d, 'map/tiles-sst/index.json').write_text('{"size":20,"deg":0.08333333333333333,"available":[]}')
            Path(d, 'map/uneven.json').write_text('{"header":{"dx":0.5,"dy":0.25},"data":[]}')
            # A platform file with a `deg` of its own is not a tile index.
            Path(d, 'map/assets.json').write_text('{"assets":[{"deg":0.01}]}')
            Path(d, 'status').mkdir()
            Path(d, 'status/status.json').write_text('{}')
            spacing = publish_r2.spacing
            self.assertEqual(spacing(Path(d, 'map/sst.json')), 1.0)
            self.assertAlmostEqual(spacing(Path(d, 'map/tiles-sst/0_0.json')), 1 / 12)
            self.assertAlmostEqual(spacing(Path(d, 'map/tiles-sst/index.json')), 1 / 12)
            self.assertEqual(spacing(Path(d, 'map/uneven.json')), 0.25)
            self.assertIsNone(spacing(Path(d, 'map/assets.json')))
            self.assertIsNone(spacing(Path(d, 'status/status.json')))
            grouped = publish_r2.groups(d, ['map/sst.json', 'map/tiles-sst/0_0.json', 'status/status.json'])
            self.assertEqual(grouped[(1.0, None)], ['map/sst.json'])
            self.assertEqual(grouped[(None, None)], ['status/status.json'])
            # The upload tags each group, and leaves the untagged untagged.
            calls = []
            with mock.patch.object(subprocess, 'run', side_effect=lambda args, **k: calls.append(args)), \
                 mock.patch.dict('os.environ', {'R2_ENDPOINT': 'x'}):
                publish_r2.upload(d, 'r/', ['map/sst.json', 'status/status.json'])
            tags = sorted(c[c.index('--metadata') + 1] if '--metadata' in c else '-' for c in calls)
            self.assertEqual(tags, ['-', 'deg=1.0'])

    def test_a_new_tagging_uploads_everything_once_and_the_state_is_not_data(self):
        local = {'a.json': md5('a'), 'b.json': md5('b')}
        self.assertEqual(publish_r2.plan(local, dict(local)), ([], []))
        self.assertEqual(publish_r2.plan(local, dict(local), everything=True), (['a.json', 'b.json'], []))
        listing = [{'Key': 'r/.publish_r2.json', 'ETag': '"s"'}, {'Key': 'r/a.json', 'ETag': f'"{md5("a")}"'}]
        self.assertEqual(publish_r2.remote_tree(listing, 'r/'), {'a.json': md5('a')})

    # ocean-now's D26 (2026-09-26): an origin R2 alone carries, premium
    # unless it declares a path free; every other origin exactly as before.

    def test_an_origin_on_pages_too_tags_no_access_and_is_never_retagged_for_it(self):
        self.assertIsNone(publish_r2.declaration_from([]))
        self.assertIsNone(publish_r2.access_for('map/sst.json', None))
        # Its state file today is {"tags": 1}: nothing moves, nothing is
        # uploaded again, and a retag for another reason writes the same.
        self.assertFalse(publish_r2.needs_retag({'tags': publish_r2.TAGS_VERSION}, None))
        self.assertEqual(publish_r2.state_for(None), {'tags': publish_r2.TAGS_VERSION})
        self.assertIsNone(publish_r2.metadata(None, None))
        self.assertEqual(publish_r2.metadata(0.25, None), 'deg=0.25')

    def test_an_r2_only_origin_is_premium_but_its_status_and_what_it_declares_free(self):
        decl = publish_r2.declaration_from(['--r2-only', '--free', 'map/open.json', '--free', 'map/tiles-open/'])
        self.assertEqual(decl, {'r2Only': True, 'free': ['map/open.json', 'map/tiles-open/']})
        access = lambda key: publish_r2.access_for(key, decl)  # noqa: E731
        self.assertEqual(access('map/licensed.json'), 'premium')
        self.assertEqual(access('map/tiles-licensed/0_0.json'), 'premium')
        self.assertIsNone(access('status/status.json'), 'the routing is every reader\'s')
        self.assertIsNone(access('map/open.json'))
        self.assertIsNone(access('map/tiles-open/0_0.json'))
        self.assertIsNone(access('map/tiles-open'))
        self.assertEqual(access('map/open.json.bak'), 'premium', 'a free path is a path, not a prefix of a name')
        self.assertEqual(access('map/tiles-opener/0_0.json'), 'premium')
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'map').mkdir()
            Path(d, 'status').mkdir()
            Path(d, 'map/licensed.json').write_text('{"header":{"dx":1.0,"dy":1.0},"data":[]}')
            Path(d, 'map/list.json').write_text('{"items":[]}')
            Path(d, 'map/open.json').write_text('{"header":{"dx":1.0,"dy":1.0},"data":[]}')
            Path(d, 'status/status.json').write_text('{}')
            calls = []
            with mock.patch.object(subprocess, 'run', side_effect=lambda args, **k: calls.append(args)), \
                 mock.patch.dict('os.environ', {'R2_ENDPOINT': 'x'}):
                publish_r2.upload(d, 'r/', ['map/licensed.json', 'map/list.json', 'map/open.json',
                                            'status/status.json'], decl)
            tags = sorted(c[c.index('--metadata') + 1] if '--metadata' in c else '-' for c in calls)
            self.assertEqual(tags, ['-', 'access=premium', 'deg=1.0', 'deg=1.0,access=premium'])

    def test_a_changed_declaration_retags_the_origin_once(self):
        decl = publish_r2.declaration_from(['--r2-only'])
        self.assertTrue(publish_r2.needs_retag({'tags': publish_r2.TAGS_VERSION}, decl))
        self.assertTrue(publish_r2.needs_retag(publish_r2.state_for(decl),
                                               publish_r2.declaration_from(['--r2-only', '--free', 'map/a.json'])))
        self.assertFalse(publish_r2.needs_retag(publish_r2.state_for(decl), decl))

    def test_a_declaration_that_is_not_one_is_refused_before_anything_is_sent(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'status').mkdir()
            Path(d, 'status/status.json').write_text('{}')
            with mock.patch.object(subprocess, 'run', side_effect=AssertionError('sent something')):
                for flags in (['--free', 'map/a.json'], ['--r2-only', '--free'], ['--r2-only', '--frees', 'x'],
                              ['--r2-only', '--free', '../x'], ['--r2-only', '--free', '/map/a.json'],
                              ['--r2-only', '--free', 'status/status.json'], ['--pages']):
                    self.assertEqual(publish_r2.main(['publish_r2.py', d, 'licensed-data-repo', *flags]), 2, flags)

    def test_main_hands_the_declaration_to_the_upload_and_the_state(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'status').mkdir()
            Path(d, 'status/status.json').write_text('{}')
            listing = [{'Key': 'licensed-data-repo/status/status.json', 'ETag': f'"{md5("{}")}"'}]
            with mock.patch.object(publish_r2, 'list_remote', return_value=listing), \
                 mock.patch.object(publish_r2, 'read_state', return_value={'tags': publish_r2.TAGS_VERSION}), \
                 mock.patch.object(publish_r2, 'upload') as upload, mock.patch.object(publish_r2, 'delete'), \
                 mock.patch.object(publish_r2, 'write_state') as write, \
                 mock.patch.object(subprocess, 'run'), mock.patch.dict('os.environ', {'R2_ENDPOINT': 'x'}):
                self.assertEqual(publish_r2.main(['publish_r2.py', d, 'licensed-data-repo', '--r2-only']), 0)
            decl = {'r2Only': True, 'free': []}
            self.assertEqual(upload.call_args.args[3], decl)
            self.assertEqual(upload.call_args.args[2], ['status/status.json'], 'a new declaration re-sends it all')
            write.assert_called_once_with('licensed-data-repo/', decl)


if __name__ == '__main__':
    unittest.main(verbosity=2)
