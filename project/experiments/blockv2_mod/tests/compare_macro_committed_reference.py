"""Require every produced tensor to match the independent graph oracle exactly."""
import argparse,json
from pathlib import Path
from macro_state import load
from macro_assets import filehash
p=argparse.ArgumentParser()
for name in ('execution','reference','output'):p.add_argument(name,type=Path)
a=p.parse_args();execution=json.loads(a.execution.read_text());reference=json.loads(a.reference.read_text())
if execution['status']!='all_instructions_executed' or execution['plan_sha256']!=reference['plan_sha256']:
 raise ValueError('incomplete or different native plan')
if execution.get('completed_calls',0)!=execution.get('native_calls') or not execution.get('completed_calls'):
 raise ValueError('native instruction completion count mismatch')
if reference.get('schema')!='native-graph-numeric-reference/1' or not reference.get('committed_values'):
 raise ValueError('missing independent full-graph reference values')
meta,words=load(a.execution.parent/'committed-state.bin')
if meta['asset_manifest_sha256']!=execution['asset_manifest_sha256']:
 raise ValueError('committed state runtime assets mismatch')
if meta['plan_sha256']!=reference['plan_sha256'] or execution['committed_state']['sha256']!=meta['sha256']:
 raise ValueError('committed state identity mismatch')
checked=0;bytes_checked=0;failures=[]
for name,row in reference['committed_values'].items():
 path=a.reference.parent/row['file']
 if filehash(path)!=row['sha256']:raise ValueError('oracle output seal')
 expected=path.read_bytes()
 if len(expected)!=row['bytes']:raise ValueError('oracle output extent')
 actual=bytearray()
 for offset in range(0,row['bytes'],64):
  address=row['base']+offset
  actual.extend(words[address].slice(0,min(64,row['bytes']-offset)).require())
 if actual!=expected:
  first=next(i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y)
  failures.append({'value':name,'first_different_byte':first,'element':first//4})
 checked+=1;bytes_checked+=len(expected)
result={'schema':'native-full-graph-numeric-comparison/1','plan_sha256':reference['plan_sha256'],
 'all_produced_tensors_bit_exact':not failures,'tensors_checked':checked,'bytes_checked':bytes_checked,
 'mismatches':failures,
 'execution_receipt_sha256':filehash(a.execution),
 'reference_receipt_sha256':filehash(a.reference),
 'committed_state_sha256':meta['sha256'],
 'asset_manifest_sha256':execution['asset_manifest_sha256'],
 'comparison_source_sha256':filehash(Path(__file__)),
 'scope':'full fixed-point graph outputs and FFN intermediates; physical timing and FP32 accuracy are separate'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if failures:raise SystemExit(1)
