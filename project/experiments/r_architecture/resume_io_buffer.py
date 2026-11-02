"""Fresh full reroute for a measured GDS antenna failure; preserve source trial."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--audit',required=True)
a=p.parse_args();assert re.fullmatch(r'attempt[0-9]+',a.source);assert re.fullmatch(r'attempt[0-9]+',a.audit)
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');src=base/a.source/'physical';dst=Path.cwd()/'physical'
r=json.loads((src/'receipt.json').read_text());assert r['exit']==0
c=r['candidate'];gate=json.loads((base/a.source/'evaluation'/(c+'.json')).read_text());assert gate['timing_pass'] and not gate['full_gds_pass']
audit=json.loads((base/a.audit/'results/ANTENNA_IO_AUDIT.json').read_text());assert audit['passed'] and audit['source_trial']==a.source and audit['candidate']==c
assert all(k.endswith('_ANTENNA')for k in audit['categories']) and audit['items']==gate['full_gds_items']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
root=src/'flow/results/nangate45'/('rarch157_'+c)/'base'
assert sha(root/'6_final.def')==audit['def_sha256']
assert sha(root/'6_final.gds')==gate['gds_sha256']
config=(src/'config.mk').read_text();netlist=Path(re.search(r'^export SYNTH_NETLIST_FILES = (.+)$',config,re.M)[1])
protected=[src/'config.mk',src/'input.sdc',root/'6_final.odb',root/'6_final.sdc',root/'6_final.def',netlist]
before={str(f):sha(f)for f in protected}
dst.mkdir(exist_ok=False);subprocess.run(['cp','-a','--reflink=auto',str(src/'flow'),str(dst/'flow')],check=True)
# Erase only stage5/6 files in this fresh copy; never accept stale prior outputs.
for f in (dst/'flow').rglob('*'):
 if f.is_file()and re.match(r'^[56]_',f.name):f.unlink()
fresh=dst/'flow/results/nangate45'/('rarch157_'+c)/'base'
shutil.copyfile(root/'6_final.odb',fresh/'4_cts.odb');shutil.copyfile(root/'6_final.sdc',fresh/'4_cts.sdc')
for name in ['input.sdc','IMPLEMENTATION.json']:shutil.copyfile(src/name,dst/name)
shutil.copyfile(Path(__file__).parent/'port_buffers.tcl',dst/'port_buffers.tcl')
names=[q['name']for q in audit['target_ports']];assert all(re.fullmatch(r'[A-Za-z0-9_\[\].]+',n)for n in names)
(dst/'required_ports.tcl').write_text('set r157_required_ports [list '+' '.join('{'+n+'}'for n in names)+']\n')
config+='\nexport PRE_GLOBAL_ROUTE_TCL = '+str(dst/'port_buffers.tcl')+'\n'
(dst/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
commands=[];exitcode=0
with(dst/'flow.log').open('w')as log:
 for target in ['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dst/'config.mk'),'WORK_HOME='+str(dst/'flow'),target]
  commands.append(cmd);s=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if s.returncode:exitcode=s.returncode;break
assert before=={str(f):sha(f)for f in protected}
rows=(dst/'PORT_BUFFER_AUDIT.tsv').read_text().splitlines()[1:]if(dst/'PORT_BUFFER_AUDIT.tsv').exists()else[]
rec=dict(candidate=c,capacity=r['capacity'],exit=exitcode,commands=commands,source=str(src),source_unchanged=True,source_sha256=before,source_gate=gate,antenna_audit_source=str(base/a.audit),required_inputs=len(names),buffered_inputs=len(rows),buffer_cell='BUF_X16',initial_legalization_existing_placement_unchanged="original_placement_unchanged=1"in(dst/"flow.log").read_text(),source_cts_inherited=True,qualification_transferred=False)
(dst/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(exitcode)
