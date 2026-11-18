"""Audit the actual clock aliases and storage groups in the six C639 samples."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


ROOT = 'TOP/test_native_decode638_product_replay'
LOCAL_PM = re.compile(re.escape(ROOT) + r'/controller/cohort/local_target\[([0-3])\]/local_controller/pm$')
MEMORY = re.compile(r'(.+)/banks\[([0-3])\]/memory$')


def read_table(path, pm_audit):
    clocks = {}
    with path.open() as stream:
        tag, first, last, scale = next(stream).split()
        if tag != 'time' or scale != '-12' or int(last) - int(first) != 81_920_000:
            raise ValueError('unexpected C639 window extent')
        for line in stream:
            fields = line.rstrip('\r\n').split('\t')
            if fields[0] != 'var' or fields[2] not in ('clk', 'clk_i', 'clk0') or fields[3] != '1':
                continue
            _, scope, pin, _, vcd_id = fields[:5]
            clocks[scope, pin] = vcd_id
    root_clock = clocks[ROOT, 'clk']
    local = {scope: vcd_id for (scope, pin), vcd_id in clocks.items() if pin == 'clk' and LOCAL_PM.fullmatch(scope)}
    gclk = clocks[ROOT + '/feed_forward/dut/G', 'clk']
    switchclk = clocks[ROOT + '/controller/cohort/transport', 'clk']
    groups = defaultdict(dict)
    for (scope, pin), clock in clocks.items():
        bank = MEMORY.fullmatch(scope)
        if pin == 'clk0' and bank:
            groups[bank[1]][bank[2]] = clock
    if len(local) != 4 or any(r['rising_edges'] != 8192 for r in pm_audit.values()):
        raise ValueError('incomplete PM site/clock observation')
    if len(groups) != 5 or any(set(bank) != set('0123') for bank in groups.values()):
        raise ValueError('expected four data storage and one mother PM group')
    if set(local.values()) | {gclk, switchclk} | {i for group in groups.values() for i in group.values()} != {root_clock}:
        raise ValueError('an observed clock is not the shared root net')
    return {'root_clock_alias': root_clock, 'rising_edges': 8192, 'local_pm': local,
            'g32': gclk, 'cohort_transport': switchclk, 's128_groups': dict(groups),
            'trace_metadata_sha256': sha256(path.read_bytes()).hexdigest()}


def main(replay, audit_path, output):
    audit_data = audit_path.read_bytes()
    audit = json.loads(audit_data)['windows']
    windows = {}
    for mode in (0, 1):
        for phase in ('gate-up', 'down', 'writer-active'):
            name = 'mode-{}-{}'.format(mode, phase)
            path = replay / 'DDR-{}'.format(mode) / ('ffn-' + phase + '-signals.tsv')
            windows[name] = read_table(path, audit[name])
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'scope': 'Native C639 representative RTL, six windows; sample evidence for disjoint leaves',
                   'pm_audit_sha256': sha256(audit_data).hexdigest(), 'windows': windows}, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main(*map(Path, sys.argv[1:]))
