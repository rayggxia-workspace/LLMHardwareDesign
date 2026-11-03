#!/usr/bin/env python3
"""Offline AF16 contract/model admission only; no RTL, inference or hardware model.

Default installation: scripts/check_af_model_admission.py. All source-lock paths
are repository-relative. An explicit --ledger can select a separately staged draft.
Exit0: static contract checks pass / request ALLOW; exit2: request GAP/UNKNOWN;
exit1: malformed data, stale sources or conformance example disagreement.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path


def unique_object(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError('duplicate JSON key: ' + key)
        out[key] = value
    return out


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def dotted(value, key):
    for part in key.split('.'):
        if not isinstance(value, dict) or part not in value:
            return {'MISSING_REQUIRED_FIELD': key}
        value = value[part]
    return value


def patched(value, changes):
    out = copy.deepcopy(value)
    for key, replacement in changes.items():
        parent = out
        parts = key.split('.')
        for part in parts[:-1]:
            parent = parent[part]
        parent[parts[-1]] = replacement
    return out


def model_result(model_id, target, family, ledger):
    matches = [m for m in family['models'] if m['model_id'] == model_id]
    if not matches:
        return {'model_id': model_id, 'target': target, 'decision': 'UNKNOWN',
                'conditions': [{'id': 'MODEL_ID', 'status': 'UNKNOWN', 'reason': 'outside locked eight-model family'}]}
    if target not in ('A16', 'F16', 'AF16'):
        raise ValueError('unknown target ' + target)
    m = matches[0]
    row = next(x for x in ledger['models'] if x['model_id'] == model_id)
    layers = [x for x in family['layer_types'] if x['model_id'] == model_id]
    attention = [x['attention'] for x in layers if x.get('attention')]
    checks = []

    def add(ident, status, actual, reason):
        checks.append({'id': ident, 'status': status, 'actual': actual, 'reason': reason})

    add('H', 'ALLOW' if m['hidden_size'] == 8 else 'GAP', m['hidden_size'], 'fixed selected hardware H=8; source H is never downsized')
    add('EXPORTED_SMALL_CASE', 'ALLOW' if m['actual_export_batch'] == 1 and m['actual_export_sequence_tokens'] == 2 else 'GAP',
        {'B': m['actual_export_batch'], 'Sq': m['actual_export_sequence_tokens']}, 'source export only; not admitted runtime length/context')
    add('HIDDEN_NUMERIC', 'UNKNOWN', row['accepted_hidden_numeric'], 'source FP32 export does not establish S16Fin10 model quantization')
    add('NUMERIC_QUALITY', 'UNKNOWN', None, 'no accepted full-model integer error/quality certificate')
    add('EPSILON', 'ALLOW' if m['rms_norm_eps_config'] == 2 ** -20 else 'GAP', m['rms_norm_eps_config'],
        'selected code1 at Fin10 is exactly2^-20; approximate replacement needs independent acceptance')
    roles = ['input'] if target == 'A16' else ['pre_ffn'] if target == 'F16' else ['input', 'pre_ffn']
    norm = sorted({s['kind'] for x in layers for s in x['normalization_sites'] if s['role'] in roles})
    add('NORM_KIND', 'ALLOW' if norm == ['RMS'] else 'GAP', norm, 'selected path ordinary RMS only; RMS0 effective gamma binding is extra work')
    post_roles = ['post_attention'] if target == 'A16' else ['post_ffn'] if target == 'F16' else ['post_attention', 'post_ffn']
    post = [s['role'] for x in layers for s in x['normalization_sites'] if s['role'] in post_roles]
    add('POST_NORM', 'GAP' if post else 'ALLOW', post, 'selected path has no extra branch postNorm before residual')
    add('GAMMA_BINDING', 'UNKNOWN', None, 'real learned gamma range/rounding/RMS0 conversion and distinct A/F versions not accepted')
    add('N_GROUP', 'ALLOW' if m['hidden_size'] <= 257 else 'GAP', m['hidden_size'], 'current N controller count<=257; word width and program must expand')
    norm_bytes = 6 * m['hidden_size']
    add('STORAGE', 'GAP' if norm_bytes > 16384 else 'UNKNOWN', {'three_norm_arrays_S16_bytes': norm_bytes},
        'three arrays alone exceed S if GAP; otherwise a complete fixed-layout/lifetime/supply program is still unproved')
    add('PARAMETER_IMAGE', 'UNKNOWN', None, 'actual accepted quantized/reordered weights, gamma, coefficients and checkpoint versions missing')
    add('SOURCE_POSITION_BOUND', 'UNKNOWN', m['source_max_position_embeddings'], 'source position maximum is not hardware accepted context/prefill range')
    if target in ('A16', 'AF16'):
        geometry = row['attention_geometry']
        expected = {'query_heads': 1, 'kv_heads': 1, 'head_dim': 8, 'gqa_replication': 1}
        add('ATTENTION_GEOMETRY', 'ALLOW' if all(geometry[k] == v for k, v in expected.items()) else 'GAP', geometry,
            'selected one Q/KV head, D8, no GQA; cannot replace source geometry with toy shape')
        bias = any(x.get('qkv_bias', False) for x in attention)
        add('QKV_BIAS', 'GAP' if bias else 'ALLOW', bias, 'selected projections have no bias stage')
        head_norm = [s['kind'] for x in layers for s in x['normalization_sites'] if s['role'] in ('query_head', 'key_head')]
        add('QK_NORM', 'GAP' if head_norm else 'ALLOW', head_norm, 'selected path lacks per-head normalization')
        add('ROPE_LAYOUT_POSITION', 'GAP', m['rope_parameters'], 'source split-half/partial/model-frequency rules not adapted by adjacent-pair fixed fixtures')
        gate = any(x.get('query_output_gate', False) for x in attention)
        add('OUTPUT_GATE', 'GAP' if gate else 'ALLOW', gate, 'selected A has no G Sigmoid context gate')
        add('ATTENTION_BOUNDARY', 'GAP' if model_id == 'falcon' else 'ALLOW', row['profile_types'],
            'Falcon H shares inputNorm and joins SSM; isolated ordinary full A changes its boundary' if model_id == 'falcon' else 'logical first residual boundary, still not accepted physical/numeric mapping')
        add('ATTENTION_GAIN', 'GAP' if model_id in ('granite', 'falcon') else 'ALLOW', model_id,
            'selected path lacks source Granite gain/score scalar or Falcon key/branch MuP' if model_id in ('granite', 'falcon') else 'ordinary inverse-sqrt(D), but real D and coefficient recipe still differ')
    if target in ('F16', 'AF16'):
        add('I', 'ALLOW' if m['ffn_intermediate_size'] == 8 else 'GAP', m['ffn_intermediate_size'], 'selected fixed I8; actual I retained')
        add('ACTIVATION', 'ALLOW' if m['activation'] == 'silu' else 'GAP', m['activation'], 'selected SiLU-gated path; Gemma GELU/postNorm requires new accepted program')
        add('FFN_BOUNDARY', 'GAP' if model_id == 'granite' else 'ALLOW', row['profile_types'], 'Granite tail is X/MoE, not complete F per expert' if model_id == 'granite' else 'complete second residual remains required')
        add('MID_STORAGE', 'GAP' if 2 * m['ffn_intermediate_size'] >= 16384 else 'UNKNOWN', 2 * m['ffn_intermediate_size'],
            'mid alone exhausts/exceeds S if GAP; otherwise actual packed loader/layout/weight supply still required')
        add('FFN_GAIN', 'GAP' if model_id == 'falcon' else 'ALLOW', model_id, 'Falcon nonlinearity-before/after MuP absent' if model_id == 'falcon' else 'no special source MuP in selected ordinary dense tail')
    if target == 'AF16':
        add('LAYER_GRAMMAR', 'GAP' if model_id in ('qwen35', 'granite', 'falcon') else 'ALLOW', row['profile_types'], 'AF wrapper is ordinary A->F; D/A_gate, X or H do not become ordinary AF')
    decision = 'GAP' if any(x['status'] == 'GAP' for x in checks) else 'UNKNOWN' if any(x['status'] == 'UNKNOWN' for x in checks) else 'ALLOW'
    return {'model_id': model_id, 'target': target, 'decision': decision, 'actual_H': m['hidden_size'],
            'actual_I': m['ffn_intermediate_size'], 'conditions': checks, 'static_only': True}


def request_result(request, family, ledger):
    if request.get('model_id') is not None:
        result = model_result(request['model_id'], request.get('target', 'AF16'), family, ledger)
        known = next((x for x in family['models'] if x['model_id'] == request['model_id']), None)
        claimed = request.get('shape', {})
        if known and ('H' in claimed and claimed['H'] != known['hidden_size'] or
                      'I' in claimed and claimed['I'] != known['ffn_intermediate_size']):
            result['conditions'].append({'id': 'NO_DOWNSIZE', 'status': 'GAP', 'reason': 'request cannot redefine locked model dimensions'})
            result['decision'] = 'GAP'
        return result
    failures = []
    declared = {r['path'].split('.')[0] for r in ledger['synthetic_contract_rules']}
    if set(request) - declared:
        failures.append('UNDECLARED_FIELDS')
    for rule in ledger['synthetic_contract_rules']:
        if canonical(dotted(request, rule['path'])) != canonical(rule['expected']):
            failures.append(rule['id'])
    return {'profile_id': request.get('profile_id'), 'decision': 'GAP' if failures else 'ALLOW',
            'failed_rules': failures, 'static_only': True,
            'allow_scope': 'only synthetic fixed AF16 ABI; not RTL/quality/physical/model admission'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--ledger', type=Path, default=Path('work/Melodydt/151/af16-model-admission.json'))
    p.add_argument('--request', type=Path)
    p.add_argument('--wrapper', type=Path, default=Path('project/rtl/block_connection_w4/block_w4_af16_top.sv'))
    p.add_argument('--model')
    p.add_argument('--target', choices=('A16', 'F16', 'AF16'), default='AF16')
    a = p.parse_args()
    root = a.root.resolve()
    ledger_path = a.ledger if a.ledger.is_absolute() else root / a.ledger
    ledger = read_json(ledger_path)
    if ledger['schema_version'] != 1 or ledger['only_static_allow_profile'] != 'synthetic_af16_h8_sq2_i8_v1':
        raise ValueError('unsupported admission contract')
    checked_sources = []
    for record in ledger['input_sources']:
        path = (root / record['path']).resolve()
        if root not in path.parents:
            raise ValueError('source outside root: ' + record['path'])
        raw = path.read_bytes()
        if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('stale locked source: ' + record['path'])
        checked_sources.append(record['path'])
    wrapper_path = a.wrapper if a.wrapper.is_absolute() else root / a.wrapper
    wrapper = wrapper_path.read_bytes()
    if len(wrapper) != ledger['wrapper_review']['bytes'] or hashlib.sha256(wrapper).hexdigest() != ledger['wrapper_review']['sha256']:
        raise ValueError('AF wrapper source changed; independent review must be refreshed')
    family = read_json(root / ledger['source_tables']['family'])
    coarse = read_json(root / ledger['source_tables']['coarse'])
    roles = read_json(root / ledger['source_tables']['roles'])
    graph_index = read_json(root / ledger['source_tables']['source_graph_index'])
    if len(family['models']) != 8 or len(ledger['models']) != 8 or len(family['layer_types']) != 10:
        raise ValueError('family inventory changed')
    if roles['role_count'] != 172 or sum(x['role_count'] for x in roles['role_shards']) != 172:
        raise ValueError('role catalog inventory changed')
    for m in family['models']:
        row = next(x for x in ledger['models'] if x['model_id'] == m['model_id'])
        cm = next(x for x in coarse['model_rows'] if x['model_id'] == m['model_id'])
        if row['H'] != m['hidden_size'] or row['I'] != m['ffn_intermediate_size'] or cm['H'] != row['H'] or cm['I'] != row['I']:
            raise ValueError('source/model dimensions disagree: ' + m['model_id'])
        if row['attention_geometry'] != cm['attention_geometry']:
            raise ValueError('attention source geometry changed')
        if (row['source_RMS_epsilon'] != m['rms_norm_eps_config'] or row['source_activation'] != m['activation']
                or row['source_RoPE'] != m['rope_parameters'] or row['source_max_position'] != m['source_max_position_embeddings']):
            raise ValueError('model algorithm/source fields disagree: ' + m['model_id'])
        for target in ('A16', 'F16', 'AF16'):
            calculated = model_result(m['model_id'], target, family, ledger)
            stored = row['selected_results'][target]
            actual = [(x['id'], x['status'], x['actual']) for x in calculated['conditions']]
            recorded = [(x['id'], x['status'], x['actual']) for x in stored['conditions']]
            if calculated['decision'] != stored['decision'] or canonical(actual) != canonical(recorded):
                raise ValueError('stale per-condition decision ledger: ' + m['model_id'] + '/' + target)
    for graph in ledger['source_graph_evidence']['records']:
        original = next(x for x in graph_index['sources'] if x['id'] == graph['id'])
        if any(original[k] != v for k, v in graph.items()):
            raise ValueError('graph provenance disagrees with locked index: ' + graph['id'])
    for shard in roles['role_shards']:
        path = root / 'work/Melodydt/151' / shard['file']
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != shard['sha256'] or len(read_json(path)['role_contracts']) != shard['role_count']:
            raise ValueError('role shard evidence mismatch: ' + shard['file'])
    if a.request or a.model:
        request_path = a.request if a.request and a.request.is_absolute() else root / a.request if a.request else None
        request = read_json(request_path) if request_path else {'model_id': a.model, 'target': a.target}
        result = request_result(request, family, ledger)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['decision'] == 'ALLOW' else 2
    # Independent fixed ABI examples carry literal expected labels/rejection IDs.
    # The checker never generates its own expected result from evaluated rules.
    fixture_results = []
    for case in ledger['conformance_examples']:
        request = patched(ledger['positive_synthetic_request'], case['patch'])
        result = request_result(request, family, ledger)
        if result['decision'] != case['expected_decision']:
            raise ValueError('example decision mismatch: ' + case['id'])
        actual = result.get('failed_rules', [x['id'] for x in result.get('conditions', []) if x['status'] == 'GAP'])
        expected = case.get('expected_failed_rules', [])
        if case.get('expected_subset', False):
            okay = set(expected).issubset(actual)
        else:
            okay = set(actual) == set(expected)
        if not okay:
            raise ValueError('example rejection mismatch: ' + case['id'])
        fixture_results.append({'id': case['id'], 'decision': result['decision'], 'checked': True})
    results = [model_result(m['model_id'], target, family, ledger) for m in family['models'] for target in ('A16', 'F16', 'AF16')]
    if any(x['decision'] == 'ALLOW' for x in results):
        raise ValueError('unexpected real-model admission without numeric certificate')
    print(json.dumps({'status': 'PASS_STATIC_ADMISSION_CHECKS', 'static_allow_profiles': [ledger['only_static_allow_profile']],
                      'source_files_verified': len(checked_sources), 'conformance_examples': fixture_results,
                      'reviewed_wrapper_sha256_verified': hashlib.sha256(wrapper).hexdigest(),
                      'real_model_results': results, 'models': 8, 'targets_per_model': 3,
                      'scope': 'contract identity/format/shape/evidence only; no RTL/inference/numeric-quality/physical execution'},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, TypeError, StopIteration) as e:
        print(json.dumps({'status': 'FAIL_STATIC_ADMISSION_CHECK', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
