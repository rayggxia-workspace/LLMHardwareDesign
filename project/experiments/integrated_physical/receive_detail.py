"""Independent actual detailed-route and RCX reception, never manufacture signoff."""
import argparse,csv,re
from common import *
from route_audit import same_wiring
from detail_spef import audit_spef
from detail_ledger import audit_ledger
from gate_dependency import checked_gate,checked_post97
from receive_physical import block,rows
p=argparse.ArgumentParser();p.add_argument('--target',type=int,choices=[93,97],required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--readback',type=Path);p.add_argument('--gate',type=Path);p.add_argument('--postgate',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);need(sm['stage']=='drt'and sm['detail_seed']==42 and sm['detail_iterations']==8 and sm['detail_child_seconds']==1100,'fixed detailed pilot');previous=Path(sm['previous_directory']);artifacts(previous)
if a.target==93:
 from receive_physical import audit
 from admission93 import admit
 postcheck=checked_gate;rawpass='PASS_COMPLETE_RAW_GATE';postpass='PASS_COMPLETE_POSTPHYSICAL_GATE'
else:
 from receive97 import audit
 from admission97 import admit,R97
 postcheck=checked_post97;rawpass='PASS97_SELECTED_RAW_GATE';postpass='PASS97_SELECTED_POSTPHYSICAL_GATE'
 if a.gate is None:a.gate=R97/'gatereceive02'
r=audit(a.stage,a.prepared,a.out,a.gate);net=load(a.stage/'final.json')['modules']['chain'+str(a.target)];old=load(previous/'final.json')['modules']['chain'+str(a.target)];identity=same_wiring(old,net);identity['final_verilog_byte_identical']=sha(previous/'final.v')==sha(a.stage/'final.v');need(sm['automatic_repairs']is False and sm['antenna_repair']is False and sm['placement_changes']is False and sm['PG_tap_fill_inserted']is False,'no hidden cell/placement/PG repair');need(block((previous/'placed.def').read_text(),'COMPONENTS ','END COMPONENTS')==block((a.stage/'placed.def').read_text(),'COMPONENTS ','END COMPONENTS'),'all original physical instance locations unchanged')
log=(a.stage/'flow.log').read_text();norm=block(log,'BEGIN_EMPTY_REFERENCE_NORMALIZATION','END_EMPTY_REFERENCE_NORMALIZATION');need(norm.strip()=='REMOVED_EMPTY_GROUND_REFERENCE=zero_','exact only empty GROUND metadata normalization');dr=block(log,'BEGIN_DETAILED_ROUTE','END_DETAILED_ROUTE');drccounts=re.findall(r'\[INFO DRT-0199\]\s+Number of violations = (\d+)\.',dr);need(drccounts and int(drccounts[-1])==0 and(a.stage/'detail.drc').read_bytes()==b'','actual executed DRT zero violations and empty final report');need(block(log,'BEGIN_ROUTE_CONNECTIVITY','END_ROUTE_CONNECTIVITY').strip()=='DESIGN_IS_ROUTED=1','actual all nets routed');ant=block(log,'BEGIN_ANTENNA_CHECK','END_ANTENNA_CHECK');need('Found 0 net violations.'in ant and'Found 0 pin violations.'in ant and'ANTENNA_VIOLATIONS=0'in ant,'actual zero antenna violations under available rules');rc=audit_spef(a.stage,net);conservation=rc.pop('net_conservation');put(a.out/'cap-conservation.json',conservation);rc['conservation_sha256']=sha(a.out/'cap-conservation.json');r['detailed_route']={'status':'PASS_ACTUAL_DRT_DRC_CONNECTIVITY_AND_ANTENNA_CHECKS','iteration_violation_counts':list(map(int,drccounts)),'electrical_identity':identity,'RCX':rc,'layer_ledger':audit_ledger(a.stage,net),'PG':'absent, no routing capacity reservation or supply network qualification'}
r['detailed_readback_status']='NOT_EXECUTED'
if a.readback is not None:
 rm=artifacts(a.readback);need(rm['status']=='EXACT_EXTRACTED_RCX_READBACK_EXECUTED_NOT_RECEIVED'and rm['stage_directory']==str(a.stage)and rm['stage_manifest_sha256']==sha(a.stage/'manifest.json'),'same detailed readback stage')
 for n in('final.odb','final.sdc','route.spef','final.json'):need(rm['inputs'][n]==sha(a.stage/n),'exact readback input '+n)
 for q in(LIB,TECH,LEF,P/'rcx_patterns.rules'):need(rm['views'][str(q)]==sha(q),'same readback library/rules')
 counts=list(csv.DictReader((a.readback/'counts.tsv').read_text().splitlines(),delimiter='\t'));need(len(counts)==2 and[x['load_fF']for x in counts]==['1','10'],'both actual readback loads')
 for k,c,scenario in zip((1,10),counts,r['scenarios']):
  for name in('r2r','setup','hold'):
   x=rows(a.stage/f'{name}-load{k}.tsv');y=rows(a.readback/f'{name}-load{k}.tsv');need(sorted(x,key=lambda q:q['endpoint'])==sorted(y,key=lambda q:q['endpoint']),'every endpoint/slack/startpoint reproduces from extracted SPEF '+name)
  for label,key in [('max slew','max_slew'),('max capacitance','max_capacitance'),('max fanout','max_fanout')]:need(c[key].isdigit()and int(c[key])==scenario['violations'][label],'actual separate readback count matches report '+label)
 r['detailed_readback_status']='PASS_EXACT_FULL_ENDPOINTS_AND_ELECTRICAL_COUNTS';r['detailed_readback_manifest_sha256']=sha(a.readback/'manifest.json')
if a.postgate is not None:postcheck(a.postgate,a.prepared,admit(),previous);r['postphysical_gate_status']=postpass+'_REUSED_EXACT_UNCHANGED_ROUTED_GRAPH';r['postphysical_gate_receipt_sha256']=sha(a.postgate/'receipt.json')
r['physical_stage_accepted']=False # Strict complete driver cap/slew checks and exact gate are mandatory before closure.
put(a.out/'receipt.json',{'schema':'physical98-detail-receipt-v1','status':'PASS_RECEPTION_OF_DETAILED_EVIDENCE_NOT_AUTOMATIC_CLOSURE','source':sources(),'result':r,'limits':['Actual detailed RCX with explicit PF/OHM units and coupling reduction1; not manufacturing-qualified extraction.','Whole store82 remains cut; no actual macro, PG/tap/fill/LVS, upstream drive or fixed-base qualification.']});print('PASS_RECEPTION_OF_DETAILED_EVIDENCE_NOT_AUTOMATIC_CLOSURE')
