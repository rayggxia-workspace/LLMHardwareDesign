"""Independent route-stage exact functional, RC, graph and endpoint reception."""
import argparse
from common import *
from route_audit import route_audit
from strict_electrical_audit import receive_strict
from gate_dependency import checked_gate,checked_post97
p=argparse.ArgumentParser();p.add_argument('--target',type=int,choices=[93,97],default=93);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gate',type=Path);p.add_argument('--postgate',type=Path);p.add_argument('--rc-replay',type=Path);p.add_argument('--strict-electrical',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False);src=sources();sm=artifacts(a.stage);need(sm['stage']in('grt','routerepair','caprepair'),'actual routing stage');previous=Path(sm['previous_directory']);pure=sm['stage']=='grt'
from incremental_audit import require_incremental
incremental_required=require_incremental(a.stage,previous)
if a.target==93:
 from receive_physical import audit,library
 from admission93 import admit
 rawpass='PASS_COMPLETE_RAW_GATE';postpass='PASS_COMPLETE_POSTPHYSICAL_GATE';postcheck=checked_gate
else:
 from receive97 import audit,library
 from admission97 import admit,R97
 rawpass='PASS97_SELECTED_RAW_GATE';postpass='PASS97_SELECTED_POSTPHYSICAL_GATE';postcheck=checked_post97
 if a.gate is None:a.gate=R97/'gatereceive02'
r=audit(a.stage,a.prepared,a.out,a.gate,None if pure else a.postgate);net=load(a.stage/'final.json')['modules']['chain'+str(a.target)];r['routing']=route_audit(a.stage,previous,net,library(LIB),pure)
if incremental_required:
 from incremental_audit import audit_incremental
 r['incremental_change_audit']=audit_incremental(a.stage,previous,a.out)
if sm.get('candidate')in('incremental-joint-fourcap-50ps93','incremental-joint-onecap-50ps97'):
 from cap_audit import audit_cap
 from receive_physical import geometry_connectivity
 mid=load(a.stage/'capisolated.json')['modules']['chain'+str(a.target)];before=load(previous/'final.json')['modules']['chain'+str(a.target)];r['exact_intermediate_frozen_cap_isolation']=audit_cap(a.stage,previous,before,mid,library(LIB));r['intermediate_cap_geometry']=geometry_connectivity((a.stage/'capisolated.def').read_text(),mid,library(LIB),before)
if sm['stage']=='caprepair':
 from cap_audit import audit_cap
 r['explicit_cap_buffer_certificate']=audit_cap(a.stage,previous,load(previous/'final.json')['modules']['chain'+str(a.target)],net,library(LIB))
if pure and a.postgate is not None:
 postcheck(a.postgate,a.prepared,admit(),previous);r['postphysical_gate_status']=postpass+'_REUSED_EXACT_UNCHANGED_CTS_NETLIST';r['postphysical_gate_receipt_sha256']=sha(a.postgate/'receipt.json');r['executed_gate_stage_manifest_sha256']=sha(previous/'manifest.json')
if a.rc_replay is not None:
 from rc_replay_audit import audit_replay
 r['RC_replay']=audit_replay(a.stage,a.rc_replay,a.out)
r['strict_electrical_status']='NOT_EXECUTED'
if a.strict_electrical is not None:r['strict_electrical']=receive_strict(a.stage,a.strict_electrical);r['strict_electrical_status']=r['strict_electrical']['status']
r['physical_stage_accepted']=a.strict_electrical is not None and r['strict_electrical']['all_electrical_maxima_met'] and a.rc_replay is not None and r['raw_gate_status']==rawpass and r['postphysical_gate_status']==postpass+('_REUSED_EXACT_UNCHANGED_CTS_NETLIST'if pure else'')and r['all_declared_internal_timing_electrical_closed']is True
put(a.out/'receipt.json',{'schema':'physical98-route-receipt-v1','status':'PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE','source':src,'result':r,'limits':['Purposely nonmanufacturable research library. No actual SRAM/PG/tap/fill/LVS.','All terminal loads and clock propagation retained; external input drive unmodeled.','M2-M10 research routing is not M1-M8-fixed customizable-base qualification.']});print('PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE')
