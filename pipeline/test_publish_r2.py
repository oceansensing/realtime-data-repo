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


if __name__ == '__main__':
    unittest.main(verbosity=2)
