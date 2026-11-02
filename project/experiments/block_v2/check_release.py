"""Verify the six-leaf handoff; never promotes unfinished R or reruns EDA."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-artifacts', action='store_true',
                        help='Also rehash all 249 unpacked members in the indexed local storage.')
    args = parser.parse_args()
    index = json.loads((ROOT/'work/YUZE-LU/143/release-six/index.json').read_text(encoding='utf-8'))
    assert set(index['accepted_macros']) == {'M', 'N', 'E', 'G', 'S', 'T'}
    assert index['R']['status'] == 'unfinished' and index['R']['qualified'] is False
    assert index['R']['selected'] is False and 'R' not in index['macros']
    checked = members = 0
    for path, digest in index['support_files_sha256'].items():
        assert sha(ROOT/path) == digest, path
        checked += 1
    for macro, row in index['macros'].items():
        assert row['qualified'] is True
        for path, digest in row['rtl_sha256'].items():
            assert sha(ROOT/path) == digest, path
        for key in ['bundle', 'received']:
            assert sha(ROOT/row[key+'_path']) == row[key+'_sha256'], (macro, key)
        bundle = json.loads((ROOT/row['bundle_path']).read_text(encoding='utf-8'))
        received = json.loads((ROOT/row['received_path']).read_text(encoding='utf-8'))
        assert bundle['passed'] and bundle['native_leaf_accepted']
        assert received['passed'] and received['native_leaf_accepted']
        assert row['archive'] == bundle['archive']
        assert len(bundle['members']) == row['verified_local_members']
        assert set(row['final_files']) == {'6_final.'+x for x in ['v', 'sdc', 'def', 'odb', 'spef', 'gds']}
        for name, item in row['final_files'].items():
            assert item['sha256'] == bundle['members']['native/'+name]['sha256']
        for path, digest in row['evidence_sha256'].items():
            assert sha(ROOT/path) == digest, path
            checked += 1
        if args.local_artifacts:
            directory = Path(row['local_directory'])/'unpacked'
            for name, item in bundle['members'].items():
                path = directory/name
                assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], path
                members += 1
    assert sha(ROOT/index['R']['rtl']) == index['R']['rtl_sha256']
    print(json.dumps(dict(passed=True, accepted=index['accepted_macros'], R='unfinished',
                         repository_files_checked=checked, local_members_checked=members,
                         scope='Evidence/source integrity only; no new EDA qualification.')))


if __name__ == '__main__':
    main()
