#!/usr/bin/env python3
"""Read-only W5-IF document/source/arithmetic checks, Python >=3.7.

This is neither an RTL simulation nor a protocol state-machine/liveness test.
Installed location: scripts/check_w5_if.py. Draft users must pass --root.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def historical_document_bytes(path, raw, expected_sha256, data, check):
    """Keep old W5 hash checks and additionally verify the explicit v0.6 edit.

    This applies to explicitly versioned documents only. Native source files
    retain their original exact fingerprints; no hash is replaced or skipped.
    """
    check(path in {'docs/COARSE_BLOCK_CONTROL_CONTRACT.md', 'docs/COARSE_BLOCK_HIERARCHY_CANDIDATE.md'},
          'no historical fallback for native code or unregistered docs')
    manifest = json.loads(data('work/Melodydt/151/h1/historical-w5/document-transform.json').decode('utf8'),
                          object_pairs_hook=unique_object)
    check(manifest['schema_version'] == 2, 'versioned document transform schema')
    matches = [x for x in manifest['documents'] if x['path'] == path]
    check(len(matches) == 1, 'exact registered historical document path')
    record = matches[0]
    check(record['historical_path'] == 'work/Melodydt/151/h1/historical-w5/' + Path(path).name + '.frozen.txt',
          'historical archive location')
    check(record['historical_sha256'] == expected_sha256, 'historical transform retains frozen SHA')
    check(hashlib.sha256(raw).hexdigest() == record['current_sha256'], 'current document transform SHA')
    prior = data(record['historical_path'])
    check(hashlib.sha256(prior).hexdigest() == expected_sha256, 'archived document frozen SHA')
    old = prior.decode('utf8')
    cursor = 0
    chunks = []
    for edit in record['edits']:
        start, end = edit['start'], edit['end']
        check(type(start) is int and type(end) is int and cursor <= start <= end <= len(old),
              'ordered historical document edit')
        check(old[start:end] == edit['old'], 'exact historical edit source')
        chunks.extend([old[cursor:start], edit['new']])
        cursor = end
    chunks.append(old[cursor:])
    transformed = ''.join(chunks)
    check(transformed.encode('utf8') == raw, 'exact declared document transformation')
    return prior


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.root.resolve()
    prefix = 'work/Melodydt/151/'
    checks = []
    inputs = {}
    historical_transforms = []

    def check(condition, label):
        if not condition:
            raise ValueError(label)
        checks.append(label)

    def data(path):
        target = (root / path).resolve()
        check(root == target or root in target.parents, 'inside root: ' + path)
        raw = target.read_bytes()
        inputs[path] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return raw

    def load(name):
        return json.loads(data(prefix + name).decode('utf-8'), object_pairs_hook=unique_object)

    def fingerprint(record, label, blob=False):
        raw = data(record['path'])
        if hashlib.sha256(raw).hexdigest() != record['sha256'] and record['path'].startswith('docs/'):
            raw = historical_document_bytes(record['path'], raw, record['sha256'], data, check)
            historical_transforms.append(record['path'])
        check(hashlib.sha256(raw).hexdigest() == record['sha256'], label + ' SHA256')
        if 'bytes' in record:
            check(len(raw) == record['bytes'], label + ' bytes')
        if blob:
            digest = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
            check(digest == record['git_blob_sha1'], label + ' git blob')

    contract = load('w5-if-contract.json')
    channels = load('w5-if-protocol-channels.json')
    traces = load('w5-if-example-traces.json')
    native = load('w5-if-native-audit.json')
    family = load('w5-if-family-audit.json')
    lock = load('w5-if-source-lock.json')

    for name, width, effective in [('command', 64, 53), ('event', 64, 48),
                                    ('offer', 40, 40), ('stored_ack', 64, 46)]:
        item = channels['wire_packing_candidate'][name]
        check(item.get('physical_flit_bits', item.get('logical_bits')) == width, name + ' carrier')
        check(item.get('effective_bits', width) == effective, name + ' effective declaration')
        covered = []
        used = 0
        for field in item['fields']:
            check(all(isinstance(field[x], int) for x in ('lsb', 'msb', 'bits')),
                  name + '.' + field['name'] + ' integer range')
            check(0 <= field['lsb'] <= field['msb'] < width and
                  field['bits'] == field['msb'] - field['lsb'] + 1,
                  name + '.' + field['name'] + ' range/width')
            covered.extend(range(field['lsb'], field['msb'] + 1))
            if field['name'] != 'reserved_zero':
                used += field['bits']
        check(sorted(covered) == list(range(width)), name + ' complete nonoverlapping carrier')
        check(used == effective, name + ' effective bits excluding reserved')

    # Independent literal fixture calculation; not generated by DUT or by a hex decoder.
    lanes = [1024, -2048, 512, 0, 1536, -1024, 256, -256]
    payload = sum((x & 65535) << (16 * i) for i, x in enumerate(lanes))
    offer = 3 | (41 << 16) | (1 << 33) | (16 << 34) | (1 << 39)
    check(traces['payload']['lanes'] == lanes, 'eight signed literal lanes')
    check(traces['payload']['hex128'].lower() == format(payload, '032x'), 'independent 8lane payload hex')
    check(traces['identity'] == {'epoch': 3, 'source_task_seq': 41, 'consumer_task_seq': 42,
                                  'fragment': 0}, 'literal trace keys')
    check(traces['payload']['offer_header40_hex'].lower() == format(offer, '010x'), 'independent OFFER40 hex')
    check(traces['payload']['offer_wire128_hex'].lower() == format(offer, '032x'), 'OFFER upper88 zero')
    check(traces['payload']['wire_beats'] == 2 and traces['payload']['native_T_payload_words'] == 1
          and traces['payload']['header_is_not_native_T_payload'] is True, 'header/payload separate accounting')

    wire = channels['wire_packing_candidate']
    endpoint = 2 * (64 + 2) + 2 * (128 + 2 + 1 + 5) + 2 * (64 + 2)
    check(endpoint == 536 == wire['pin_budget_candidate']['island_logical_endpoint_sum'], '536 endpoint arithmetic')
    hold = channels['holding_budget_candidate']
    check(sum(hold['per_island_explicit_records'].values()) == 656 == hold['record_sum_bits'], '656 holding arithmetic')
    check(hold['record_sum_bytes'] * 8 == 656, '82byte holding conversion')
    b8 = native['proposed']['B8_candidate']
    check(b8['one_island_endpoint_sum']['total'] == endpoint and b8['I2_island_endpoint_sum_bits'] == 2 * endpoint,
          'native/protocol endpoint agreement')
    st = b8['storage_declared_candidate']
    check(sum(st['local_bits'].values()) == 656 == st['local_sum_bits'], 'native 656 holding arithmetic')
    mother = sum(st['mother_per_local_bits'].values())
    facts = channels['event_progress']['latched_facts_candidate_bits'] + channels['event_progress']['pending_facts_candidate_bits']
    reject = sum(st['local_rejection_status_bits'].values())
    check(mother == 128 and facts == 26 and reject == 9, 'mother/facts/rejection declared bits')
    subtotal = 656 + mother + facts + reject
    check(subtotal == 819 == st['local_plus_mother_plus_26facts_and_rejection_bits_per_local'], '819 incomplete subtotal arithmetic')
    check(st['I2_enumerated_payload_plus_facts_and_rejection_bits'] == 2 * subtotal, '1638 two-island incomplete subtotal')
    check(st['not_minimum_area_or_total_controller_budget'] is True and len(st['unknown_extra_bits']) > 0
          and hold['not_a_complete_hardware_or_area_budget'] is True, 'subtotal is explicitly incomplete')

    # Bounded ANSI top declarations only; not a general SystemVerilog parser.
    check(set(native['profiles']) == {'P2_LITERAL_MST', 'W1_VARIABLE_MST', 'W4_F8_RMS',
                                      'W4_A8_QK_SOFTMAX_PV'}, '4 native profile inventory')
    for ident, profile in native['profiles'].items():
        raw = data(profile['path'])
        check(hashlib.sha256(raw).hexdigest() == profile['source_sha256'], ident + ' source SHA256')
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', raw.decode('utf-8'), flags=re.S)
        match = re.search(r'\bmodule\s+' + re.escape(profile['module']) + r'\s*\((.*?)\);', text, re.S)
        check(match is not None, ident + ' ANSI module header')
        ports = []
        direction, bits = None, None
        for token in match.group(1).split(','):
            declaration = re.fullmatch(r'\s*(?:(input|output)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?)?(\w+)\s*', token)
            check(declaration is not None, ident + ' bounded ANSI declaration')
            if declaration.group(1):
                direction = declaration.group(1)
                bits = abs(int(declaration.group(2)) - int(declaration.group(3))) + 1 if declaration.group(2) else 1
            check(direction is not None, ident + ' declaration direction')
            ports.append((declaration.group(4), direction, bits))
        expected = [(x['name'], x['direction'], x['bits']) for x in profile['ports']]
        check(ports == expected, ident + ' actual source port signature')
        check(len(ports) == profile['signal_count'], ident + ' signal count')
        for direction in ('input', 'output'):
            check(sum(x[2] for x in ports if x[1] == direction) == profile[direction + '_bits'], ident + ' ' + direction + ' bits')
        check(sum(x[2] for x in ports) == profile['logical_endpoint_bits_including_clock_reset_abort'], ident + ' endpoint sum')
        check(profile['ingress_beats'] * 16 == profile['input_transfer_bytes'] and
              profile['output_beats'] * 16 == profile['output_bytes'], ident + ' frame bytes')
        check(profile['normal_S_writes'] + profile['normal_S_reads'] == profile['normal_S_transactions'], ident + ' ordinaryS arithmetic')

    check(len(lock['sources']) == 23 and len({x['path'] for x in lock['sources']}) == 23,
          '23 unique selected source-lock records')
    changed = {x['path'] for x in lock['sources'] if x['unchanged_in_this_delivery'] is False}
    unchanged_count = 0
    for source in lock['sources']:
        check(source['at_commit'] == lock['input_commit'], 'source baseline: ' + source['path'])
        if source['unchanged_in_this_delivery']:
            fingerprint(source, 'unchanged ' + source['path'], blob=True)
            unchanged_count += 1
    check(lock['no_new_RTL_or_simulation'] is True, 'source lock no implementation claim')
    # Changed baseline docs retain their old fingerprints; transformed artifacts have new locks.
    for artifact in contract['artifact_transforms']:
        raw = data(artifact['formal'])
        check(hashlib.sha256(raw).hexdigest() == artifact['formal_sha256'], 'formal transform ' + artifact['formal'])
    check(contract['artifact_transforms'] == lock['artifact_transforms'], 'transform manifests agree')
    for source in family['input_provenance']:
        if source['path'] not in changed:
            fingerprint(source, 'family source ' + source['path'])

    models = family['models']
    profiles = family['profiles']
    check(len(models) == 8 and len({x['model_id'] for x in models}) == 8, '8 unique models')
    check({x['profile'] for x in profiles} == {'A_plain', 'A_gate', 'F', 'D', 'H', 'X'} and len(profiles) == 6,
          '6 unique complete profile requirements')
    check(family['scope']['models'] == 8 and family['scope']['profiles'] == 6, 'family declared inventory')
    check(max(x['H'] for x in models) == 3072 and 3072 * 2 == 6144, 'maximum hidden S16 one-token capacity example')
    check(family['protocol_review']['full_family_profiles_admitted'] == [], 'no full-family receive admission')
    check(contract['implementation']['new_RTL'] is False and contract['implementation']['RTL_simulation'] is False,
          'contract no new RTL/simulation')

    expected_traces = {'success', 'finite_backpressure', 'malformed_duplicate_header_phasefault',
                       'writeACK_pending_cohort_failure_partial', 'prestart_cancel', 'command_rejection'}
    check(set(traces['traces']) == expected_traces and len(traces['traces']) == 6, '6 unique trace groups')
    labels = [step['time'] for trace in traces['traces'].values() for step in trace]
    check(len(labels) == len(set(labels)), 'unique causal trace labels')
    check(traces['status'] == 'SPECIFICATION_EXAMPLES_NOT_SIMULATION_OR_TEST_CODE' and
          'not measuredcycles' in traces['clock'], 'trace non-simulation declaration')
    print(json.dumps({'status': 'PASS', 'kind': 'STATIC_CONTRACT_DOCUMENT_SOURCE_ARITHMETIC_CHECK_NOT_SIMULATION',
                      'root': str(root), 'checks_passed': len(checks), 'models': 8, 'profiles': 6,
                      'trace_groups': 6, 'native_profiles': len(native['profiles']),
                      'unchanged_source_locks_verified': unchanged_count,
                      'historical_document_transforms_verified': sorted(set(historical_transforms)),
                      'changed_baseline_sources_not_compared_to_old_hash': sorted(changed),
                      'subtotal_bits_per_island_incomplete': subtotal, 'inputs': inputs,
                      'limits': ['not RTL simulation', 'not protocol state-machine or liveness testing',
                                 'not synthesis/physical/minimum-area evidence', 'not full-profile admission']},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({'status': 'FAIL', 'kind': 'STATIC_CONTRACT_CHECK_NOT_SIMULATION',
                          'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
