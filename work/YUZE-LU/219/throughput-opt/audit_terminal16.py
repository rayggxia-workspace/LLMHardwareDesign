"""Independently associate collected real-value programs with selected loops."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser()
    for name in ('results','ir','plan','regions','output'):p.add_argument(name,type=Path)
    a=p.parse_args();sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
    from native_pointwise import execute
    from resident_model_boundaries import boundary_program
    from resident_replay import replay
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    cold=read(a.results/'resident-model-loops-terminal-r16/generated/report.json')
    folder=a.results/'resident-continuation-model-terminal-r16';warm=read(folder/'generated/report.json')
    boundary=a.results/'resident-boundary-program-terminal-r16';br=read(boundary/'generated/report.json')
    ir=read(a.ir);plan=read(a.plan);actions={x['id']:x for x in ir['resident_actions']};expected={}
    for row in plan['tasks']:
        if row['id'] not in actions:continue
        b=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding'])
        recipe=ir['resident_recipes'][b['resident_region']['recipe']]
        expected[tuple(recipe['primitives'])]=recipe
    if not warm['passed'] or not br['passed'] or not cold['passed']:raise ValueError('terminal report failed')
    if not {sha(a.ir),sha(a.plan)}<=set(warm['inputs_sha256'].values()):raise ValueError('terminal selected inputs differ')
    if len(warm['samples'])!=3 or len(br['samples'])!=3:raise ValueError('terminal sample count differs')
    for gold,w,b in zip(cold['samples'],warm['samples'],br['samples']):
        for actual in (w,b):
            if (actual['ids']!=gold['ids'] or actual['logits_raw_sha256']!=gold['logits_raw_sha256'] or
                actual['relative_l2']!=gold['relative_l2'] or not actual['top1_equal']):
                raise ValueError('terminal original integer/HF result differs')
        if not w['bit_exact_to_original'] or not w['resident']['passed']:raise ValueError('terminal loop replay failed')
        loops=w['resident']['loops']
        if len(loops)!=len(expected) or {tuple(x['primitives']) for x in loops}!=set(expected):
            raise ValueError('terminal selected loop association differs')
        for row in loops:
            r=expected[tuple(row['primitives'])]
            if (not row['continued'] or row['elements']!=r['loop']['elements'] or
                row['native_operations']!=row['elements']*len(r['graph']['operations']) or
                row['external_words']!=r['continuation_loop']['totals']['external_words']):
                raise ValueError('terminal finite-S loop work/traffic differs')
    if sha(a.regions) not in br['inputs_sha256'].values():raise ValueError('terminal boundary native source differs')
    survey=read(boundary/'generated/timed-survey.json');timing=read(boundary/'generated/qualification.json')
    graphs=[g for r in read(a.regions) for g in r['graphs']]
    fixtures=read(boundary/'generated/actual-boundary-fixtures.json');cases=0
    if len(fixtures)!=br['actual_region_cases'] or len(graphs)!=len(survey['rows']):raise ValueError('terminal boundary extent differs')
    for f in fixtures:
        graph=graphs[f['region_index']];row=survey['rows'][f['region_index']]
        if f['element']!=graph['index']:raise ValueError('terminal boundary element differs')
        inputs={(n,i):v for n,i,v in f['inputs']};gold=execute(graph,inputs)
        for strategy in br['strategies']:
            body=boundary_program(row,strategy,survey['actors'],next(iter(row['programs'].values()))['zero_address'],timing)
            actual=replay(graph,body,inputs)['observed_native_outputs']
            if actual!={n['output']:gold[n['output']] for n in graph['operations']}:
                raise ValueError('terminal actual-value finite-S replay differs')
            cases+=1
    critical={}
    for f,names in ((folder,('resident_records.py','resident_replay.py','resident_loop_replay.py',
                           'resident_continuation.py','verify_resident_continuation.py','resident_bindings.py',
                           'verify_resident_bindings.py','resident_model_loops.py','native_pointwise.py','resident_timing.py','wide_program.py')),
                    (boundary,('resident_model_boundaries.py','resident_survey.py','resident_records.py','resident_replay.py','resident_timing.py','native_pointwise.py','wide_program.py'))):
        receipt=read(f/'receipt.json')
        for name in names:
            data=(Path('project/experiments/block_synthesis')/name).read_text(encoding='utf-8').encode()
            if hashlib.sha256(data).hexdigest()!=receipt['source_sha256'][name]:raise ValueError('terminal critical source changed '+name)
        critical[f.name]=len(names)
    result={'passed':True,'full_original_integer_samples':3,'selected_continuous_loops':len(expected),
            'elements_per_selected_loop':sorted({r['loop']['elements'] for r in expected.values()}),
            'actual_boundary_fixtures':len(fixtures),'independent_actual_value_program_replays':cases,
            'current_critical_source_matches':critical,
            'report_sha256':{'cold':sha(a.results/'resident-model-loops-terminal-r16/generated/report.json'),
                             'warm':sha(folder/'generated/report.json'),'boundary':sha(boundary/'generated/report.json')},
            'scope':'selected continuous loops inside full original integer graph plus actual-value finite-S boundary programs; not whole-system execution or performance'}
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
