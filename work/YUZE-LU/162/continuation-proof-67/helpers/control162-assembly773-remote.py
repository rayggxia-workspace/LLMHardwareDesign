from pathlib import Path
import subprocess,json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-router-hotspot-assembly-773';assert not out.exists();out.mkdir();prior=b/'r256-router-hotspot-profile-772';assert json.loads((prior/'receipt.json').read_text())['record_returncode']==0
code=r'''from pathlib import Path
import subprocess,json,re,hashlib,time
out=Path(OUT);prior=Path(PRIOR);binary=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates/7370/route/router');r=dict(time=time.time(),whole_system_qualified=False,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),perf_sha256=hashlib.sha256((prior/'perf.data').read_bytes()).hexdigest())
for label,args in [('buildids',['perf','buildid-list','-i',str(prior/'perf.data')]),('elf',['readelf','-n',str(binary)]),('assembly',['perf','annotate','--stdio','-i',str(prior/'perf.data')])]:
 v=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);r[label+'_returncode']=v.returncode;(out/(label+'.stdout')).write_bytes(v.stdout);(out/(label+'.stderr')).write_bytes(v.stderr)
elf=(out/'elf.stdout').read_text();ids=(out/'buildids.stdout').read_text();m=re.search(r'Build ID: ([0-9a-f]+)',elf);assert m and m.group(1)in ids;r['recorded_binary_buildid_matches_current']=True
lines=(out/'assembly.stdout').read_text().splitlines();hot=[]
for i,line in enumerate(lines):
 m=re.match(r'\s*(\d+\.\d+)\s*:\s*(.*)',line)
 if m and float(m.group(1))>=1:hot.append(dict(percent=float(m.group(1)),line=line,previous=lines[max(0,i-1)]))
r['top_assembly_lines']=sorted(hot,key=lambda x:-x['percent'])[:20];(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(buildid_match=True,top_lines=r['top_assembly_lines'][:12])))
'''.replace('OUT',repr(str(out))).replace('PRIOR',repr(str(prior)))
compile(code,'compute773','exec');z=subprocess.run(['srun','--jobid=95391','--overlap','-n1','-c1','python3','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/'launcher.stdout').write_bytes(z.stdout);(out/'launcher.stderr').write_bytes(z.stderr);print(z.stdout.decode());print(z.stderr.decode()[-1500:]if z.returncode else'');assert not z.returncode
