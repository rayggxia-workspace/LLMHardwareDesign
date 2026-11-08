"""R8.3 semantic task -> compiler -> independent audit -> actual host replay."""
from pathlib import Path
import argparse,json
from compiler import compile_task
from audit import audit
from main64_fixtures import PAIRS,example
from main64_reference import evaluate
from main64_host import save

def generate(pair,out):
    out=Path(out)
    for variant in range(3):
        task,inputs=example(pair,variant);bundle=compile_task(task)
        audit(task,bundle);ref=evaluate(task,inputs)
        save(out/str(variant),task,bundle,inputs,ref)
    print('PASS main64 three compiled variants',pair)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pair',type=int,choices=range(9),required=True);p.add_argument('out',type=Path);a=p.parse_args();generate(PAIRS[a.pair],a.out)

