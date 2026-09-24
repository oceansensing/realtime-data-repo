#!/usr/bin/env python3
"""The R2 publish: the tree this run built, published to Cloudflare R2.

  python3 pipeline/publish_r2.py <built-site-dir> <owner/repository>

**R2 is a publish target of its own, not a mirror of Pages** (ocean-now's
D24; the owner, 2026-09-24: *"When operational R2 server should be able to
function on its own without GitHub. Cross check with GitHub is a feature but
not requirement."*). Every origin's workflow runs this beside its Pages
deploy — on the same artifact, after the same publish decision, depending on
neither the deploy nor GitHub Pages being up — so the bucket holds, under
`<repository>/`, what this run built, whatever became of the Pages side. A
failure here never touches Pages, and a failed Pages deploy never stops this.

**Only what changed is uploaded.** A file's MD5 against the bucket's ETag,
which is the MD5 for anything uploaded in one part — so the multipart
threshold is raised past any file a tree carries. Re-uploading every tile
every run would be three to four million writes a month across the six
origins, past R2's free million; what changes is a fraction of that.

**Then the bucket is listed again and every file compared with what the run
built**, and anything that still differs fails the job loudly. That check
asks nothing of GitHub; comparing the bucket with Pages is a separate,
optional feature.

Two refusals, both before anything is sent: a tree without
`status/status.json` — every origin publishes one, and it is what the app
reads first (an empty or broken artifact would otherwise delete the
repository's whole prefix) — and a repository name that is not one. The
first draft asked for `map/manifest.json`, which no origin publishes; its
first run refused, sent nothing, and Pages published beside it as designed
(sentinel3-data-repo, 2026-09-24).

Environment: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (the R2 token's
pair), R2_ENDPOINT, and R2_BUCKET (default `oceannow-data`). Standard
library only, like the orchestrator beside it, plus the AWS CLI the runner
carries.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BUCKET = os.environ.get('R2_BUCKET', 'oceannow-data')
# Every file a tree carries is far smaller: the largest, the wind grid, is
# about 25 MB. Past this the CLI uploads in parts and the ETag stops being
# an MD5, which would read as a difference on every run.
MULTIPART_THRESHOLD = '256MB'


def prefix_for(repository):
    """`owner/name` or `name` to `name/` — with the slash, so
    `espc-model-repo/` can never match `espc-model-fields-repo/`."""
    # Strictly what follows the last slash: `oceansensing/` names an owner
    # and no repository, and must not be read as one called `oceansensing`.
    name = repository.strip().split('/')[-1]
    if not name or name in ('.', '..') or any(c in name for c in ' \\'):
        raise ValueError(f'not a repository name: {repository!r}')
    return name + '/'


def local_tree(root):
    """Every file under root, by its path relative to root, with its MD5."""
    root = Path(root)
    out = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and not path.is_symlink():
            out[path.relative_to(root).as_posix()] = hashlib.md5(path.read_bytes()).hexdigest()
    return out


def remote_tree(listing, prefix):
    """The bucket's keys under prefix, relative to it, with their ETags
    (quotes stripped). A key outside the prefix is never this repository's."""
    out = {}
    for obj in listing:
        key = obj.get('Key', '')
        if key.startswith(prefix) and len(key) > len(prefix):
            out[key[len(prefix):]] = obj.get('ETag', '').strip('"')
    return out


def plan(local, remote):
    """What to upload (new or changed) and what to delete (gone from the tree)."""
    uploads = sorted(k for k, md5 in local.items() if remote.get(k) != md5)
    deletes = sorted(k for k in remote if k not in local)
    return uploads, deletes


def aws(*args):
    return ['aws', '--endpoint-url', os.environ['R2_ENDPOINT'], '--region', 'auto', *args]


def list_remote(prefix):
    result = subprocess.run(aws('s3api', 'list-objects-v2', '--bucket', BUCKET, '--prefix', prefix,
                                '--output', 'json'), capture_output=True, text=True, check=True)
    return json.loads(result.stdout or '{}').get('Contents') or []


def upload(root, prefix, keys):
    if not keys:
        return
    with tempfile.TemporaryDirectory() as staging:
        for key in keys:
            target = Path(staging, key)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(root, key), target)
        subprocess.run(aws('s3', 'cp', staging, f's3://{BUCKET}/{prefix}', '--recursive',
                           '--no-progress', '--only-show-errors'), check=True)


def delete(prefix, keys):
    for i in range(0, len(keys), 1000):
        batch = {'Objects': [{'Key': prefix + k} for k in keys[i:i + 1000]], 'Quiet': True}
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(batch, f)
        try:
            subprocess.run(aws('s3api', 'delete-objects', '--bucket', BUCKET,
                               '--delete', f'file://{f.name}'), check=True, capture_output=True)
        finally:
            os.unlink(f.name)


def main(argv):
    if len(argv) != 3:
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    root, repository = Path(argv[1]), argv[2]
    try:
        prefix = prefix_for(repository)
    except ValueError as e:
        print(f'publish_r2: refusing: {e}', file=sys.stderr)
        return 2
    local = local_tree(root)
    if 'status/status.json' not in local:
        print(f'publish_r2: refusing: {root} has no status/status.json '
              f'({len(local)} files) — an empty or broken artifact would empty {prefix}', file=sys.stderr)
        return 2
    subprocess.run(['aws', 'configure', 'set', 'default.s3.multipart_threshold', MULTIPART_THRESHOLD],
                   check=True)
    uploads, deletes = plan(local, remote_tree(list_remote(prefix), prefix))
    upload(root, prefix, uploads)
    delete(prefix, deletes)
    left = plan(local, remote_tree(list_remote(prefix), prefix))
    if left[0] or left[1]:
        print(f'publish_r2: FAIL {BUCKET}/{prefix} still differs from the built tree: '
              f'{len(left[0])} to upload, {len(left[1])} to delete — first {(left[0] + left[1])[:5]}',
              file=sys.stderr)
        return 1
    print(f'publish_r2: {BUCKET}/{prefix} equals the built tree: {len(local)} files, '
          f'{len(uploads)} uploaded, {len(deletes)} deleted')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
