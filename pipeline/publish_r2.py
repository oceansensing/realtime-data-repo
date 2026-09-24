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

**Every grid carries its spacing** as the object's `deg` metadata — the
smaller of its header's `dx` and `dy`, or a tile index's `deg` — which the
data host reads to hold D23's line (the owner, 2026-09-24: anything finer
than 0.25° is premium). A file that is not a grid carries none and is
anyone's. The tagging has a version, kept in `<repository>/.publish_r2.json`;
when it moves, everything is uploaded again once so no object keeps an old
tag.

Environment: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (the R2 token's
pair), R2_ENDPOINT, and R2_BUCKET (default `oceannow-data`). Standard
library only, like the orchestrator beside it, plus the AWS CLI the runner
carries.
"""

import hashlib
import json
import os
import re
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
# The tagging scheme's version: moving it re-uploads every object once.
TAGS_VERSION = 1
STATE = '.publish_r2.json'
# A grid's header is in its first few hundred bytes; a tile index is small.
HEAD_BYTES = 65536
_SPACING = re.compile(rb'"d([xy])"\s*:\s*([0-9.eE+-]+)')
_INDEX_DEG = re.compile(rb'"deg"\s*:\s*([0-9.eE+-]+)')


def spacing(path):
    """A grid's spacing in degrees, from its own header: the smaller of the
    first `dx` and `dy`, which in a coarse grid come before any region it
    links (and a region's own `deg`). A tile index says its cells' `deg`.
    None for everything else — status, platforms, forecasts' lists."""
    path = Path(path)
    if path.suffix != '.json':
        return None
    with path.open('rb') as f:
        head = f.read(HEAD_BYTES)
    found = {}
    for m in _SPACING.finditer(head):
        found.setdefault(m.group(1), float(m.group(2)))
        if len(found) == 2:
            break
    if found:
        return min(found.values())
    if path.name == 'index.json' and path.parent.name.startswith('tiles'):
        m = _INDEX_DEG.search(head)
        if m:
            return float(m.group(1))
    return None


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
        if key.startswith(prefix) and len(key) > len(prefix) and key[len(prefix):] != STATE:
            out[key[len(prefix):]] = obj.get('ETag', '').strip('"')
    return out


def plan(local, remote, everything=False):
    """What to upload (new or changed — or all of it, when the tagging moved)
    and what to delete (gone from the tree)."""
    uploads = sorted(k for k, md5 in local.items() if everything or remote.get(k) != md5)
    deletes = sorted(k for k in remote if k not in local)
    return uploads, deletes


def groups(root, keys):
    """The keys to upload, by the spacing each is tagged with (None: untagged)."""
    out = {}
    for key in keys:
        out.setdefault(spacing(Path(root, key)), []).append(key)
    return out


def aws(*args):
    return ['aws', '--endpoint-url', os.environ['R2_ENDPOINT'], '--region', 'auto', *args]


def list_remote(prefix):
    result = subprocess.run(aws('s3api', 'list-objects-v2', '--bucket', BUCKET, '--prefix', prefix,
                                '--output', 'json'), capture_output=True, text=True, check=True)
    return json.loads(result.stdout or '{}').get('Contents') or []


def upload(root, prefix, keys):
    for deg, batch in groups(root, keys).items():
        with tempfile.TemporaryDirectory() as staging:
            for key in batch:
                target = Path(staging, key)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(root, key), target)
            tag = [] if deg is None else ['--metadata', f'deg={deg!r}']
            subprocess.run(aws('s3', 'cp', staging, f's3://{BUCKET}/{prefix}', '--recursive',
                               *tag, '--no-progress', '--only-show-errors'), check=True)


def tags_version(prefix):
    """The tagging version the bucket's objects were written under, or 0."""
    result = subprocess.run(aws('s3', 'cp', f's3://{BUCKET}/{prefix}{STATE}', '-'),
                            capture_output=True, text=True)
    try:
        return json.loads(result.stdout).get('tags', 0) if result.returncode == 0 else 0
    except ValueError:
        return 0


def write_state(prefix):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'tags': TAGS_VERSION}, f)
    try:
        subprocess.run(aws('s3', 'cp', f.name, f's3://{BUCKET}/{prefix}{STATE}', '--only-show-errors'),
                       check=True)
    finally:
        os.unlink(f.name)


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
    retag = tags_version(prefix) != TAGS_VERSION
    uploads, deletes = plan(local, remote_tree(list_remote(prefix), prefix), everything=retag)
    upload(root, prefix, uploads)
    delete(prefix, deletes)
    if retag:
        write_state(prefix)
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
