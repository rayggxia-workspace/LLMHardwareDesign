"""Strict Issue93 admission: numerical receipts, exact mapped RTL and input bytes."""
from common import *
R93=Path('/public/home/yuzelu/RuizhiLiang/issue93-gamma-stream-20261025')
SOURCE=R93/'phase5';MAP=R93/'map-b001';INPUT=R93/'input02'
def admit():
 need(sha(SOURCE/'binding.json')=='f93f7f7329fca535c4ff140967751eb50e1244b4d92ffc665ad8bb87900dd86f','frozen source binding bytes');bd=load(SOURCE/'binding.json');need(bd['commit']=='4815ed601801d0d6725163a8c059e9f5b774e466','frozen93 functional source')
 for n,h in bd['sources'].items():need(sha(SOURCE/n)==h,'upstream original source '+n)
 need(sha(MAP/'manifest.json')=='95d4b0b0fe95398b4b5de301dc92df749ab7ade8656512c3687427b03684a73b','frozen actual map manifest');mm=artifacts(MAP);im=artifacts(INPUT)
 need(sha(R93/'cost01.json')=='b938eb3efc1567d7b0f5dff5cd37a202c008a219b4d005923a4d95e77c40661b','strict inventory receipt bytes');cost=load(R93/'cost01.json');need(cost['schema']=='gamma93-cost-v1'and cost['status']=='PASS_L2_AND_LOGIC_INVENTORY_NOT_PHYSICAL_SIGNOFF','exact arithmetic/memory inventory')
 need(mm['schema']=='gamma93-run-v1'and mm['status']=='LOGIC_ONLY_MAPPED_NOT_PPA'and mm['top']=='chain93'and mm['baseline']is False,'actual93 mapping')
 need(mm['library_sha256']==sha(LIB),'same mapped Liberty')
 for n,h in bd['sources'].items():
  if n.startswith('project/rtl/'):need(mm['source']['sources'].get(n)==h,'same actual mapped RTL '+n)
 need(im['schema']=='gamma93-input-v1'and im['status']=='PASS_VERIFIED_INPUTS_NOT_RTL','actual input producer')
 for e in im['artifacts']:need(sha(INPUT/e['path'])==e['sha256'],'complete input SHA')
 rec=[]
 for stall in (0,1):
  p=R93/f'receipt-s{stall}04.json';need(sha(p)==['d106cc3e004bae10535e9caadc825cdabeacebadfe1821596ae2270f88a26d63','025a81883efdb64a31aa4ce43ffe3ed5fd9c51a485b6df4e348640493539cc44'][stall],'frozen strict L2 bytes');r=load(p);run=R93/f'rtl-s{stall}03';rm=artifacts(run)
  need(r['schema']=='gamma93-receipt-v1'and r['status']=='PASS_GAMMA_INTEGER_AND_PROTOCOL','independent L2 acceptance')
  need(type(r['stall'])is int and r['stall']==stall and r['source']==bd and r['run_source']==rm['source'],'L2 exact source/stall')
  for key,value in {'records':51,'bit_exact_success_outputs':48,'expected_zero_den_records':1,'actual_bad_transport_runs_rejected':2}.items():need(type(r[key])is int and r[key]==value,'L2 cohort count '+key)
  need(r['run_manifest_sha256']==sha(run/'manifest.json')and r['input_manifest_sha256']==sha(INPUT/'manifest.json'),'L2 exact input/run')
  need(rm['status']=='RTL_EXECUTED_NOT_RECEIVED'and rm['baseline']is False and type(rm['stall'])is int and rm['stall']==stall,'actual qualifying run')
  rec.append({'path':str(p),'sha256':sha(p),'run_directory':str(run),'run_manifest_sha256':sha(run/'manifest.json')})
 return {'schema':'admission98-93-v1','source':bd,'source_directory':str(SOURCE),'mapping_directory':str(MAP),'mapping_manifest_sha256':sha(MAP/'manifest.json'),'input_directory':str(INPUT),'input_manifest_sha256':sha(INPUT/'manifest.json'),'inventory_receipt_sha256':sha(R93/'cost01.json'),'L2':rec,'gate_exception':'RTL output-register epoch seed is not applied to mapped output pins. Gate repeats same numeric last command without state injection; terminal gate evidence excluded.'}
