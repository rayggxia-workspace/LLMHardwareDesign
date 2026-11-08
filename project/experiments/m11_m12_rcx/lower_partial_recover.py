"""Resume only unfinished electrodes after a confirmed scheduler time limit."""
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import time

MASTER = struct.Struct('<I6dQd')
PARAMETERS = ['4096', '262144', '.5', '32', '256', '104729', '.01', '.05']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def validate(raw, records, allow_incomplete_tail=False):
    """Keep complete, ordered, valid lines; never silently skip a bad row."""
    lines = raw.splitlines(keepends=True)
    accepted = []
    discarded = b''
    for n, line in enumerate(lines):
        if not line.endswith(b'\n'):
            assert allow_incomplete_tail and n == len(lines) - 1
            discarded = line
            break
        assert n < len(records)
        row = json.loads(line)
        master = MASTER.unpack(records[n])
        assert row['master'] == master[0]
        assert row['before_ff'] > 0 and row['after_ff'] > 0
        assert all(math.isfinite(row[k]) and row[k] >= 0 for k in
                   ['before_sigma_ff', 'after_sigma_ff', 'paired_delta_sigma_ff'])
        assert abs(row['after_ff'] - row['before_ff'] - row['delta_ff']) <= 1e-8 * row['before_ff']
        assert row['full_delta_interval_low_ff'] <= row['delta_ff'] <= row['full_delta_interval_high_ff']
        assert row['analysis_precision_fraction'] == .01 and row['offset'] == .5
        assert row['per_net_confidence'] == .95 and type(row['qualified_precision']) is bool
        assert 4096 <= row['walks'] <= 262144 and row['walks'] % 256 == 0
        assert row['margin_um'] in [32, 64, 128, 256]
        assert abs(row['target_volume_um3'] - master[-1]) <= 1e-8 * master[-1] + 1e-16
        accepted.append(row)
    return accepted, b''.join(lines[:len(accepted)]), discarded


def main():
    started = time.monotonic()
    config_path = Path(os.environ['LOWER_CONFIG'])
    config = json.loads(config_path.read_text())
    case = config['cases'][int(os.environ.get('LOWER_INDEX', '0'))]
    assert case['terminal_state'] == 'TIMEOUT' and 'TIMEOUT' in case['accounting']
    original = Path(case['result'])
    invocation_path = original.parent / 'invocation.json'
    invocation = json.loads(invocation_path.read_text())
    assert invocation['script'] == 'lower_pair_run.py'
    assert invocation['code_root'] == config['original_code_root']
    assert invocation['source_sha256'] == config['original_script_sha256']
    assert invocation['source_manifest_sha256'] == config['original_manifest_sha256']
    assert invocation['arguments'] == config['original_arguments']
    assert invocation['output_root'] == config['original_output_root']
    assert int(invocation['array_index']) == case['shard']
    assert invocation['job_id'] == case['physical_job']
    assert str(original.parent) == invocation['output_root'] + '/job-' + case['physical_job'] + '-' + str(case['shard'])
    assert not (original / 'paired-solve.json').exists(), 'Use an existing completed receipt directly'
    scheduler_error = Path(case['slurm_stderr']).read_text()
    assert 'DUE TO TIME LIMIT' in scheduler_error and 'JOB ' + case['physical_job'] + ' ' in scheduler_error
    preparation_path = Path(config['tiles']) / 'prepare.json'
    preparation = json.loads(preparation_path.read_text())
    build_path = Path(config['build']) / 'build.json'
    build = json.loads(build_path.read_text())
    assert preparation['all_tile_files_hash_verified']
    assert build['all_controls_passed'] and build['cached_scene_view_exact']
    assert build['binary_sha256'] == config['accepted_binary_sha256']
    binary = Path(build['binary'])
    assert sha(binary) == build['binary_sha256']
    geometry = Path(preparation['geometry'])
    assert sha(geometry / 'masters.bin') == preparation['masters_sha256']
    raw_masters = (original / 'masters.bin').read_bytes()
    assert len(raw_masters) % MASTER.size == 0
    records = [raw_masters[n:n + MASTER.size] for n in range(0, len(raw_masters), MASTER.size)]
    expected_count = 2225422 * (case['shard'] + 1) // 256 - 2225422 * case['shard'] // 256
    assert len(records) == expected_count and len({MASTER.unpack(r)[0] for r in records}) == expected_count
    source = original / 'native-pairs.jsonl'
    original_hash = sha(source)
    prefix_rows, prefix, discarded = validate(source.read_bytes(), records, True)
    assert sha(source) == original_hash, 'The terminated source must remain unchanged'
    out = Path(os.environ['LOWER_OUT'])
    assert out.parent.parent == Path(config['original_output_root'])
    out.mkdir()
    (out / 'masters.bin').write_bytes(raw_masters)
    (out / 'reused-prefix.jsonl').write_bytes(prefix)
    remaining = records[len(prefix_rows):]
    missing = out / 'missing-masters.bin'
    missing.write_bytes(b''.join(remaining))
    command = [str(binary), str(geometry), str(missing), os.environ['LOWER_CPUS'], *PARAMETERS]
    suffix_path = out / 'continued-pairs.jsonl'
    with suffix_path.open('xb') as stdout, (out / 'field.log').open('xb') as stderr:
        if remaining:
            subprocess.run(command, stdout=stdout, stderr=stderr, check=True)
    suffix_rows, suffix, tail = validate(suffix_path.read_bytes(), remaining)
    assert not tail and len(suffix_rows) == len(remaining)
    all_rows = prefix_rows + suffix_rows
    assert len(all_rows) == len(records)
    final = out / 'native-pairs.jsonl'
    final.write_bytes(prefix + suffix)
    recovery = dict(original_result=str(original), original_invocation_sha256=sha(invocation_path),
                    original_partial_rows_sha256=original_hash, original_masters_sha256=sha(original / 'masters.bin'),
                    accounting=case['accounting'], scheduler_stderr_sha256=sha(case['slurm_stderr']),
                    reused_complete_rows=len(prefix_rows), computed_missing_rows=len(suffix_rows),
                    ignored_uncommitted_tail_bytes=len(discarded),
                    new_binary_is_identical=True, original_global_master_ids_and_rng_unchanged=True,
                    no_completed_electrodes_recomputed=True, recovery_configuration_sha256=sha(config_path))
    (out / 'recovery.json').write_text(json.dumps(recovery, indent=2) + '\n')
    unqualified = [r['master'] for r in all_rows if not r['qualified_precision']]
    result = dict(tile_preparation=config['tiles'], tile_preparation_sha256=sha(preparation_path),
                  build=config['build'], build_metadata_sha256=sha(build_path),
                  binary_sha256=sha(binary), rows_sha256=sha(final), rows_bytes=final.stat().st_size,
                  reporter_command=command, minimum_walks=4096, maximum_walks=262144,
                  seed=104729, offset=.5, initial_margin_um=32, maximum_margin_um=256,
                  confidence_budget=.05, cached_scene_view=True,
                  legacy_global_shard_membership_preserved=True, selected_population=2225422,
                  shard=case['shard'], shards=256, masters=[r['master'] for r in all_rows],
                  unqualified_masters=unqualified, all_precision_gates_passed=not unqualified,
                  analysis_precision_fraction=.01, acceptance_threshold_selected_by_user=False,
                  elapsed_seconds=time.monotonic() - started, recovery=recovery,
                  scope='Unchanged quiet-signal uniform-eps metal comparison. Complete source rows reused verbatim; only missing electrodes continued after scheduler timeout. No timing qualification.')
    (out / 'paired-solve.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(shard=case['shard'], reused=len(prefix_rows), computed=len(suffix_rows),
                          rows=len(all_rows), unqualified=len(unqualified))), flush=True)


if __name__ == '__main__':
    main()
