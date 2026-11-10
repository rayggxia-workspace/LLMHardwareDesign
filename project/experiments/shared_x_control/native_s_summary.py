#!/usr/bin/env python3
"""Reduce actual bank/ordinary-port RTL traces; no performance extrapolation."""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path


def summarize(path: Path) -> dict:
    rows = list(csv.DictReader(path.open()))
    pending = [collections.deque() for _ in range(4)]
    RTT = [[] for _ in range(4)]
    counts = collections.Counter()
    commands, loads, uses = {}, [], []
    current_use = None
    p0_reads = 0
    first_copy, last_copy = None, None
    max_owners = 0
    for row in rows:
        cycle, event, resource, identity, detail, value = (
            int(row['cycle']), row['event'], int(row['resource']),
            int(row['identity']), int(row['detail']), int(row['value']))
        counts[event] += 1
        if event == 'NREQ':
            pending[resource].append((cycle, identity, detail))
            max_owners = max(max_owners, value)
        elif event == 'NRSP':
            max_owners = max(max_owners, value)
            assert pending[resource], (path, 'orphan native response', row)
            start, write, address = pending[resource].popleft()
            RTT[resource].append({'request': start, 'response': cycle,
                                  'cycles': cycle-start, 'write': bool(write),
                                  'address': address})
        elif event == 'UREQ':
            if first_copy is None:
                first_copy = cycle
        elif event == 'PACK':
            last_copy = cycle
        elif event == 'SREQ':
            p0_reads += 1
        elif event == 'CMD':
            commands[(resource, identity)] = {
                'slot': resource, 'generation': identity, 'kk': detail,
                'planned_uses': value, 'command_accepted_cycle': cycle}
        elif event == 'LOAD':
            load = dict(commands[(resource, identity)])
            load.update(terminal_taken_cycle=cycle,
                        command_to_terminal_cycles=cycle-load['command_accepted_cycle'],
                        error=bool(detail))
            assert not detail, (path, 'unexpected LOAD error')
            loads.append(load)
        elif event == 'MUSE':
            assert current_use is None, (path, 'overlapping raw M A stream')
            current_use = {'slot': resource, 'generation': identity, 'kk': detail,
                           'use_sequence': value, 'accepted_cycle': cycle,
                           'A_accepted_cycles': [], 'reads_before': p0_reads}
        elif event == 'ASTEP':
            assert current_use is not None, (path, 'A stream without use')
            assert (resource, identity, detail) == (
                current_use['slot'], current_use['generation'], current_use['kk'])
            assert value == len(current_use['A_accepted_cycles'])
            current_use['A_accepted_cycles'].append(cycle)
            if value == 7:
                current_use.update(
                    use_to_first_A_handshake_cycles=current_use['A_accepted_cycles'][0]-current_use['accepted_cycle'],
                    use_to_last_A_handshake_cycles=cycle-current_use['accepted_cycle'],
                    concurrent_S_reads_during_use=p0_reads-current_use.pop('reads_before'),
                    includes_testbench_M_backpressure=True)
                uses.append(current_use)
                current_use = None
    assert not current_use and all(not queue for queue in pending), (path, 'undrained')
    assert counts['UREQ'] == 32 and counts['PACK'] == 96
    assert counts['SREQ'] == counts['SRSP'] == 32
    assert counts['MUSE'] == 3 and counts['ASTEP'] == 24
    assert len(loads) == 2 and len(uses) == 3
    assert max_owners in (1,2), (path, 'owner queue bounds')
    assert first_copy is not None and last_copy is not None
    return {
        'trace': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'events': dict(counts), 'native_port_RTT': RTT,
        'loads': loads, 'M_uses': uses, 'max_owner_metadata_slots': max_owners,
        'copy_512B_first_source_request_to_last_3P_ACK_cycles': last_copy-first_copy+1,
        'A_register_payload_bytes': 512, 'P_copy_hold_payload_bytes_each': 16,
        'A_total_S128_reads_for_three_uses': 32,
        'repeat_same_kk_requires_no_new_S_reads': uses[1]['kk'] == uses[0]['kk'],
        'note': 'A uses may overlap loading of a distinct second tile; per-use concurrent reads do not mean its own tile was reloaded.'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    traces = [summarize(path) for path in sorted(args.root.glob('native_s_a_copy-*.csv'))]
    assert len(traces) == 18, len(traces)
    output = {
        'schema': 'issue250-actual-s128-native-timelines/1',
        'Slurm_job': os.getenv('SLURM_JOB_ID'),
        'scope': 'candidate A/copy/mux RTL plus unchanged local_s_base and four real bank behavioral views per S; host tasks drive commands, no MC/LC program yet',
        'six_seeds_times_three_reset_initial_states': True,
        'copy_completely_committed_before_A_commands': os.getenv('NATIVE_NO_OVERLAP','0') == '1',
        'second_A_command_waits_first_LOAD_terminal': os.getenv('NATIVE_SINGLE_FIRST','0') == '1',
        'functional_clock_period_ns': 10,
        'clock_reason': 'bank DELAY=3ns is arbitrary functional delay, not characterized cell delay',
        'bank_sha256': '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7',
        'STA_300MHz_proof': False,
        'token_s_or_energy': None,
        'added_scratch_SRAM_bytes': 0,
        'new_S_data_ports': 0,
        'mux_storage_each': 'two owner bits and two 32bit tags plus queue pointers/count/arbitration; existing SRAM response payload buffers reused',
        'traces': traces}
    args.output.write_text(json.dumps(output, indent=2)+'\n')


if __name__ == '__main__':
    main()
