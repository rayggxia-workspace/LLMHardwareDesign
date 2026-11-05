from pathlib import Path
import subprocess,json,concurrent.futures
h=Path(__file__).parent;out=h/'control162-warm-probe969';out.mkdir()
base=(h/'control162-release-fixture946/input-971.txt').read_text(encoding='utf-8');header,body=base.split('\n',1)
prefix=h/'control162-release-fixture946/before-971.txt.native-prefix-paths.txt'
binary=h/'control162-warm968.exe'
def one(seed):
 p=out/str(seed);p.mkdir();fields=header.split();fields[3]=str(seed);(p/'input.txt').write_text(' '.join(fields)+'\n'+body)
 with(p/'log.txt').open('w')as log:r=subprocess.run([str(binary),str(p/'input.txt'),str(p/'output.txt'),'--critical-first','--native-prefix-first','--pin-access=none','--native-prefix-flexible','--native-prefix-input='+str(prefix),'--weighted-bidirectional','--ordinary-zero-pattern'],stdout=log,stderr=subprocess.STDOUT)
 return dict(seed=seed,passed=r.returncode==0,last=(p/'log.txt').read_text().splitlines()[-1])
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(one,range(971,995)))
(out/'receipt.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
