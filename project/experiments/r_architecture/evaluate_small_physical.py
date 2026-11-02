"""Gate fresh physical outputs and, only on clean STA, run the full GDS deck."""
from pathlib import Path
import json,subprocess,concurrent.futures,hashlib,os,xml.etree.ElementTree as ET,argparse,re

B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt062')
OUT=Path.cwd()/'evaluation';OUT.mkdir(exist_ok=False)
parser=argparse.ArgumentParser()
parser.add_argument('--trial',action='append',help='B256=attempt068; selected completed producer')
args=parser.parse_args()
roots={256:B.parent/'attempt065/physical',1024:B/'B1024/physical'}
if args.trial:
    roots={}
    for spec in args.trial:
        label,relative=spec.split('=',1)
        assert label in ['B256','B1024']
        assert re.fullmatch(r'attempt[0-9]+(?:/B[0-9]+)?',relative)
        roots[int(label[1:])]=B.parent/relative/'physical'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def run(cap):
    c='B'+str(cap)
    root=roots[cap]
    nickname='rarch157_'+c
    logs=root/'flow/logs/nangate45'/nickname/'base'
    rec=root/'receipt.json';m=logs/'6_report.json';route=logs/'5_2_route.json'
    d=dict(candidate=c,source=str(root),timing_pass=False,qualified=False,files={})
    for p in [rec,m,route,root/'IMPLEMENTATION.json',root/'input.sdc',root/'config.mk']:
        if p.exists():d['files'][str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
    if rec.exists() and m.exists() and route.exists():
        r=json.loads(rec.read_text());v=json.loads(m.read_text());g=json.loads(route.read_text())
        d['metrics']=v
        d['timing_pass']=(r['exit']==0 and
            v['finish__timing__setup__ws']>=0 and v['finish__timing__hold__ws']>=0 and
            all(v[k]==0 for k in ['finish__timing__drv__setup_violation_count',
                'finish__timing__drv__hold_violation_count','finish__timing__drv__max_cap',
                'finish__timing__drv__max_slew']) and g['detailedroute__route__drc_errors']==0)
    if d['timing_pass']:
        env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
        cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(root/'config.mk'),
             'WORK_HOME='+str(root/'flow'),'do-gds']
        with (OUT/(c+'-gds.log')).open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
        d['gds_exit']=r.returncode
        gds=root/'flow/results/nangate45'/nickname/'base/6_final.gds'
        if r.returncode==0 and gds.exists():
            deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
            report=OUT/(c+'-full-deck.lyrdb')
            with (OUT/(c+'-full-deck.log')).open('w') as f:
                r=subprocess.run(['klayout','-b','-rd','in_gds='+str(gds),'-rd',
                    'report_file='+str(report),'-r',str(deck)],stdout=f,stderr=subprocess.STDOUT)
            d.update(deck_exit=r.returncode,deck_sha256=sha(deck),gds_sha256=sha(gds))
            if r.returncode==0 and report.exists():
                d['full_gds_items']=len(ET.parse(report).getroot().findall('./items/item'))
                d['full_gds_pass']=d['full_gds_items']==0
    result=OUT/(c+'.json');result.write_text(json.dumps(d,indent=2)+'\n');return d

with concurrent.futures.ThreadPoolExecutor(max_workers=min(2,len(roots))) as pool:rows=list(pool.map(run,roots))
(OUT/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
