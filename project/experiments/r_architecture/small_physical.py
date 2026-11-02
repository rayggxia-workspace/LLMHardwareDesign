"""Two bounded representative trials; independent 16-core flows, no filler work."""
from pathlib import Path
import concurrent.futures, subprocess, json, sys, os

ROOT=Path.cwd()
SCRIPT=Path(__file__).resolve().parent/'physical.py'

def run(item):
    cap,die=item
    out=ROOT/('B'+str(cap));out.mkdir(exist_ok=False)
    cmd=[sys.executable,str(SCRIPT),'--candidate','B'+str(cap),
         '--capacity',str(cap),'--die',str(die),'--density','0.40']
    with (out/'driver.log').open('w') as stream:
        result=subprocess.run(cmd,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
    return dict(capacity=cap,die_um=die,exit=result.returncode,path=str(out),
                qualified=False,command=cmd)

if __name__=='__main__':
    assert int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=32
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(run,[(256,1000),(1024,1600)]))
    (ROOT/'SMALL_PHYSICAL.json').write_text(json.dumps(rows,indent=2)+'\n')
    raise SystemExit(int(any(r['exit'] for r in rows)))
