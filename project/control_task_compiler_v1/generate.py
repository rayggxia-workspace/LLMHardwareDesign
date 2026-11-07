"""Generate audited compiler fixtures and host replay without RTL execution."""
from pathlib import Path
import argparse,hashlib,json,sys
from compiler import compile_task
from audit import audit
from fixtures import example,TARGETS
from reference import evaluate
from host import save

def main():
    p=argparse.ArgumentParser();p.add_argument('--target',choices=TARGETS,required=True);p.add_argument('output',type=Path);a=p.parse_args();out=[]
    for variant in range(3):
        task,inputs=example(a.target,variant);bundle=compile_task(task);check=audit(task,bundle);reference=evaluate(task,inputs)
        folder=a.output/str(variant);count=save(folder,task,bundle,inputs,reference)
        out.append(dict(variant=variant,commands=count,independent=check,sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.iterdir()) if f.is_file()}))
    (a.output/'generated.json').write_text(json.dumps(dict(target=a.target,cases=out),indent=2)+'\n')
    print('PASS compiled and independently checked',a.target,len(out),'cases')
if __name__=='__main__':main()
