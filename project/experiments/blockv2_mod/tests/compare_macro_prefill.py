"""Report complete logits against FP32; metrics are not automatic qualification."""
import argparse,json
from pathlib import Path
import numpy as np
from macro_assets import filehash
p=argparse.ArgumentParser()
for name in ('execution','reference','assets','graph','output'):p.add_argument(name,type=Path)
a=p.parse_args()
execution=json.loads(a.execution.read_text());reference=json.loads(a.reference.read_text())
assets=json.loads(a.assets.read_text());graph=json.loads(a.graph.read_text())
if execution['status']!='all_instructions_executed':raise ValueError('incomplete native execution')
if assets['checkpoint_files_sha256']!=reference['checkpoint_files_sha256']:raise ValueError('reference checkpoint mismatch')
if execution['plan_sha256']!=assets['plan_sha256'] or graph['source_model_sha256']!=assets['graph_sha256']:
 raise ValueError('reference graph/plan mismatch')
input_row=next(r for r in assets['regions'] if r['name']=='input_ids')
origin=input_row['origin']
tokens=origin['tokens'] if 'tokens' in origin else [origin['token']]
if tokens!=reference['tokens'][0]:raise ValueError('different runtime tokens')
row=next(r for r in execution['outputs'] if r['value']=='logits')
path=a.execution.parent/row['file']
if filehash(path)!=row['sha256'] or filehash(a.reference.parent/'logits.npy')!=reference['logits_sha256']:
 raise ValueError('output seal')
shape=graph['values']['logits']['shape']
actual=np.fromfile(path,dtype='<i4').astype(np.float64).reshape(shape)*2.0**row['exponent']
expected=np.load(a.reference.parent/'logits.npy').astype(np.float64)
if actual.shape!=expected.shape or not np.isfinite(actual).all() or not np.isfinite(expected).all():
 raise ValueError('logits shape/finite values')
error=actual-expected;positions=[]
for i,(x,y) in enumerate(zip(actual.reshape(-1,shape[-1]),expected.reshape(-1,shape[-1]))):
 positions.append({'position':i,'native_top1':int(x.argmax()),'FP32_top1':int(y.argmax()),
  'top1_agrees':bool(x.argmax()==y.argmax()),
  'cosine':float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y))),
  'relative_l2':float(np.linalg.norm(x-y)/np.linalg.norm(y)),
  'max_abs_error':float(np.max(np.abs(x-y)))})
result={'scope':'full short-stage logit comparison; quantized macro output versus checkpoint FP32',
 'positions':positions,'plan_sha256':execution['plan_sha256'],'native_output_sha256':row['sha256'],
 'reference_output_sha256':reference['logits_sha256'],
 'execution_receipt_sha256':filehash(a.execution),
 'reference_receipt_sha256':filehash(a.reference),
 'asset_manifest_sha256':filehash(a.assets),
 'graph_file_sha256':filehash(a.graph),
 'comparison_source_sha256':filehash(Path(__file__)),
 'all_top1_agree':all(r['top1_agrees'] for r in positions),
 'numerical_qualification':False,'reason':'comparison metrics; no calibrated end-to-end acceptance threshold asserted',
 'time_ps':execution['time_ps'],'timing_calibrated':execution['timing_calibrated']}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
