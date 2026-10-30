from pathlib import Path
import hashlib,json,subprocess,shlex,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'diagnostics/v410-bulk-gds-20261030-467';assert not r.exists()
assert subprocess.check_output(['squeue','-h','-j','93555','-o','%T|%N'],universal_newlines=True).strip()=='RUNNING|node21'
live=json.loads((b/'block-v1-20261030-404/tasks/native-node-queue/queue-live.json').read_text());assert live['active']==['revision300-route-r']and list(live['cpu_affinities'].values())==[list(range(16))]
r.mkdir();source=b/'diagnostics/v410-enclosure-bulk-20261030-453/merge';before=b/'diagnostics/v410-via-gds-20261030-452/before/gds-flow/results/nangate45/bv1_block_v1_v/base'
expected={'source_before_def':'167cece0db2b53363f9bc0da57e3d46d156ccaeb39f43cd9841ed3217535d0f6','source_after_def':'73e998b59c8637fa6ff9d879831a67f13655f661cc6a6477ba73d234ebbc1623','reused_before_gds':'10f26f4d58126f8598cc5dba1efbe4b6ab4bac2e86d10625a437192c3f638405'}
paths={'source_before_def':source/'before.def','source_after_def':source/'after.def','reused_before_gds':before/'6_final.gds'}
assert hashlib.sha256((before/'6_final.def').read_bytes()).hexdigest()==expected['source_before_def']
for n,p in paths.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[n],n
config=b/'block-v1-20261030-410/tasks/revision300-route-v/config.mk';sif=Path('/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif')
for cat in ('results','logs','objects','reports'):(r/'gds-flow'/cat/'nangate45/bv1_block_v1_v/base').mkdir(parents=True)
script='''import pya,json,hashlib
from pathlib import Path
paths=[Path(BEFORE),Path('gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds')];layouts=[]
for p in paths:
 l=pya.Layout();l.read(str(p));assert len(l.top_cells())==1;layouts.append(l)
a,z=layouts;assert a.dbu==z.dbu;rows=[]
for pair in sorted(set((i.layer,i.datatype)for l in layouts for i in l.layer_infos())):
 regs=[]
 for l in layouts:
  i=l.find_layer(*pair);v=pya.Region()if i is None else pya.Region(l.top_cell().begin_shapes_rec(i));v.merge();regs.append(v)
 d=regs[0]^regs[1];count=sum(1 for _ in d.each());rows.append(dict(layer=pair,xor_polygons=count,before_area=regs[0].area(),after_area=regs[1].area()));assert count==0,(pair,count)
json.dump(dict(passed=True,all_recursive_non_text_layer_union_xor_zero=True,dbu_um=a.dbu,layers=rows,gds_sha256=[hashlib.sha256(p.read_bytes()).hexdigest()for p in paths],scope='Actual fullhierarchy GDS mask XOR for all191 nets/194 via realization definitions. Reused452 before GDS has exact byte-bound identical source DEF. No P&R rerun or duplicated before stream; no deck/STA/function qualification or transfer to463.'),open('full-mask-xor.json','w'),indent=2)
'''.replace('BEFORE',repr(str(before/'6_final.gds')))
(r/'xor.py').write_text(script)
guard="from pathlib import Path;d=dict(x.split(':',1)for x in Path('/proc/meminfo').read_text().splitlines());assert int(d['MemAvailable'].split()[0])*1024>(128*1.2+16)*1024**3;assert 'job_93555'in Path('/proc/self/cgroup').read_text()"
body='set -e\nsource /OpenROAD-flow-scripts/env.sh\ncp '+shlex.quote(str(source/'after.def'))+' '+shlex.quote(str(r/'gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.def'))+'\nmake -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG='+shlex.quote(str(config))+' WORK_HOME='+shlex.quote(str(r/'gds-flow'))+' NUM_CORES=16 do-gds\nklayout -b -r '+shlex.quote(str(r/'xor.py'))+'\n'
(r/'run.sh').write_text(body)
cmd='python3 -c '+shlex.quote(guard)+' && export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH && exec taskset --cpu-list 32-47 singularity exec --cleanenv --bind /public/home/yuzelu --pwd '+str(r)+' --env OMP_NUM_THREADS=16 '+str(sif)+' bash '+str(r/'run.sh')
argv=['srun','--jobid=93555','--overlap','--ntasks=1','--cpus-per-task=96','--cpu-bind=none','--time=0','bash','-c',cmd]
record=dict(state='RUNNING',started_utc=datetime.datetime.utcnow().isoformat()+'Z',parent_job='93555',new_allocation=False,source_commit='c695c2545386375fc193ec9004ee4181fec7be3e',inputs={n:dict(path=str(paths[n]),sha256=h)for n,h in expected.items()},config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),actual_before_def_matches_reused_gds_input=True,cpus=list(range(32,48)),memory_forecast_gib=128,memory_guard_gib=16,memory_margin=1.2,argv=argv,scope='Finite full-GDS mask proof closing bulk453 realization gap. No new implementation, no current463/R modification, no repeated P&R/deck/accepted M/S/T.')
(r/'launch.json').write_text(json.dumps(record,indent=2)+'\n');print('START',str(r),flush=True)
with(r/'step.log').open('w')as log:
 p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT);record['srun_pid']=p.pid;(r/'launch.json').write_text(json.dumps(record,indent=2)+'\n');rc=p.wait()
record.update(state='COMPLETED'if rc==0 else'FAILED',returncode=rc,finished_utc=datetime.datetime.utcnow().isoformat()+'Z');(r/'launch.json').write_text(json.dumps(record,indent=2)+'\n');print(record['state'],rc,flush=True);assert rc==0
