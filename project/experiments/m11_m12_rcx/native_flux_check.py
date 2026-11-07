"""Compare owner-partitioned charge to an independently discretized cavity."""
import json
import os
from pathlib import Path
import subprocess
from native_scene import write


def main():
    src=Path(__file__).resolve().parent
    out=Path(os.environ['COUPLING_OUT'])/'result'
    out.mkdir()
    with (out/'compile.log').open('xb') as log:
        subprocess.run(['g++','-std=c++20','-O3','-fopenmp',str(src/'native_flux_fv.cpp'),'-o',str(out/'flux_fv')],stdout=log,stderr=subprocess.STDOUT,check=True)
    reference=[]
    for step in [.25,.125,.0625]:
        raw=subprocess.check_output([str(out/'flux_fv'),str(step),os.environ['COUPLING_THREADS']])
        record=json.loads(raw)
        (out/('fv-'+str(step)+'.json')).write_bytes(raw)
        reference.append(record)
    entries=[(0,0,[-3,-.5,2,0,.5,3]),(0,1,[0,-.5,2,3,.5,3]),
             (1,1,[-4,-1,4,-.5,1,4.5]),
             (1,1,[-8.1,-4.1,.01,-8,4.1,8.1]),(1,1,[8,-4.1,.01,8.1,4.1,8.1]),
             (1,1,[-8,-4.1,.01,8,-4,8.1]),(1,1,[-8,4,.01,8,4.1,8.1]),
             (1,1,[-8,-4,8,8,4,8.1])]
    write(out/'cavity.bin',['split','grounded_shield'],entries,grounded=[1])
    (out/'masters.txt').write_text('0\n')
    solver=Path(os.environ['COUPLING_FLUX_SOLVER'])
    measured=[]
    for offset in [.25,.125,.0625]:
        with (out/('field-'+str(offset)+'.jsonl')).open('xb') as stream,(out/('field-'+str(offset)+'.log')).open('xb') as log:
            subprocess.run([str(solver),str(out/'cavity.bin'),str(out/'masters.txt'),os.environ['COUPLING_THREADS'],'1048576',str(offset),'222013'],stdout=stream,stderr=log,check=True)
        measured.append(json.loads((out/('field-'+str(offset)+'.jsonl')).read_text()))
    extrapolated={name:2*reference[-1][name]-reference[-2][name] for name in ['left_ff','right_ff']}
    result=dict(reference=reference,extrapolated=extrapolated,
                field=[dict(offset=o,total_ff=r['total_ff'],left_ff=r['values'][0][2],right_ff=r['values'][0][4],
                            left_sigma_ff=r['values'][0][3],right_sigma_ff=r['values'][0][5]) for o,r in zip([.25,.125,.0625],measured)],
                qualification='Independent mesh-refinement and field-offset control; inspect numerical differences before accepting local charge.')
    (out/'flux-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
