"""Read-only verification of exact per-round source/input/result evidence.

Does not simulate, compile or transfer qualification to later source versions.
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--current-run', action='append', default=[],
                        help='explicitly check these run source hashes against current local files')
    args = parser.parse_args()
    index = json.loads((HERE / 'index.json').read_bytes())
    artifacts = {}
    for row in index['artifacts']:
        name = row['path']
        require(name not in artifacts, 'duplicate artifact ' + name)
        path = HERE / name
        require(path.resolve().is_relative_to(HERE.resolve()), 'out-of-scope artifact')
        stored = path.read_bytes()
        require(len(stored) == row['stored_bytes'] and sha(stored) == row['stored_sha256'], 'stored SHA drift ' + name)
        if row['encoding'] == 'gzip+base64':
            raw = gzip.decompress(base64.b64decode(stored, validate=False))
        else:
            require(row['encoding'] == 'raw', 'unknown artifact encoding')
            raw = stored
        require(len(raw) == row['raw_bytes'] and sha(raw) == row['raw_sha256'], 'original SHA drift ' + name)
        artifacts[name] = (row, raw)
    counts = dict(artifacts=len(artifacts), source_members=0, inputs=0, selected_results=0, current_sources=0, indexed_remote_only=0)
    statuses = []
    for run, record in index['runs'].items():
        rows = {r['source_path']: raw for r, raw in artifacts.values() if r['run'] == run}
        require(len(rows) == sum(r['run'] == run for r, _ in artifacts.values()), 'duplicate run path')
        manifest = json.loads(rows['inputs.json'])
        collection = json.loads(rows['collection.json'])
        summary = json.loads(rows['receipts.summary.json'])
        require(record['source_commit'] == manifest['source_commit'] == collection['source_commit'], 'source identity mismatch')
        require(record['job'] == collection['job'], 'job status drift')
        require(record['classification'] == collection['classification'], 'run classification drift')
        require(summary == record['summary'], 'archive summary drift')
        require(sha(rows['collection.json']) == summary['collection_sha256'], 'collection SHA drift')
        code_manifest = {name: digest for digest, name in (line.split('  ', 1) for line in rows['source-files.sha256'].decode().splitlines())}
        require(code_manifest == manifest['code_sha256'], 'deployed source hash manifest mismatch')
        input_manifest = {name: digest for digest, name in (line.split('  ', 1) for line in rows['input-files.sha256'].decode().splitlines())}
        require(input_manifest == manifest['input_sha256'], 'deployed input hash manifest mismatch')
        snapshot = artifacts[record['source_snapshot']][1]
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as archive:
            members = archive.getmembers()
            require(all(m.isfile() for m in members), 'snapshot contains a non-file')
            require(len(members) == len(code_manifest) and {m.name for m in members} == set(code_manifest), 'source snapshot coverage')
            for member in members:
                raw = archive.extractfile(member).read()
                require(sha(raw) == code_manifest[member.name], 'source snapshot drift ' + member.name)
                counts['source_members'] += 1
                if run in args.current_run:
                    require(sha((REPO / member.name).read_bytes()) == code_manifest[member.name], 'current source differs from requested run: ' + member.name)
                    counts['current_sources'] += 1
        for name, digest in input_manifest.items():
            require(sha(rows['frozen-inputs/' + name]) == digest, 'frozen input drift ' + name)
            counts['inputs'] += 1
        outputs = {name: digest for digest, name in (line.split('  ', 1) for line in rows['output-files.sha256'].decode().splitlines())}
        if 'retention.json' in rows:
            retention = json.loads(rows['retention.json'])
            require(retention['run'] == run and retention['source_commit'] == record['source_commit'], 'retention identity mismatch')
            require(retention['local_receipt_archive_sha256'] == summary['receipts_sha256'], 'retention archive mismatch')
            indexed = {entry['path']: entry for entry in retention['files']}
            require(len(indexed) == len(retention['files']), 'duplicate retention path')
            require(set(indexed) == set(collection['collected_files']) | {'collection.json'}, 'retention coverage mismatch')
            for name, entry in indexed.items():
                require(entry['server_path'] == collection['run_root'] + '/' + name, 'retention location drift')
                if name in rows:
                    require(entry['retention'] == 'repository' and sha(rows[name]) == entry['sha256'] and len(rows[name]) == entry['bytes'], 'retained content drift ' + name)
                else:
                    require(entry['retention'] == 'server_and_local_archive' and name in outputs and outputs[name] == entry['sha256'] and entry['bytes'] > 100000, 'remote-only hash index drift ' + name)
                    counts['indexed_remote_only'] += 1
        selected = {name: raw for name, raw in rows.items() if name.startswith('results/')}
        for name, raw in selected.items():
            require(sha(raw) == outputs[name], 'server output SHA drift ' + name)
            counts['selected_results'] += 1
        result = json.loads(rows['results/result.json']) if 'results/result.json' in rows else None
        expected_pass = (record['job']['state'] == 'COMPLETED' and record['job']['exit_code'] == '0:0'
                         and result is not None and result.get('passed') is True and not collection['warnings'])
        require(record['whole_run_passed'] is expected_pass and collection['whole_run_passed'] is expected_pass,
                'failed/partial run reported as passed')
        if result is not None:
            require(result['source_commit'] == record['source_commit'], 'result source identity drift')
            require(result['manifest_sha256'] == sha(rows['inputs.json']), 'result belongs to another deployment manifest')
            require(sha(rows['results/result.json']) == summary['main_result_sha256'], 'main result SHA drift')
            if expected_pass:
                require(not result.get('error') and not result.get('errors') and not result.get('traceback'),
                        'passed result contains a recorded failure')
        statuses.append(dict(run=run, round=record['round'], state=record['job']['state'],
                             passed=expected_pass, source_commit=record['source_commit']))
    require(set(args.current_run) <= set(index['runs']), 'unknown requested current-source run')
    print(json.dumps(dict(passed=True, counts=counts, runs=statuses,
                         scope='evidence and optional explicit current-source comparison; no EDA, physical or full-LLM execution'), indent=2))


if __name__ == '__main__':
    main()
