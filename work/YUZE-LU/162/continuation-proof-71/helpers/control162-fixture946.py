from pathlib import Path
import subprocess,json,random,time,collections
h=Path(__file__).parent;out=h/'control162-release-fixture946';assert not out.exists();out.mkdir();exe=h/'control162-pin-release945.exe';began=time.monotonic();counts=collections.Counter()
for seed in range(946,1946):
 r=random.Random(seed);nx=ny=24;locked=8;count=24;points=r.sample([(x,y)for x in range(4,20)for y in range(4,20)],2*count);inp=out/('input-%d.txt'%seed)
 inp.write_text('24 24 24 %d 80 256 8 1 1 1 1 0 0 1 0 2 1\n'%seed+''.join('n%d 2 %d %d %d %d %d\n'%(i,*points[2*i],*points[2*i+1],90 if i<locked else-1)for i in range(count)))
 flags=['--critical-first','--native-prefix-first','--pin-access=ordinary-first','--native-batch-ripup','--weighted-bidirectional','--ordinary-zero-pattern']
 before=out/('before-%d.txt'%seed);a=subprocess.run([str(exe),str(inp),str(before),*flags],capture_output=True);message=a.stderr.decode().strip();counts[message or'passed']+=1
 if a.returncode and message.startswith('disconnected bidirectional tree:')and Path(str(before)+'.native-prefix-paths.txt').exists():
  after=out/('after-%d.txt'%seed);z=subprocess.run([str(exe),str(inp),str(after),*flags,'--release-pin-reservations'],capture_output=True)
  if z.returncode==0:
   assert Path(str(before)+'.native-prefix-paths.txt').read_bytes()==Path(str(after)+'.native-prefix-paths.txt').read_bytes()
   (out/'fixture.json').write_text(json.dumps(dict(seed=seed,nx=nx,ny=ny,locked=locked,count=count,points=points,flags=flags,before_error=message,after_passed=True,before_stdout=a.stdout.decode(),after_stdout=z.stdout.decode(),seconds=time.monotonic()-began,counts=dict(counts)),indent=2));print(json.dumps(dict(found=True,seed=seed,before=message,seconds=time.monotonic()-began,counts=dict(counts))),flush=True);break
 if(seed-946)%50==49:print(json.dumps(dict(tested=seed-945,seconds=time.monotonic()-began,counts=dict(counts))),flush=True)
else:print(json.dumps(dict(found=False,counts=dict(counts),seconds=time.monotonic()-began)))
