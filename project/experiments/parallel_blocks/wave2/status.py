"""Lightweight read-only status; compatible with login-node Python 3.6."""
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1])
assert root.parent == Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7')
assert re.fullmatch(r'parallel-blocks-wave2-[0-9]+', root.name)
submission = json.loads((root / 'submission.json').read_text())
def small(path):
    return path.read_text(errors='replace') if path.is_file() and path.stat().st_size < 2*1024*1024 else None
def tail(path):
    if not path.is_file():return None
    with path.open('rb') as f:
        f.seek(max(0,path.stat().st_size-4000))
        return '\n'.join(f.read().decode(errors='replace').splitlines()[-12:])
def command(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    return dict(exit_code=p.returncode,stdout=p.stdout.strip(),stderr=p.stderr.strip())
jobs=[str(s['job_id']) for s in submission['plan'].values() if 'job_id' in s]
if 'audit_job_id' in submission:jobs.append(str(submission['audit_job_id']))
record=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),submission=submission,
    scheduler=command(['sacct','-n','-P','-j',','.join(jobs),'--format=JobIDRaw,JobName%40,State,ExitCode,Elapsed,AllocCPUS,NodeList']),
    resources=command(['sacct','-n','-P','-j',','.join(jobs),'--format=JobIDRaw,Elapsed,AllocCPUS,CPUTimeRAW,TotalCPU,MaxRSS']),
    tasks={},completion_exists=(root/'completion.json').is_file(),completion_sha256=small(root/'completion.sha256'))
for label, stream in submission['plan'].items():
    for spec in stream['tasks']:
        name=spec['name']; base=root/name
        item=dict(spec=spec,stream=label,started=small(base/'started-utc.txt'),finished=small(base/'finished-utc.txt'),
            exit_code=small(base/'exit-code.txt'),hash_exit_code=small(base/'output-hash-exit-code.txt'),log_tail=tail(base/'step.log'))
        validation=small(base/'validation.json')
        if validation:item['validation']=json.loads(validation)
        progress=small(base/'ram-progress.json')
        if progress:item['ram_cases_finished']=len(json.loads(progress))
        progress=small(base/'view-progress.json')
        if progress:item['views_finished']=list(json.loads(progress))
        if spec['kind']=='physical':
            nickname='parallel_'+spec['case'].replace('-','_')
            logs=base/'flow/logs/nangate45'/nickname/'base'
            results=base/'flow/results/nangate45'/nickname/'base'
            metrics={}
            logfiles=sorted(logs.glob('*.log'),key=lambda p:p.stat().st_mtime)
            if logfiles:
                recent=logfiles[-1]
                item['latest_flow_log']=dict(file=recent.name,bytes=recent.stat().st_size,
                    modified_utc=datetime.datetime.fromtimestamp(recent.stat().st_mtime,datetime.timezone.utc).isoformat(),
                    tail=tail(recent))
            for p in sorted(logs.glob('*.json')):
                raw=small(p)
                if raw:
                    try:metrics[p.name]=json.loads(raw)
                    except ValueError:pass
            final=metrics.get('6_report.json',{})
            item['metrics']=metrics
            item['quality']={
                'drc':metrics.get('5_2_route.json',{}).get('detailedroute__route__drc_errors'),
                'setup_ws_ns':final.get('finish__timing__setup__ws'),
                'hold_ws_ns':final.get('finish__timing__hold__ws'),
                'max_cap':final.get('finish__timing__drv__max_cap'),
                'max_slew':final.get('finish__timing__drv__max_slew'),
                'max_fanout':final.get('finish__timing__drv__max_fanout'),
                'instance_area_um2':final.get('finish__design__instance__area')}
            item['stages']=[p for p,odb,j in [('synth','1_synth.odb','1_synth.json'),
                ('place','3_place.odb','3_5_place_dp.json'),('cts','4_cts.odb','4_1_cts.json'),
                ('grt','5_1_grt.odb','5_1_grt.json'),('drt','5_2_route.odb','5_2_route.json'),
                ('finish','6_final.odb','6_report.json')] if (results/odb).is_file() and j in metrics]
            meta=small(base/'experiment.json')
            if meta:
                item['experiment']=json.loads(meta)
                top=item['experiment']['top']
                item['abstracts_present']={suffix:(results/(top+suffix)).is_file() for suffix in ('.lef','_typ.lib','.detailed.lef')}
            log=small(logs/'6_report.log') or ''
            item['final_markers']=[l for l in log.splitlines() if 'PSM-0040' in l or '[ERROR' in l]
        record['tasks'][name]=item
print(json.dumps(record,indent=2))
