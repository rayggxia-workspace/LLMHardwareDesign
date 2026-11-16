"""Produce a compact proof index from this clean run and its independent diagnostics."""
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


def field(log, name):
    return next(x.split('=',1)[1] for x in log if x.startswith(name+'='))


root=Path.cwd()
diagnosis_job,*job_ids=sys.argv[1:]
input_dir=root/'precheck-final'
before=read(root/'precheck-first/access-summary.json')
after=read(input_dir/'access-summary.json')
overlay=read(input_dir/'lower-evidence.json')
native=read(root/'native-audit.json')
assert after['nets']==1184 and before['terminals']==after['terminals']==2858
assert before['prior_44_checked']==after['prior_44_checked']==44
assert after['empty_top_segments']=={'M11':0,'M12':0,'V11':0}
entries=[]
clean_counts=0
for job in job_ids:
    log,=root.glob('*-{}.log'.format(job))
    lines=log.read_text().splitlines()
    run=Path(field(lines,'run'))
    result=read(run/'routes.json')
    paths=run/'paths.txt'
    assert result['geometry_check']['passed'] and len(result['routes'])==result['geometry_check']['nets_checked']
    assert len(result['routes'])+len(result['failed'])==1184
    assert result['context']['lower_escape_overlay_sha256']==sha(input_dir/'lower-evidence.json')
    assert sha(run/'graph.txt')==sha(input_dir/'graph.txt')
    clean='clean nets=1184 M11=0 M12=0 V11=0 restored=0' in lines
    clean_counts+=clean
    entries.append({'job':job,'log':str(log),'run':str(run),'routed':len(result['routes']),
                    'unresolved':len(result['failed']),'geometry':result['geometry_check'],'paths_sha256':sha(paths),
                    'zero_start':clean,'trace':[x for x in lines if x.startswith(('params=','clean nets=',
                      'this_round_seed=','candidate_source=','trunks placed=','short_branches','complete_before_repair=',
                      'reservations ','repair tried=','group initial=','selection candidates=','close initial=','done '))],
                    'families':result['evidence']})
assert clean_counts>=3
best=entries[0]
assert best['routed']==max(x['routed'] for x in entries)
diagnostic_log,=root.glob('final-diagnose-{}.log'.format(diagnosis_job))
lines=diagnostic_log.read_text().splitlines()
assert field(lines,'routing')==best['run']
diag=Path(field(lines,'run'))
stats=read(diag/'diagnosis.json')
assert stats['routed']==best['routed'] and stats['unresolved']==best['unresolved']
with (diag/'unresolved.tsv').open() as f:
    ids={r['net_id']:r['cause'] for r in csv.DictReader(f,delimiter='\t')}
assert len(ids)==best['unresolved'] and Counter(ids.values())==stats['breakdown']
old_file=root.parent/'hpy-pr276-toponly.rPq68zlF/causes.m5Ba0Tql/causes.tsv'
with old_file.open() as f:
    prior=[int(r['index']) for r in csv.DictReader(f,delimiter='\t') if r['after'] in ('driver_access','sink_access')]
nets=read(input_dir/'derived-spec.json')['nets']
previously_access={nets[i]['id'] for i in prior}
assert len(previously_access)==44
jobs=list(dict.fromkeys([*job_ids,diagnosis_job,'118042','118051','118053','118054','118055','118056','118057','118060','118061','118075','118102','118108']))
raw=subprocess.check_output(['sacct','-nX','-P','-j',','.join(jobs),'-o','JobID,State,ExitCode,Elapsed'],universal_newlines=True).splitlines()
slurm={parts[0]:dict(zip(('state','exit','elapsed'),parts[1:])) for parts in (x.split('|') for x in raw)}
assert all(slurm[j]['state']=='COMPLETED' and slurm[j]['exit']=='0:0' for j in jobs)
before.pop('focus'); after.pop('focus')
print(json.dumps({'server_root':str(root),'input':{'before_fanout':before,'after_fanout':after,
 'native_terminal_ownership':native,'placement_sha256':overlay['placement_sha256'],
 'graph_sha256':sha(input_dir/'graph.txt'),'access_tsv_sha256':sha(input_dir/'access.tsv'),
 'spec_sha256':sha(input_dir/'derived-spec.json'),'fanout':overlay['clean_1184_fanout']},
 'comparison_870':{'job':'116910','used_as_seed':False,'previous_access_failures':44,
     'now_routed':len(previously_access-set(ids)),'still_unresolved_by_current_cause':dict(Counter(ids[n] for n in previously_access&set(ids)))},
 'best_job':best['job'],'routing_runs':entries,'slurm':slurm,'cut_screen':{'job':'118108',**read(root/'cut-scan.json')},'diagnostics':{'job':diagnosis_job,
     'path':str(diag/'unresolved.tsv'),'sha256':sha(diag/'unresolved.tsv'),'summary':stats}},sort_keys=True,indent=2))
