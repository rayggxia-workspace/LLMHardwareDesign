"""Build a source-only frozen input archive; upload and Slurm submission separate."""
from pathlib import Path
import hashlib,json,tarfile,sys
R=Path(__file__).resolve().parents[4];P=Path(__file__).resolve().parent
stage=int(sys.argv[1]);assert stage>0
files=list((R/'project/rtl/control_v1').glob('*.sv'))+list((R/'project/rtl/r_local_state').glob('*.sv'))
files+=list((R/'project/rtl/block_v2').glob('*'))+list((R/'project/rtl/block_feed_v1').glob('*.sv'))+[R/'project/rtl/block_v1/transaction6k.sv']
files+=[R/'project/experiments/control_v1'/n for n in ('test_system.cpp','test_adapter_r.cpp','test_c.cpp','test_route.cpp','test_s_arbiter.cpp','test_reset.cpp','test_status.cpp','BUF_X16.v','native_t_lint.vlt','native_r_lint.vlt','run.py')]
files+=[P/'run.py',P/'run.sbatch',Path(__file__)]
manifest={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files if p.is_file()}
index=P/f'INPUTS-{stage:02}.json';assert not index.exists()
index.write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
archive=P/f'source-{stage:02}.tar';assert not archive.exists()
with tarfile.open(archive,'w')as t:
 for n in manifest:t.add(R/n,arcname=n)
 t.add(index,arcname='INPUTS.json')
print(json.dumps({'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'input_count':len(manifest)}))
