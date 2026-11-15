"""Compare declared live-outs after whole-package execution of a different schedule.

An intermediate intentionally left only in SRAM is not a required DDR output.
Source graph, hardware and complete allocation must match the sealed oracle plan.
"""
import argparse,json
from pathlib import Path
from macro_state import load
from macro_assets import filehash
from native_package_runtime import load as load_package
p=argparse.ArgumentParser()
for name in ('execution','reference','oracle_package','selected_package','plan','output'):
 p.add_argument(name,type=Path)
p.add_argument('--all-produced',action='store_true')
a=p.parse_args()
execution=json.loads(a.execution.read_text());reference=json.loads(a.reference.read_text())
plan=json.loads(a.plan.read_text())
om,op,_=load_package(a.oracle_package);nm,np,_=load_package(a.selected_package)
if reference['plan_sha256']!=om['plan_sha256']:raise ValueError('oracle package mismatch')
if execution['plan_sha256']!=nm['plan_sha256'] or plan['plan_sha256']!=nm['plan_sha256']:
 raise ValueError('execution / selected plan mismatch')
if om['graph_sha256']!=nm['graph_sha256'] or reference['graph_sha256']!=nm['graph_sha256']:
 raise ValueError('different source graphs')
if op['storage.json']!=np['storage.json'] or op['hardware.json']!=np['hardware.json']:
 raise ValueError('different hardware or allocation')
if execution['status']!='all_instructions_executed' or execution.get('completed_calls')!=nm['native_calls']:
 raise ValueError('whole instruction package not completed')
meta,words=load(a.execution.parent/'committed-state.bin')
if meta['plan_sha256']!=nm['plan_sha256'] or meta['asset_manifest_sha256']!=execution['asset_manifest_sha256']:
 raise ValueError('execution state binding mismatch')
if execution['committed_state']['sha256']!=meta['sha256']:raise ValueError('state seal')
names=sorted(reference['committed_values']) if a.all_produced else plan.get('exported_values')
if not names or not set(names)<=set(reference['committed_values']):raise ValueError('missing exported reference values')
checked=0;failures=[]
for name in names:
 row=reference['committed_values'][name];path=a.reference.parent/row['file']
 if filehash(path)!=row['sha256']:raise ValueError('reference value seal')
 expected=path.read_bytes()
 if len(expected)!=row['bytes']:raise ValueError('reference extent')
 region=np['storage.json']['regions'][name]
 if region['base']!=row['base'] or region['bytes']!=row['bytes']:raise ValueError('reference layout')
 actual=bytearray()
 for offset in range(0,row['bytes'],64):
  actual.extend(words[row['base']+offset].slice(0,min(64,row['bytes']-offset)).require())
 if actual!=expected:
  first=next(i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y)
  failures.append({'value':name,'first_different_byte':first})
 checked+=len(expected)
result={'schema':'native-exported-graph-comparison/1','plan_sha256':nm['plan_sha256'],
 'comparison_set':'all_produced' if a.all_produced else 'declared_liveouts',
 'oracle_plan_sha256':om['plan_sha256'],'whole_package_executed':True,
 'all_exported_values_bit_exact':not failures,'values_checked':names,'bytes_checked':checked,
 'mismatches':failures,'execution_receipt_sha256':filehash(a.execution),
 'reference_receipt_sha256':filehash(a.reference),'comparison_source_sha256':filehash(Path(__file__)),
 'scope':'full graph live-outs and declared persistent state; elided DDR intermediates are not compared'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if failures:raise SystemExit(1)
