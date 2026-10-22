"""Exact logical cone certificate for mapped versus physically repaired netlists.

Buffers, inverter parity and drive strengths are normalized. Every state input
and external output must have the identical logic graph. Unrecognized logic
transformations fail conservatively; this is not a general SAT/RTL proof.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import subprocess


def family(master):
    return re.sub(r'_X\d+$', '', master)


def state(master):
    return master.startswith(('fakeram', 'DFF', 'SDFF', 'DLH', 'DLL', 'LATCH', 'llhd_opentpu_', 'llhd_match_'))


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def graph(module):
    cells = module['cells']
    drivers, anchors = {}, {}
    for name, port in module['ports'].items():
        if port['direction'] == 'input':
            for index, bit in enumerate(port['bits']):
                anchors.setdefault(bit, []).append((name, index))
    for name, cell in cells.items():
        for pin, bits in cell['connections'].items():
            if cell['port_directions'][pin] != 'output':
                continue
            for index, bit in enumerate(bits):
                if isinstance(bit, str):
                    continue
                assert bit not in drivers, 'Multiple drivers on net '+str(bit)
                drivers[bit] = (name, pin, index)

    @lru_cache(None)
    def resolve(bit):
        if isinstance(bit, str):
            return ('constant-0', int(bit)) if bit in ('0', '1') else ('constant-'+bit, 0)
        if bit in anchors:
            return (signature(['input', sorted(anchors[bit])]), 0)
        assert bit in drivers, 'Reachable undriven internal net '+str(bit)
        name, pin, index = drivers[bit]
        cell = cells[name]
        master = family(cell['type'])
        if state(master):
            return (signature(['state-output', name, master, pin, index]), 0)
        inputs = [(p, [resolve(b) for b in bits]) for p, bits in sorted(cell['connections'].items())
                  if cell['port_directions'][p] == 'input']
        if master in ('BUF', 'CLKBUF', 'INV'):
            assert len(inputs) == 1 and len(inputs[0][1]) == 1
            base, parity = inputs[0][1][0]
            return (base, parity ^ (master == 'INV'))
        return (signature(['logic', master, inputs, pin, index, cell.get('parameters', {})]), 0)

    result = {}
    for name, port in module['ports'].items():
        if port['direction'] == 'output':
            for index, bit in enumerate(port['bits']):
                result['output/'+name+'/'+str(index)] = resolve(bit)
    states = {}
    for name, cell in cells.items():
        if not state(cell['type']):
            continue
        states[name] = family(cell['type'])
        for pin, bits in cell['connections'].items():
            if cell['port_directions'][pin] == 'input':
                for index, bit in enumerate(bits):
                    result['state/'+name+'/'+pin+'/'+str(index)] = resolve(bit)
    return dict(states=states, cones=result,
                ports={name: (p['direction'], len(p['bits'])) for name, p in module['ports'].items()})


def compare(before, after):
    a, b = graph(before), graph(after)
    differences = [key for key in sorted(set(a['cones']) | set(b['cones']))
                   if a['cones'].get(key) != b['cones'].get(key)]
    return dict(passed=a['states'] == b['states'] and a['ports'] == b['ports'] and not differences,
                state_inventory_equal=a['states'] == b['states'], port_contract_equal=a['ports'] == b['ports'],
                checked_state_instances=len(a['states']), checked_cones=len(a['cones']),
                differing_cones=len(differences), first_differences=differences[:40],
                normalized_graph_sha256=signature(a))


def certify(mapped, final, top, libraries, directory, negative_control=False):
    directory.mkdir()
    modules = []
    for label, path in [('mapped', mapped), ('physical', final)]:
        commands = ['read_liberty -lib '+json.dumps(str(p)) for p in libraries]
        output = directory/(label+'.json')
        commands += ['read_verilog '+json.dumps(str(path)), 'hierarchy -check -top '+top,
                     'check -assert', 'write_json '+json.dumps(str(output))]
        script = directory/(label+'.ys')
        script.write_text('\n'.join(commands)+'\n')
        with (directory/(label+'.log')).open('w') as log:
            subprocess.run(['yosys', '-Q', '-T', '-s', str(script)], stdout=log, stderr=subprocess.STDOUT, check=True)
        modules.append(json.loads(output.read_text())['modules'][top])
    result = compare(*modules)
    if negative_control:
        # Alter a real state input only in memory; the actual netlist is untouched.
        physical = modules[1]
        target = next(c for c in physical['cells'].values() if c['type'].startswith('DFF') and 'D' in c['connections'])
        old = target['connections']['D']
        target['connections']['D'] = ['0' if old != ['0'] else '1']
        result['negative_control_detected'] = not compare(modules[0], physical)['passed']
        target['connections']['D'] = old
        assert result['negative_control_detected'], 'Logical auditor failed its state-input mutation control'
    result['scope'] = ('Exact same named state machines or child-macro instances and identical logical cones after drive/buffer/inverter normalization; '
                       'SRAM/child models unchanged. Parent certificates require the separate child certificates. '
                       'Does not prove upstream RTL or physical manufacturing correctness.')
    return result
