"""Independently audit an IR/bundle pair, then emit binary/PM/load artifacts."""
from pathlib import Path
import argparse,json
from compiler import decode
from audit import audit
from host import load_plan

def main():
    p=argparse.ArgumentParser();p.add_argument('task',type=Path);p.add_argument('bundle',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        task=decode(a.task.read_bytes());bundle=decode(a.bundle.read_bytes());audit(task,bundle)
        data={name:bytes.fromhex(value) for name,value in bundle['images_hex'].items()};plan=load_plan(task,bundle)
        a.out.mkdir(parents=True,exist_ok=True)
        for name,b in data.items():
            (a.out/(name+'.bin')).write_bytes(b)
            (a.out/(name+'.mem')).write_text(''.join(f'{int.from_bytes(b[i:i+16],"little"):032x}\n' for i in range(0,len(b),16)),encoding='ascii')
        (a.out/'loader-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        (a.out/'manifest.json').write_text(json.dumps({k:v for k,v in bundle.items() if k!='images_hex'},indent=2)+'\n')
    except (OSError,ValueError,KeyError) as e:p.exit(2,str(e)+'\n')
    print('PASS emitted three audited image/PM pairs and qualification loader plan')
if __name__=='__main__':main()
