"""Recover immutable Issue219 evidence, retaining originals and server hashes."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
HOST='yuzelu@10.129.166.172'
NAMES={'plan':'224-preparation-reuse-plan','five':'225-preparation-reuse-five',
       'failed-nine':'226-preparation-reuse-nine','nine':'227-preparation-reuse-nine-ready',
       'audit':'228-preparation-reuse-audit'}


def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def main():
    out=HERE/'results';raw=out/'raw';raw.mkdir(parents=True,exist_ok=True)
    receipts={}
    for key,name in NAMES.items():
        receipt=Path.home()/'AppData/Local/Codex'/('algorithm-fix-'+name+'.json')
        receipts[key]=json.loads(receipt.read_text(encoding='utf-8'))
    files={
        'plan':['generated/summary.json','generated/five-groups-plan.json',
                'generated/nine-groups-count-experiment-plan.json','generated/nine-groups-budget-plan.json',
                'tests.log','whole-plan-audit.json','input.sha256','output.sha256','slurm.log'],
        'five':['generated/report.json','replay.log','build.log','input.sha256','output.sha256','slurm.log'],
        'nine':['generated/report.json','replay.log','build.log','input.sha256','output.sha256','slurm.log'],
        'failed-nine':['input.sha256','slurm.log'],
        'audit':['tests.log','whole-plan-audit.json','static-conflict.json','profile.json','input.sha256','output.sha256','slurm.log']}
    recovered={}
    for key,paths in files.items():
        for name in paths:
            server=receipts[key]['directory']+'/'+name;local=raw/key/name;local.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['scp','-q',HOST+':'+server,str(local)],check=True,timeout=60)
            expected=subprocess.check_output(['ssh',HOST,'sha256sum '+shlex.quote(server)],timeout=30).decode().split()[0]
            digest=hashlib.sha256(local.read_bytes()).hexdigest()
            if digest!=expected:raise ValueError('recovery SHA mismatch '+server)
            recovered[str(local.relative_to(out)).replace('\\','/')]={'sha256':digest,'server':server}
    baseline=json.loads((ROOT/'work/YUZE-LU/219/results/state-cost-v2/plan/summary.json').read_text(encoding='utf-8'))
    new=json.loads((raw/'plan/generated/summary.json').read_text(encoding='utf-8'))
    comparison=[]
    for old,row in zip(baseline['results'],new['results']):
        comparison.append({'scenario':row['scenario'],'old_makespan':old['search_bound'],'new_makespan':row['search_bound'],
            'reduction_fraction':1-row['search_bound']/old['search_bound'],
            'old_external_words':old['external_transfer_words'],'new_external_words':row['external_transfer_words'],
            'traffic_reduction_fraction':1-row['external_transfer_words']/old['external_transfer_words'],
            'old_wires':old['search_wire_cost'],'new_wires':row['search_wire_cost'],
            'old_compile_seconds':old['compile_seconds'],'new_compile_seconds':row['compile_seconds'],
            'old_external_bytes':old['required_external_bytes'],'new_external_bytes':row['required_external_bytes'],
            'equal_wire_budget':row.get('equal_wire_budget')})
    write(out/'comparison.json',comparison);write(out/'plan-summary.json',new)
    for key in ('five','nine'):
        report=json.loads((raw/key/'generated/report.json').read_text())
        if report['status']!='selected_cache_program_passed':raise ValueError('numeric failed '+key)
        for sample in report['samples']:
            if not sample['passed'] or not sample['bit_exact_to_all_spill']:raise ValueError('numeric sample failed')
            for part in [sample['cache'],sample['cache']['preparation']]:
                part['event_count']=len(part.pop('events',[]))
        write(out/(key+'-numeric-summary.json'),report)
    for name in ('tests.log','whole-plan-audit.json','static-conflict.json','profile.json'):
        (out/name).write_bytes((raw/'audit'/name).read_bytes())
    reference=receipts['audit']['source_sha256'];variants={}
    for key,receipt in receipts.items():
        changed=[name for name,sha in reference.items() if name.endswith('.py') and receipt['source_sha256'].get(name)!=sha]
        if changed not in ([],['utilization.py']):raise ValueError('unexpected runtime source change '+str(changed))
        variants[key]=changed
    for name,sha in reference.items():
        current=ROOT/'project/experiments/block_synthesis'/name
        data=current.read_text(encoding='utf-8').encode('utf-8')
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('final source differs '+name)
    jobs=','.join(str(r['job']) for r in receipts.values())
    slurm=subprocess.check_output(['ssh',HOST,'sacct -j '+jobs+' --format=JobID,State,Elapsed,ExitCode,AllocCPUS,Timelimit -P'],timeout=30)
    (out/'slurm.psv').write_bytes(slurm)
    write(out/'receipt.json',{'baseline_pr_head':'1d284bdcb38bc9625c74d6ffeabae151094520b7',
        'implementation_commit':'f0948355e','attempts':{k:{'directory':r['directory'],'job':r['job'],
        'python_source_diff_from_final':variants[k]} for k,r in receipts.items()},
        'source_sha256':reference,'recovered':recovered,
        'note':'only utilization opportunity diagnostic changed after planning; compiler/scheduler/checkers/replay identical; original files retained under ignored raw/'})
    print(json.dumps({'recovered_files':len(recovered),'comparison':comparison}))


if __name__=='__main__':main()
