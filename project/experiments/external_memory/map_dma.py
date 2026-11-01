"""Map the tested DMA only. This does not qualify a new physical macro."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
RTL='project/rtl/external_memory/finite_dma.sv'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rtl-receipt',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    verified=json.loads(a.rtl_receipt.read_text())
    assert verified['passed'] and set(verified['results'])=={'cell','sram'}
    assert all(len(rows)==3 and all(row['passed'] for row in rows) for rows in verified['results'].values())
    assert all([(row['initial_reset'],row['initial_seed']) for row in rows]==[(1,156),(2,156),(2,157)] for rows in verified['results'].values())
    assert verified['source_sha256'][RTL]==sha(ROOT/RTL)
    assert len(os.sched_getaffinity(0))<=4
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    script=f'read_liberty -lib {lib}\nread_verilog -sv {ROOT/RTL}\nhierarchy -check -top finite_dma\n'
    script+='synth -top finite_dma -noabc\ndfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\ncheck -assert\n'
    script+='stat -liberty '+str(lib)+'\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (out/'map.ys').write_text(script)
    receipt=dict(passed=False,physical_qualified=False,source_sha256={RTL:sha(ROOT/RTL)},
                 rtl_receipt_sha256=sha(a.rtl_receipt),liberty_sha256=sha(lib),
                 started_unix=time.time(),affinity=sorted(os.sched_getaffinity(0)),
                 slurm_job_id=os.environ.get('SLURM_JOB_ID'))
    try:
        with (out/'tool.txt').open('w')as f:
            subprocess.run(['yosys','-V'],stdout=f,stderr=subprocess.STDOUT,check=True)
        with (out/'map.log').open('w')as f:
            subprocess.run(['yosys','-s',str(out/'map.ys')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
        module=json.loads((out/'mapped.json').read_text())['modules']['finite_dma']
        cells={}
        for cell in module['cells'].values():
            assert not cell['type'].startswith('$'),cell['type']
            cells[cell['type']]=cells.get(cell['type'],0)+1
        receipt.update(passed=True,cell_counts=cells,outputs={name:sha(out/name) for name in ('mapped.v','mapped.json','map.log','map.ys','tool.txt')})
    finally:
        receipt['ended_unix']=time.time()
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    main()
