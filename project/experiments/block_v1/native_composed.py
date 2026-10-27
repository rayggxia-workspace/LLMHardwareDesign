"""Exact final C8/S16K + T6K + priced glue, under the full mixed oracle.

Only physical leaves with successful sealed producers can enter. Zero-delay
function does not qualify parent geometry, delays, recovery/epoch injection,
macro boundaries, or the common twelve-layer parent.
"""
import concurrent.futures
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import time

INITIALS = [('all-ones', 1, 121), ('random-121', 2, 121), ('random-122', 2, 122)]


def adapt_driver(text):
    """Construct the DUT after commandArgs, before either normal or error use."""
    before = 'static Vshared121 d;'
    assert text.count(before) == 1
    text = '#include <memory>\n' + text.replace(before, 'static Vshared121* native_d;\n#define d (*native_d)\n')
    before = 'int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);'
    assert text.count(before) == 1
    text = text.replace(before, 'int main(int argc,char**argv){Verilated::commandArgs(argc,argv);'
                        'std::unique_ptr<Vshared121> model(new Vshared121);native_d=model.get();try{')
    before = 'need(argc==5,"vectors output stall pilot");'
    assert text.count(before) == 1
    return text.replace(before, 'need(argc==7,"vectors output stall pilot plus two initialization arguments");')


def runtime_arguments(inp, folder, stall, initial, seed):
    assert all(type(v) is int for v in [stall, initial, seed])
    assert stall in (0, 1) and (initial, seed) in [(i, s) for _, i, s in INITIALS]
    return [str(inp/'vectors.tsv'), str(folder/'actual.jsonl'), str(stall), '0',
            '+verilator+rand+reset+'+str(initial), '+verilator+seed+'+str(seed)]


def initialization_control(root, out, cpus, run):
    """Actual installed Verilator/Liberty test of construction and seed ordering."""
    from io_slots import file_sha
    assert cpus == 8
    library = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    (out/'export.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(library)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys', '-s', 'export.ys'], 'export.log')
    (out/'initial.v').write_text('module shared121(input clk,din,output [127:0] result_data);\n'+
        ''.join('DFF_X1 f%d(.CK(clk),.D(din),.Q(result_data[%d]));\n' % (i, i) for i in range(128))+'endmodule\n')
    fixture = '''#include "Vshared121.h"
#include "verilated.h"
#include <iostream>
#include <stdexcept>
static Vshared121 d;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==5,"vectors output stall pilot");
d.clk=0;d.din=0;d.eval();std::cout<<"{\\"words\\":[";
for(int i=0;i<4;i++){if(i)std::cout<<',';std::cout<<d.result_data[i];}std::cout<<"]}\\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
'''
    (out/'initial.cpp').write_text(adapt_driver(fixture))
    verilator = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    run([verilator, '--cc', '--exe', '--build', '-j', str(cpus), '-Wno-fatal', '--top-module', 'shared121',
         '--prefix', 'Vshared121', '--Mdir', str(out/'obj'), '--threads', '2', '--x-initial', 'unique',
         '--x-assign', 'unique', str(out/'initial.v'), str(out/'cells.v'), str(out/'initial.cpp')], 'build.log')
    binary = out/'obj/Vshared121'
    def simulate(spec):
        name, initial, seed = spec
        run([str(binary), 'vectors', 'output', '0', '0', '+verilator+rand+reset+'+str(initial),
             '+verilator+seed+'+str(seed)], name+'.log')
        rows = [json.loads(line) for line in (out/(name+'.log')).read_text().splitlines() if line.startswith('{')]
        assert len(rows) == 1 and set(rows[0]) == {'words'}
        words = rows[0]['words']; assert len(words) == 4 and all(type(w) is int and 0 <= w <= 0xffffffff for w in words)
        return name, words
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: values = dict(pool.map(simulate, INITIALS))
    assert values['all-ones'] == [0xffffffff]*4
    assert all(values[name] not in [[0]*4, [0xffffffff]*4] for name in ['random-121', 'random-122'])
    assert values['random-121'] != values['random-122']
    missing_argv = [str(binary), 'vectors', 'output', '0', '0']
    with (out/'missing-initialization.log').open('w') as stream:
        missing = subprocess.run(missing_argv, stdout=stream, stderr=subprocess.STDOUT).returncode
    assert missing == 1 and 'plus two initialization arguments' in (out/'missing-initialization.log').read_text()
    record = dict(schema='block-v1-native-composed-initialization/1', passed=True, observed_initial_words=values,
                  library_sha256=file_sha(library), module_sha256=file_sha(Path(__file__)),
                  original_mixed_driver_sha256=file_sha(root/'project/experiments/block_v1/committed_sim.cpp'),
                  generated_control_driver_sha256=file_sha(out/'initial.cpp'), binary_sha256=file_sha(binary),
                  missing_initialization_rejected=dict(argv=missing_argv, returncode=missing,
                      log_sha256=file_sha(out/'missing-initialization.log')),
                  allocated_cpus=cpus, simultaneous_models=3, model_threads=2,
                  scope='128 actual Liberty DFFs under the installed Verilator; all-ones and distinct seeded initial states before first clock, using the exact driver-construction adapter. No full composition or four-state claim.')
    (out/'native-composed-initialization.json').write_text(json.dumps(record, indent=2)+'\n')


def receive_binding(build, bundle):
    """Independent mathematical receiver also checks compiled physical sources."""
    from io_slots import file_sha, slot
    binding = build['native_composed_binding']; path = Path(binding['path'])
    base = path.parent.parents[2]
    with slot(base):
        assert file_sha(path) == binding['sha256']
        record = json.loads(path.read_text()); assert record['schema'] == 'block-v1-native-composed-binding/1'
        assert record['policy'] in ('A', 'C') and record['qualified_hard_macro'] is False
        for filename, sha in record['inputs'].items(): assert file_sha(Path(filename)) == sha
        assert set(record['leaves']) == {'shared109', 'transaction6k'}
        for top, leaf in record['leaves'].items():
            receipt = json.loads(Path(leaf['receipt']).read_text()); assert receipt['passed'] is True
            assert record['inputs'][leaf['receipt']] == file_sha(Path(leaf['receipt']))
            for entry in bundle['files']:
                if entry['path'].startswith('project/rtl/'): assert receipt['inputs'][entry['path']] == entry['sha256']
            for filename, sha in leaf['sealed_outputs'].items():
                assert receipt['outputs'][filename] == sha
                assert record['inputs'][str(Path(leaf['receipt']).parent/filename)] == sha
            formal = json.loads(Path(leaf['formal']).read_text())
            assert formal['passed'] is True and all(formal['checks'].values())
            view = formal['physical_functional_view']; assert view['passed'] is True
            assert record['inputs'][leaf['formal']] == file_sha(Path(leaf['formal']))
            assert record['models'][view['full_view']] == view['full_view_sha256']
            assert formal['full_final_netlist_sha256'] == leaf['original_final_sha256']
            raw = {name:sha for name,sha in leaf['sealed_outputs'].items() if name.endswith('/6_final.v')}
            assert len(raw) == 1 and next(iter(raw.values())) == leaf['original_final_sha256']
            assert all(view['input_sha256'][str(Path(leaf['receipt']).parent/name)] == sha
                       for name, sha in leaf['sealed_outputs'].items() if name.endswith(('/6_final.v', '/6_final.odb')))
        glue = json.loads(Path(record['glue_proof']).read_text()); assert glue['passed'] is True
        glue_receipt = json.loads((Path(record['glue_proof']).parent/'receipt.json').read_text())
        assert glue_receipt['passed'] is True
        assert glue_receipt['outputs']['native-glue.json'] == file_sha(Path(record['glue_proof']))
        assert glue_receipt['outputs']['mapped.v'] == record['models'][record['glue_netlist']]
        assert glue['physical_glue_cell_count'] > 0 and Decimal(glue['glue_area_um2']) > 0
        assert record['models'][record['glue_netlist']] == glue['mapped_netlist_sha256']
        for filename, sha in record['models'].items(): assert file_sha(Path(filename)) == sha
        initialization = json.loads(Path(record['initialization_control']).read_text())
        init_receipt = json.loads((Path(record['initialization_control']).parent/'receipt.json').read_text())
        assert init_receipt['passed'] is True and initialization['passed'] is True
        assert init_receipt['outputs']['native-composed-initialization.json'] == file_sha(Path(record['initialization_control']))
        assert initialization['module_sha256'] == file_sha(Path(__file__))
        assert initialization['library_sha256'] == record['inputs'][record['library']]
        assert initialization['original_mixed_driver_sha256'] == file_sha(Path(record['original_driver']))
        assert Path(record['compiled_driver']).read_text() == adapt_driver(Path(record['original_driver']).read_text())
        assert record['compiled_driver'] in build['command']['argv']
        assert set(record['models']) == {record['glue_netlist'], record['cells_model'],
            *(json.loads(Path(leaf['formal']).read_text())['physical_functional_view']['full_view'] for leaf in record['leaves'].values())}
        assert Path(record['cells_export_script']).read_text() == 'read_liberty -ignore_miss_func -ignore_miss_dir '+record['library']+'\nwrite_verilog -noattr cells.v\n'
        assert set(record['models']) <= set(build['command']['argv'])
        assert '--x-initial' in build['command']['argv'] and '--x-assign' in build['command']['argv']
        assert build['command']['argv'][build['command']['argv'].index('--x-initial')+1] == 'unique'
        assert build['command']['argv'][build['command']['argv'].index('--x-assign')+1] == 'unique'
    return record


def verify(root, out, cpus, run, policy):
    from io_slots import file_sha
    from native_formal import receive
    from native_allocation_group import memory_snapshot
    assert cpus == 24 and policy in ('A', 'C')
    base = out.parents[2]; inputs = {}; leaves = {}; models = []
    control = base/'block-v1-20261027-138/tasks/native-composed-init-control'
    bound = json.loads((control/'receipt.json').read_text()); assert bound['passed'] is True
    path = control/'native-composed-initialization.json'; assert file_sha(path) == bound['outputs'][path.name]
    initialization = json.loads(path.read_text()); assert initialization['passed'] is True
    assert initialization['module_sha256'] == file_sha(Path(__file__))
    def bind(path): inputs[str(path)] = file_sha(path); return inputs[str(path)]
    bind(control/'receipt.json'); bind(path)
    glue = base/'block-v1-20261027-137/tasks/native-glue-map'
    bound = json.loads((glue/'receipt.json').read_text()); assert bound['passed'] is True
    for name in ['native-glue.json', 'mapped.v']: assert bind(glue/name) == bound['outputs'][name]
    glue_proof = json.loads((glue/'native-glue.json').read_text()); assert glue_proof['passed'] is True
    for filename, sha in glue_proof['input_sha256'].items():
        assert bind(Path(filename)) == sha
        if '/project/rtl/' in filename: assert file_sha(root/'project/rtl'/filename.split('/project/rtl/', 1)[1]) == sha
    bind(glue/'receipt.json')
    for top, pipeline in [('shared109', 'native_pipeline_const_protected.json'), ('transaction6k', 'native_pipeline_viaonly.json')]:
        config = json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
        source = base/config['candidate_run']/('tasks/'+config.get('candidate_task_prefix', 'native-run-')+top+'-'+policy.lower())
        receipt = json.loads((source/'receipt.json').read_text()); assert receipt['passed'] is True
        bind(source/'receipt.json')
        prep = base/config['preparation_run']/'tasks/native-prepare'
        results = source/'flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base'
        sealed = {}
        for name in ['6_final.odb', '6_final.v', '6_final.sdc', '6_final.spef']:
            relative = str((results/name).relative_to(source)); sealed[relative] = bind(results/name)
            assert sealed[relative] == receipt['outputs'][relative]
        folder = out/top; folder.mkdir()
        def child_run(argv, log): run(argv, str(folder.relative_to(out)/log), cwd=folder)
        formal = receive(source, receipt, results, top, prep, logic_context=(root, folder, child_run))
        assert formal['passed'] is True and formal['physical_functional_view']['passed'] is True
        proof = folder/'formal.json'; proof.write_text(json.dumps(formal, indent=2)+'\n'); bind(proof)
        view = Path(formal['physical_functional_view']['full_view']); bind(view); models.append(view)
        leaves[top] = dict(receipt=str(source/'receipt.json'), formal=str(proof), pipeline=pipeline,
                           sealed_outputs=sealed, original_final_sha256=sealed[str((results/'6_final.v').relative_to(source))])
    library = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    assert bind(library) == initialization['library_sha256']
    (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(library)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys', '-s', 'cells.ys'], 'cells.log')
    bind(out/'cells.ys')
    models += [glue/'mapped.v', out/'cells.v']
    model_hashes = {str(p): bind(p) for p in models}
    driver = out/'native-mixed.cpp'; source_driver = root/'project/experiments/block_v1/committed_sim.cpp'
    assert bind(source_driver) == initialization['original_mixed_driver_sha256']
    driver.write_text(adapt_driver(source_driver.read_text())); bind(driver)
    # No source RTL for either leaf or memory is passed to this compiler.
    verilator = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    argv = [verilator, '--cc', '--exe', '--build', '-j', str(cpus), '-Wno-fatal', '--top-module', 'shared121',
            '--prefix', 'Vshared121', '--Mdir', str(out/'obj'), '--output-split', '12000', '--output-split-cfuncs', '150',
            '--threads', '4', '--x-initial', 'unique', '--x-assign', 'unique', '-CFLAGS', '-std=c++17 -O2',
            *map(str, models), str(driver)]
    binding_path = out/'native-composed-binding.json'
    record = dict(schema='block-v1-native-composed-binding/1', policy=policy, inputs=inputs, leaves=leaves,
                  models=model_hashes, glue_proof=str(glue/'native-glue.json'), glue_netlist=str(glue/'mapped.v'),
                  initialization_control=str(path), library=str(library), cells_model=str(out/'cells.v'),
                  cells_export_script=str(out/'cells.ys'), original_driver=str(source_driver), compiled_driver=str(driver),
                  glue_area_um2=glue_proof['glue_area_um2'], qualified_hard_macro=False,
                  recovery_and_terminal_epoch_gate_qualified=False, parent_physical_qualified=False)
    binding_path.write_text(json.dumps(record, indent=2)+'\n')
    run(argv, 'build-composed.log')
    binary = out/'obj/Vshared121'; bundle = json.loads((root/'bundle-manifest.json').read_text())
    build = dict(top='shared121', binary=str(binary), binary_sha256=file_sha(binary), source_commit=bundle['source_commit'],
                 source_bundle_sha256=file_sha(root/'bundle-manifest.json'), command=dict(argv=argv),
                 native_composed_binding=dict(path=str(binding_path), sha256=file_sha(binding_path)))
    (out/'build.json').write_text(json.dumps(build, indent=2)+'\n')
    receive_binding(build, bundle)
    inp = base/'block-v1-20261027-004/tasks/fixtures/upstream/input01'
    memory = memory_snapshot()
    parallel = next((n for n in [6, 3, 1] if memory['MemAvailable'] >= n*16*1024**3*1.2), 1)
    assert 4*parallel <= cpus
    def simulate(spec):
        name, initial, seed, stall = spec
        folder = out/(name+'-stall'+str(stall)); folder.mkdir()
        command = [str(binary), *runtime_arguments(inp, folder, stall, initial, seed)]
        started = time.time()
        with (folder/'simulation.log').open('w') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
        (folder/'simulation-command.json').write_text(json.dumps(dict(argv=command, exit=code, seconds=time.time()-started))+'\n')
        manifest = dict(schema='shared121-committed-run/1', suite='mixed-committed', stall=stall, pilot=0,
                        initial_state_mode=initial, runtime_seed=seed, binary_sha256=build['binary_sha256'],
                        build_path=str(out/'build.json'), build_sha256=file_sha(out/'build.json'), source_commit=build['source_commit'],
                        source_bundle_sha256=build['source_bundle_sha256'], input_manifest_sha256=file_sha(inp/'manifest.json'))
        manifest['artifacts'] = [dict(path=p.name, bytes=p.stat().st_size, sha256=file_sha(p)) for p in folder.iterdir() if p.is_file()]
        (folder/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        assert code == 0, str(folder)
        run(['python3', str(root/'project/experiments/block_v1/receive121.py'), '--input', str(inp), '--run', str(folder),
             '--out', str(folder/'received')], folder.name+'-receive.log')
        received = json.loads((folder/'received/receipt.json').read_text())
        assert received['status'] == 'PASS_SHARED121_COMPLETE_INTEGER_COMMITTED_MIXED'
        return dict(name=folder.name, initial_mode=initial, seed=seed, stall=stall, started=started, finished=time.time(),
                    oracle_receipt_sha256=file_sha(folder/'received/receipt.json'), rows=len(received['rows']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
        observed = list(pool.map(simulate, [(n, i, s, stall) for n, i, s in INITIALS for stall in [0, 1]]))
    receive_binding(build, bundle)
    result = dict(schema='block-v1-native-composed-function/1', passed=True, policy=policy, build=build,
                  cases=observed, allocated_cpus=cpus, simultaneous_models=parallel, threads_per_model=4,
                  memory_preflight=memory, per_model_memory_estimate_bytes=16*1024**3,
                  recovery_and_terminal_epoch_gate_qualified=False, parent_physical_qualified=False, qualified_hard_macro=False,
                  scope='Actual sealed C8/S16K and T6K final ODB signal-cell views plus separately mapped/priced glue, complete four-profile mixed oracle in two stall modes and three initial states. No behavioral RAM, rerun synthesis of leaves, full recovery, delay/four-state, parent or macro-boundary qualification.')
    (out/'native-composed-function.json').write_text(json.dumps(result, indent=2)+'\n')
