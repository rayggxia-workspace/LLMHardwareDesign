"""Cross-check oracle matrix math with frozen M RTL vectors, report Qwen metrics."""
import json
from pathlib import Path
from collections import OrderedDict
import numpy as np
from native_graph_numeric_reference import Oracle
from macro_assets import filehash
ev=Path('evidence/architecture-revision-185');folder=ev/'projection-local-114576'
def words(p):return b''.join(bytes.fromhex(x)[::-1] for x in p.read_text().splitlines() if x)
cases=json.loads((folder/'cases.json').read_text())
for i,row in enumerate(cases):
 oracle=object.__new__(Oracle);oracle.storage={'weights':{'W':{'shape':[row['n'],row['k']]}}};oracle.cache=OrderedDict()
 oracle.weights={'W':np.frombuffer(words(folder/f'weights-{i}.hex'),dtype=np.uint8).reshape(row['n']//8,row['k']//128,1088)}
 x=np.frombuffer(words(folder/f'input-{i}.hex'),dtype='<i4')
 expected=np.frombuffer(words(folder/f'expected-{i}.hex'),dtype='<i4')
 got=oracle.matrix(x[:row['k']],'W')
 assert np.array_equal(got,expected[:row['n']]),i
root=ev/'graph-numeric-reference-115050';d=json.loads((root/'receipt.json').read_text())
record=d['outputs']['logits'];raw=root/record['file']
assert filehash(raw)==record['sha256']
x=np.fromfile(raw,dtype='<i4').astype(np.float64).reshape(record['shape'])*2.0**record['exponent']
ref=ev/'macro-prefill-reference-115013';refmeta=json.loads((ref/'receipt.json').read_text())
assert filehash(ref/'logits.npy')==refmeta['logits_sha256']
y=np.load(ref/'logits.npy').astype(np.float64);positions=[]
for i,(a,b) in enumerate(zip(x.reshape(-1,x.shape[-1]),y.reshape(-1,y.shape[-1]))):
 positions.append({'position':i,'native_top1':int(a.argmax()),'FP32_top1':int(b.argmax()),
 'cosine':float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))),
 'relative_l2':float(np.linalg.norm(a-b)/np.linalg.norm(b)),'max_abs_error':float(np.abs(a-b).max())})
result={'M_RTL_cases':len(cases),'M_RTL_values':sum(r['n'] for r in cases),
 'full_Qwen_fixed_point_vs_FP32':positions,'TLM_match_checked':False,'scope':'numeric oracle qualification and quality metrics, not instruction execution acceptance'}
(ev/'graph-numeric-reference-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
