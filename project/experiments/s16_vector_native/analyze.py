"""Read-only postprocessing of recovered evidence; does not run local EDA."""
import argparse,hashlib,importlib.util,json,math,re,shutil,sys
from copy import deepcopy
from pathlib import Path

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(c,m):
    if not c:raise ValueError(m)
def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    records={};results={};verified=0
    expected={41:'d1aa084436b2a25e06e775dfc304ddc929293830dcecde3239f419a8396a6bf0',
              42:'3ca4cb4f9f40e4f3c8771cb0460711aa350a368ea1e047da7291452cf0104e5b',
              43:'3a4bb994cd5fa35a77168f135645a033bb4b9f0df429650bf2d9d9dbd37a4f8a'}
    for n,h in expected.items():
        r=a.runs/f'run{n}'/'receipts';col=json.loads((r/'collection.json').read_bytes())
        require(sha(r.parent/'receipts.tar')==h,'archive SHA')
        for name,item in col['files'].items():
            require(sha(r/name)==item['sha256'] and (r/name).stat().st_size==item['bytes'],'received SHA '+name);verified+=1
        d=json.loads((r/'results/result.json').read_bytes());require(d['passed'],'run failed');results[n]=d
        records[str(n)]={'job':d['job'],'source_commit':d['source_commit'],'received_files':len(col['files']),
            'receipts_sha256':h,'result_sha256':sha(r/'results/result.json'),
            'server_directory':f'/public/home/yuzelu/Melodydt/issue247-area-speed/run{n}',
            'tools':d['tools'],'sacct':(r/'sacct.txt').read_text(),
            'files':col['files']}
        for filename in ['inputs.json','source-files.sha256','input-files.sha256','output-files.sha256','tools.sha256','sacct.txt']:
            target=a.out/f'run{n}'/filename;target.parent.mkdir(exist_ok=True);shutil.copyfile(r/filename,target)
    native=results[43];cal=results[41];model=results[42]
    rtl={k:v for k,v in native['source_sha256'].items() if k.startswith('project/rtl/')}
    require(all(cal['source_sha256'][k]==v for k,v in rtl.items()),'RTL changed after calibration')
    require(native['functional_passed'] and native['default_exact_pairs']==3,'native gates')
    native_summary={'source_commit':native['source_commit'],'calibration_identical_production_files':len(rtl),
        'default_exact_pairs':3,'tests':{},'area':native['area'],'native_full_model_tokens_per_second':None,
        'physical_clock_qualified':False}
    for name,test in native['tests'].items():
        require(test['passed'] and len(test['runs'])==3,'three-seed tests')
        native_summary['tests'][name]=[]
        for run_index,run in enumerate(test['runs']):
            f=a.runs/'run43/receipts/results'/run['log'];require(sha(f)==run['log_sha256'],'native log SHA')
            parsed=[]
            for line in f.read_text().splitlines():
                if line.startswith(('NEXP_FULL_U ','NEXP_COMPUTE ','E_U_MEASURE ','E_PIPE_MEASURE ')):
                    parsed.append({'prefix':line.split()[0],**{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}})
            require(parsed==run['measurements'],'native measurements/log mismatch')
            item={k:v for k,v in run.items() if k in ['seed','checks','log','log_sha256']}
            item['measurements_count']=len(parsed)
            if run_index==0:
                item['selected_measurements']=[x for x in parsed if x['prefix'] in ['NEXP_COMPUTE','E_PIPE_MEASURE'] or x.get('tag')==0x4e583136]
            native_summary['tests'][name].append(item)
    old=[x for x in native['tests']['bridge-u']['runs'][0]['measurements'] if x['prefix']=='E_U_MEASURE']
    new=[x for x in native['tests']['bridge-pipeline-u']['runs'][0]['measurements'] if x['prefix']=='E_U_MEASURE']
    require(len(old)==len(new)==128,'full U coverage')
    require(all({k:v for k,v in x.items() if k not in ['pipe','cycles']}=={k:v for k,v in y.items() if k not in ['pipe','cycles']} for x,y in zip(old,new)),'matched work')
    full=[]
    for extra in [0,1]:
        for legal in [True,False]:
            xs=[x for x in old if x['extra']==extra and (x['op']<14)==legal]
            ys=[x for x in new if x['extra']==extra and (x['op']<14)==legal]
            before=sum(x['cycles'] for x in xs);after=sum(x['cycles'] for x in ys)
            full.append(dict(extra=extra,legal=legal,count=len(xs),before=before,after=after,speedup_percent=(before/after-1)*100))
    native_summary['full_U_totals']=full
    native_summary['changed_U_cases']=[dict(before=x,after=y) for x,y in zip(old,new) if x['cycles']!=y['cycles']]
    native_summary['full_U_operation_cycles']=[dict(op=x['op'],extra=x['extra'],sources=x['sources'],before=x['cycles'],after=y['cycles']) for x,y in zip(old,new) if x['index']%256==0]
    prior=json.loads((a.runs/'run35/receipts/results/result.json').read_bytes())
    modeldir=Path(__file__).resolve().parent.parent/'s16_vector_model';sys.path.insert(0,str(modeldir))
    spec=importlib.util.spec_from_file_location('s16_model_runner',modeldir/'run.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    table=[];negative=0;baseline=0
    for c in model['cases']:
        f=a.runs/'run42/receipts/results'/c['log'];require(sha(f)==c['log_sha256'],'model log SHA')
        rows=[json.loads(line[7:]) for line in f.read_text().splitlines() if line.startswith('RESULT ')]
        require(len(rows)==1 and rows[0]==c['result'],'model result/log mismatch');row=rows[0]
        ref=next(x['result'] for x in prior['cases'] if x['optimization']=='base' and all(x[k]==c[k] for k in ['workload','profile','dual_ports']))
        mod.check(row,ref,c['case'])
        if c['case']=='base':baseline+=1
        for field in c['negative_checks']:
            bad=deepcopy(row);bad[field]+=1
            try:mod.check(bad,ref,c['case'])
            except ValueError:negative+=1
            else:raise ValueError('tamper accepted')
        table.append({k:c[k] for k in ['case','workload','profile','dual_ports','command','log','log_sha256']}|
            {'tokens_per_second':row['tokens_per_second'],'ticks':row['ticks'],'tokens':row['tokens'],
             'speedup_percent':(row['tokens_per_second']/ref['tokens_per_second']-1)*100,
             'spans_ticks':row['spans_ticks'],'vector_work_ticks':row['vector_work_ticks'],
             'optimization':{k:row['optimization_sweep'][k] for k in ['native_S16','vector_lanes','vector_old','vector_new','nexp_old','nexp_new']},
             'read_bus_bytes':row['read_bus_bytes'],'write_bus_bytes':row['write_bus_bytes']})
    require(len(table)==32 and negative==160 and baseline==8,'model coverage')
    result=dict(passed=True,verified_received_files=verified,model_cases=32,baseline_exact=8,negative_checks=160,
        model_scope=model['scope'],calibration=model['profile'],native=native_summary,model=table)
    for filename,value in [('analysis.json',result),('evidence-index.json',records)]:
        (a.out/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'files':verified,'model_cases':32,'baseline_exact':8,'negative_checks':160,'full_U_totals':full}))
if __name__=='__main__':main()
