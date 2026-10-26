"""Reproducible offline experiment suite. All raw DAGs/plans stay in new output.

python -B -m project.analysis.workload_mapping.search_experiment --output-dir
.local/runs/search01 --suite full --workers 4 --export
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from .cli import new_output, code_hashes
from .core import canonical
from .search import Hardware, solve, exact, Infeasible
from .search_check import replay, export
from .search_model import transformer
from .test_search import micro

REPO=Path(__file__).resolve().parents[3]


def write(path,data):
    path.write_bytes(canonical(data))


def cases(suite):
    if suite=='smoke':
        return [dict(id='tiny',prefill=8,decode=2,layers=1,rows=4,columns=4,tiny=True,
                     capacity=1024,category='smoke')]
    result=[]
    for p,d,l in [(128,16,1),(512,16,1),(128,64,1),(128,16,4)]:
        for cap in (512,1024,2048):
            result.append(dict(id=f'p{p}-d{d}-l{l}-k{cap}',prefill=p,decode=d,layers=l,
                               rows=32,columns=128,capacity=cap*1024,category='main'))
    for r,c in [(16,64),(64,128)]:
        for cap in (512,1024):
            result.append(dict(id=f'tile-r{r}-c{c}-k{cap}',prefill=128,decode=16,layers=1,
                               rows=r,columns=c,capacity=cap*1024,category='tiling'))
    # Same workload/inventory/search shortlist, changing one search ingredient.
    for name,settings in [('no-future-bound',dict(initial_bound=False)),
                          ('depth1-width1',dict(depth=1,width=1)),
                          ('depth3-width4',dict(depth=3,width=4))]:
        result.append(dict(id='ablate-'+name,prefill=128,decode=16,layers=1,rows=32,
                           columns=128,capacity=512*1024,category='ablation',settings=settings))
    return result


def cell(args):
    config,root,do_export=args
    root=Path(root)/config['id'];root.mkdir()
    start=time.perf_counter()
    w=transformer(**{k:config[k] for k in ['prefill','decode','layers','rows','columns']},tiny=config.get('tiny',False))
    h=Hardware(capacity=config['capacity'],vector_capacity=1024 if config.get('tiny') else 524288)
    write(root/'workload.json',w.document())
    write(root/'hardware.json',asdict(h))
    # A constructive infeasibility witness, not a failed algorithm silently
    # excluded from comparison. No scheduling can shrink a pinned task's set.
    for t in w.tasks:
        footprint=sum(w.values[v].size for v in t.reads)+w.values[t.output].size+t.workspace+h.control_bytes
        if all(footprint>h.cap(r) for r in h.resources(t)):
            science=dict(config=config,status='infeasible',task=t.id,working_set=footprint,
                         capacities={r:h.cap(r) for r in h.resources(t)},workload_sha256=w.digest())
            write(root/'science.json',science)
            return science,dict(case=config['id'],seconds=time.perf_counter()-start)
    science=dict(config=config,status='pass',workload_sha256=w.digest(),results={})
    runtime=dict(case=config['id'],algorithms={})
    settings=dict(width=3,depth=2,frontier=4)
    settings.update(config.get('settings',{}))
    for method in ('fixed','greedy','beam'):
        plan=solve(w,h,method,**settings)
        proof=replay(w,h,plan)
        proof['expanded']=plan['expanded']
        proof['placements']={r:sum(e['resource']==r for e in plan['plan']) for r in h.names}
        proof['search_budget']=plan['search_budget']
        science['results'][method]=proof
        elapsed=plan.pop('algorithm_seconds')
        runtime['algorithms'][method]=dict(seconds=elapsed)
        write(root/(method+'.plan.json'),plan)
        if do_export and method=='beam':
            graph,blocks,mapped=export(w,h,plan)
            assert sum(c['transport']['wire_bytes'] for c in mapped['mapping_request']['communication'])==plan['wire_bytes']
            write(root/'graph.json',graph);write(root/'blocks.json',blocks)
            write(root/'mapping_request.json',mapped['mapping_request'])
            science['public_adapter_roundtrip']='pass; producer plus independent consumer'
    a,b,c=[science['results'][m]['wire_bytes'] for m in ('fixed','greedy','beam')]
    science['reductions_percent']=dict(greedy_vs_fixed=100*(a-b)/a,beam_vs_fixed=100*(a-c)/a,
                                       beam_vs_greedy=100*(b-c)/b)
    science['search_settings']=settings
    write(root/'science.json',science);write(root/'runtime.json',runtime)
    return science,runtime


def run(output,suite='full',workers=1,export_contract=False):
    if type(workers) is not int or workers<1 or workers>int(os.environ.get('SLURM_CPUS_PER_TASK','4')):
        raise ValueError('workers exceed allocation or supported local bound')
    out=new_output(REPO,output)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain','--','project/analysis/workload_mapping'],cwd=REPO,text=True)
    if dirty.strip():raise ValueError('commit clean research source before qualification')
    hashes=code_hashes()
    configs=cases(suite)
    target='tiny' if suite=='smoke' else 'p128-d16-l1-k512'
    tasks=[(config,str(out),export_contract and config['id']==target) for config in configs]
    if workers==1:
        results=list(map(cell,tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results=list(pool.map(cell,tasks))
    exact_results=[]
    for seed in range(12):
        w=micro(seed);h=Hardware(capacity=1024,matrices=1)
        optimum=exact(w,h)
        observed={m:solve(w,h,m,width=3,depth=2,frontier=4) for m in ('fixed','greedy','beam')}
        for record in observed.values():replay(w,h,record,False)
        exact_results.append(dict(seed=seed,optimum=optimum,
            costs={m:r['wire_bytes'] for m,r in observed.items()},
            gaps_percent={m:100*(r['wire_bytes']-optimum)/optimum for m,r in observed.items()}))
    main=[x[0] for x in results if x[0]['config']['category']=='main' and x[0]['status']=='pass']
    totals={m:sum(c['results'][m]['wire_bytes'] for c in main) for m in ('fixed','greedy','beam')}
    reductions={}
    if main:
        a,b,c=[totals[m] for m in ('fixed','greedy','beam')]
        reductions=dict(greedy_vs_fixed=100*(a-b)/a,beam_vs_fixed=100*(a-c)/a,beam_vs_greedy=100*(b-c)/b)
    science=dict(schema='workload-search-experiment/1',suite=suite,
        scope='serial communication optimization under synthetic resource/kernels; no real-model numerical or physical/time proof',
        cases=[x[0] for x in results],exact_small_instances=exact_results,
        aggregate=dict(main_cases=len(main),wire_bytes=totals,reductions_percent=reductions,
            beam_wins_vs_greedy=sum(x['results']['beam']['wire_bytes']<x['results']['greedy']['wire_bytes'] for x in main),
            beam_losses_vs_greedy=sum(x['results']['beam']['wire_bytes']>x['results']['greedy']['wire_bytes'] for x in main)),
        physical='blocked',end_to_end_seconds=None)
    if hashes!=code_hashes():raise ValueError('source/input changed during run')
    write(out/'science.json',science)
    write(out/'runtime.json',dict(source_commit=commit,workers=workers,cells=[x[1] for x in results]))
    write(out/'receipt.json',dict(schema='workload-search-receipt/1',source_commit=commit,
        source_clean=True,source_sha256=hashes,science_sha256=hashlib.sha256((out/'science.json').read_bytes()).hexdigest(),
        checked_cases=len(configs),exact_cases=12,independent_replay='every legal algorithm plan',
        original_fixture_policy='unchanged; run existing validate_delivery separately',network='no acquisition or SSH in research code'))
    print(json.dumps(dict(status='pass',cases=len(configs),aggregate=science['aggregate'],
                          science_sha256=hashlib.sha256((out/'science.json').read_bytes()).hexdigest())),flush=True)
    return science


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',required=True)
    p.add_argument('--suite',choices=['smoke','full'],default='full')
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--export',action='store_true')
    args=p.parse_args()
    run(args.output_dir,args.suite,args.workers,args.export)


if __name__=='__main__':main()
