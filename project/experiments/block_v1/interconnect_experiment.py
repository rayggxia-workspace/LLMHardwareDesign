"""Finite real-producer/consumer link experiment; no production macro edits."""
import json
import math
from pathlib import Path
import re
import ast

from interconnect_spef import (audit_native, header, link_spef, paired_links,
                              prepare, sha, wrapper)

PLATFORM = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
LIBRARY = PLATFORM / 'lib/NangateOpenCellLibrary_typical.lib'
TOOLS = Path(__file__).parent


def restore_physical(native, destination):
    """Restore exact accepted ODB antenna devices omitted by final write_verilog."""
    from native_passive_endpoint import qualify
    qualified = qualify(LIBRARY.read_text())
    result = {}
    for side, row in native.items():
        source = Path(row['verilog'])
        original = source.read_bytes()
        assert sha(source) == row['hashes']['6_final.v']
        receipt_path = Path(row['physical_receipt_path'])
        assert sha(receipt_path) == row['physical_receipt_sha256']
        receipt = json.loads(receipt_path.read_text())
        assert receipt['passed']
        inventory = receipt_path.parent / 'passive-inventory.tsv'
        assert sha(inventory) == receipt['outputs'][inventory.name]
        devices = []
        identities = set()
        for line in inventory.read_text().splitlines():
            name, master, typ, direction, net = line.split('\t')
            instance, pin = name.rsplit('/', 1)
            assert (master,typ,direction,pin) == ('ANTENNA_X1','CORE_ANTENNACELL','INPUT','A')
            assert instance not in identities
            identities.add(instance)
            assert re.fullmatch(r'[A-Za-z_]\w*(?:\[\d+\])?', net)
            devices.append('ANTENNA_X1 \\' + instance + ' (.A(' + net + '));\n')
        assert devices and b'ANTENNA_X1' not in original
        assert original.count(b'endmodule') == 1
        before, after = original.split(b'endmodule')
        extra = ''.join(devices).encode()
        target = destination / (side + '-with-physical.v')
        target.write_bytes(before + extra + b'endmodule' + after)
        # Exact inverse, including bytes/whitespace, not only a cell count.
        assert target.read_bytes().replace(extra, b'', 1) == original
        assert sha(source) == row['hashes']['6_final.v']
        result[side] = dict(path=str(target), sha256=sha(target),
                            original_verilog_sha256=row['hashes']['6_final.v'],
                            physical_receipt_sha256=sha(receipt_path),
                            inventory_sha256=sha(inventory), original_antenna_devices=len(devices),
                            passive_library=qualified)
    return result


def reuse_graphs(root, out, pair, old_run):
    """Reuse already passed native RC preparation, never failed macro STA."""
    import shutil
    old = out.parents[2] / old_run / 'tasks' / ('interconnect-prepare-' + pair)
    receipt = json.loads((old/'receipt.json').read_text())
    assert receipt['passed']
    for filename in ('prepared.json','interconnect-prepare.json'):
        assert sha(old/filename) == receipt['outputs'][filename]
    old_code = old.parents[1] / 'src/project/experiments/block_v1/interconnect_spef.py'
    assert sha(old_code) == receipt['inputs']['project/experiments/block_v1/interconnect_spef.py']
    def functions(path):
        return {n.name: ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body
                if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    previous,current=functions(old_code),functions(TOOLS/'interconnect_spef.py')
    for name in ('sha','plain','Records','blocks','inventory','selection','node','transform','header',
                 'write_net','prepare','canonical_maps'):
        assert previous[name] == current[name], ('Native graph implementation changed',name)
    meta=json.loads((old/'prepared.json').read_text())
    meta['common_paths']={}
    for topology in ('direct','endpoints','relay'):
        name='common-'+topology+'.spef';p=old/name
        assert sha(p) == receipt['outputs'][name] == meta['common_sha256'][topology]
        meta['common_paths'][topology]=str(p)
    meta['reused_preparation']=dict(path=str(old),receipt_sha256=sha(old/'receipt.json'),
                                    policy='Passed original native RC only; failed/cancelled candidate STA is never reused')
    return meta


def fixture(folder, vector=False):
    folder.mkdir(exist_ok=True)
    native = {}
    for side in ('left', 'right'):
        v = folder / (side + '.v')
        v.write_text(f'module fixture_{side}(input clk,d,output q); '
                     'DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n')
        spef = folder / (side + '.spef')
        text = header({1: 'clk', 2: 'd', 3: 'q', 4: 'ff'})
        for number, port, pin, direction in [(1, 'clk', 'CK', 'I'), (2, 'd', 'D', 'I'), (3, 'q', 'Q', 'O')]:
            text += (f'*D_NET *{number} 0.010\n*CONN\n*P {port} {direction}\n'
                     f'*I *4:{pin} {direction}\n*CAP\n1 {port} 0.004\n'
                     f'2 *4:{pin} 0.006\n*RES\n1 {port} *4:{pin} 2.5\n*END\n\n')
        spef.write_text(text)
        native[side] = dict(top='fixture_' + side, verilog=str(v), spef=str(spef))
    links = [dict(id='f000', source=['left', 'q'], sink=['right', 'd'], role='data', bit=0)]
    if vector:
        for side in ('left','right'):
            v=Path(native[side]['verilog'])
            v.write_text(f'module fixture_{side}(input clk,input [1:0] d,output [1:0] q); '
                         'DFF_X1 ff0(.CK(clk),.D(d[0]),.Q(q[0])); '
                         'DFF_X1 ff1(.CK(clk),.D(d[1]),.Q(q[1])); '
                         'ANTENNA_X1 protect(.A(d[0])); endmodule\n')
            names={1:'clk',2:'d[0]',3:'q[0]',4:'ff0',5:'d[1]',6:'q[1]',7:'ff1',8:'protect'}
            text=header(names)
            text+='*D_NET *1 0.01\n*CONN\n*P clk I\n*I *4:CK I\n*I *7:CK I\n*CAP\n1 clk 0.004\n2 *4:CK 0.003\n3 *7:CK 0.003\n*RES\n1 clk *4:CK 2.5\n2 clk *7:CK 2.5\n*END\n\n'
            for bit,di,qi,ff in [(0,2,3,4),(1,5,6,7)]:
                for number,port,pin,direction in [(di,f'd[{bit}]','D','I'),(qi,f'q[{bit}]','Q','O')]:
                    protect=port=='d[0]'
                    text+=f'*D_NET *{number} '+('0.011'if protect else'0.010')+'\n*CONN\n'
                    text+=f'*P {port} {direction}\n*I *{ff}:{pin} {direction}\n'
                    if protect:text+='*I *8:A I *D ANTENNA_X1\n'
                    text+=f'*CAP\n1 {port} 0.004\n2 *{ff}:{pin} 0.006\n'
                    if protect:text+='3 *8:A 0.001\n'
                    text+=f'*RES\n1 {port} *{ff}:{pin} 2.5\n'
                    if protect:text+=f'2 {port} *8:A 1.\n'
                    text+='*END\n\n'
            Path(native[side]['spef']).write_text(text)
        links=[dict(id=f'f{i:03}',source=['left',f'q[{i}]'],sink=['right',f'd[{i}]'],role='data',bit=i)for i in range(2)]
    return native, links


def tcl_list(values):
    assert all('{' not in str(v) and '}' not in str(v) for v in values)
    return '[list ' + ' '.join('{' + str(v) + '}' for v in values) + ']'


def sta_script(native, common, case_dir, observations):
    text = f'set_thread_count 16\nread_liberty {{{LIBRARY}}}\n'
    for name in ('NangateOpenCellLibrary.tech.lef', 'NangateOpenCellLibrary.macro.mod.lef'):
        text += 'read_lef {' + str(PLATFORM / 'lef' / name) + '}\n'
    for row in native.values():
        text += 'read_verilog {' + row['verilog'] + '}\n'
    text += 'read_verilog {' + str(case_dir / 'wrapper.v') + '}\nlink_design interconnect_fixture\n'
    text += '''set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um
set_units -time ns -capacitance fF -resistance kOhm -distance um
create_clock -name core -period 3.333333333333333 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks core]
set_clock_transition 0.05 [get_clocks core]
set data_inputs {}
foreach p [all_inputs] {if {[get_full_name $p] ne "clk"} {lappend data_inputs $p}}
set_input_delay -clock core -min 0.2 $data_inputs
set_input_delay -clock core -max 0.8 $data_inputs
set_output_delay -clock core -min 0.2 [all_outputs]
set_output_delay -clock core -max 0.8 [all_outputs]
set_driving_cell -lib_cell BUF_X2 -pin Z $data_inputs
set_load 50 [all_outputs]
'''
    text += f'read_spef {{{common}}}\nread_spef {{{case_dir / "links.spef"}}}\n'
    text += '''set_propagated_clock [all_clocks]
sta::find_timing
report_units
write_sdc -digits 12 constraints-readback.sdc
report_parasitic_annotation -report_unannotated > annotation.rpt
set f [open summary.tsv w]
puts $f "setup_count\\t[sta::endpoint_violation_count max]"
puts $f "hold_count\\t[sta::endpoint_violation_count min]"
puts $f "time_unit_seconds\\t[sta::time_ui_sta 1]"
puts $f "cap_unit_farads\\t[sta::capacitance_ui_sta 1]"
foreach kind {capacitance slew fanout} {
 puts $f "$kind\\t[sta::max_${kind}_violation_count]\\t[sta::max_${kind}_check_slack]\\t[sta::max_${kind}_check_limit]"
}
close $f
report_worst_slack -max -digits 12 > timing.rpt
report_worst_slack -min -digits 12 >> timing.rpt
report_checks -path_delay min_max -group_path_count 5 -format full_clock_expanded -digits 12 >> timing.rpt
report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 12 -no_line_splits > electrical.rpt
set setup_stream [open check-setup.rpt w]
puts $setup_stream [check_setup -verbose]
close $setup_stream
set f [open links.tsv w]
'''
    for row in observations['links']:
        text += 'set source_name {' + row['source_driver'] + '}\n'
        text += 'set sink_names ' + tcl_list(row['first_native_loads']) + '\n'
        text += '''set source_pins [get_pins -quiet $source_name]
if {[llength $source_pins]!=1} {error "Missing actual native source driver: $source_name"}
set sink_pins [get_pins -quiet $sink_names]
if {[llength $sink_pins]!=[llength $sink_names]} {error "Missing actual native receiver pins"}
'''
        for kind in ('max', 'min'):
            text += 'set paths [find_timing_paths -path_delay ' + kind + ' -through $source_pins -through $sink_pins -group_path_count 1]\n'
            text += 'if {![llength $paths]} {error "No constrained real producer-to-consumer path"}\n'
            text += '''set p [lindex $paths 0]
foreach candidate $paths {if {[get_property $candidate slack] < [get_property $p slack]} {set p $candidate}}
'''
            text += ('puts $f "' + row['id'] + '\t' + kind + '\t[get_property $p slack]'
                     '\t[get_full_name [get_property $p startpoint]]'
                     '\t[get_full_name [get_property $p endpoint]]"\n')
    text += 'close $f\n'
    text += 'source {' + str(TOOLS / 'native_annotation.tcl') + '}\n'
    return text


def read_results(folder, link_count):
    summary = {}
    for line in (folder / 'summary.tsv').read_text().splitlines():
        key, *values = line.split('\t')
        assert key not in summary
        summary[key] = values
    # Same1e-6 relative unit tolerance as native_sta.py: OpenSTA returns
    # float32-scaled SI units (9.999999717e-10), not exact Python doubles.
    # A1000x ns/ps or fF/pF mistake remains a hard failure.
    assert abs(float(summary['time_unit_seconds'][0]) / 1e-9 - 1) < 1e-6
    assert abs(float(summary['cap_unit_farads'][0]) / 1e-15 - 1) < 1e-6
    assert (folder/'check-setup.rpt').read_text().strip() == '1','Unconstrained data/clock or another setup-sanity failure'
    paths = {}
    for line in (folder / 'links.tsv').read_text().splitlines():
        name, kind, slack, start, end = line.split('\t')
        value = float(slack)
        assert math.isfinite(value)
        assert (name, kind) not in paths
        paths[name, kind] = dict(slack_ns=value, startpoint=start, endpoint=end)
    assert len(paths) == 2 * link_count
    unannotated = {}
    for line in (folder / 'annotation-connectivity.tsv').read_text().splitlines():
        name, fanout = line.split('\t')
        assert fanout.isdigit(), (name, fanout)
        unannotated[name] = int(fanout)
    assert not any(unannotated.values()), ('Connected unannotated native driver', unannotated)
    counts = {k: int(summary[k][0]) for k in ('setup_count', 'hold_count', 'capacitance', 'slew', 'fanout')}
    electrical_passed = all(counts[k] == 0 for k in ('capacitance', 'slew', 'fanout'))
    setup = min(p['slack_ns'] for (name, kind), p in paths.items() if kind == 'max')
    hold = min(p['slack_ns'] for (name, kind), p in paths.items() if kind == 'min')
    text = (folder / 'sta.log').read_text()
    forbidden = [line for line in text.splitlines()
                 if re.search(r'\[(?:ERROR|WARNING)\b', line)]
    # No warning waiver is applied: even messages not classified here remain
    # archived for explicit review. This list deliberately fails unknown tool
    # warnings rather than silently accepting partial SPEF consumption.
    assert not forbidden, forbidden[:20]
    return dict(summary=summary, counts=counts, electrical_passed=electrical_passed,
                min_link_setup_ns=setup, min_link_hold_ns=hold,
                link_paths={name: {kind: paths[name, kind] for kind in ('max', 'min')}
                            for name, _ in paths},
                zero_fanout_unannotated_drivers=unannotated,
                connected_parasitics_annotated=True,
                declared_model_passed=(electrical_passed and setup >= 0 and hold >= 0
                                       and counts['setup_count'] == counts['hold_count'] == 0))


def run_case(native, prepared, out, topology, length, factor, run,
             resistance_multiplier=1., capacitance_multiplier=1., cell='BUF_X4'):
    meta = json.loads((prepared / 'prepared.json').read_text())
    if 'native_verilog' in meta:
        native = {side: dict(row,verilog=meta['native_verilog'][side]['path'])
                  for side,row in native.items()}
        for side,row in native.items():
            assert sha(row['verilog']) == meta['native_verilog'][side]['sha256']
    observations = link_spef(meta, out / 'links.spef', topology, length, factor,
                             resistance_multiplier=resistance_multiplier,
                             capacitance_multiplier=capacitance_multiplier,cell=cell)
    common = Path(meta['common_paths'][topology]) if 'common_paths' in meta else prepared / ('common-' + topology + '.spef')
    proof = audit_native(meta, common, out / 'links.spef')
    (out / 'wrapper.v').write_text(wrapper(meta, native, topology,cell=cell))
    (out / 'sta.tcl').write_text(sta_script(native, common, out, observations))
    run(['openroad', '-no_init', '-exit', out / 'sta.tcl'], 'sta.log')
    measured = read_results(out, len(meta['links']))
    return dict(schema='finite-real-producer-link/1', passed=True,
                experiment_completed=True, topology=topology, length_um=length,
                variant='high' if factor == 1.5 else 'base', native_preservation=proof,
                native_common_sha256=meta['common_sha256'][topology],
                links_spef_sha256=sha(out / 'links.spef'),
                wrapper_sha256=sha(out / 'wrapper.v'), observations=observations,
                **measured, production_macros_modified=False,
                geometry_qualified=False, calibrated_12layer_rc_qualified=False,
                scope='Both complete native gate-level macros and their native RC/coupling records, shared ideal clock root plus original CTS, live data/valid/ready wires. Candidate buffers and8um local stubs are electrical what-if resources, not placed or fabricated hardware. Single fanout, declared RC length scan only; no complete controller/protocol/system/manufacturing qualification.')


def probe(root, out, cpus, run):
    assert cpus == 16
    native, links = fixture(out / 'fixtures',vector=True)
    prepared = out / 'prepared'
    prepare(native, prepared, links)
    # run() writes logs relative to OUT, so use a temporary adapter for each
    # independently saved real OpenROAD consumer control.
    import subprocess
    measured = {}
    for name, topology, rm, cm in [('direct', 'direct', 1., 1.),
                                    ('endpoints', 'endpoints', 1., 1.),
                                    ('relay', 'relay', 1., 1.),
                                    ('mixed-relay', 'relay', 1., 1.),
                                    ('huge-r', 'direct', 100000., 1.),
                                    ('huge-c', 'direct', 1., 100.)]:
        folder = out / name
        folder.mkdir()
        def local_run(argv, log):
            with (folder / log).open('w') as stream:
                p = subprocess.run(list(map(str, argv)), cwd=folder,
                                   stdout=stream, stderr=subprocess.STDOUT)
            assert p.returncode == 0, (name, log)
        cell=dict(tx='BUF_X8',mid='BUF_X8',rx='BUF_X2') if name=='mixed-relay' else 'BUF_X4'
        length={'f000':568.,'f001':1200.} if name=='mixed-relay' else 568.
        measured[name] = run_case(native, prepared, folder, topology, length, 1., local_run,
                                 resistance_multiplier=rm, capacitance_multiplier=cm,cell=cell)
    assert measured['direct']['min_link_setup_ns'] > 0
    assert measured['huge-r']['min_link_setup_ns'] < measured['direct']['min_link_setup_ns'] - 1
    assert measured['huge-c']['counts']['capacitance'] > 0
    assert measured['huge-c']['min_link_setup_ns'] < measured['direct']['min_link_setup_ns'] - .1
    assert all(measured[k]['connected_parasitics_annotated'] for k in measured)
    from native_cell_gate import group, attribute
    text = LIBRARY.read_text()
    cells = {}
    for name in ('BUF_X1', 'BUF_X2', 'BUF_X4', 'BUF_X8'):
        body = group(text, 'cell', name)
        cells[name] = dict(area_um2=float(attribute(body, 'area')),
                           input_cap_ff=float(attribute(group(body, 'pin', 'A'), 'capacitance')),
                           output_max_cap_ff=float(attribute(group(body, 'pin', 'Z'), 'max_capacitance')))
    assert measured['mixed-relay']['declared_model_passed']
    result = dict(passed=True, actual_hierarchical_native_join_consumed=True,
                  positive_topologies=['direct', 'endpoints', 'relay','mixed-relay'],
                  actual_huge_r_and_c_negative_controls_rejected=True,
                  cases=measured, cells=cells, library_sha256=sha(LIBRARY),
                  scope='Four real Liberty DFFs with two protection devices, true vector ports, split native SPEFs and merged links. Tool/graph controls only; no real macro qualification.')
    (out / 'interconnect-probe.json').write_text(json.dumps(result, indent=2) + '\n')


def spec(root):
    return json.loads((root / 'project/experiments/block_v1/interconnect-sources.json').read_text())


def native_pair(root, pair):
    source = spec(root)['macros']
    return {side: source[kind] for side, kind in zip(('left', 'right'), pair)}


def prepare_macro(root, out, cpus, run, pair):
    from io_slots import slot
    assert cpus == 16 and pair in ('mt', 'ts')
    native = native_pair(root, pair)
    base = out.parents[2]
    control = out.parent / 'interconnect-probe'
    receipt = json.loads((control / 'receipt.json').read_text())
    assert receipt['passed'] and sha(control / 'interconnect-probe.json') == receipt['outputs']['interconnect-probe.json']
    with slot(base):
        for row in native.values():
            for name, path in [('6_final.v', row['verilog']), ('6_final.spef', row['spef']), ('6_final.sdc', row['sdc'])]:
                assert sha(path) == row['hashes'][name]
        old_run=spec(root).get('reuse_preparation_run')
        result = reuse_graphs(root,out,pair,old_run) if old_run else prepare(native,out,paired_links(*pair))
        result['native_verilog']=restore_physical(native,out)
        (out/'prepared.json').write_text(json.dumps(result)+'\n')
    report = dict(passed=True, pair=pair, native_sources=native,
                  source_control_receipt_sha256=sha(control / 'receipt.json'),
                  native_record_inventory=result['expected_native_records'],
                  common_sha256=result['common_sha256'], selected_links=len(result['links']),
                  restored_original_physical_devices=result['native_verilog'],
                  reused_preparation=result.get('reused_preparation'),
                  production_macros_modified=False, physical_implementation_completed=False)
    (out / 'interconnect-prepare.json').write_text(json.dumps(report, indent=2) + '\n')


def measure(root, out, cpus, run, pair, topology, length, variant):
    assert cpus == 16 and pair in ('mt', 'ts') and variant in ('base', 'high')
    prepared = out.parent / ('interconnect-prepare-' + pair)
    receipt = json.loads((prepared / 'receipt.json').read_text())
    assert receipt['passed'] and sha(prepared / 'prepared.json') == receipt['outputs']['prepared.json']
    measured = run_case(native_pair(root, pair), prepared, out, topology, length,
                        1.5 if variant == 'high' else 1., run)
    measured['pair'] = pair
    measured['native_preparation_receipt_sha256'] = sha(prepared / 'receipt.json')
    (out / 'interconnect-result.json').write_text(json.dumps(measured, indent=2) + '\n')


def measure_profile(root,out,cpus,run,pair,topology,variant):
    """Twelve bounded actual-pin sensitivity cases, not another size sweep."""
    from interconnect_pin_profiles import profiles
    assert cpus==16 and pair in ('mt','ts') and topology in ('direct','endpoints','relay')
    assert variant in ('high','section')
    profile=profiles(root)
    prepared=out.parent/('interconnect-prepare-'+pair)
    receipt=json.loads((prepared/'receipt.json').read_text())
    assert receipt['passed'] and sha(prepared/'prepared.json')==receipt['outputs']['prepared.json']
    cells=dict(tx='BUF_X8',mid='BUF_X8',rx='BUF_X2')
    base=.15539099611464
    # Independently solved ideal cross section. It is a declared environment,
    # not a calibrated upper bound or a manufacturing/process corner.
    c_per_um=.23308649417196 if variant=='high' else .336771929059818
    measured=run_case(native_pair(root,pair),prepared,out,topology,
                      profile['pairs'][pair]['selected_lengths_um'],1.,run,
                      resistance_multiplier=1.5,capacitance_multiplier=c_per_um/base,cell=cells)
    measured.update(pair=pair,variant=variant,profile=profile['pairs'][pair],
                    pin_source_hashes=profile['inputs'],gap_um=profile['gap_um'],
                    effective_c_per_um_ff=c_per_um,effective_r_per_um_ohm=.0225,
                    cell_selection=cells,native_preparation_receipt_sha256=sha(prepared/'receipt.json'),
                    environment='Declared RC high sensitivity' if variant=='high' else
                    'Ideal homogeneous dielectric2D cross section, two continuous planes and grounded neighbors; not actual patterned3D stack or a certified bound')
    (out/'interconnect-result.json').write_text(json.dumps(measured,indent=2)+'\n')
