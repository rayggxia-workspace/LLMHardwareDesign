"""Index the fixed-input scarce-first experiment and its independent checks."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(lines, name):
    return next(x.split('=',1)[1] for x in lines if x.startswith(name+'='))


def obtain(root, job):
    log,=root.glob('*-{}.log'.format(job))
    lines=log.read_text().splitlines()
    return log, lines, Path(value(lines,'run'))


root=Path.cwd()
probe_id, diagnosis_id, *jobs=sys.argv[1:]
previous=root.parent/'hpy-pr276-clean1184.kFNrCO4l'
layout=root/'precheck-final'
fixed={name:sha(layout/name) for name in ('graph.txt','derived-spec.json','lower-evidence.json','access.tsv')}
assert all(sha(previous/'precheck-final'/name)==hash for name, hash in fixed.items())
_,_,probe=obtain(root,probe_id)
options=read(probe/'options.json')
near_id='118291'
_,_,near_probe=obtain(root,near_id)
near_options=read(near_probe/'options.json')
allowed_options={sha(p/'path-options.tsv') for p in (probe,near_probe)}
assert options['nets']==1184 and options['targets']==1674 and sum(options['sampled_corridors'].values())==1674
assert options['initial_top']=={'M11':0,'M12':0,'V11':0}
assert options['initial_top']==read(layout/'access-summary.json')['empty_top_segments']
runs=[]
routes={}
for j in jobs:
    log, lines, folder=obtain(root,j)
    result=read(folder/'routes.json')
    assert result['geometry_check']['passed'] and result['geometry_check']['nets_checked']==len(result['routes'])
    assert len(result['routes'])+len(result['failed'])==1184 and not set(result['routes'])&set(result['failed'])
    assert sha(folder/'graph.txt')==fixed['graph.txt']
    assert result['context']['lower_escape_overlay_sha256']==fixed['lower-evidence.json']
    clean='clean nets=1184 M11=0 M12=0 V11=0 restored=0' in lines
    if clean:
        assert sha(folder/'path-options.tsv') in allowed_options
        assert any(x.startswith('scarce_first attempted=1674 ') for x in lines)
    else:
        assert Path(value(lines,'this_round_seed')).parent==root
    routes[j]=result
    runs.append({'job':j,'routed':len(result['routes']),'unrouted':len(result['failed']),'source':str(folder),
                 'zero_start':clean,'routes_json_sha256':sha(folder/'routes.json'),'paths_sha256':sha(folder/'paths.txt'),
                 'log':str(log),'independent_geometry':result['geometry_check'],'families':result['evidence'],
                 'trace':[x for x in lines if x.startswith(('params=','clean nets=','reserved_pins=',
                     'scarce_first ','before_transaction=','repair tried=','done ','this_round_seed=',
                     'group initial=','selection candidates=','close initial=','retained_this_round='))]})
assert sum(r['zero_start'] for r in runs)>=3
best=runs[0]
assert best['routed']==max(r['routed'] for r in runs)
log, lines, diag=obtain(root,diagnosis_id)
assert value(lines,'routing')==best['source']
diagnosis=read(diag/'diagnosis.json')
with (diag/'unresolved.tsv').open() as f:
    pending=list(csv.DictReader(f,delimiter='\t'))
assert len(pending)==len({r['net_id'] for r in pending})==best['unrouted']==diagnosis['unresolved']
assert set(routes[best['job']]['failed'])=={x['net_id'] for x in pending}
assert Counter(x['cause'] for x in pending)==diagnosis['breakdown']
baseline_log,=previous.glob('last-118129.log')
baseline_dir=Path(value(baseline_log.read_text().splitlines(),'run'))
baseline=read(baseline_dir/'routes.json')
assert baseline['geometry_check']['passed'] and len(baseline['routes'])==849
basenet, finalnet=set(baseline['routes']),set(routes[best['job']]['routes'])
assert (basenet|set(baseline['failed']))==(finalnet|{x['net_id'] for x in pending})
job_ids=[probe_id,near_id,diagnosis_id,*jobs]
accounting=subprocess.check_output(['sacct','-nX','-P','-j',','.join(job_ids),'-o',
                                     'JobID,State,ExitCode,Elapsed'],universal_newlines=True)
slurm={v[0]:dict(zip(('state','exit','elapsed'),v[1:])) for v in (x.split('|') for x in accounting.splitlines())}
assert all(slurm[j]['state']=='COMPLETED' and slurm[j]['exit']=='0:0' for j in set(job_ids))
print(json.dumps({'server':str(root),'fixed_input_sha256':fixed,
                  'placement_sha256':read(layout/'lower-evidence.json')['placement_sha256'],
                  'probe':{'job':probe_id,'result':options,'options_sha256':sha(probe/'path-options.tsv')},
                  'short_branch_probe':{'job':near_id,'result':near_options,'options_sha256':sha(near_probe/'path-options.tsv')},
                  'best':best['job'],'routing_runs':runs,'slurm':slurm,
                  'baseline_849':{'added':len(finalnet-basenet),'lost':len(basenet-finalnet),
                                  'common':len(finalnet&basenet),'job':'118129','used_as_seed':False},
                  'diagnosis':{'job':diagnosis_id,'log':str(log),'tsv':str(diag/'unresolved.tsv'),
                               'tsv_sha256':sha(diag/'unresolved.tsv'),'result':diagnosis}},indent=2,sort_keys=True))
