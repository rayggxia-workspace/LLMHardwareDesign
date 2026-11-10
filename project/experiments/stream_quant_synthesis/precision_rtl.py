"""Replay real FFN accumulator conversion and G payloads against unchanged RTL."""
import argparse
import json
import os
from pathlib import Path
import shutil
from prepare import REPO,sha
from run import execute,VERILATOR

HERE=Path(__file__).resolve().parent


def main(root):
    assert os.environ.get('SLURM_JOB_ID')
    out=root/'results';out.mkdir(exist_ok=False)
    q=root/'quality';report=json.loads((q/'precision.json').read_text());assert report['passed']
    env=dict(os.environ);env.pop('VERILATOR_ROOT',None)
    obj=out/'obj-real-G';rtl=REPO/'project/rtl/block_v2'
    result=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),job=os.environ['SLURM_JOB_ID'])
    result['verilator']=execute([VERILATOR,'--version'],out/'verilator.log',out,env)
    execute([VERILATOR,'--cc','--exe','--build','-j','4','--top-module','block_v2_g','-Wall',
             '-I'+str(rtl),'-Mdir',obj,rtl/'block_v2_g.sv',HERE/'tb_precision_g.cpp'],out/'g-build.log',out,env)
    log=execute([obj/'Vblock_v2_g',q/'g-real-vectors.txt'],out/'real-G.log',out,env)
    result['G']=json.loads(log.strip().splitlines()[-1]);assert result['G']['passed'] and result['G']['packets']==report['G_frames']
    folder=out/'real-rq';folder.mkdir();shutil.copyfile(q/'requant-vectors.txt',folder/'requant-vectors.txt')
    obj=folder/'obj'
    execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_requant4','-GQBITS=16',
             '-Wall','-j','4','--Mdir',obj,HERE/'w8_requantize4.sv',HERE/'tb_requant4.sv'],folder/'build.log',folder,env)
    log=execute([obj/'Vtb_requant4'],folder/'rtl.log',folder,env)
    assert 'REQUANT_RTL_PASS' in log and f"checks={report['requant_frames']}" in log
    result['requant']=dict(passed=True,frames=report['requant_frames'],log=log)
    result['input_sha256']={name:sha(q/name) for name in ('precision.json','g-real-vectors.txt','requant-vectors.txt')}
    result['passed']=True
    (out/'precision-rtl.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PRECISION_RTL_PASS '+json.dumps(dict(G=result['G']['packets'],requant=result['requant']['frames'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
