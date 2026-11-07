"""Bind the qualified physical mother to existing native Block/LC RTL fixtures.

Does not replace P/U local controllers with newer upstream cores. Local program
memories in the reused fixtures are behavioral; Block private S is actual SRAM.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--kind', choices=['P', 'U', 'C', 'F', 'J', 'CF-duplex'], required=True)
    p.add_argument('--native-audit', type=Path, required=True)
    p.add_argument('--gate-receipt', type=Path, required=True)
    p.add_argument('--cells', type=Path, required=True)
    p.add_argument('--cfj-upstream', type=Path, required=True)
    p.add_argument('--pu-source', type=Path)
    a = p.parse_args()
    audit = json.loads(a.native_audit.read_text())
    gate = json.loads(a.gate_receipt.read_text())
    assert audit['passed'] and audit['full_gds_drc_performed'] and gate['passed']
    assert audit['final_sha256']['v'] == gate['final_netlist_sha256']
    final = Path(audit['candidate']) / 'flow/results/nangate45/mother_control_64/base/6_final.v'
    assert sha(final) == audit['final_sha256']['v']
    assert sha(a.cells) == gate['cells_sha256']
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    bundle = out / 'bundle'
    prior = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02')
    env = dict(os.environ, CFJ_CONTROL64_SOURCE=str(a.cfj_upstream.resolve()), PU_INSTRUCTION_BITS='64')
    def run(command, log, cwd=out):
        with (out / log).open('w') as stream:
            subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                           stdout=stream, stderr=subprocess.STDOUT, check=True)
    if a.kind in ('P', 'U'):
        pu = (a.pu_source or ROOT).resolve()
        run([sys.executable, '-B', pu / 'project/experiments/pu_leaf_base/control_replay.py', pu, bundle, a.kind], 'stage.log')
    else:
        run([sys.executable, '-B', ROOT / 'project/experiments/cfj_leaf_base/stage_regression.py', prior / 'bundle.tar.gz', bundle, 'controller64'], 'stage.log')
        if a.kind == 'CF-duplex':
            run([sys.executable, '-B', ROOT / 'project/experiments/cfj_leaf_base/stage_duplex.py', bundle], 'duplex-stage.log')
    design = bundle / 'design'
    ctrl = bundle / 'staged/project/control_rtl_min_v0_1'
    # Public ports must exist at the same widths; never silently tie off a new
    # mother input or silently change the frozen local controller.
    wrapper = (ROOT / 'project/rtl/mother_control_v1/mother_control_64.sv').read_text().split(');', 1)[0]
    ports = re.findall(r'(input|output) wire (\[[^\]]+\])?\s*(\w+)', wrapper)
    wires = (ctrl / 'tb_network_mc_wires.svh').read_text().split('mc_min_controller #', 1)[0]
    for direction, width, name in ports:
        found = re.findall(r'\b(?:reg|wire)\s*(\[[^\]]+\])?\s*' + name + r'\s*;', wires)
        assert found == [width], (name, width, found)
    wires += 'mother_control_64 dut(\n' + ',\n'.join('    .' + name + '(' + name + ')' for _, _, name in ports) + '\n);\n'
    (ctrl / 'tb_network_mc_wires.svh').write_text(wires)
    pair = design / 'tb_native_pair.sv'
    text = pair.read_text()
    start = text.index('    network_pm #')
    end = text.index(';', start) + 1
    assert 'fault_xor_i' in text[start:end]
    pair.write_text(text[:start] + '    // Mother PM is inside the qualified physical netlist.\n' + text[end:])
    shutil.copyfile(final, design / 'mother-final.v')
    shutil.copyfile(a.cells, design / 'mother-cells.sv')
    native = bundle / 'staged/native'
    pj = bundle / 'staged/pj/project/rtl'
    bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    assert sha(bank) == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    kind = dict(P=3, U=-1, C=2, F=1, J=4, **{'CF-duplex': -1})[a.kind]
    # Include the registered two-local link when the compact frontend uses it.
    sources = [ctrl / 'lc_min_controller.sv', ctrl / 'tb_network_pm.sv']
    link = ctrl / 'two_local_link.sv'
    if link.exists():
        sources.append(link)
    sources += sorted(design.glob('*.sv')) + [design / 'mother-final.v'] + sorted(native.glob('*.sv'))
    sources += [bank] + sorted((pj / 'block_pj_v1').glob('*.sv')) + [pj / 'block_v2/block_v2_m.sv', pj / 'block_v1/transaction6k.sv']
    verilator = '/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator'
    cmd = [verilator, '--binary', '--timing', '--assert', '--timescale-override', '1ns/1ps', '--x-initial', 'unique', '--x-assign', 'unique', '-Wno-fatal', '--top-module', 'tb_native_pair', '-GSINGLE_KIND=' + str(kind), '-j', os.environ.get('SLURM_CPUS_PER_TASK', '4'), '--Mdir', str(out / 'obj'), '-I' + str(ctrl), '-I' + str(native), '-I' + str(design), str(native / 'native_r.vlt'), *map(str, sources)]
    run(cmd, 'compile.log')
    cases = [('normal', 0, 0, 0)]
    if a.kind == 'U':
        cases += [('stalled', 1, 0, 0), ('fault', 0, 1, 0), ('stalled-fault', 1, 1, 0), ('reset', 1, 0, 1)]
    if a.kind == 'CF-duplex':
        cases += [('stalled', 1, 0, 0), ('reset', 1, 0, 1)]
    results = []
    for name, stall, fault, reset in cases:
        image_dir = out / name
        args = [sys.executable, '-B', str(design / 'images.py'), str(bundle / 'staged'), str(image_dir), '--kind', str(kind)]
        if fault:
            args.append('--fault')
        words = subprocess.check_output(args, env=env, text=True).splitlines()
        assert len(words) == 3
        for index in range(3):
            image_path = image_dir / ('mother.mem' if index == 0 else 'local' + str(index - 1) + '.mem')
            word0 = int(image_path.read_text().splitlines()[0], 16)
            assert (word0 >> 64) & 65535 == 2
        for reset_mode, seed in [(1, 143), (2, 143), (2, 144)]:
            log = name + '-' + str(reset_mode) + '-' + str(seed) + '.log'
            command = [str(out / 'obj/Vtb_native_pair'), '+MOTHER=' + str(image_dir / 'mother.mem'), '+MWORDS=' + words[0], '+LOCAL0=' + str(image_dir / 'local0.mem'), '+WORDS0=' + words[1], '+LOCAL1=' + str(image_dir / 'local1.mem'), '+WORDS1=' + words[2], '+STALL=' + str(stall), '+FAULT=' + str(fault), '+RESET_TRIAL=' + str(reset), '+verilator+rand+reset+' + str(reset_mode), '+verilator+seed+' + str(seed)]
            run(command, log)
            assert 'PASS native' in (out / log).read_text()
            results.append(dict(case=name, reset_mode=reset_mode, seed=seed, log_sha256=sha(out / log)))
    report = dict(schema='mother-block-consistency/1', passed=True, kind=a.kind, instruction_bits=64,
        physical_mother=True, mother_final_netlist_sha256=sha(final), actual_local_rtl=True,
        actual_block_rtl=True, actual_private_s_sram=True, local_program_memory='behavioral fixture',
        final_block_netlist=False, topology='two resident targets', full_isa=False, results=results,
        source_sha256={str(path.relative_to(bundle)) if path.is_relative_to(bundle) else str(path): sha(path) for path in sources})
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
