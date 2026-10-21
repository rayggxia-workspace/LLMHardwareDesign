"""Prepare and check two-hard-block wiring from audited, unqualified baseline views.

This emits no runnable PNR configuration and does not promote baseline blocks.
Run on a compute node: Yosys checks the actual generated black-box connection.
"""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
baseline = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-01/baseline-views')
source_validation = baseline / 'validation.json'
data = json.loads(source_validation.read_text())
assert data['passed'] and not data['top_pnr_executed']
manifest = (baseline / 'output-files.sha256').read_text().splitlines()
expected_hashes = {line.split(None, 1)[1].lstrip('*').removeprefix('./'): line.split()[0] for line in manifest}
assert hashlib.sha256(source_validation.read_bytes()).hexdigest() == expected_hashes['validation.json']
views = data['views']
act, mxu, merged = (views[k] for k in ('opentpu-act', 'opentpu-mxu', 'opentpu-act-mxu'))
assert all(not v['qualified_hard_macro'] for v in views.values())
assert len({v['alias'] for v in views.values()}) == 3

# Original slice direction: MXU drives addresses/ren/computing; ACT drives data.
links = {'ren': 'act_ren', 'r_use': 'computing', 'r_blk': 'act_blk', 'r_blk2': 'act_blk2',
         'r_hi': 'act_hi', 'r_grp': 'act_grp', 'r_data': 'act_data', 'r_scale': 'act_scale'}
for a, m in links.items():
    ap, mp = act['ports'][a], mxu['ports'][m]
    assert ap['width'] == mp['width'] and {ap['direction'], mp['direction']} == {'input', 'output'}
external = {n: p for n, p in act['ports'].items() if n not in links}
for name, port in mxu['ports'].items():
    if name in set(links.values()) - {'computing'}:
        continue
    if name in external:
        assert name == 'clk' and external[name] == port
    external[name] = port
assert external == merged['ports']
assert len(external) == 40 and sum(p['width'] for p in external.values()) == 1662


def declaration(name, port):
    assert port['direction'] in ('input', 'output') and port['width'] > 0
    return port['direction'] + ' wire ' + (('[%d:0] ' % (port['width'] - 1)) if port['width'] > 1 else '') + name


blackboxes = []
for view in (act, mxu):
    blackboxes.append('(* blackbox *) module ' + view['alias'] + '(\n  ' +
                      ',\n  '.join(declaration(n, p) for n, p in view['ports'].items()) + ');\nendmodule\n')
(root / 'macro_blackboxes.v').write_text('\n'.join(blackboxes))
top = 'llhd_opentpu_hierarchy_preparation'
verilog = '// Preparation only: baseline macro electrical checks failed. No added state or serialization.\n'
verilog += 'module ' + top + '(\n  ' + ',\n  '.join(declaration(n, p) for n, p in external.items()) + ');\n'
for name in links.values():
    if name not in external:
        width = mxu['ports'][name]['width']
        verilog += '  wire ' + ('[%d:0] ' % (width - 1) if width > 1 else '') + name + ';\n'
for instance, view, mapping in [('u_act', act, links), ('u_mxu', mxu, {})]:
    verilog += '  ' + view['alias'] + ' ' + instance + '(\n    ' + ',\n    '.join(
        '.' + name + '(' + mapping.get(name, name) + ')' for name in view['ports']) + ');\n'
verilog += 'endmodule\n'
(root / 'hierarchy_preparation.v').write_text(verilog)
(root / 'check.ys').write_text('read_verilog -lib macro_blackboxes.v\nread_verilog hierarchy_preparation.v\n'
    'hierarchy -check -top ' + top + '\ncheck -assert\nwrite_json checked-top.json\n')
with (root / 'yosys-check.log').open('w') as log:
    subprocess.run(['yosys', '-Q', '-T', '-s', 'check.ys'], stdout=log, stderr=subprocess.STDOUT, check=True)
checked = json.loads((root / 'checked-top.json').read_text())['modules'][top]
assert {n: {'direction': p['direction'], 'width': len(p['bits'])} for n, p in checked['ports'].items()} == external
assert set(checked['cells']) == {'u_act', 'u_mxu'}
connection_rows = []
for a, m in links.items():
    abits = checked['cells']['u_act']['connections'][a]
    mbits = checked['cells']['u_mxu']['connections'][m]
    assert abits == mbits
    if m == 'computing':
        assert abits == checked['ports']['computing']['bits']
    connection_rows.append(dict(act_port=a, mxu_port=m, width=len(abits), exact_bit_identity=True))
assert checked['cells']['u_act']['connections']['clk'] == checked['cells']['u_mxu']['connections']['clk'] == checked['ports']['clk']['bits']

# A shared square fits both orientations at R0, with 80 um channel/edge margins.
# A future flat comparator must be reimplemented in this outer die, not use the
# existing merged macro's different footprint or add standalone block areas.
import math
edge = channel = 80.0
aw, ah = act['size_um']; mw, mh = mxu['size_um']
side = math.ceil(max(aw + mw + channel + 2*edge, ah + mh + channel + 2*edge) / 10.0) * 10.0
placements = {'horizontal': {'u_act': [edge, edge], 'u_mxu': [edge + aw + channel, edge]},
              'vertical': {'u_act': [edge, edge], 'u_mxu': [edge, edge + ah + channel]}}
for label, locations in placements.items():
    for instance, (width, height) in [('u_act', (aw, ah)), ('u_mxu', (mw, mh))]:
        x, y = locations[instance]
        assert x + width <= side - edge and y + height <= side - edge
    (root / (label + '-placement.tcl')).write_text('# Preparation coordinates; requires qualified replacement views and PG audit.\n' + ''.join(
        'place_macro -macro_name %s -location {%s %s} -orientation R0\n' % (name, xy[0], xy[1]) for name, xy in locations.items()))
contract = dict(top=top, external_ports=external, external_signal_bits=1662, connections=connection_rows,
    address_and_data_bits=sum(row['width'] for row in connection_rows if row['mxu_port'] != 'computing'),
    computing_feedback_bits=1, shared_clock='clk', added_registers=0,
    clock_ns=2.5, io_delay_ns=0.5, channel_um=channel, die_um=[0, 0, side, side],
    placements=placements, rotations='R0 only', baseline_view_names=[act['alias'], mxu['alias']],
    baseline_prior_max_cap={k: v['prior_max_cap_violations'] for k, v in views.items()},
    formal_top_pnr_executed=False, formal_top_ready=False,
    required_before_formal_comparison=[
        'New ACT/MXU/merged final extraction reports: DRC/antenna, setup/hold, all electrical rules and PG pass',
        'Selected input hashes; LEF/Liberty/netlist port identity and timing arc coverage audit',
        'Internal block clock checks retained separately: current timing models lack minimum_period',
        'Explicit adjacent-block driver/load and timing budget policy; no unmodeled interface claim',
        'Power pin/OBS inspection and strict VDD/VSS connectivity with geometric via audit',
        'Flat merged implementation rerun at identical outer die, clock, IO budget and model revision',
        'Report actual top wires/CTS/PG/channel area plus block resource cost; no sum-of-block proxy',
        'Functional/physical equivalence gaps remain explicit; this contract does not close them'])
(root / 'top-contract.json').write_text(json.dumps(contract, indent=2) + '\n')
(root / 'baseline-inputs.sha256').write_text(hashlib.sha256(source_validation.read_bytes()).hexdigest() + '  ' + str(source_validation) + '\n')
(root / 'validation.json').write_text(json.dumps(dict(passed=True, kind='Generated two-hard-block wiring and floorplan preparation',
    macro_instances=2, external_ports=40, external_signal_bits=1662, internal_data_address_bits=684,
    computing_feedback_bits=1, exact_bit_identity=True, shared_clock=True, added_registers=0,
    top_pnr_executed=False, qualified_hard_macros=False, top_contract=contract,
    scope='Black-box wiring check and proposed common die only; baseline views still fail capacitance and full timing arc/PG/functional qualification remain pending'), indent=2) + '\n')
