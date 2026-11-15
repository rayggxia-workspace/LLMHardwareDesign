"""Join complete short Qwen execution evidence; no physical or broad quality claim."""
from pathlib import Path
from hashlib import sha256
import json, sys
from native_package_runtime import load
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/architecture-revision-185'
evidence={}
def hashed(p):
 p=Path(p);h=sha256(p.read_bytes()).hexdigest();evidence[str(p.resolve())]=h;return h
def read(p):
 p=Path(p);hashed(p);return json.loads(p.read_text())
proof=read(EV/'selected-nine-assembly-114958/receipt.json')
assert proof['elaboration_accepted'] and len(proof['functional_instances'])==30
assert len(proof['LC_targets'])==9
for name,h in proof['source_sha256'].items():
 assert hashed(Path(name))==h, ('assembly source changed',name)
admission=read(EV/'pr185-admission-114959/receipt.json')
assert admission['architecture_admission']
for name,h in admission['sources'].items():
 p=Path(name);p=p if p.is_absolute() else ROOT/p
 assert hashed(p)==h, ('admission source changed',name)
phases={}
for stage,job,exactname,fpname,assetname,refname,expected_calls,expected_pages,expected_tensors in [
 ('prefill',115069,'prefill-bit-exact-115071.json','prefill-comparison-115071.json',
  'macro-prefill-assets-114989/assets.json','graph-numeric-reference-115054/receipt.json',141490,13,651),
 ('decode',115084,'decode-bit-exact-115086.json','decode-FP32-comparison-115100.json',
  'macro-decode-assets-115071/assets.json','graph-numeric-reference-115085/receipt.json',70457,4,723)]:
 package=EV/'shared-memory-bound-packages-114908'/(stage+'-package')
 manifest,payloads,pages=load(package)
 hashed(package/'manifest.json')
 runpath=EV/('macro-'+stage+'-'+str(job))/'receipt.json'
 run=read(runpath);exact=read(EV/exactname);fp=read(EV/fpname);assets=read(EV/assetname);ref=read(EV/refname)
 assert run['status']=='all_instructions_executed'
 assert run['completed_calls']==run['native_calls']==manifest['native_calls']==expected_calls
 assert run['pages_executed']==len(pages)==expected_pages and not run['active_calls']
 assert run['package_manifest_sha256']==hashed(package/'manifest.json')
 assert run['asset_manifest_sha256']==hashed(EV/assetname)
 assert run['plan_sha256']==manifest['plan_sha256']==exact['plan_sha256']==fp['plan_sha256']==ref['plan_sha256']==assets['plan_sha256']
 assert manifest['graph_sha256']==assets['graph_sha256']==ref['graph_sha256']
 assert exact['all_produced_tensors_bit_exact'] and not exact['mismatches']
 assert exact['tensors_checked']==len(ref['committed_values'])==expected_tensors
 assert exact['execution_receipt_sha256']==fp['execution_receipt_sha256']==hashed(runpath)
 assert exact['reference_receipt_sha256']==hashed(EV/refname)
 assert exact['committed_state_sha256']==run['committed_state']['sha256']
 assert exact['asset_manifest_sha256']==fp['asset_manifest_sha256']==run['asset_manifest_sha256']
 assert exact['comparison_source_sha256']==hashed(ROOT/'tests/compare_macro_committed_reference.py')
 assert fp['comparison_source_sha256']==hashed(ROOT/'tests/compare_macro_prefill.py')
 assert fp['all_top1_agree']
 assert len(fp['positions'])==(2 if stage=='prefill' else 1)
 hw=json.loads(payloads['hardware.json']);wire=json.loads(payloads['candidate-wiring.json'])
 assert hw['base_id']==run['base_id']==wire['base_id']
 assert wire['rtl_binding_complete'] and not wire['physical_binding_complete']
 # Preserve the actual model provenance of each run. Do not relabel old source
 # hashes as current; prefill predates the LC admission-only strengthening.
 phases[stage]={'plan_sha256':run['plan_sha256'],'graph_sha256':manifest['graph_sha256'],
  'base_id':hw['base_id'],'wiring_sha256':manifest['payloads']['candidate-wiring.json']['sha256'],
  'calls':expected_calls,'mother_pages':expected_pages,'tensors':expected_tensors,
  'bytes_checked':exact['bytes_checked'],'time_ps':run['time_ps'],
  'FP32_positions':fp['positions'],'execution_sources':run['source_sha256']}
assert phases['prefill']['base_id']==phases['decode']['base_id']
assert phases['prefill']['wiring_sha256']==phases['decode']['wiring_sha256']
prefill=read(EV/'macro-prefill-115069/receipt.json')
decode_assets=read(EV/'macro-decode-assets-115071/assets.json')
bridge=read(EV/'decode-state-inputs-115071/runtime-inputs.json')
assert decode_assets['source_execution_plan_sha256']==bridge['source_plan_sha256']==prefill['plan_sha256']
assert decode_assets['source_state_sha256']==bridge['source_state_sha256']==prefill['committed_state']['sha256']
assert bridge['destination_plan_sha256']==phases['decode']['plan_sha256'] and len(bridge['inputs'])==72
assert decode_assets['input_token']==phases['prefill']['FP32_positions'][-1]['native_top1']
result={'schema':'Qwen-short-functional-acceptance/1','Qwen_accepted':True,
 'acceptance_scope':'complete 36-layer B1 S2 prefill plus one history-two decode; exact integer tensor results and observed three-position FP32 top-1 agreement',
 'phases':phases,'real_prefill_KV_consumed':True,'input_token':decode_assets['input_token'],
 'timing_calibrated':False,'physical_implementation_accepted':False,
 'broad_model_accuracy_qualified':False,'continuous_request_throughput_accepted':False,
 'PM_loading_and_external_stage_transition_timing_included':False,
 'remaining_benchmarks_accepted':False,'source_sha256':hashed(Path(__file__)),'evidence_sha256':evidence}
out=Path(sys.argv[1]);out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('phases','evidence_sha256')}))
