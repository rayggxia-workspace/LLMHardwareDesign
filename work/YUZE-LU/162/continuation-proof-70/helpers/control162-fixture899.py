from pathlib import Path
import subprocess,json,random,time
h=Path(__file__).parent;out=h/'control162-batch-fixture899';out.mkdir(exist_ok=True);exe=h/'control162-native-batch898.exe';began=time.monotonic();records=[]
for seed in range(899,1099):
 r=random.Random(seed);points=r.sample([(x,y)for x in range(5,27)for y in range(5,27)],24)
 inp=out/('input-%d.txt'%seed);target=out/('output-%d.txt'%seed)
 inp.write_text('32 32 12 %d 80 256 12 1 1 1 1 0 0 1 0 2 1\n'%seed+''.join('n%d 2 %d %d %d %d 90\n'%(i,*points[2*i],*points[2*i+1])for i in range(12)))
 p=subprocess.run([str(exe),str(inp),str(target),'--critical-first','--native-prefix-first','--native-batch-ripup'],capture_output=True)
 log=Path(str(target)+'.native-prefix.log');rows=[json.loads(l)for l in log.read_text().splitlines()if l.startswith('{')]if log.exists()else[]
 batch=[x for x in rows if x.get('native_batch_removed_trees',0)>0]
 records.append(dict(seed=seed,returncode=p.returncode,batch=batch,stderr=p.stderr.decode()))
 if p.returncode==0 and batch:
  (out/'fixture.json').write_text(json.dumps(dict(seed=seed,points=points,records=records,seconds=time.monotonic()-began),indent=2));print(json.dumps(dict(found=True,seed=seed,batch=batch,seconds=time.monotonic()-began)));break
else:print(json.dumps(dict(found=False,records=records[-4:])))
