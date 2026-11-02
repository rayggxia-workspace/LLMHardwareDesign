"""Final extracted STA, strict native LEC, actual PG/pins, full original GDS deck."""
from pathlib import Path
import os,subprocess,json,argparse,hashlib,xml.etree.ElementTree as ET
from lec_receive import inspect,fixture
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
O=Path.cwd()/'evaluation';O.mkdir(exist_ok=False);P=Path(__file__).resolve().parent
B=a.physical;R=B/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base';L=B/'flow/logs/nangate45'/('r166_'+str(a.capacity))/'base'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec={'passed':False,'physical':str(B),'capacity':a.capacity,'checks':{}};checks=rec['checks'];env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
def run(args,log):
 with(O/log).open('w')as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
try:
 (O/'lec-controls').mkdir();fixture(P,O/'lec-controls',run)
 producer=json.loads((B/'receipt.json').read_text());assert producer['exit']==0
 m=json.loads((L/'6_report.json').read_text());d=json.loads((L/'5_2_route.json').read_text())
 checks['setup_hold']=m['finish__timing__setup__ws']>=0 and m['finish__timing__hold__ws']>=0
 checks['timing_electrical_zero']=all(m[k]==0 for k in ['finish__timing__drv__setup_violation_count','finish__timing__drv__hold_violation_count','finish__timing__drv__max_cap','finish__timing__drv__max_slew'])
 checks['route_drc_zero']=d['detailedroute__route__drc_errors']==0
 checks['unchanged_sdc']=sha(B/'input.sdc')==sha(P/'physical.sdc')
 checks['lec_mutation_controls']=json.loads((O/'lec-controls/native-formal-control.json').read_text())['passed']
 rec['metrics']=m
 lec=inspect((L/'6_final_lec_check.log').read_text());rec['lec']=lec;checks['strict_final_lec']=lec['passed'] and sha(R/'6_final_lec.v')==sha(R/'6_final.v')
 env.update(INPUT_ODB=str(R/'6_final.odb'),OUTPUT_TSV=str(O/'physical.tsv'));run(['openroad','-no_init','-exit',P/'physical_probe.tcl'],'physical.log')
 lines=(O/'physical.tsv').read_text().splitlines();regions=[s.split('\t')for s in lines if s.startswith('REGION\t')];pins=[s.split('\t')for s in lines if s.startswith('PIN\t')]
 checks['pins_pg']=len(pins)==821 and all(s[2]=='metal10'for s in pins) and not any(s.startswith('BADPG')for s in lines)
 checks['storage_fences']=len(regions)==2*(a.capacity//128) and all(int(s[2])>0 and int(s[3])==0 for s in regions)
 rec['regions']=regions
 cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(B/'config.mk'),'WORK_HOME='+str(B/'flow')]
 run(cmd+['do-gds'],'gds.log')
 deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');assert sha(deck)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
 run(['klayout','-b','-rd','in_gds='+str(R/'6_final.gds'),'-rd','report_file='+str(O/'full-deck.lyrdb'),'-r',deck],'full-deck.log')
 n=len(ET.parse(O/'full-deck.lyrdb').getroot().findall('./items/item'));rec['full_deck_items']=n;rec['deck_sha256']=sha(deck);checks['full_original_gds_zero']=n==0
 protected={str(f):sha(f)for f in R.glob('6_final.*')}
 run(cmd+['do-generate_abstract'],'abstract.log')
 checks['abstract_source_unchanged']=protected=={f:sha(Path(f))for f in protected}
 checks['abstract_views']=all(f.exists() and f.stat().st_size>0 for f in [R/'r_stream_local.lef',R/'r_stream_local_typ.lib'])
 rec['artifacts']={str(f):{'bytes':f.stat().st_size,'sha256':sha(f)}for f in list(R.glob('6_final.*'))+[R/'r_stream_local.lef',R/'r_stream_local_typ.lib']if f.is_file()}
 rec['passed']=all(checks.values())
except Exception as e:rec['error']=repr(e)
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'passed':rec['passed'],'checks':checks,'error':rec.get('error')}));raise SystemExit(0 if rec['passed']else 1)
