"""Check full routed views and power-tool support; NOT energy calibration.

No default-activity power estimate is accepted as workload energy. Abstract
timing libraries are deliberately bypassed; SRAM uses its original bank lib.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    root = Path.cwd()
    base = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign')
    bank = base / 'issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib'
    if sha(bank) != '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189':
        raise ValueError('bank power/timing library drift')
    n_tar = base.parent / 'llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/029/bundle-n/block-v2-n-native.tar.gz'
    if sha(n_tar) != '81077733877a58d0fa80ebc40951fc229b70e94666d04c50a5387a2ae8e7457c':
        raise ValueError('N accepted archive drift')
    n = root / 'n-source'
    n.mkdir(exist_ok=False)
    with tarfile.open(str(n_tar)) as t:
        members = [x for x in t.getmembers() if x.name.startswith('native/')]
        if any('..' in Path(x.name).parts or x.issym() or x.islnk() for x in members):
            raise ValueError('unexpected archive path/link')
        t.extractall(str(n), members=members)
    cases = [
        ('M', base / 'issue-187-p16-j16/005-leaf-views/inputs/M', False),
        ('E', base / 'issue-201-compact-ge/2ba89c0bd/release/e_compact', False),
        ('G', base / 'issue-201-compact-ge/2ba89c0bd/release/g', False),
        ('N', n / 'native', False),
        ('S-base', base / 'issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base', True),
        ('S-P', base / 'issue-200-compact-local-s/run10-delay1/results/4/flow/results/nangate45/local_s_p/base', True)]
    std = '/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'

    def worker(case):
        name, source, has_bank = case
        out = root / name
        out.mkdir(exist_ok=False)
        files = [source / ('6_final.' + suffix) for suffix in ('odb', 'sdc', 'spef', 'v')]
        inputs = {str(p): sha(p) for p in files}
        body = 'read_liberty {%s}\n' % std
        if has_bank:
            body += 'read_liberty {%s}\n' % bank
            inputs[str(bank)] = sha(bank)
        body += 'read_db {%s}\nread_sdc {%s}\nread_spef {%s}\n' % tuple(files[:3])
        body += '''set_propagated_clock [all_clocks]
report_units
help read_vcd
help report_activity_annotation
help report_power
puts "No VCD loaded: all reported power below is UNQUALIFIED default activity."
report_activity_annotation
report_power
puts "POWER_INVENTORY_COMPLETED"
'''
        script = out / 'probe.tcl'
        script.write_text(body)
        command = ['srun', '--exact', '--exclusive', '-N1', '-n1', '-c10', '--cpu-bind=cores',
                   '/public/software/singularity-ce-4.3.4/bin/singularity', 'exec', '--cleanenv',
                   '--bind', '/public/home/yuzelu',
                   '/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif',
                   'bash', '-c', 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -threads 10 -exit "$1"',
                   'power-inventory', str(script)]
        with (out / 'probe.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        text = (out / 'probe.log').read_text()
        receipt = {'name': name, 'inputs': inputs, 'tool_command': command,
                   'returncode': result.returncode,
                   'tool_completed': result.returncode == 0 and 'POWER_INVENTORY_COMPLETED' in text,
                   'vcd_loaded': False, 'workload_energy_qualified': False,
                   'reason': 'power-tool and library support inventory only; activity calibration not performed',
                   'probe_log_sha256': sha(out / 'probe.log')}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(worker, cases))
    (root / 'power-inventory.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'cases': len(results), 'tool_completed': sum(x['tool_completed'] for x in results),
                      'qualified_energy': False}))
    if not all(x['tool_completed'] for x in results):
        raise RuntimeError('inspect individual tool logs')


if __name__ == '__main__':
    main()
