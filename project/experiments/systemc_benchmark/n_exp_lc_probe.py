"""Audit serialized compact images and replay the E13/S/N recipe on native U64.

No timing coefficients are inferred from this testbench. PM is behavioral,
the two U targets are a control fixture, and no whole-model score is produced.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

ABI, TOPOLOGY = 0x01930001, 0x01930010
ORACLE_SHA = 'f2b456fdcb537d8cf770467af41a7c486621148c8d86c20fc9b7db3720d66a9b'
ROWS = (
    ((0x100, 308, 8, 13), (0x101, 41993, 0, 0),
     (0x100, 1, 0, 0), (0x100, 5, 9, 33), (0x100, 1, 0, 2),
     (0x100, 341, 9, 19), (0x101, 44042, 0, 0)),
    ((0x103, 41, 0, 0), (0x102, 0, 0, 0),
     (0x103, 43, 0, 0), (0x102, 0, 0, 0)))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def audit_images(directory):
    """Decode bytes directly; do not import the assembler or fixture generator."""
    result = {}
    for block, name in enumerate(('mother', 'local0', 'local1')):
        path = directory/(name+'.mem')
        lines = path.read_text().splitlines()
        need(lines and all(re.fullmatch('[0-9a-fA-F]{32}', x) for x in lines), 'memory words')
        data = b''.join(int(x, 16).to_bytes(16, 'little') for x in lines)
        local = block > 0
        rows = ROWS[block-1] if local else ()
        instructions = []
        if local:
            for index in range(len(rows)):
                instructions += [(0x41 << 56) | (index << 32), (0x44 << 56) | 1]
            instructions += [0x4f << 56]
        else:
            instructions = [(0x10 << 56) | (2 << 40),
                            (0x10 << 56) | (1 << 48) | (3 << 40),
                            (0x11 << 56) | 12, 0x1f << 56]
        count = len(instructions)
        end_inst = 128+((count+1)//2)*16
        expected_length = end_inst+(64+128*len(rows) if local else 0)
        header = bytearray(128)
        struct.pack_into('<QHBBIII', header, 0, 0x313041534943424c, 2, int(local),
                         8, expected_length, 0, count)
        for offset, value in ((24, 128), (36, end_inst if local else 0),
                              (44, end_inst+64 if local else 0), (52, count),
                              (56, int(local)), (60, 19300+block),
                              (64, TOPOLOGY), (68, ABI), (84, 0x17630001)):
            struct.pack_into('<I', header, offset, value)
        struct.pack_into('<H', header, 28, int(local))
        struct.pack_into('<H', header, 32, len(rows))
        need(data[:128] == header and len(data) == expected_length,
             name+': header identities/bounds/reserved bytes')
        words = [int.from_bytes(data[128+8*i:136+8*i], 'little') for i in range(count)]
        need(words == instructions, name+': decoded instruction sequence')
        need(not any(data[128+8*count:end_inst]), name+': compact padding')
        if local:
            task = bytearray(64)
            struct.pack_into('<H', task, 0, 1)
            for offset, value in ((16, count), (20, 1), (24, 19300+block),
                                  (28, TOPOLOGY), (44, ABI)):
                struct.pack_into('<I', task, offset, value)
            need(data[end_inst:end_inst+64] == task, name+': task descriptor')
            for index, (op, n0, n1, n2) in enumerate(rows):
                record = bytearray(128)
                struct.pack_into('<HHH', record, 0, 1, 0, op)
                record[8:12] = bytes([255]*4)
                record[20:26] = bytes([255]*6)
                struct.pack_into('<I', record, 56, ABI)
                struct.pack_into('<III', record, 64, n0, n1, n2)
                start = end_inst+64+index*128
                need(data[start:start+128] == record, name+': service descriptor '+str(index))
        result[name] = dict(sha256=sha(path), bytes=len(data), instruction_count=count,
                            execution_count=len(rows), instructions_hex=[hex(x) for x in words])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('experiment', type=Path)
    p.add_argument('oracle_fixtures', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--systemc', action='store_true')
    p.add_argument('--native-reference', type=Path)
    a = p.parse_args()
    need(a.systemc == bool(a.native_reference), 'SystemC replay requires independent native reference')
    need(sha(a.oracle_fixtures) == ORACLE_SHA, 'unfrozen native oracle fixtures')
    images = audit_images(a.experiment/'images')
    fixtures = []
    for line in a.oracle_fixtures.read_text().splitlines():
        fields = list(map(int, line.split()))
        if fields[:3] == [0, 1, 1]:
            need(len(fields) == 5, 'scalar oracle row')
            fixtures.append((fields[4], fields[3]))
    need(len(fixtures) == 11 and len(set(x for x, _ in fixtures)) == 11, 'eleven independent Exp inputs')
    a.output.mkdir(exist_ok=False)
    rejected = []
    for label, image_name, offset in (('header-bounds', 'mother', 12),
                                       ('opcode', 'mother', 135),
                                       ('padding', 'local0', 248),
                                       ('native-source', 'local0', 388)):
        directory = a.output/'negative-images'/label
        shutil.copytree(a.experiment/'images', directory)
        path = directory/(image_name+'.mem')
        raw = bytearray(b''.join(int(x, 16).to_bytes(16, 'little')
                                 for x in path.read_text().splitlines()))
        raw[offset] ^= 1
        path.write_text(''.join('%032x\n' % int.from_bytes(raw[i:i+16], 'little')
                                for i in range(0, len(raw), 16)))
        try:
            audit_images(directory)
        except ValueError as exc:
            rejected.append(dict(mutation=label, byte_offset=offset, reason=str(exc)))
        else:
            raise ValueError('corrupted image was accepted: '+label)
    results = []
    for kind in ('rtl', 'gate'):
        binary = a.experiment/kind/'obj/Vtb_native_pair'
        for x, expected in fixtures:
            for stall in (0, 1):
                for init, seed in ((1, 143), (2, 143), (2, 144)):
                    logfile = a.output/('%s-x%d-stall%d-init%d-seed%d.log' % (kind, x, stall, init, seed))
                    command = [str(binary)]
                    for name, count_name in (('mother', 'MWORDS'), ('local0', 'WORDS0'), ('local1', 'WORDS1')):
                        command += ['+'+name.upper()+'='+str(a.experiment/'images'/(name+'.mem')),
                                    '+'+count_name+'='+str(images[name]['bytes']//16)]
                    command += ['+STALL='+str(stall), '+FAULT=0', '+RESET_TRIAL=0',
                                '+EXP_INPUT='+str(x), '+EXP_EXPECTED='+str(expected),
                                '+verilator+rand+reset+'+str(init), '+verilator+seed+'+str(seed)]
                    with logfile.open('wb') as out:
                        run = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT)
                    text = logfile.read_text()
                    match = re.findall(r'PASS N_EXP_LC x=(-?\d+) expected=(\d+) elapsed_ps=(\d+)', text)
                    need(run.returncode == 0 and len(match) == 1 and
                         tuple(map(int, match[0][:2])) == (x, expected), 'native failure: '+str(logfile))
                    if a.systemc:
                        need(text.count('PASS actual_SystemC_kernel version=SystemC 3.0.1') == 1,
                             'missing actual SystemC completion: '+str(logfile))
                    results.append(dict(kind=kind, x=x, expected=expected, stall=stall, init=init, seed=seed,
                                        elapsed_ps=int(match[0][2]), log_sha256=sha(logfile)))
    by_case = {}
    for row in results:
        key = (row['x'], row['stall'])
        by_case.setdefault(key, set()).add(row['elapsed_ps'])
    need(all(len(values) == 1 for values in by_case.values()), 'RTL/gate/init timing disagreement')
    if a.systemc:
        reference = json.loads(a.native_reference.read_text())
        need(reference['images'] == images, 'SystemC/native image identity mismatch')
        def timing_rows(rows):
            return {(r['kind'], r['x'], r['stall'], r['init'], r['seed']):
                    (r['expected'], r['elapsed_ps']) for r in rows}
        need(len(reference['results']) == len(results) and
             timing_rows(reference['results']) == timing_rows(results), 'SystemC/native timing mismatch')
    report = dict(images=images, oracle_sha256=ORACLE_SHA, executions=len(results),
                  rejected_images=rejected,
                  actual_SystemC_kernel=a.systemc,
                  native_reference_sha256=sha(a.native_reference) if a.native_reference else None,
                  kinds=dict(Counter(r['kind'] for r in results)), results=results,
                  timing_boundary='Testbench runtime includes control and PM fixture; not a reusable Exp latency',
                  exclusions=['physical PM', 'delay/glitch/STA', 'whole-model SystemC', 'full energy', 'FPGA acceptance'])
    (a.output/'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS', len(results), 'native LC executions; independent compact-byte audit')


if __name__ == '__main__':
    main()
