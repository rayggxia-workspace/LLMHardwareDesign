"""Finish a proven routed producer rejected only by the make DRC launcher.

Never edits the producer or waives any final gate. Copies and binds all six
files, then runs the unchanged full merged-GDS deck. Independent acceptance
remains mandatory even when pipeline completion is recorded.
"""
import argparse,hashlib,json,os,shutil,subprocess,time,xml.etree.ElementTree as E
from pathlib import Path

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--producer',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
assert os.environ.get('SLURM_JOB_ID');source=a.producer.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
pr=source/'receipt.json';old=json.loads(pr.read_text())
assert not old['passed'] and not old['pipeline_completed']
assert old['failure']=="RuntimeError(('whole-gds-drc.log', 2))"
assert old['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish','do-gds']
assert old['commands'][-1]['log']=='whole-gds-drc.log' and old['commands'][-1]['returncode']==2
for c in old['commands']:
    assert sha(source/c['log'])==c['sha256']
    if c is not old['commands'][-1]:assert c['returncode']==0
log=(source/'whole-gds-drc.log').read_text()
assert '1_2_yosys.v' in log and 'Permission denied' in log and 'do-yosys' in log
for p,h in old['inputs'].items():assert sha(Path(p))==h
assert sha(Path(old['structural_proof']['path']))==old['structural_proof']['sha256']
assert set(old['final_files'])=={'6_final.'+x for x in ('v','sdc','def','odb','gds','spef')}
record={k:v for k,v in old.items()if k not in ('failure','commands','final_files','job_id')}
record.update(passed=False,pipeline_completed=False,qualified=False,commands=[],final_files={},job_id=os.environ['SLURM_JOB_ID'],
    resumed_producer=dict(path=str(source),receipt_sha256=sha(pr),failure=old['failure'],commands=old['commands']),
    scope='Same completed route and RCX; separate immutable full-GDS DRC/render completion. All independent final gates required.')
record['inputs'][str(pr)]=sha(pr)
def save():(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
def run(cmd,name):
    start=time.time();cmd=list(map(str,cmd))
    with (out/name).open('w')as f:p=subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT)
    record['commands'].append(dict(argv=cmd,log=name,sha256=sha(out/name),returncode=p.returncode,seconds=time.time()-start));save();assert p.returncode==0
try:
    for name,v in old['final_files'].items():
        src=Path(v['path']);assert sha(src)==v['sha256'];dst=out/name;shutil.copyfile(src,dst);assert sha(dst)==v['sha256']
        record['inputs'][str(src)]=sha(src);record['final_files'][name]=dict(path=str(dst),sha256=sha(dst),bytes=dst.stat().st_size)
    for name in ['input.sdc','pins.json','pins.tcl']:
        src=source/name;shutil.copyfile(src,out/name);assert sha(src)==sha(out/name);record['inputs'][str(src)]=sha(src)
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');record['inputs'][str(deck)]=sha(deck)
    run(['klayout','-b','-r',deck,'-rd','in_gds='+str(out/'6_final.gds'),'-rd','report_file='+str(out/'full.lyrdb')],'whole-gds-drc.log')
    items=E.parse(out/'full.lyrdb').findall('.//items/item')
    record['whole_gds_drc']=dict(path=str(out/'full.lyrdb'),sha256=sha(out/'full.lyrdb'),items=len(items),clean=not items)
    text='''import pya
view=pya.LayoutView()
view.load_layout(INPUT,0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image(OUTPUT,1600,1600)
'''.replace('INPUT',repr(str(out/'6_final.gds'))).replace('OUTPUT',repr(str(out/'layout.png')))
    (out/'render.py').write_text(text);run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',out/'render.py'],'render.log')
    assert (out/'layout.png').stat().st_size>1000
    record['image']=dict(path=str(out/'layout.png'),sha256=sha(out/'layout.png'))
    for p,h in record['inputs'].items():assert sha(Path(p))==h
    for v in record['final_files'].values():assert sha(Path(v['path']))==v['sha256']
    record.update(passed=True,pipeline_completed=True)
except Exception as e:record['failure']=repr(e);raise
finally:save()
