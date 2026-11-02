import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155');out=b/'initial-state-queue-001';out.mkdir();src=b/'actual-probe-006/tmp-max';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(src/'trimmed.sp')=='4b8e89c53f02b2b7fb1792ccb72ef3256878a42cc17883b5e506953edb46bf5b'
lines=[]
for line in (src/'trimmed.sp').read_text().splitlines():
 line=line.strip()
 if not line or line.startswith('*'):continue
 if line.startswith('+'):lines[-1]+=' '+line[1:].strip()
 else:lines.append(line)
sub={};cur=None
for line in lines:
 tokens=line.split();head=tokens[0].lower()
 if head=='.subckt':cur=tokens[1].lower();assert cur not in sub;sub[cur]=[]
 elif head=='.ends':cur=None
 elif cur is not None and head.startswith('x'):sub[cur].append((tokens[0].lower(),tokens[-1].lower()))
leaves=[]
def visit(cell,path,depth=0):
 assert depth<30
 if cell in ('cell_1rw','dummy_cell_1rw'):leaves.append((path,cell));return
 for name,typ in sub[cell]:visit(typ,path+'.'+name,depth+1)
visit('s_sram_256x128_freepdk45','xs_sram_256x128_freepdk45');assert leaves and len({p for p,c in leaves})==len(leaves)
configs=['dummy0','dummy1','all0','all1','allrandom','real0'];counts={}
for name in configs:
 dst=out/name;dst.mkdir()
 for n in ('trimmed.sp','delay_meas.sp'):(dst/n).write_bytes((src/n).read_bytes())
 ic=[]
 for path,typ in leaves:
  if name.startswith('dummy') and typ!='dummy_cell_1rw':continue
  if name=='real0' and typ!='cell_1rw':continue
  value=int(name.endswith('1')) if name!='allrandom' else (hashlib.sha256(path.encode()).digest()[0]&1)
  ic.append('.ic V('+path+'.q)='+str(1.1*value)+' V('+path+'.q_bar)='+str(1.1*(1-value)))
 s=(src/'delay_stim.sp').read_text().replace(str(src),str(dst));assert '.ic ' not in s.lower();assert s.lower().count('\n.end\n')==1
 s=s.replace('\n.end\n','\n'+'\n'.join(ic)+'\n.end\n');(dst/'delay_stim.sp').write_text(s);(dst/'.spiceinit').write_text('set num_threads=1\nset ngbehavior=hsa\noption klu\n');counts[name]=len(ic)
runner=(b/'solver-queue-001/run.py').read_text().replace("['gear50','gear100','trap100']",repr(configs));(out/'run.py').write_text(runner)
script=(b/'solver-queue-001/job.sbatch').read_text().replace(str(b/'solver-queue-001'),str(out)).replace('yzl-sram-solvers','yzl-sram-initial');(out/'job.sbatch').write_text(script)
job=subprocess.check_output(['sbatch','--parsable','--output='+str(out/'slurm.log'),str(out/'job.sbatch')],universal_newlines=True).strip()
r=dict(job=job,cpus=3,workers=3,dynamic_queue=configs,initializations=counts,leaf_counts={c:sum(t==c for _,t in leaves)for c in ('cell_1rw','dummy_cell_1rw')},source_input_sha256={n:sha(src/n) for n in ('trimmed.sp','delay_stim.sp','delay_meas.sp')},scope='Deterministic valid initial states of storage cells only; replicas not initialized; actual devices/loads/slews/clock/measurements/tolerances unchanged; diagnostic only',qualified=False)
(out/'submission.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
