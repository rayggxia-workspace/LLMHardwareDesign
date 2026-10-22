"""Small evidence primitives for the selected Issue19 input contract."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REMOTE_ROOT = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06'
CAPTURE_SOURCES = ['capture.py', 'evidence.py', 'inputs.json', 'top-contract-completion.json']
RUN_SOURCES = ['evidence.py', 'run.py', 'views.py', 'liberty_profile.py', 'graph.py', 'verify.py', 'archive.py',
               'inputs.json', 'top-contract-completion.json', '../macro_endpoints/lef_profile.py']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def provenance(names):
    if git('status', '--porcelain'):
        raise AssertionError('Commit source/config and use a clean worktree before formal execution')
    return {'source_commit': git('rev-parse', 'HEAD'), 'source_dirty': False,
            'files': {(HERE / n).resolve().relative_to(ROOT).as_posix(): sha((HERE / n).read_bytes()) for n in names},
            'python': sys.version, 'platform': platform.platform(), 'temporary_directory': os.environ.get('TEMP'),
            'python_cache_prefix': sys.pycache_prefix}


def verify_source(record, names, current=False):
    expected = {(HERE / n).resolve().relative_to(ROOT).as_posix() for n in names}
    if record['source_dirty'] is not False or set(record['files']) != expected:
        raise AssertionError('Incomplete/dirty source provenance')
    for name, digest in record['files'].items():
        data = subprocess.check_output(['git', 'show', record['source_commit'] + ':' + name], cwd=ROOT)
        if sha(data) != digest or (current and sha((ROOT / name).read_bytes()) != digest):
            raise AssertionError('Source does not match its Git blob: ' + name)


def index(folder):
    return {p.relative_to(folder).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def verify_index(folder, files, manifest):
    folder = Path(folder).resolve()
    if set(index(folder)) != {*files, manifest}:
        raise AssertionError('Missing or unindexed evidence file')
    for name, info in files.items():
        path = (folder / name).resolve()
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or not path.is_relative_to(folder):
            raise AssertionError('Unsafe evidence path')
        data = path.read_bytes()
        if len(data) != info['bytes'] or sha(data) != info['sha256']:
            raise AssertionError('Evidence bytes/SHA changed: ' + name)


def config(data):
    cfg = json.loads(data)
    allowed = {}
    for candidate, task, macro, size in [('ACT20', 'act-cap20', 'llhd_opentpu_act', 792384),
                                          ('MXU20', 'mxu-cap20', 'llhd_opentpu_mxu', 1569065)]:
        for name in ['boundary.sv', 'elab.json', 'experiment.json', 'output-files.sha256', macro + '_typ.lib']:
            allowed[candidate + '/' + name] = task + '/' + (
                'flow/results/nangate45/parallel_opentpu_' + ('act' if candidate == 'ACT20' else 'mxu') + '/base/'
                if name.endswith('.lib') else '') + name
    if (cfg['schema'] != 1 or cfg['input_version'] != 'act-mxu-three-view-wave206-v1'
            or cfg['ssh_host'] != 'yuzelu@10.129.166.172' or cfg['allowed_root'] != REMOTE_ROOT
            or len(cfg['files']) != 10 or {x['name']: x['relative_path'] for x in cfg['files']} != allowed
            or cfg['limits'] != {'max_file_bytes': 8000000, 'max_total_bytes': 9000000}):
        raise AssertionError('Configuration leaves the declared ten-file read-only scope')
    if [(m['id'], m['macro'], m['task']) for m in cfg['macros']] != [
            ('ACT20', 'llhd_opentpu_act', 'act-cap20'), ('MXU20', 'llhd_opentpu_mxu', 'mxu-cap20')]:
        raise AssertionError('Unknown macro identity')
    return cfg


def check_observation(cfg, item, row, data):
    stamp = row['stat_before']
    resolved = PurePosixPath(row['resolved_path'])
    if (row['requested_path'] != REMOTE_ROOT + '/' + item['relative_path']
            or not resolved.is_absolute() or '..' in resolved.parts
            or not str(resolved).startswith(REMOTE_ROOT + '/')
            or stamp != row['stat_after'] or len(stamp) != 4
            or any(type(v) is not int or v < 0 for v in stamp) or stamp[2] != len(data)
            or len(data) != row['bytes'] or sha(data) != row['sha256']
            or len(data) != item['previous_observed_bytes'] or len(data) > cfg['limits']['max_file_bytes']):
        raise AssertionError('Unstable, changed, out-of-scope or corrupted source: ' + item['name'])
    if item['prior_expected_sha256'] is not None and sha(data) != item['prior_expected_sha256']:
        raise AssertionError('Pinned upstream expected hash mismatch: ' + item['name'])


def checksum_entries(data):
    entries = {}
    for line in data.decode('ascii').splitlines():
        if len(line) < 67 or line[64:66] not in ('  ', ' *'):
            raise AssertionError('Malformed producer SHA-256 index')
        digest, name = line[:64], line[66:]
        if any(c not in '0123456789abcdef' for c in digest) or name in entries:
            raise AssertionError('Invalid/duplicate producer index entry')
        entries[name] = digest
    return entries


def validate_snapshot(folder, check_code=True):
    folder = Path(folder)
    manifest = json.loads((folder / 'capture.json').read_bytes())
    verify_index(folder, manifest['files'], 'capture.json')
    cfg_bytes = (folder / 'inputs.json').read_bytes()
    cfg = config(cfg_bytes)
    expected_files = {x['name'] for x in cfg['files']} | {'inputs.json', 'contract.json', 'lef16-capture.json', 'ACT20.lef', 'MXU20.lef'}
    if set(manifest['files']) != expected_files or manifest['config_sha256'] != sha(cfg_bytes):
        raise AssertionError('Snapshot does not contain the selected views')
    if manifest['remote_user'] != 'yuzelu' or manifest['ssh_host'] != cfg['ssh_host']:
        raise AssertionError('Unexpected capture identity')
    config_name = (HERE / 'inputs.json').relative_to(ROOT).as_posix()
    contract_name = (HERE / 'top-contract-completion.json').relative_to(ROOT).as_posix()
    contract_data = (folder / 'contract.json').read_bytes()
    if (manifest['provenance']['files'][config_name] != sha(cfg_bytes)
            or manifest['provenance']['files'][contract_name] != sha(contract_data)
            or sha(contract_data) != cfg['upstream']['contract_sha256']):
        raise AssertionError('Input contract/config is not from the declared source snapshot')
    if check_code:
        verify_source(manifest['provenance'], CAPTURE_SOURCES, current=True)
    from capture import program
    if (manifest['reused_lef16_archive_sha256'] != cfg['lef16']['archive_sha256']
            or manifest['collector_sha256'] != sha(program(cfg).encode())):
        raise AssertionError('Capture collector/archive provenance changed')
    rows = manifest['observations']
    if len(rows) != 10 or {x['name'] for x in rows} != {x['name'] for x in cfg['files']}:
        raise AssertionError('Wrong captured file set')
    by_name = {x['name']: x for x in rows}
    for item in cfg['files']:
        check_observation(cfg, item, by_name[item['name']], (folder / item['name']).read_bytes())
    if sum(r['bytes'] for r in rows) > cfg['limits']['max_total_bytes']:
        raise AssertionError('Capture exceeds total byte limit')
    old = json.loads((folder / 'lef16-capture.json').read_bytes())
    if (sha((folder / 'lef16-capture.json').read_bytes()) != cfg['lef16']['capture_sha256']
            or old['provenance']['source_commit'] != cfg['lef16']['source_commit']):
        raise AssertionError('LEF16 source capture changed')
    comparisons = []
    for m in cfg['macros']:
        candidate = m['id']
        lef_data = (folder / (candidate + '.lef')).read_bytes()
        if sha(lef_data) != cfg['lef16']['lef_sha256'][candidate] or sha(lef_data) != old['files'][candidate + '.lef']['sha256']:
            raise AssertionError('Wrong LEF16 geometry version')
        entries = checksum_entries((folder / candidate / 'output-files.sha256').read_bytes())
        selected = {'boundary.sv': folder / candidate / 'boundary.sv', 'elab.json': folder / candidate / 'elab.json',
                    'experiment.json': folder / candidate / 'experiment.json',
                    m['result'] + '/' + m['macro'] + '_typ.lib': folder / candidate / (m['macro'] + '_typ.lib'),
                    m['result'] + '/' + m['macro'] + '.lef': folder / (candidate + '.lef')}
        for relative, path in selected.items():
            actual = sha(path.read_bytes())
            if entries.get(relative) != actual:
                raise AssertionError('Selected view differs from producer output index: ' + candidate + '/' + relative)
            comparisons.append({'candidate': candidate, 'producer_relative_path': relative, 'sha256': actual})
    return cfg, manifest, comparisons
