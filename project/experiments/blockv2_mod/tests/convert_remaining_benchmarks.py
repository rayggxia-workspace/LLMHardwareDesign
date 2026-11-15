"""Attempt each catalog graph through the current Algo1 frontend and selector.

This is a coverage experiment, not numerical or TLM acceptance. Each graph runs
in an isolated process. A failing graph must not suppress the remaining results.
Execution is gated by an explicit, evidence-backed Qwen acceptance receipt.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import argparse, json, os, subprocess, sys, traceback

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')

def worker(case_path, output):
    case = json.loads(case_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    stage = 'source_identity'
    result = {'case': case, 'complete_plan': False, 'machine_package_complete': False,
              'TLM_accepted': False, 'scope': 'single decoder-layer graph conversion'}
    def persist():
        save(output / 'result.json', result)
    try:
        actual = digest(case['onnx'])
        result['onnx_sha256'] = actual
        if actual != case['recorded_onnx_sha256']:
            raise ValueError('ONNX differs from catalog source')
        if digest(case['graph_metadata']) != case['graph_metadata_sha256']:
            raise ValueError('graph metadata differs from catalog source')
        stage = 'onnx_import'
        from frontend import import_onnx
        original = import_onnx(Path(case['onnx']))
        result['imported_operations'] = len(original['tasks'])
        stage = 'semantic_recognition'
        from recipe_graph import build as build_graph
        from verify_recipe_graph import verify as verify_graph
        graph = build_graph(original)
        proof = verify_graph(original, graph)
        graphdir = output / 'graph'
        graphdir.mkdir()
        save(graphdir / 'native-recipe-graph.json', graph)
        save(output / 'source-coverage.json', proof)
        result['recipe_kinds'] = dict(Counter(t['kind'] for t in graph['tasks']))
        result['recognition_notes'] = graph.get('recognition_notes', {})
        stage = 'value_layout'
        from value_layout import build as build_layout
        layout = build_layout(graph)
        save(graphdir / 'native-value-layout.json', layout)
        stage = 'operand_lowering'
        from operand_recipes import lower
        from verify_operand_recipes import verify as verify_operands
        recipes = lower(graph, layout)
        save(graphdir / 'native-operand-recipes.json', recipes)
        save(output / 'operand-verification.json', verify_operands(graph, recipes))
        shared = ['--graph-directory', str(graphdir),
                  '--hardware', str(ROOT / 'hardware/blockv2-mod-shared-memory.json'),
                  '--services', str(ROOT / 'hardware/service-controller-contracts.json')]
        for stage, script, args in [
            ('candidate_generation', 'run_macro_graph_frontend.py',
             ['--output', str(output / 'candidates')]),
            ('algo1_selection', 'run_macro_selection.py',
             ['--candidate-directory', str(output / 'candidates'),
              '--output', str(output / 'plan')])]:
            with (output / (stage + '.log')).open('w') as log:
                completed = subprocess.run(
                    [sys.executable, str(ROOT / 'compiler' / script)] + shared + args,
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if completed.returncode:
                raise RuntimeError(stage + ' exited ' + str(completed.returncode) +
                                   '; see ' + stage + '.log')
        plan = json.loads((output / 'plan/plan.json').read_text())
        result.update(complete_plan=True, plan_sha256=plan['plan_sha256'],
                      calls=len(plan['calls']),
                      next_required='product endpoint materialization, elaboration, package and TLM')
        stage = 'selected_plan'
        result['status'] = 'selected_plan_only'
    except Exception as exc:
        result.update(status='gap', error_type=type(exc).__name__, error=str(exc),
                      traceback=traceback.format_exc())
    finally:
        result['last_stage'] = stage
        result['responsibility_scope'] = {
            'source_identity': 'source/provenance',
            'onnx_import': 'Algo1 graph importer',
            'semantic_recognition': 'Algo1 semantic recognizer',
            'value_layout': 'Algo1 tensor layout lowering',
            'operand_lowering': 'Algo1 operand lowering',
            'candidate_generation': 'Algo1 candidate generation; inspect log before attributing a hardware gap',
            'algo1_selection': 'Algo1 selection; inspect log before attributing a hardware gap',
            'selected_plan': 'remaining deployment/evaluation work',
        }[stage]
        persist()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path)
    p.add_argument('--qwen-acceptance', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--worker-case', type=Path, help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.worker_case:
        worker(a.worker_case, a.output)
        return
    if not a.catalog or not a.qwen_acceptance:
        p.error('--catalog and --qwen-acceptance are required')
    acceptance = json.loads(a.qwen_acceptance.read_text())
    if acceptance.get('Qwen_accepted') is not True:
        raise ValueError('Qwen acceptance has not been established')
    evidence = acceptance.get('evidence_sha256')
    if not evidence:
        raise ValueError('acceptance must bind its evidence files')
    for name, expected in evidence.items():
        if digest(name) != expected:
            raise ValueError('Qwen acceptance evidence changed: ' + name)
    catalog = json.loads(a.catalog.read_text())
    if digest(catalog['source_index']) != catalog['source_index_sha256']:
        raise ValueError('benchmark catalog source index changed')
    a.output.mkdir(parents=True, exist_ok=False)
    env = json.loads((ROOT / 'reproducibility/environment.json').read_text())
    child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
                     PYTHONPATH=os.pathsep.join([str(ROOT/'hardware')] +
                                               env['module_roots'] + env['extra_python_roots']))
    from concurrent.futures import ThreadPoolExecutor, as_completed
    cases = []
    for model in catalog['model_layers']:
        for graph in model['graphs']:
            name = model['model_layer'] + '-' + graph['flavor']
            case = dict(graph, model_layer=model['model_layer'],
                        source_scope=model['source_scope'],
                        checkpoint_loaded=model['checkpoint_loaded'])
            cases.append((name, case))
    def run_case(item):
        name, case = item
        casefile = a.output / (name + '.input.json')
        save(casefile, case)
        target = a.output / name
        with (a.output / (name + '.log')).open('w') as log:
            run = subprocess.run([env['python'], '-B', str(Path(__file__).resolve()),
                                  '--worker-case', str(casefile.resolve()),
                                  '--output', str(target.resolve())],
                                 cwd=ROOT, env=child_env, stdout=log, stderr=subprocess.STDOUT)
        receipt = target / 'result.json'
        row = json.loads(receipt.read_text()) if receipt.exists() else {
            'status': 'worker_failure', 'complete_plan': False,
            'error': 'worker returned no result; inspect graph log'}
        row.update(case_name=name, process_exit=run.returncode)
        return row
    rows = []
    workers = min(2, max(1, int(os.environ.get('SLURM_CPUS_PER_TASK', '1'))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_case, item) for item in cases]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            save(a.output / 'summary.json', {
                'schema': 'benchmark-Algo1-conversion/1',
                'catalog_sha256': digest(a.catalog),
                'qwen_acceptance_sha256': digest(a.qwen_acceptance),
                'runner_sha256': digest(__file__),
                'workers': workers,
                'attempted': len(rows), 'expected': len(cases),
                'results': sorted(rows, key=lambda r: r['case_name']),
                'numerical_acceptance': False, 'TLM_acceptance': False})
            print(row['case_name'] + ': ' + row['status'], flush=True)
    if any(r['status'] == 'worker_failure' for r in rows):
        raise SystemExit(2)

if __name__ == '__main__':
    main()
