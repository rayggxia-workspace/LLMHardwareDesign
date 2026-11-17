import sys,re,json,subprocess,hashlib,shutil
from pathlib import Path
p=Path(sys.argv[1]);s=(p/'map.log').read_text()
# Yosys retained directories are recorded explicitly; only copy this job's ABC files.
paths=re.findall(r"Extracting gate netlist of module .*? to `([^']+)/input.blif'",s)
assert paths, 'No retained ABC input directory found'
actual=sorted(p.glob('_tmp_yosys-abc-*'));assert len(actual)==len(paths)==1
paths=actual
results=[]
for i,path in enumerate(paths):
 src=Path(path);src=src if src.is_absolute() else p/src
 dest=p/f'abc-group-{i}';shutil.copytree(src,dest)
 lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
 cmd=f'read_lib {lib}; cec {dest}/input.blif {dest}/output.blif'
 log=dest/'cec.log'
 with log.open('w') as o:r=subprocess.run(['yosys-abc','-c',cmd],stdout=o,stderr=subprocess.STDOUT)
 t=log.read_text();assert r.returncode==0 and ('Networks are equivalent' in t or 'Networks are equivalent after' in t),t[-3000:]
 results.append({'directory':str(dest),'proved':True,'input_sha':hashlib.sha256((dest/'input.blif').read_bytes()).hexdigest(),'output_sha':hashlib.sha256((dest/'output.blif').read_bytes()).hexdigest()})
(p/'receipt.json').write_text(json.dumps({'passed':True,'mapped_byte_identity':True,'mapped_sha':hashlib.sha256((p/'mapped.v').read_bytes()).hexdigest(),'groups':results,'scope':'Exact repeated synthesis output matches actual FAST netlist; ABC combinational mapping of each retained source-normalized logic group CEC-proven. Yosys RTL preprocessing and dfflibmap remain trusted transformations, not separately proved here.'},indent=2))
