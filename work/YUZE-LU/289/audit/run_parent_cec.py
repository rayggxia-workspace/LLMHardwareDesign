import sys,json,hashlib,subprocess
from pathlib import Path
p=Path(sys.argv[1]);base=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117'); actual=base/'cu/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base'; replay=p/'flow/results/nangate45/c-overlay-current/base'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
bind={}
for name in ['1_2_yosys.v','1_synth_lec.v']:
 assert (actual/name).read_bytes()==(replay/name).read_bytes();bind[name]=sha(actual/name)
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');groups=[]
for d in sorted((p/'abc').glob('_tmp_yosys-abc-*')):
 cmd=['yosys-abc','-c',f'read_lib {lib}; cec {d}/input.blif {d}/output.blif']
 with (d/'cec.log').open('w') as o:r=subprocess.run(cmd,stdout=o,stderr=subprocess.STDOUT)
 txt=(d/'cec.log').read_text();assert r.returncode==0 and 'Networks are equivalent' in txt,txt[-2000:]
 groups.append({'directory':str(d),'command':cmd,'input_sha':sha(d/'input.blif'),'output_sha':sha(d/'output.blif'),'log_sha':sha(d/'cec.log'),'passed':True})
assert groups
receipt={'passed':True,'actual_parent_netlists_byte_identical':bind,'groups':groups,'lib_sha':sha(lib),'scope':'Actual parent exact synthesis replay with retained ABC groups; combinational ABC technology mapping CEC proven. RTL normalization and sequential lowering require separate evidence.'}
(p/'cec-receipt.json').write_text(json.dumps(receipt,indent=2));print(receipt)
