"""Verify exact artifact membership, hashes, committed code, and replay."""
import argparse
import json
from pathlib import Path
from evidence import RUN_SOURCES, sha, validate_snapshot, verify_index, verify_source


def verify(folder, replay=True):
    folder = Path(folder)
    manifest = json.loads((folder/'manifest.json').read_bytes())
    verify_index(folder, manifest['files'], 'manifest.json')
    if sha((folder/'inputs/capture.json').read_bytes()) != manifest['input_manifest_sha256']:
        raise AssertionError('Capture manifest changed')
    validate_snapshot(folder/'inputs')
    verify_source(manifest['provenance'], RUN_SOURCES, current=replay)
    if replay:
        from run import derive
        expected = derive(folder/'inputs')
        if {k for k in manifest['files'] if not k.startswith('inputs/')} != set(expected):
            raise AssertionError('Unexpected derived artifacts')
        for name, data in expected.items():
            if data != (folder/name).read_bytes():
                raise AssertionError('Replay differs: ' + name)
    return {'status':'PASS', 'files':len(manifest['files']), 'replay':replay,
            'source_commit':manifest['provenance']['source_commit']}


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('folder',type=Path)
    p.add_argument('--no-replay',action='store_true')
    a=p.parse_args()
    print(json.dumps(verify(a.folder,not a.no_replay)))
