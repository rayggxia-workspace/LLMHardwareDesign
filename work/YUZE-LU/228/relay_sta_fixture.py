"""Replay the historical P VALID fixture with the new overlay and declared research RC."""
import argparse
import json
from pathlib import Path
import re


def wire_rc(route, scale):
    length = sum(abs(a - b) for edge in route['segments'] for a, b in zip(edge['a'], edge['b'])) / 2000
    cuts = len(route['via10']) + len(route['via11'])
    return length, scale * 0.155390385 * length / 1000, scale * (0.015 * length + 0.08 * cuts)


def spef_net(name, driver, sink, cap, resistance):
    nodes = [driver, *(f'{name}:{i}' for i in range(1, 4)), sink]
    lines = [f'*D_NET {name} {cap:.8f}', '*CONN', f'*I {driver} O', f'*I {sink} I', '*CAP']
    lines.extend(f'{i} {node} {cap * weight:.8f}'
                 for i, (node, weight) in enumerate(zip(nodes, (.125, .25, .25, .25, .125)), 1))
    lines.append('*RES')
    lines.extend(f'{i} {a} {b} {resistance / 4:.8f}'
                 for i, (a, b) in enumerate(zip(nodes, nodes[1:]), 1))
    return '\n'.join([*lines, '*END', ''])


def prepare(reference, geometry, output):
    stages = {
        'direct': [('p_gate_valid_pre', 'P0:m_to_g_valid', 'P0:g_from_m_valid')],
        'relay': [('p_gate_valid_pre', 'P0:m_to_g_valid', 'P0:upper_valid_in'),
                  ('p_gate_valid_post', 'P0:upper_valid_out', 'P0:g_from_m_valid')],
    }
    tcl = (reference / 'sta-high.tcl').read_text()
    tcl = tcl.split('report_worst_slack', 1)[0]
    top = (reference / 'top.v').read_text()
    for label, scenario in [('direct', 'no-repeaters'), ('relay', 'repeaters')]:
        design = top
        if label == 'direct':
            for old, new in [
                ('.g_from_m_valid(p_gate_valid_post)', '.g_from_m_valid(p_gate_valid_pre)'),
                ('.upper_valid_in(p_gate_valid_pre)', '.upper_valid_in()'),
                ('.upper_valid_out(p_gate_valid_post)', '.upper_valid_out()'),
            ]:
                if design.count(old) != 1:
                    raise ValueError('unexpected frozen fixture endpoint: ' + old)
                design = design.replace(old, new)
        topology = json.loads((geometry / (scenario + '-routes.json')).read_text())
        wires = topology['physical_routes']['routes']
        if len(wires) != len(stages[label]) or not topology['geometry_check']['passed']:
            raise ValueError('unexpected fixture route')
        verilog = output / (label + '.v')
        verilog.write_text(design)
        for corner, scale in [('low', .7), ('high', 1.5)]:
            parasitics = (reference / ('upper-' + corner + '.spef')).read_text()
            parasitics, removed = re.subn(r'^\*D_NET p_gate_valid_(?:pre|post) [^\n]+\n.*?^\*END\n',
                                          '', parasitics, flags=re.MULTILINE | re.DOTALL)
            if removed != 2:
                raise ValueError('unexpected number of baseline SPEF nets')
            parasitic = output / f'{label}-{corner}.spef'
            receipt = []
            for i, (name, driver, sink) in enumerate(stages[label]):
                length, cap, resistance = wire_rc(wires[f'segment/0/{i}'], scale)
                parasitics += spef_net(name, driver, sink, cap, resistance)
                receipt.append({'stage': f'segment/0/{i}', 'net': name, 'length_um': length,
                                'wire_cap_pf': cap, 'wire_resistance_ohm': resistance})
            parasitic.write_text(parasitics)
            (output / f'{label}-{corner}-rc.json').write_text(json.dumps(receipt, indent=2) + '\n')
            script = tcl.replace(str(reference / 'top.v'), str(verilog))
            script = script.replace(str(reference / 'upper-high.spef'), str(parasitic))
            script += '''
puts "VALID_SETUP"
report_checks -through [get_pins P0/g_from_m_valid] -to [all_registers -data_pins] -path_delay max -group_path_count 1 -digits 6 -format full_clock_expanded
puts "VALID_HOLD"
report_checks -through [get_pins P0/g_from_m_valid] -to [all_registers -data_pins] -path_delay min -group_path_count 1 -digits 6 -format full_clock_expanded
puts "VALID_ELECTRICAL"
report_check_types -max_capacitance -max_slew -violators -digits 6
puts "VALID_NETS"
foreach n [get_nets p_gate_valid_*] { report_net [get_full_name $n] }
puts "VALID_END"
'''
            (output / f'{label}-{corner}.tcl').write_text(script)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('geometry', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    prepare(args.reference.resolve(), args.geometry.resolve(), args.output.resolve())
