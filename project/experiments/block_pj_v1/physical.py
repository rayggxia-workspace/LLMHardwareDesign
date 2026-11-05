"""First hierarchical route of the two wrappers on exact released leaves."""
import json
import os
from pathlib import Path
import sys
import subprocess

repo, leaves, parent = (Path(p) for p in sys.argv[1:4])
which = sys.argv[4]
out = parent / which
out.mkdir()
top = f'block_{which.lower()}16'
experiment = repo / 'project/experiments'
sys.path.insert(0, str(experiment / 'block_v1'))
from constraints import generate as constraints

flow = Path('/OpenROAD-flow-scripts/flow')
rtl = repo / 'project/rtl/block_pj_v1'
grt_mode = os.environ.get('PJ_GRT_MODE', 'default')
if which == 'P':
    width = 3100
    height = 2220 if grt_mode == 'guide-compact' else width
    macros = {'p4': ('store', 104, 104), 'M': ('multiply', 2064, 104), 'G': ('gate', 2064, 1152)}
else:
    width = 2600
    height = 2040 if grt_mode == 'guide-compact' else width
    macros = {'n4': ('store', 104, 104), 'T': ('lease', 1392, 104), 'E': ('arithmetic', 1392, 1264)}
views = [leaves / 'views' / leaf for leaf in macros]
receipts = [json.loads((view / 'receipt.json').read_text()) for view in views]
for name, view in zip(macros, views):
    # OpenDB derives its library identity from the LEF basename.
    if os.environ.get('PJ_CONSERVATIVE_LEF') == '1':
        env = dict(os.environ, PJ_LEAF_ODB=str(leaves / 'inputs' / name / '6_final.odb'),
                   PJ_LEAF_ROUTES=str(out / f'{name}-access.tsv'))
        with (out / f'{name}-access.log').open('w') as log:
            subprocess.run(['openroad', '-no_init', '-threads', '1', '-exit',
                            str(Path(__file__).with_name('leaf_access.tcl'))],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([sys.executable, str(Path(__file__).with_name('conservative_lef.py')),
                        str(view / 'leaf.lef'), env['PJ_LEAF_ROUTES'], str(out / f'{name}.lef')], check=True)
    else:
        (out / f'{name}.lef').symlink_to(view / 'leaf.lef')
    (out / f'{name}.gds').symlink_to(leaves / 'inputs' / name / '6_final.gds')
budget = json.loads((experiment / 'block_v1/physical-budget-300mhz.json').read_text())
(out / 'input.sdc').write_text(constraints(budget).replace('-period 3.33333 ', '-period 3.333333333333 '))
placement = []
for instance, x, y in macros.values():
    placement += [f'place_macro -macro_name {instance} -location {{{x} {y}}} -orientation R0 -exact',
                  f'[[ord::get_db_block] findInst {instance}] setPlacementStatus FIRM']
(out / 'placement.tcl').write_text('\n'.join(placement) + '\n')
pdn = '''add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name parent -voltage_domains CORE -pins metal10
add_pdn_stripe -grid parent -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins
add_pdn_stripe -grid parent -layer metal4 -width 0.48 -pitch 56 -offset 2
add_pdn_stripe -grid parent -layer metal7 -width 1.40 -pitch 30 -offset 2
add_pdn_stripe -grid parent -layer metal10 -width 1.40 -pitch 60 -offset 5
add_pdn_connect -grid parent -layers {metal1 metal4}
add_pdn_connect -grid parent -layers {metal4 metal7}
add_pdn_connect -grid parent -layers {metal7 metal10}
'''
for instance, _, _ in macros.values():
    pdn += f'define_pdn_grid -name grid_{instance} -voltage_domains CORE -macro -instances {instance} -grid_over_pg_pins -halo {{2 2 2 2}}\n'
    pdn += f'add_pdn_connect -grid grid_{instance} -layers {{metal7 metal10}}\n'
(out / 'pdn.tcl').write_text(pdn)
instances = ' '.join(v[0] for v in macros.values())
pg_filter = Path(__file__).with_name('filter_pg_landings.tcl')
(out / 'post-pdn.tcl').write_text(
    f'source {{{pg_filter}}}\npj_filter_pg {{{instances}}} {{{out / "pg-removed.tsv"}}}\n')

# Keep signal pins clear of child masters. Split neighboring bits across four
# near-boundary lines on the existing M10 landing grid. Use every second
# 4 um post-process track to also align with the 1.6 um native M10 pitch.
pin_script = r'''set block [ord::get_db_block]
set names {}
foreach term [$block getBTerms] {
    if {[$term getSigType] ni {POWER GROUND}} {lappend names [$term getName]}
}
set aligned_width [expr {8 * ($width / 8)}]
set aligned_height [expr {8 * ($height / 8)}]
# The native paired grid uses 60um pitch with alternating VDD/VSS
# centers every 30um, starting 5um after the snapped core origin.
set pg_origin [expr {[[$block getCoreArea] xMin]/double([$block getDbUnitsPerMicron]) + 5}]
proc pg_clear {x pg_origin} {
    set dx [expr {$x - $pg_origin}]
    expr {abs($dx - 30.0*round($dx/30.0)) >= 4.0}
}
set xslots {}
for {set x 64.095} {$x < $width-64} {set x [expr {$x+8}]} {
    if {[pg_clear $x $pg_origin]} {lappend xslots $x}
}
set west {}
set east {}
for {set i 0} {[llength $west]<2 || [llength $east]<2} {incr i} {
    set l [expr {24.095+8*$i}]
    set r [expr {$aligned_width-24+.095-8*$i}]
    if {[llength $west]<2 && [pg_clear $l $pg_origin]} {lappend west $l}
    if {[llength $east]<2 && [pg_clear $r $pg_origin]} {lappend east $r}
}
# Reserve the closest ordinary landing sites for the M result outputs.
set k 0
set positions {}
foreach pin [lsort -dictionary $names] {
    if {$pin eq "clk"} {
        if {![pg_clear [lindex $clock_anchor 0] $pg_origin]} {error "Clock anchor collides with PG"}
        place_pin -pin_name $pin -layer metal10 -location $clock_anchor -pin_size {2 2}
        continue
    }
    set edge [expr {$k % 4}]
    set slot [expr {$k / 4}]
    set phase [expr {$slot % 2}]
    set x [lindex $xslots $slot]
    set y [expr {40.070+8.0*$slot}]
    switch $edge {
        0 {set x [lindex $west $phase]}
        1 {set x [lindex $east $phase]}
        2 {set y [expr {24.070+8.0*$phase}]}
        3 {set y [expr {$aligned_height-24.0+.070-8.0*$phase}]}
    }
    if {$move_rx_pin && $pin eq {rx_tag[28]}} {
        if {$edge != 0} {error "Expected RX tag pin on west boundary"}
        set x 32.095
    }
    if {$x eq "" || $x >= $width || $y >= $height || ![pg_clear $x $pg_origin]} {error "M10 signal landing unavailable: $pin"}
    dict set positions $pin [list $x $y]
    incr k
}
if {$group_result} {
    set result_pins {}
    set candidates {}
    dict for {pin xy} $positions {
        lassign $xy x y
        set distance [expr {abs($x - 2950.0) + abs($y - 440.0)}]
        lappend candidates [list $distance $pin]
        if {[string match {cmd_result*} $pin]} {lappend result_pins $pin}
    }
    set candidates [lsort -real -index 0 $candidates]
    set occupied {}
    foreach pin $result_pins candidate $candidates {
        if {$pin eq ""} {break}
        dict set occupied [lindex $candidate 1] 1
    }
    set displaced {}
    dict for {pin xy} $positions {
        if {[dict exists $occupied $pin] && [lsearch -exact $result_pins $pin] < 0} {
            lappend displaced $pin
        }
    }
    set available {}
    foreach pin $result_pins {
        if {![dict exists $occupied $pin]} {lappend available [dict get $positions $pin]}
    }
    if {[llength $displaced] != [llength $available]} {error "Unbalanced M result landing assignment"}
    set original $positions
    foreach pin $result_pins candidate $candidates {
        if {$pin eq ""} {break}
        dict set positions $pin [dict get $original [lindex $candidate 1]]
    }
    foreach pin $displaced xy $available {dict set positions $pin $xy}
}
dict for {pin xy} $positions {
    place_pin -pin_name $pin -layer metal10 -location $xy -pin_size {2 2}
}
'''
clock_anchor = '1992.095 920.070' if which == 'P' else '1320.095 720.070'
move_rx_pin = int(which == 'J' and grt_mode in ('guide-min2', 'guide-compact'))
(out / 'pins.tcl').write_text(f'set width {width}\nset height {height}\nset clock_anchor {{{clock_anchor}}}\n'
                             f'set move_rx_pin {move_rx_pin}\n'
                             f'set group_result {int(which == "P" and os.environ.get("PJ_GROUP_RESULT") == "1")}\n'
                             + pin_script)

def entry(name, value):
    return f'export {name} = {value}\n'

cfg = {
    'PLATFORM': 'nangate45',
    'DESIGN_NAME': top,
    'DESIGN_NICKNAME': top,
    'VERILOG_FILES': f'{rtl / (top + ".sv")} {rtl / "pj_sram_client.sv"} {rtl / "pj_mem_port.sv"} {rtl / "pj_feed_hold.sv"}',
    'SDC_FILE': out / 'input.sdc',
    'ADDITIONAL_LEFS': ' '.join(str(out / f'{n}.lef') for n in macros),
    'ADDITIONAL_LIBS': ' '.join(str(p / 'leaf.lib') for p in views),
    'ADDITIONAL_GDS': ' '.join(str(out / f'{n}.gds') for n in macros),
    'DIE_AREA': f'0 0 {width} {height}',
    'CORE_AREA': f'20 20 {width-20} {height-20}',
    'MACRO_PLACEMENT_TCL': out / 'placement.tcl',
    'PDN_TCL': out / 'pdn.tcl',
    'POST_PDN_TCL': out / 'post-pdn.tcl',
    'FOOTPRINT_TCL': out / 'pins.tcl',
    'MACRO_PLACE_HALO': '20 20',
    'PLACE_DENSITY': '.30',
    'SYNTH_HIERARCHICAL': 0,
    'TNS_END_PERCENT': 100,
    'HOLD_SLACK_MARGIN': os.environ.get('PJ_HOLD_TARGET', '.005'),
    'CTS_ARGS': '-sink_clustering_enable -repair_clock_nets -apply_ndr none -no_insertion_delay -balance_levels -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}',
    'CAP_MARGIN': int(os.environ.get('PJ_CAP_MARGIN', '35')),

    'KEEP_VARS': 1,
}
if os.environ.get('PJ_BALANCED_CTS') == '1':
    cfg['CTS_ARGS'] = ('-sink_clustering_enable -repair_clock_nets -apply_ndr none '
                       '-no_insertion_delay -balance_levels -root_buf CLKBUF_X3 '
                       '-buf_list {CLKBUF_X2 CLKBUF_X3}')

if grt_mode == 'cugr':
    cfg['GLOBAL_ROUTE_USE_CUGR'] = 1
elif grt_mode in ('guide', 'guide-via', 'guide-min2', 'guide-compact'):
    # An imperfect guide is an input to detailed routing; the final gates
    # still require actual connected detail wires, DRC and extracted timing.
    cfg['GLOBAL_ROUTE_ARGS'] = '-allow_congestion -congestion_iterations 8'
    if grt_mode != 'guide':
        cfg['DETAILED_ROUTE_ARGS'] = (
            '-via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 '
            '-via_access_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5')
else:
    assert grt_mode == 'default', grt_mode
(out / 'config.mk').write_text(''.join(entry(k, v) for k, v in cfg.items()))
command = ['make', '-C', str(flow), f'DESIGN_CONFIG={out / "config.mk"}',
           f'WORK_HOME={out / "flow"}', 'NUM_CORES=12',
           f'MIN_ROUTING_LAYER={"metal2" if grt_mode == "guide-min2" else "metal1"}',
           'MAX_ROUTING_LAYER=metal10', 'MAX_CLK_ROUTING_LAYER=metal10']
receipt = dict(top=top, budget=budget, leaves=receipts, placements=macros,
               commands=[], qualification='Trial physical implementation with preliminary leaf timing views')
for stage in ('synth', 'do-floorplan', 'do-place', 'do-cts', 'do-route', 'do-finish', 'do-gds'):
    invocation = command + [stage]
    if grt_mode == 'guide-compact' and stage == 'do-cts':
        # The placement estimate on the compact geometry exhausted the
        # buffer budget at the route-aware hold target. Defer that target
        # to global route, where actual guides constrain repair.
        invocation.append('HOLD_SLACK_MARGIN=.005')
    receipt['commands'].append(invocation)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (out / f'{stage}.log').open('w') as log:
        subprocess.run(invocation, stdout=log, stderr=subprocess.STDOUT, check=True)
