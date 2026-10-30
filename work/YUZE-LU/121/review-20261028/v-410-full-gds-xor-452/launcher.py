from pathlib import Path
import json,subprocess,shlex,hashlib,datetime,concurrent.futures
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');out=b/'diagnostics/v410-via-gds-20261030-452';assert not out.exists();out.mkdir()
assert subprocess.check_output(['squeue','-h','-j','93555','-o','%T|%N'],universal_newlines=True).strip()=='RUNNING|node21'
for n in ('v410-pruned-jog-20261030-450/bulk','v410-via-enclosure-20261030-451/clone','v410-via-enclosure-20261030-451/merge'):
 assert json.loads((b/'diagnostics'/n/'launch.json').read_text())['state']=='COMPLETED'
sif=b.parents[2]/'opt/eda/containers/orfs-current-repacked.sif'
sif=Path('/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif')
config=b/'block-v1-20261030-410/tasks/revision300-route-v/config.mk';src=b/'diagnostics/v410-via-enclosure-20261030-451/merge'
meta=dict(source_commit='78332dd56acae9d366c501cc36c13010826c75d0',parent_job='93555',new_allocation=False,source_receipt_sha256=hashlib.sha256((src/'probe-result.json').read_bytes()).hexdigest(),config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),state='RUNNING',scope='Read-only fullGDS export of exact451 before/after DEF; then actual wholehierarchy all-layer mask XOR and complete unmodified deck. Diagnostic only, no timing/qualification transfer. Cached explicit-via identity control remains196.')
(out/'launch.json').write_text(json.dumps(meta,indent=2)+'\n')
children=[]
for i,stage in enumerate(('before','after')):
 p=out/stage;p.mkdir();r=p/'gds-flow/results/nangate45/bv1_block_v1_v/base';r.mkdir(parents=True)
 for cat in ('logs','objects','reports'):(p/'gds-flow'/cat/'nangate45/bv1_block_v1_v/base').mkdir(parents=True)
 # Copy and all compute occur inside allocation.
 script='source /OpenROAD-flow-scripts/env.sh\ncp '+shlex.quote(str(src/(stage+'.def')))+' '+shlex.quote(str(r/'6_final.def'))+'\nmake -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG='+shlex.quote(str(config))+' WORK_HOME='+shlex.quote(str(p/'gds-flow'))+' NUM_CORES=16 do-gds\n'
 (p/'run.sh').write_text('set -e\n'+script)
 guard='from pathlib import Path; d=dict(x.split(":",1)for x in Path("/proc/meminfo").read_text().splitlines()); assert int(d["MemAvailable"].split()[0])*1024>(128*1.2+16)*1024**3; assert "job_93555"in Path("/proc/self/cgroup").read_text()'
 cmd='python3 -c '+shlex.quote(guard)+' && export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH && exec taskset --cpu-list '+str(16+i*16)+'-'+str(31+i*16)+' singularity exec --cleanenv --bind /public/home/yuzelu --pwd '+shlex.quote(str(p))+' --env OMP_NUM_THREADS=16 '+str(sif)+' bash '+str(p/'run.sh')
 log=(p/'step.log').open('w');proc=subprocess.Popen(['srun','--jobid=93555','--overlap','--ntasks=1','--cpus-per-task=96','--cpu-bind=none','--time=00:30:00','bash','-c',cmd],stdout=log,stderr=subprocess.STDOUT);children.append((proc,log,p));print(stage,proc.pid,flush=True)
for proc,log,p in children:
 rc=proc.wait();log.close();assert rc==0,(p.name,rc)
# Compare full layouts, including every recursive conductor/cut and all other non-text masks.
script=r"""import pya,json,hashlib
from pathlib import Path
layouts=[]
for stage in ('before','after'):
 p=Path(stage)/'gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds';l=pya.Layout();l.read(str(p));assert len(l.top_cells())==1;layouts.append(l)
a,z=layouts;assert a.dbu==z.dbu
pairs=sorted(set((i.layer,i.datatype)for l in layouts for i in l.layer_infos()));rows=[]
for pair in pairs:
 regs=[]
 for l in layouts:
  i=l.find_layer(*pair);r=pya.Region()if i is None else pya.Region(l.top_cell().begin_shapes_rec(i));r.merge();regs.append(r)
 diff=regs[0]^regs[1];count=sum(1 for _ in diff.each());rows.append(dict(layer=pair,xor_polygons=count,before_area=regs[0].area(),after_area=regs[1].area()));assert count==0,(pair,count)
json.dump(dict(passed=True,all_recursive_non_text_layer_union_xor_zero=True,dbu_um=a.dbu,layers=rows,scope='Actual complete before/after GDS independently streamed from exact451 DEF including all library cells, cuts and masks; fullhierarchy materialized XOR. Identity, not qualification.'),open('full-mask-xor.json','w'),indent=2)
"""
(out/'xor.py').write_text(script)
# Both independent successors start as soon as both GDS exports are complete.
checks=[('xor',48,'klayout -b -r '+shlex.quote(str(out/'xor.py'))),('deck',64,'klayout -b -rd in_gds='+str(out/'after/gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds')+' -rd report_file='+str(out/'full-deck.lyrdb')+' -r /OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')]
children=[]
for name,lo,body in checks:
 cmd='python3 -c '+shlex.quote(guard)+' && export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH && exec taskset --cpu-list '+str(lo)+'-'+str(lo+15)+' singularity exec --cleanenv --bind /public/home/yuzelu --pwd '+str(out)+' --env OMP_NUM_THREADS=16 '+str(sif)+' bash -c '+shlex.quote('source /OpenROAD-flow-scripts/env.sh; '+body)
 log=(out/(name+'.log')).open('w');proc=subprocess.Popen(['srun','--jobid=93555','--overlap','--ntasks=1','--cpus-per-task=96','--cpu-bind=none','--time=00:30:00','bash','-c',cmd],stdout=log,stderr=subprocess.STDOUT);children.append((proc,log,name));print(name,proc.pid,flush=True)
rcs={}
for proc,log,name in children:rcs[name]=proc.wait();log.close()
meta.update(state='COMPLETED'if all(v==0 for v in rcs.values())else'FAILED',check_returncodes=rcs,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(out/'launch.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta['state'],rcs,flush=True)
