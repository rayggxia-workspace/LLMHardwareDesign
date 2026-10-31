from pathlib import Path
import base64,datetime,hashlib,json,shlex,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');out=b/'diagnostics/v410-enclosure-bulk-20261030-453';payload=json.loads((out/'payload.json').read_bytes());assert hashlib.sha256((out/'payload.json').read_bytes()).hexdigest()=='6ec2a604da3e0aaf4c661403fd90df2e850715b5c9cff22ddbe484e7ca623a10'
assert subprocess.check_output(['squeue','-h','-j','93555','-o','%T|%N'],universal_newlines=True).strip()=='RUNNING|node21'
assert json.loads((b/'block-v1-20261030-404/tasks/native-node-queue/queue-live.json').read_text())['active']==['revision300-route-r']
for stage in ('before','after'):assert (b/'diagnostics/v410-via-gds-20261030-452'/stage/'gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds').exists()
helpers=out/'helpers';helpers.mkdir()
for n,row in payload['helpers'].items():
 raw=base64.b64decode(row['base64']);assert hashlib.sha256(raw).hexdigest()==row['sha256'];(helpers/n).write_bytes(raw)
source=b/'diagnostics/v410-subset-clearance-20261030-445/bulk';odb=source/'probe.odb';expected=json.loads((source/'probe-result.json').read_bytes())['files']['probe.odb']['sha256']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
assert sha(odb)==expected
sif=Path('/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif');assert sha(sif)=='49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a'
selected='set selected [list '+' '.join('[encoding convertfrom utf-8 [binary decode hex '+n.encode().hex()+']]'for n in sorted(payload['plan']['nets']))+']\n';setup='set_thread_count 16\nread_db {'+str(odb)+'}\nset ::env(BV1_GEOMETRY_SOURCE) {'+str(helpers/'odb_geometry.tcl')+'}\nsource {'+str(helpers/'native_escape_geometry.tcl')+'}\n'+selected
base=out/'baseline';base.mkdir();(base/'run.tcl').write_text(setup+'write_def before.def\nwrite_verilog before.v\nescape_geometry before-geometry.tsv $selected\n')
guard='from pathlib import Path; d=dict(x.split(":",1)for x in Path("/proc/meminfo").read_text().splitlines()); assert int(d["MemAvailable"].split()[0])*1024>(176*1.2+16)*1024**3; assert "job_93555" in Path("/proc/self/cgroup").read_text()'
def launch(p,lo,body,logname):
 cmd='python3 -c '+shlex.quote(guard)+' && export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH && exec taskset --cpu-list '+str(lo)+'-'+str(lo+15)+' singularity exec --cleanenv --bind /public/home/yuzelu --pwd '+str(p)+' --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 '+str(sif)+' bash -c '+shlex.quote('source /OpenROAD-flow-scripts/env.sh; '+body)
 log=(p/logname).open('w');proc=subprocess.Popen(['srun','--jobid=93555','--overlap','--ntasks=1','--cpus-per-task=96','--cpu-bind=none','--time=00:30:00','bash','-c',cmd],stdout=log,stderr=subprocess.STDOUT);print(p.name,proc.pid,flush=True);return proc,log
meta=dict(state='RUNNING',source_commit=payload['source_commit'],parent_job='93555',new_allocation=False,source_odb=str(odb),source_odb_sha256=expected,sif_sha256=sha(sif),cpu_masks={'baseline':list(range(16,32)),'clone':list(range(32,48)),'merge':list(range(80,96))},memory_basis='Three16GiB OpenROAD slots + conservative two64GiB concurrent452GDS/XOR slots, forecast176GiB*1.2+16GiB guard/liveMemAvailable; actualR0-15. No extra allocation/cancel.',payload_sha256=sha(out/'payload.json'));(out/'launch.json').write_text(json.dumps(meta,indent=2)+'\n')
children=[(base,)+launch(base,16,'openroad -no_init -exit run.tcl','step.log')]
for case,lo in zip(payload['cases'],(32,80)):
 p=out/case['name'];p.mkdir();(p/'plan.json').write_text(json.dumps(case,indent=2)+'\n');(p/'patch.def').write_text(case['patch_def']);assert sha(p/'patch.def')==case['patch_sha256']
 for n in ('before.def','before.v','before-geometry.tsv'):(p/n).symlink_to(base/n)
 (p/'run.tcl').write_text(setup+'read_def -floorplan_initialize {'+str(p/'patch.def')+'}\nwrite_def after.def\nwrite_verilog after.v\nwrite_db probe.odb\nescape_geometry after-geometry.tsv $selected\ndrt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n')
 children.append((p,)+launch(p,lo,'openroad -no_init -exit run.tcl','step.log'))
rcs={}
for p,proc,log in children:rcs[p.name]=proc.wait();log.close()
meta.update(state='EDA_COMPLETED'if all(v==0 for v in rcs.values())else'FAILED',returncodes=rcs,source_odb_unchanged=sha(odb)==expected,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(out/'launch.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta['state'],rcs,flush=True)
