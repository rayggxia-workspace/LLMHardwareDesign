"""Reuse the completed FD meshes; refine only the field's reporting offset."""
import json
import os
from pathlib import Path
import subprocess


out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
ref=Path(os.environ['COUPLING_FLUX_REFERENCE'])
proof=json.loads((ref/'flux-check.json').read_text())
solver=Path(os.environ['COUPLING_FLUX_SOLVER'])
records=[]
for offset in [.03125,.015625]:
    target=out/('offset-'+str(offset)+'.jsonl')
    with target.open('xb') as stdout,(out/('offset-'+str(offset)+'.log')).open('xb') as stderr:
        subprocess.run([str(solver),str(ref/'cavity.bin'),str(ref/'masters.txt'),os.environ['COUPLING_THREADS'],'4194304',str(offset),'222017'],stdout=stdout,stderr=stderr,check=True)
    r=json.loads(target.read_text())
    records.append(dict(offset=offset,total_ff=r['total_ff'],left_ff=r['values'][0][2],left_sigma_ff=r['values'][0][3],right_ff=r['values'][0][4],right_sigma_ff=r['values'][0][5]))
extrapolated={key:2*records[-1][key]-records[-2][key] for key in ['left_ff','right_ff']}
result=dict(field=records,zero_offset_extrapolation=extrapolated,independent_fd_extrapolation=proof['extrapolated'],
            changes={key:extrapolated[key]-proof['extrapolated'][key] for key in ['left_ff','right_ff']},
            qualification='Inspect independent-grid and offset convergence before accepting local charges.')
(out/'flux-refine.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
