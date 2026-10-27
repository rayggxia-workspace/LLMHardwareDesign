"""Map and price real shared121 glue; keep both physical leaves explicit.

The combinational cut exposes every leaf input and makes every leaf output
symbolic, so glue is checked for all possible leaf states. This is separate
from routing the parent and from behavioral acceptance of the physical leaves.
"""
import concurrent.futures
import copy
from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import time

LEAVES = {'core': 'shared109', 'sink': 'transaction6k'}


def cut(data):
    """Preserve graph bits and expose all connections of the two actual leaves."""
    result = copy.deepcopy(data)
    module = result['modules']['shared121']
    boundary = {}
    used = {b for n in module['netnames'].values() for b in n['bits'] if type(b) is int}
    used.update(b for n in module['ports'].values() for b in n['bits'] if type(b) is int)
    used.update(b for c in module['cells'].values() for bits in c['connections'].values() for b in bits if type(b) is int)
    next_bit = max(used, default=1) + 1
    for instance, master in LEAVES.items():
        cell = module['cells'].pop(instance)
        assert cell['type'] == master and not cell.get('parameters')
        leaf = result['modules'][master]
        assert int(leaf['attributes']['blackbox'], 2) == 1
        assert set(cell['connections']) == set(cell['port_directions']) <= set(leaf['ports'])
        boundary[instance] = {}
        for name, port in leaf['ports'].items():
            direction = port['direction']
            assert direction in ('input', 'output')
            if name in cell['connections']: assert cell['port_directions'][name] == direction
            else: assert direction == 'output', 'Missing actual leaf input'
            bits = list(cell['connections'].get(name, [])); width = len(port['bits'])
            assert width > 0 and len(bits) in (0, width)
            if not bits:
                # Unused leaf outputs still receive symbolic input ports.
                # An empty leaf input would instead be a wiring failure.
                assert direction == 'output'
                bits = list(range(next_bit, next_bit + width)); next_bit += width
            key = 'cut_' + instance + '__' + name
            assert key not in module['ports'] and key not in module['netnames']
            module['ports'][key] = dict(direction='output' if direction == 'input' else 'input', bits=bits)
            module['netnames'][key] = dict(hide_name=0, bits=bits, attributes={})
            boundary[instance][name] = dict(leaf_direction=direction, width=width,
                                           actual_connected_bits=cell['connections'].get(name, []), cut_port=key)
    for master in LEAVES.values(): result['modules'].pop(master)
    result['modules']['glue_cut'] = result['modules'].pop('shared121')
    module['attributes'] = {'top': '1'}
    return result, boundary


def verify(root, out, cpus, run):
    from io_slots import file_sha
    from native_const_probe import restore
    from native_formal import inspect
    from structural_view import unsigned
    assert cpus == 8
    library = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    inputs = [root/'project/rtl/block_v1/shared121.sv', root/'project/rtl/shared_gdn/shared109.sv',
              root/'project/rtl/block_v1/transaction6k.sv', library]
    bindings = {str(p): file_sha(p) for p in inputs}
    script = 'read_liberty -lib ' + str(library) + '\n'
    script += 'read_verilog -lib -sv ' + ' '.join(map(str, inputs[1:3])) + '\n'
    script += 'read_verilog -sv ' + str(inputs[0]) + '\nhierarchy -check -top shared121\n'
    script += 'proc\nopt\ncheck -assert\nwrite_json generic.json\n'
    script += 'synth -top shared121 -noabc\ndfflibmap -liberty ' + str(library) + '\n'
    script += 'abc -liberty ' + str(library) + '\nclean\ncheck -assert\nwrite_json literal.json\n'
    script += 'hilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\ncheck -assert\n'
    script += 'stat -liberty ' + str(library) + '\nwrite_json mapped.json\nwrite_verilog -noattr -noexpr mapped.v\n'
    (out/'map-glue.ys').write_text(script)
    run(['yosys', '-s', 'map-glue.ys'], 'map-glue.log')
    graphs = {name: json.loads((out/(name+'.json')).read_text()) for name in ['generic', 'literal', 'mapped']}
    _, ties = restore(graphs['literal'], graphs['mapped'], library.read_text())
    top = graphs['mapped']['modules']['shared121']
    assert {n: c['type'] for n, c in top['cells'].items() if c['type'] in LEAVES.values()} == LEAVES
    areas = {}; current = None
    for line in library.read_text().splitlines():
        match = re.match(r'\s*cell\s*\(\s*"?([^"\s)]+)"?\s*\)', line)
        if match: current = match.group(1)
        match = re.match(r'\s*area\s*:\s*([^;]+);', line)
        if match and current: areas[current] = Decimal(match.group(1))
    assert len(areas) > 100
    census = Counter(c['type'] for n, c in top['cells'].items() if n not in LEAVES)
    assert census and set(census) <= set(areas), 'Unmapped or unpriced active glue'
    assert all(not re.search(r'DFF|LATCH', name, re.I) for name in census)
    area = sum((areas[n]*count for n, count in census.items()), Decimal(0)); assert area > 0
    boundaries = {}; metadata = {}
    for label, data in graphs.items():
        exposed, boundary = cut(data)
        boundaries[label] = boundary
        metadata[label] = unsigned(exposed)
        (out/(label+'-cut.json')).write_text(json.dumps(exposed)+'\n')
        (out/(label+'-cut.ys')).write_text('read_json '+label+'-cut.json\nwrite_verilog -noattr '+label+'-cut.v\n')
        run(['yosys', '-s', label+'-cut.ys'], label+'-cut.log')
    signatures = [{(i, n): (p['leaf_direction'], p['width']) for i, ports in b.items() for n, p in ports.items()}
                  for b in boundaries.values()]
    assert signatures[0] == signatures[1] == signatures[2]
    equiv = ''
    for label, design in [('generic', 'gold'), ('mapped', 'gate')]:
        equiv += 'read_liberty -ignore_miss_func -ignore_miss_dir ' + str(library) + '\n'
        equiv += 'read_verilog ' + label + '-cut.v\nprep -top glue_cut -flatten\n'
        equiv += 'rename glue_cut ' + design + '\ndesign -stash ' + design + '\ndesign -reset\n'
    equiv += 'design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\n'
    equiv += 'equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_status -assert\n'
    (out/'equivalence.ys').write_text(equiv)
    run(['yosys', '-s', 'equivalence.ys'], 'equivalence.log')
    assert 'Equivalence successfully proven!' in (out/'equivalence.log').read_text()
    binary = Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    control = out.parents[2]/'block-v1-20261027-073/tasks/native-formal-control'
    bound = json.loads((control/'receipt.json').read_text()); assert bound['passed'] is True
    proof_path = control/'native-formal-control.json'
    assert file_sha(proof_path) == bound['outputs'][proof_path.name]
    actual_control = json.loads(proof_path.read_text())
    assert actual_control['passed'] is True and actual_control['binary_sha256'] == file_sha(binary)

    def formal(case):
        folder = out/case; folder.mkdir(); start = time.time()
        if case == 'positive': after = out/'mapped-cut.v'
        else:
            graph = copy.deepcopy(graphs['mapped'])
            instance, pin = {'bad-command': ('core', 'cmd'), 'bad-ack': ('core', 'ack'),
                             'bad-revoke': ('sink', 'revoke_valid')}[case]
            assert len(graph['modules']['shared121']['cells'][instance]['connections'][pin]) == 1
            graph['modules']['shared121']['cells'][instance]['connections'][pin] = ['0']
            graph, _ = cut(graph); unsigned(graph)
            (folder/'fault.json').write_text(json.dumps(graph)+'\n')
            (folder/'emit.ys').write_text('read_json fault.json\nwrite_verilog -noattr fault.v\n')
            with (folder/'emit.log').open('w') as stream:
                subprocess.run(['yosys', '-s', 'emit.ys'], cwd=folder, stdout=stream, stderr=subprocess.STDOUT, check=True)
            after = folder/'fault.v'
        config = 'format: verilog\ninput_paths:\n  - '+str(out/'literal-cut.v')+'\n  - '+str(after)+'\n'
        config += 'liberty_files:\n - '+str(library)+'\nlog_file: '+str(folder/'kepler.log')+'\n'
        (folder/'config.yml').write_text(config)
        env = dict(os.environ, OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        with (folder/'command.log').open('w') as stream:
            code = subprocess.run([str(binary), '--config', str(folder/'config.yml')], cwd=folder,
                                  env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
        text = (folder/'kepler.log').read_text(); received = inspect(text)
        if case == 'positive': assert code == 0 and received['passed'], received
        else:
            assert not received['passed']
            assert 'Found difference' in text or re.search(r'SAT solver finished: SAT\s*$', text, re.M)
        return case, dict(returncode=code, received=received, started=start, finished=time.time(),
                          changed_leaf_pin=None if case == 'positive' else [instance, pin],
                          config_sha256=file_sha(folder/'config.yml'), log_sha256=file_sha(folder/'kepler.log'))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        cases = dict(pool.map(formal, ['positive', 'bad-command', 'bad-ack', 'bad-revoke']))
    assert all(file_sha(Path(p)) == sha for p, sha in bindings.items())
    result = dict(schema='block-v1-native-glue/1', passed=True, top='shared121', input_sha256=bindings,
                  mapped_netlist_sha256=file_sha(out/'mapped.v'), mapped_graph_sha256=file_sha(out/'mapped.json'),
                  physical_glue_cells=dict(census), physical_glue_cell_count=sum(census.values()), glue_area_um2=str(area),
                  leaf_instances_explicitly_excluded=LEAVES, leaf_costs_included=False,
                  physical_glue_qualified=False, qualified_hard_macro=False,
                  boundary=boundaries['mapped'], signed_metadata_only=metadata, tie_cell_restoration=ties,
                  rtl_to_mapped_equivalence_log_sha256=file_sha(out/'equivalence.log'), native_lec_cases=cases,
                  native_lec_control_receipt_sha256=file_sha(control/'receipt.json'), allocated_cpus=cpus,
                  simultaneous_formal_processes=4, omp_threads_per_process=2,
                  scope='Real wrapper glue mapped and separately priced; all-symbolic leaf-boundary equivalence and three real wiring faults. Both physical leaves, parent routing/PG/CTS and routed behavioral composition remain required')
    (out/'native-glue.json').write_text(json.dumps(result, indent=2)+'\n')
