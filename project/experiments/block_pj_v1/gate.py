"""Independent physical, full hierarchy STA, GDS and final netlist checks."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

repo, leaves, physical, root = (Path(p) for p in sys.argv[1:5])
which, gate = sys.argv[5:7]
top = f'block_{which.lower()}16'
out = root / f'{which}-{gate}'
out.mkdir()
parent = physical / which
final = parent / 'flow/results/nangate45' / top / 'base'
legacy = repo / 'project/experiments/block_v1'
sys.path.insert(0, str(legacy))
from native_drc import summarize
from native_annotation import inspect as inspect_annotation

platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
liberty = platform / 'lib/NangateOpenCellLibrary_typical.lib'
bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank')
bank_lib, = bank.glob('*TT_1p1V_25C.lib')
tech, = (platform / 'lef').glob('*.tech.lef')
cells, = (platform / 'lef').glob('*.macro.mod.lef')
compiler = Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
leaf_instances = dict(p4='store', M='multiply', G='gate') if which == 'P' else dict(n4='store', T='lease', E='arithmetic')
used = set()
receipt = dict(passed=False, block=top, gate=gate, commands=[])


def sha(path):
    with path.open('rb') as source:
        value = hashlib.sha256()
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
            value.update(chunk)
        return value.hexdigest()


def path(value):
    value = Path(value)
    assert value.is_file(), value
    used.add(value)
    return value


def leaf(name, ext):
    return path(leaves / 'inputs' / name / f'6_final.{ext}')


def result(ext):
    return path(final / f'6_final.{ext}')


def run(args, log):
    cmd = list(map(str, args))
    with (out / log).open('w') as stream:
        code = subprocess.run(cmd, cwd=out, stdout=stream, stderr=subprocess.STDOUT).returncode
    receipt['commands'].append(dict(command=cmd, log=log, exit_code=code, sha256=sha(out / log)))
    assert code == 0, (code, log)


def tcl(name, script):
    file = out / (name + '.tcl')
    file.write_text(script)
    run(['openroad', '-no_init', '-threads', '12', '-exit', file], name + '.log')


def odb_netlists():
    # Match the extracted RC with the real signal-bearing cells, including the
    # input-only antenna protection removed from ORFS's logical netlist.
    sources = {n: leaf(n, 'odb') for n in leaf_instances}
    sources['parent'] = result('odb')
    outputs = {}
    for name, odb in sources.items():
        v = out / f'{name}-odb.v'
        script = f'read_db {{{odb}}}\n'
        script += '''set remove {}
foreach lib [[ord::get_db] getLibs] {
    foreach master [$lib getMasters] {
        set has_signal 0
        foreach term [$master getMTerms] {
            if {[$term getSigType] ni {POWER GROUND}} {set has_signal 1}
        }
        if {!$has_signal} {lappend remove [$master getName]}
    }
}
'''
        script += f'write_verilog -remove_cells $remove {{{v}}}\n'
        if name == 'parent':
            script += '''set block [ord::get_db_block]
set f [open unused-boundaries.tsv w]
foreach term [$block getBTerms] {
    if {[$term getIoType] ne "INPUT"} {continue}
    set net [$term getNet]
    if {$net eq "NULL" || (![llength [$net getITerms]] && [llength [$net getBTerms]] == 1)} {
        puts $f "parent-input\t[$term getName]"
    }
}
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getType] ne "BLOCK"} {continue}
    foreach term [$inst getITerms] {
        set pin [$term getMTerm]
        if {[$pin getIoType] eq "OUTPUT" && [$term getNet] eq "NULL"} {
            puts $f "leaf-output\t[$inst getName]/[$pin getName]"
        }
    }
}
close $f
'''
        tcl(f'{name}-readback', script)
        outputs[name] = path(v)
    return outputs


def timing():
    netlists = odb_netlists()
    script = ''.join(f'read_lef {{{path(p)}}}\n' for p in (tech, cells))
    # Only the genuine SRAM bank is an opaque timing cell in expanded STA.
    bank_lef, = bank.glob('*.lef')
    script += f'read_lef {{{path(bank_lef)}}}\n'
    script += ''.join(f'read_liberty {{{path(p)}}}\n' for p in (liberty, bank_lib))
    script += ''.join(f'read_verilog {{{v}}}\n' for v in netlists.values())
    script += f'link_design -hier {top}\n'
    script += f'read_sdc {{{path(parent / "input.sdc")}}}\nread_spef {{{result("spef")}}}\n'
    script += ''.join(f'read_spef -path {inst} {{{leaf(n, "spef")}}}\n' for n, inst in leaf_instances.items())
    script += '''set_propagated_clock [all_clocks]
report_parasitic_annotation -report_unannotated > annotation.rpt
@ANNOTATION@
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -digits 6
report_checks -path_delay max -group_path_count 15 -digits 6 -format full_clock_expanded
report_checks -path_delay min -group_path_count 15 -digits 6 -format full_clock_expanded
report_check_types -max_capacitance -max_count 20 -digits 6
report_check_types -max_slew -max_count 20 -digits 6
report_check_types -violators -max_slew -max_capacitance -max_fanout -max_delay -min_delay -recovery -removal -min_period -min_pulse_width -digits 6 > electrical-violations.rpt
check_setup -verbose > check-setup.rpt
'''
    script = script.replace('@ANNOTATION@', f'source {{{path(legacy / "native_annotation.tcl")}}}')
    tcl('hierarchy-sta', script)
    receipt['annotation'] = inspect_annotation(out)
    log = (out / 'hierarchy-sta.log').read_text()
    unused = {'parent-input': set(), 'leaf-output': set()}
    for line in (out / 'unused-boundaries.tsv').read_text().splitlines():
        kind, name = line.split('\t')
        unused[kind].add(name)
    rc_proof = receipt['annotation']
    covered = set(rc_proof['connected_or_unresolved']) & unused['parent-input']
    receipt['unannotated_unused_top_inputs_proven_by_odb'] = sorted(covered)
    rc_complete = (rc_proof['checks']['all_native_drivers_resolved'] and not rc_proof['partial_drivers']
                   and set(rc_proof['connected_or_unresolved']) == covered)
    unexpected = []
    for line in log.splitlines():
        if not re.search(r'(?i)(not found|not annotated|not connected to net|black box|not linked|syntax error)', line):
            continue
        disconnected = re.search(r'^\[WARNING STA-1655\].*?, (\S+) not connected to net (\S+)\.$', line)
        if not disconnected or disconnected[2] not in unused['leaf-output'] or disconnected[2].split('/')[-1] != disconnected[1]:
            unexpected.append(line)
    receipt['unexpected_link_diagnostics'] = unexpected
    for sense in ('max', 'min'):
        match = re.search(r'worst slack ' + sense + r'\s+([-+\d.]+)', log)
        assert match, sense
        receipt[f'{sense}_slack_ns'] = float(match[1])
    abstract = ''.join(f'read_liberty {{{path(p)}}}\n' for p in (liberty,))
    abstract += ''.join(f'read_liberty {{{path(leaves / "views" / n / "leaf.lib")}}}\n' for n in leaf_instances)
    abstract += f'read_db {{{result("odb")}}}\nread_sdc {{{path(parent / "input.sdc")}}}\nread_spef {{{result("spef")}}}\n'
    abstract += 'set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
    abstract += f'write_abstract_lef -bloat_factor 0 {top}.lef\nwrite_timing_model {top}.lib\n'
    tcl('export', abstract)
    electrical = (out / 'electrical-violations.rpt').read_text().strip()
    no_paths = re.fullmatch(r'Group\s+Slack\s+[-]+\s+No paths found\.', electrical)
    receipt['checks'] = {
        'setup': receipt['max_slack_ns'] >= 0,
        'hold': receipt['min_slack_ns'] >= 0,
        'electrical': not electrical or no_paths is not None,
        'constrained': not (out / 'check-setup.rpt').read_text().strip(),
        'rc_coverage': rc_complete,
        'linked': not unexpected,
    }


def geometry():
    script = f'set ::env(BV1_ODB) {{{result("odb")}}}\n'
    script += f'source {{{path(legacy / "native_physical.tcl")}}}\n'
    script += f'set ::env(BV1_UNDRIVEN_REPORT) drivers.tsv\nsource {{{path(legacy / "native_undriven.tcl")}}}\n'
    script += '''set block [ord::get_db_block]
set f [open connectivity.tsv w]
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} {continue}
    set drivers 0
    set loads 0
    foreach term [$net getITerms] {
        set direction [[$term getMTerm] getIoType]
        if {$direction eq "OUTPUT"} {incr drivers}
        if {$direction in {INPUT INOUT}} {incr loads}
    }
    foreach term [$net getBTerms] {
        if {[$term getIoType] eq "INPUT"} {incr drivers}
        if {[$term getIoType] in {OUTPUT INOUT}} {incr loads}
    }
    if {$loads && ($drivers != 1 || [$net getWire] eq "NULL")} {
        puts $f "[$net getName]\t$drivers\t$loads\t[$net getWire]"
    }
}
close $f
set f [open hard-leaves.tsv w]
foreach i [$block getInsts] {
    if {[[$i getMaster] getType] eq "BLOCK"} {puts $f "[$i getName]\t[[$i getMaster] getName]"}
}
close $f
write_def native-before.def
drt::check_drc_cmd native-drc.rpt 0 0 0 0 native_whole_drc
write_def native-after.def
'''
    tcl('physical', script)
    summary = dict((line.split('\t', 1) for line in (out / 'physical-summary.tsv').read_text().splitlines()))
    got = dict((line.split('\t') for line in (out / 'hard-leaves.tsv').read_text().splitlines()))
    expected = {i: json.loads(path(leaves / 'views' / n / 'receipt.json').read_text())['master'] for n, i in leaf_instances.items()}
    rows = [line.split('\t') for line in (out / 'physical-pins.tsv').read_text().splitlines()]
    pins = {name: (layer, tuple(map(int, bbox))) for name, layer, *bbox in rows}
    landing = all(layer == 'metal10' and x1-x0 == y1-y0 == 4000 and
                  ((x0+x1)//2 - 190) % 8000 == ((y0+y1)//2 - 140) % 8000 == 0
                  for layer, (x0, y0, x1, y1) in pins.values())
    receipt['checks'] = {
        'same_route_db': sha(out / 'native-before.def') == sha(out / 'native-after.def'),
        'native_drc': not (out / 'native-drc.rpt').read_text().strip(),
        'placed': summary['unplaced'] == '0',
        'pg': summary['pg_VDD'] == summary['pg_VSS'] == '1' and summary['incorrect_pg_iterms'] == '0',
        'hard_leaves': got == expected,
        'ports': landing and len(pins) == len(rows) > 0,
        'connectivity': not (out / 'connectivity.tsv').read_text().strip() and summary['open_signal_inputs'] == '0',
    }


def drc():
    if not (final / '6_final.gds').is_file():
        command = ['make', '-C', str(platform.parents[1]), f'DESIGN_CONFIG={path(parent / "config.mk")}',
                   f'WORK_HOME={parent / "flow"}', 'NUM_CORES=12',
                   'MIN_ROUTING_LAYER=metal1', 'MAX_ROUTING_LAYER=metal10', 'do-gds']
        run(command, 'stream.log')
    deck = path(platform / 'drc/FreePDK45.lydrc')
    report = out / 'full-deck.lyrdb'
    run(['klayout', '-b', '-rd', f'in_gds={result("gds")}', '-rd', f'report_file={report}', '-r', deck], 'klayout.log')
    summary = summarize(report)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    receipt['checks'] = {'full_deck': summary['total_items'] == 0}


def function():
    netlists = odb_netlists()
    library = out / 'cells.ys'
    library.write_text(f'read_liberty -ignore_miss_func -ignore_miss_dir {path(liberty)}\nwrite_verilog -noattr cells.v\n')
    run(['yosys', '-s', library], 'cells.log')
    bench = repo / 'project/experiments/block_pj_v1'
    command = [path(compiler), '--binary', '--timing', '-j', '12', '--threads', '4',
               '--x-initial', 'unique', '--x-assign', 'unique',
               '--output-split', '12000', '--output-split-cfuncs', '150', '--output-groups', '0',
               '-CFLAGS', '-O1', '-Wno-fatal', '--top-module', 'tb_pj', '--Mdir', out / 'obj']
    if which == 'P':
        command.append('-DTEST_P')
    command += [path(bench / 'tb_pj.sv'), path(bench / 'sram_model.sv'), out / 'cells.v', *netlists.values()]
    run(command, 'build.log')
    receipt['checks'] = {}
    for mode in range(3):
        log = f'init-{mode}.log'
        run([out / 'obj/Vtb_pj', f'+verilator+rand+reset+{mode}', f'+verilator+seed+{187+mode}'], log)
        receipt['checks'][f'init_{mode}'] = f'PASS {which}16 ' in (out / log).read_text()


try:
    {'electrical': timing, 'physical': geometry, 'drc': drc, 'function': function}[gate]()
    receipt['passed'] = all(receipt['checks'].values())
finally:
    receipt['inputs'] = {str(f): sha(f) for f in sorted(used)}
    receipt['evidence'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert receipt['passed'], receipt['checks']
