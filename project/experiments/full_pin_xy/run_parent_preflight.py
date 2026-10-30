"""Independent placed-parent geometry DRC; never a routing/connectivity pass.

Reads only already frozen placed.odb checkpoints from active own parent jobs.
No routing, source writes or job modification. Pin min-area can need routing;
an error count alone is not proof of an irreparable fixed short.
"""
from pathlib import Path
import datetime,json,os,re,subprocess,sys
from run_exports import ROOT,IMAGE,BIN,sha

driver=Path(__file__).resolve().parent;parent_rev,design,focus,revision=sys.argv[1:5]
source=ROOT/'parents'/parent_rev/(design+'-'+focus+'-A');checkpoint=sys.argv[5] if len(sys.argv)>5 else 'placed.odb'
assert checkpoint in ['placed.odb','global.odb'];odb=source/checkpoint
assert odb.exists();before=sha(odb)
out=ROOT/'parent_preflight'/revision/(design+'-'+focus+'-A');out.mkdir(parents=True,exist_ok=False)
env='PINXY_DRC_ODB={},PINXY_TOP_LAYER=10,PINXY_DRC_OUT={},PINXY_PREFLIGHT_STATE={}'.format(odb,out/'placed.drc',out/'source_state.tsv')
script=driver/('parent_fixed_preflight.tcl' if checkpoint=='global.odb' else 'independent_drc.tcl')
command=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),'--env',env,IMAGE,BIN,'-threads','1','-no_init','-exit',str(script)]
with (out/'native.log').open('x') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
report=out/'placed.drc';text=report.read_text() if report.exists() else ''
types={}
for kind in re.findall(r'^violation type:\s*(.+)',text,re.M):types[kind]=types.get(kind,0)+1
record={'scope':'FIXED_PLACED_PARENT_GEOMETRY_ONLY; no routed net or full GDS/LVS/system qualification',
 'design':design,'focus':focus,'source_parent_revision':parent_rev,'source_odb':str(odb),'source_sha256':before,'source_unchanged':sha(odb)==before,
 'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(driver/'driver_commit.txt').read_text().strip(),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'new_process':True,'native_returncode':r.returncode,'native_DRC_count':sum(types.values()) if r.returncode==0 and report.exists() else None,'violation_types':types,
 'signal_routing_completed':False,'connectivity_checked':False,'full_qualification':False,
 'report_sha256':sha(report) if report.exists() else None,'command':command,
 'interpretation':'Separate immutable PG/OBS/contact geometry from signal-route effects. Min-area and similar errors may require future access wires; never stop an active trial based solely on this count.'}
if (out/'source_state.tsv').exists():record['source_signal_nets_with_dbWire']=int((out/'source_state.tsv').read_text().split()[1])
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print('PLACED_PARENT_PREFLIGHT',design,types,flush=True)
sys.exit(r.returncode)
