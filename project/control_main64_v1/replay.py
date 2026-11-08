"""Replay main's 64-bit native fixtures using its actual mother+PM RTL.

This is a testbench binding, not a unified production boot top. The main P/U
controller and service generation are preserved without the PR180 LC overlay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from check import ROOT, check, frozen_control, sha

KINDS = ('P', 'U', 'C', 'F', 'J', 'C-roundtrip', 'CF-duplex', 'U-duplex', 'U-fma-duplex')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--kind', choices=KINDS + ('mother',), required=True)
    args = parser.parse_args()
    check()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    frozen = frozen_control(out / 'control-frozen')
    env = dict(os.environ, PU_INSTRUCTION_BITS='64', CFJ_CONTROL64_SOURCE=str(frozen))

    def run(command, log):
        with (out / log).open('w') as stream:
            subprocess.run(list(map(str, command)), env=env, stdout=stream,
                           stderr=subprocess.STDOUT, check=True)

    if args.kind == 'mother':
        run([sys.executable, '-B', ROOT / 'project/experiments/mother_control_v1/regression.py',
             '--out', out / 'mother', '--upstream', frozen, '--instruction-bits', '64'], 'mother.log')
        print('PASS main64 mother', flush=True)
        return
    bundle = out / 'bundle'
    if args.kind in ('P', 'U', 'U-duplex', 'U-fma-duplex'):
        if args.kind.startswith('U-'):
            env['PU_U_NATIVE_REPLAY'] = args.kind[2:]
        run([sys.executable, '-B', ROOT / 'project/experiments/pu_leaf_base/control_replay.py',
             ROOT, bundle, 'P' if args.kind == 'P' else 'U'], 'stage.log')
    else:
        archive = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02/bundle.tar.gz')
        run([sys.executable, '-B', ROOT / 'project/experiments/cfj_leaf_base/stage_regression.py',
             archive, bundle, 'controller64'], 'stage.log')
        if args.kind == 'CF-duplex':
            run([sys.executable, '-B', ROOT / 'project/experiments/cfj_leaf_base/stage_duplex.py', bundle], 'duplex-stage.log')
    design = bundle / 'design'
    ctrl = bundle / 'staged/project/control_rtl_min_v0_1'
    native = bundle / 'staged/native'
    pj = bundle / 'staged/pj/project/rtl'
    rtl = ROOT / 'project/rtl/mother_control_v1'
    # Match the same public port contract as main's consistency.py. Replace
    # the fixture MC and its PM together: the main mother already owns a PM.
    declaration = (rtl / 'mother_control_64.sv').read_text().split(');', 1)[0]
    ports = re.findall(r'(input|output) wire (\[[^\]]+\])?\s*(\w+)', declaration)
    wires = (ctrl / 'tb_network_mc_wires.svh').read_text().split('mc_min_controller #', 1)[0]
    for _, width, name in ports:
        found = re.findall(r'\b(?:reg|wire)\s*(\[[^\]]+\])?\s*' + name + r'\s*;', wires)
        assert found == [width] or (name == 'rst_ni' and found == ['', '']), (name, width, found)
    wires += 'mother_control_64 dut(\n' + ',\n'.join('.' + n + '(' + n + ')' for _, _, n in ports) + '\n);\n'
    (ctrl / 'tb_network_mc_wires.svh').write_text(wires)
    pair = design / 'tb_native_pair.sv'
    text = pair.read_text()
    start = text.index('    network_pm #')
    end = text.index(';', start) + 1
    assert 'fault_xor_i' in text[start:end]
    pair.write_text(text[:start] + '    // Mother PM is inside mother_control_64.\n' + text[end:])
    sources = [ctrl / 'lc_min_controller.sv', ctrl / 'tb_network_pm.sv']
    if (ctrl / 'two_local_link.sv').exists():
        sources.append(ctrl / 'two_local_link.sv')
    sources += sorted(design.glob('*.sv')) + sorted(native.glob('*.sv'))
    sources += sorted((pj / 'block_pj_v1').glob('*.sv'))
    sources += [pj / 'block_v2/block_v2_m.sv', pj / 'block_v1/transaction6k.sv']
    sources += [rtl / n for n in ('mc_min_controller.sv', 'control_pm.sv', 'mother_control_64.sv')]
    sources += [ROOT / 'project/rtl/s_sram/block_feed_s16k_sram.sv']
    # The native fixture already stages the same SRAM wrapper; compile once.
    sources = [p for p in sources if p != native / 'block_feed_s16k_sram.sv']
    bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    assert sha(bank) == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    sources.append(bank)
    kind = {'P':3, 'U':-1, 'C':2, 'F':1, 'J':4,
            'C-roundtrip':-1, 'CF-duplex':-1, 'U-duplex':-1, 'U-fma-duplex':-1}[args.kind]
    cmd = ['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator', '--binary',
           '--timing', '--assert', '--timescale-override', '1ns/1ps', '--x-initial', 'unique',
           '--x-assign', 'unique', '-Wno-fatal', '--top-module', 'tb_native_pair', '-GSINGLE_KIND=' + str(kind),
           '-j', os.environ.get('SLURM_CPUS_PER_TASK', '4'), '--Mdir', str(out / 'obj'),
           '-I' + str(ctrl), '-I' + str(native), '-I' + str(design), '-I' + str(rtl),
           str(native / 'native_r.vlt'), *map(str, sources)]
    run(cmd, 'compile.log')
    cases = [('normal', 0, 0, 0)]
    if args.kind in ('U', 'C-roundtrip'):
        cases += [('stalled', 1, 0, 0), ('fault', 0, 1, 0), ('stalled-fault', 1, 1, 0), ('reset', 1, 0, 1)]
    if args.kind in ('CF-duplex', 'U-duplex', 'U-fma-duplex'):
        cases += [('stalled', 1, 0, 0), ('reset', 1, 0, 1)]
    results = []
    for name, stall, fault, reset in cases:
        image = out / name
        command = [sys.executable, '-B', design / 'images.py', bundle / 'staged', image, '--kind', kind]
        if fault:
            command += ['--fault']
        words = subprocess.check_output(list(map(str, command)), env=env, text=True).splitlines()
        assert len(words) == 3
        images = {}
        for filename in ('mother.mem', 'local0.mem', 'local1.mem'):
            path = image / filename
            assert (int(path.read_text().splitlines()[0], 16) >> 64) & 65535 == 2
            images[filename] = sha(path)
        for mode, seed in ((1,143), (2,143), (2,144)):
            log = f'{name}-{mode}-{seed}.log'
            run([out / 'obj/Vtb_native_pair', '+MOTHER=' + str(image / 'mother.mem'), '+MWORDS=' + words[0],
                 '+LOCAL0=' + str(image / 'local0.mem'), '+WORDS0=' + words[1],
                 '+LOCAL1=' + str(image / 'local1.mem'), '+WORDS1=' + words[2], '+STALL=' + str(stall),
                 '+FAULT=' + str(fault), '+RESET_TRIAL=' + str(reset), '+verilator+rand+reset+' + str(mode),
                 '+verilator+seed+' + str(seed)], log)
            assert 'PASS native' in (out / log).read_text()
            results.append(dict(case=name, reset_mode=mode, seed=seed, image_sha256=images, log_sha256=sha(out / log)))
            print('PASS main64', args.kind, log, flush=True)
    def label(path):
        if path.is_relative_to(bundle):
            return 'fixture/' + path.relative_to(bundle).as_posix()
        if path.is_relative_to(ROOT):
            return path.relative_to(ROOT).as_posix()
        return 'qualified-sram-bank.v'
    report = dict(schema='main64-import-replay/1', kind=args.kind, passed=True, instruction_bits=64,
                  mother='main RTL with actual 16KiB program SRAM', local_program_memory='behavioral fixture',
                  actual_local_controller_rtl=True, actual_block_rtl=True, actual_private_s_sram=True,
                  unified_boot_manager=False, full_isa=False, physical_signoff=False, results=results,
                  source_sha256={label(p):sha(p) for p in sources})
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
