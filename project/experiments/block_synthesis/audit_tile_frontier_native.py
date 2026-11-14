"""Count activation traffic in an archived native projection command DAG."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def audit(candidate):
    down = [call for call in candidate['calls'] if call['recipe_part'] == 'down']
    mid = next(call['storage_value'] for call in down if call['direction'] == 'load')
    copies = [call for call in down if call['direction'] == 'load']
    writes = [call for call in candidate['calls']
              if call['recipe_part'] == 'gated_activation' and call['direction'] == 'store'
              and call['storage_value'] == mid]
    scopes = [bytes.fromhex(call['descriptor_hex']) for call in down if call['direction'] == 'compute']
    if not scopes or not writes or any(call['storage_value'] != mid for call in copies):
        raise ValueError('expected one intermediate with native scopes, loads and stores')
    coverage = defaultdict(int)
    for call in copies:
        coverage[call['ddr_address'], call['byte_count']] += 1
    if any(c['completion'] != 'destination_commit_ack' for c in (*copies, *writes)):
        raise ValueError('unexpected transfer completion contract')
    if any(call['byte_count'] != 512 for call in writes):
        raise ValueError('expected 512 B native store ranges')
    k_extents = set()
    output_groups = []
    for descriptor in scopes:
        if len(descriptor) != 128 or int.from_bytes(descriptor[6:8], 'little') != 2:
            raise ValueError('expected 128 B stream descriptor')
        k = int.from_bytes(descriptor[76:78], 'little')
        first_k = int.from_bytes(descriptor[78:80], 'little')
        last_k = int.from_bytes(descriptor[80:82], 'little')
        if first_k != 0 or last_k != k:
            raise ValueError('expected one complete K stream per native scope')
        groups = descriptor[74] & 0x1f  # groups occupy bits 592 through 596
        ways = descriptor[82] & 3
        if not 1 <= groups <= 16 or ways != 1:
            raise ValueError('expected one way and up to 16 RF contexts')
        k_extents.add(k)
        output_groups.append(groups * 8)
    if len(k_extents) != 1:
        raise ValueError('inconsistent reduction lengths')
    loaded = sum(c['byte_count'] for c in copies)
    written = sum(c['byte_count'] for c in writes)
    unique = sum(size for _, size in coverage)
    if unique != written:
        raise ValueError('writer and unique loader extent differ')
    k = next(iter(k_extents))
    rows, tail = divmod(unique, 4 * k)
    if not rows or tail:
        raise ValueError('native middle tensor must be S32')
    return {'binding': candidate['binding'], 'k': k, 'rows': rows,
            'output_columns_per_scope': sorted(set(output_groups)),
            'directions': dict(Counter(call['direction'] for call in down)),
            'mid_reads_bytes': loaded, 'mid_writes_bytes': written,
            'unique_mid_bytes': unique, 'load_reuse_counts': sorted(set(coverage.values())),
            'mid_handoff_bytes': loaded + written}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    payload = args.candidate.read_bytes()
    print(json.dumps({'source_sha256': hashlib.sha256(payload).hexdigest(),
                      **audit(json.loads(payload))}, indent=2))


if __name__ == '__main__':
    main()
