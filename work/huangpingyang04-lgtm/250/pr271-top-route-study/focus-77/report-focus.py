"""Cross-check the final board, the 77 focus nets, and the unchanged inputs."""
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


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f,delimiter='\t'))


root=Path.cwd()
diag_job,*job_ids=sys.argv[1:]
prior=root.parent/'hpy-pr276-scarce1184.fOd5vRE3'
layout=root/'focus-layout'
spec=read(layout/'derived-spec.json')
old_spec=read(prior/'precheck-final/derived-spec.json')
fanout=read(layout/'fanout.json')
ledger=read(layout/'lower-evidence.json')
assert spec['nets']==old_spec['nets'] and len(spec['nets'])==1184
assert spec['technology']==old_spec['technology'] and spec['obstacles']==old_spec['obstacles']
assert ledger['placement_sha256']==read(prior/'precheck-final/lower-evidence.json')['placement_sha256']
changed={p for p in set(spec['pins'])|set(old_spec['pins']) if spec['pins'].get(p)!=old_spec['pins'].get(p)}
assert changed=={fanout['pin'],'frozen_escape_source/'+fanout['pin']}
assert sha(layout/'paths.txt')==fanout['paths_sha256']


def job(number):
    log,=root.glob('*-{}.log'.format(number))
    lines=log.read_text().splitlines()
    directory=Path(next(line[4:] for line in lines if line.startswith('run=')))
    return log,lines,directory


_,_,old_plan=job('118338')
_,_,new_plan=job('118345')
old_entries=rows(old_plan/'reservations.tsv')
entries={int(r['net']):r for r in rows(new_plan/'reservations.tsv')}
vias={int(r['net']):r for r in rows(new_plan/'v11-audit.tsv')}
assert Counter(r['status'] for r in old_entries)=={'reserved':69,'fanout_needed':1}
assert len(entries)==70 and all(r['status']=='reserved' for r in entries.values())
assert len(vias)==7 and all(0<int(r['dx'])+int(r['dy'])<21 for r in vias.values())
assert not set(entries)&set(vias)
targets=set(entries)|set(vias)
baseline=read(prior/'mix.2pnpdNhU/routes.json')
assert baseline['geometry_check']['passed'] and len(baseline['routes'])==825
assert all(spec['nets'][i]['id'] in baseline['failed'] for i in targets)

runs=[]; routes={}
for number in job_ids:
    log,lines,directory=job(number)
    result=read(directory/'routes.json')
    assert result['geometry_check']['passed'] and result['geometry_check']['nets_checked']==len(result['routes'])
    assert len(result['routes'])+len(result['failed'])==1184 and not set(result['routes'])&set(result['failed'])
    assert sha(directory/'graph.txt')==sha(layout/'graph.txt')
    assert result['context']['lower_escape_overlay_sha256']==sha(layout/'lower-evidence.json')
    clean='clean nets=1184 M11=0 M12=0 V11=0 restored=0' in lines
    if not clean:
        parent=Path(next(l.split('=',1)[1] for l in lines if l.startswith('this_round_seed=')))
        assert parent.parent==root
    routes[number]=result
    t={i for i in targets if spec['nets'][i]['id'] in result['routes']}
    runs.append({'job':number,'directory':str(directory),'routed':len(result['routes']),'unrouted':len(result['failed']),
                 'zero_start':clean,'focus_entry_routed':len(t&set(entries)),'focus_geometry_routed':len(t&set(vias)),
                 'paths_sha256':sha(directory/'paths.txt'),'routes_sha256':sha(directory/'routes.json'),
                 'verification':result['geometry_check'],'log':str(log),
                 'trace':[x for x in lines if x.startswith(('params=','clean nets','focus_early','before_transaction',
                           'scarce_first','repair tried=','done ','group initial=','this_round_seed=',
                           'close initial=','retained_this_round='))]})
best=runs[0]
assert best['routed']==max(x['routed'] for x in runs)
_,lines,diagnostic=job(diag_job)
assert 'routing='+best['directory'] in lines
summary=read(diagnostic/'diagnosis.json')
pending={r['net_id']:r for r in rows(diagnostic/'unresolved.tsv')}
assert set(pending)==set(routes[best['job']]['failed']) and len(pending)==summary['unresolved']==best['unrouted']
assert Counter(x['cause'] for x in pending.values())==summary['breakdown']
summary['focus_remaining']={}
for focus_label,group in [('entry',entries),('geometry',vias)]:
    summary['focus_remaining'][focus_label]=dict(Counter(pending[n]['cause'] for n in (spec['nets'][i]['id'] for i in group) if n in pending))
with (root/'focused-nets.tsv').open('w') as stream:
    table=csv.writer(stream,delimiter='\t',lineterminator='\n')
    table.writerow(['net_id','pin','category','reserved_m11','isolated_v11_repair','first_v11_dx_dbu','first_v11_dy_dbu','final_status','remaining_cause'])
    for i in sorted(targets):
        n=spec['nets'][i]; group=entries if i in entries else vias
        category='entry' if i in entries else 'geometry'
        apart=group[i]; pin=(n['driver'],*n['sinks'])[int(apart['pin'])]
        failure=pending.get(n['id'])
        table.writerow([n['id'],pin,category,apart.get('status',''),apart.get('legal_after_v11_repair',''),
                        '' if i not in vias else int(vias[i]['dx'])*400,
                        '' if i not in vias else int(vias[i]['dy'])*400,
                        'unrouted' if failure else 'routed',failure['cause'] if failure else 'none'])
all_jobs=list(dict.fromkeys(['118338','118344','118345',diag_job,*job_ids]))
a=subprocess.check_output(['sacct','-nX','-P','-j',','.join(all_jobs),'-o','JobID,State,ExitCode,Elapsed'],universal_newlines=True)
slurm={cols[0]:dict(zip(('state','exit','elapsed'),cols[1:])) for cols in (line.split('|') for line in a.splitlines())}
assert all(slurm[j]['state']=='COMPLETED' and slurm[j]['exit']=='0:0' for j in all_jobs)
previous,now=set(baseline['routes']),set(routes[best['job']]['routes'])
print(json.dumps({'input_sha256':{p:sha(layout/p) for p in ('graph.txt','derived-spec.json','lower-evidence.json','access.tsv')},
                  'placement_sha256':ledger['placement_sha256'],'fanout':fanout,'reservations':{'job':'118345','assigned':70,
                     'before_fanout':69,'paths_sha256':sha(new_plan/'entry.paths'),'tsv_sha256':sha(new_plan/'reservations.tsv')},
                  'isolated_geometry':{'job':'118345','tested':7,'solved':sum(int(r['legal_after_v11_repair']) for r in vias.values()),
                     'tsv_sha256':sha(new_plan/'v11-audit.tsv')},
                  'best_job':best['job'],'routing_jobs':runs,'slurm':slurm,'cause_job':diag_job,'cause_summary':summary,
                  'unresolved_sha256':sha(diagnostic/'unresolved.tsv'),'focus_sha256':sha(root/'focused-nets.tsv'),
                  'baseline_825':{'common':len(previous&now),'gained':len(now-previous),'lost':len(previous-now),
                                  'used_as_seed':False}},indent=2,sort_keys=True))
