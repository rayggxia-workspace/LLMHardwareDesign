"""Bind real RTL behavioral proofs to the exact full-assembly closure."""
import argparse,json,hashlib
from pathlib import Path
from command_pipeline_contract import SERVICE_PIPELINE,CAPABILITY_RTL
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser()
p.add_argument('--assembly-receipt',type=Path,required=True)
p.add_argument('--evidence',type=Path,nargs='+',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assembly=json.loads(a.assembly_receipt.read_text())
expected={k:v for k,v in SERVICE_PIPELINE.items() if k!='revision'}
if not assembly.get('elaboration_accepted'):raise ValueError('full assembly required')
found={};sources={};proofs=[];slots=None
for path in a.evidence:
 d=json.loads(path.read_text());proof_sources=set()
 if d.get('passed') is not True:raise ValueError('failed evidence '+str(path))
 if d.get('evidence_kind') not in ('rtl_behavior','rtl_tlm_differential'):raise ValueError('RTL behavior evidence required; model-only receipt cannot qualify hardware')
 for name,h in d.get('evidence',{}).items():
  if digest(Path(name))!=h:raise ValueError('modified execution log '+name)
 for name,h in d['source_sha256'].items():
  f=Path(name)
  if digest(f)!=h:raise ValueError('stale evidence source '+name)
  if f.suffix in ('.sv','.svh','.v') and name not in d.get('testbench_sources',[]):
   key=str(f.resolve())
   if key in assembly['source_sha256']:
    if assembly['source_sha256'][key]!=h:raise ValueError('RTL differs from assembled base '+key)
    sources[key]=h;proof_sources.add(f.name)
 for key,value in d.get('verified_capabilities',{}).items():
  if key in expected:
   if type(value)!=type(expected[key]) or value!=expected[key]:raise ValueError('capability mismatch '+key)
   if CAPABILITY_RTL[key] not in proof_sources:raise ValueError('capability RTL absent from assembly: '+key)
   found[key]=value
 if 'read_slots_per_owner' in d:
  if slots and slots!=(d['read_slots_per_owner'],d['write_slots_per_owner']):raise ValueError('source adapter capacities disagree')
  if 'native64_dma_read_window_client.sv' not in proof_sources:raise ValueError('read adapter absent from assembly')
  slots=(d['read_slots_per_owner'],d['write_slots_per_owner'])
 proofs.append({'path':str(path.resolve()),'sha256':digest(path)})
if found!=expected or slots is None:raise ValueError('missing verified capabilities: '+str(set(expected)-set(found)))
result={'schema':'command-pipeline-capacity/1','passed':True,'source_sha256':sources,
 'read_slots_per_owner':slots[0],'write_slots_per_owner':slots[1],
 'service_pipeline':SERVICE_PIPELINE,'proofs':proofs,'assembly_receipt_sha256':digest(a.assembly_receipt),
 'scope':'RTL behavior plus exact full-assembly source closure; full model execution separately required'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
