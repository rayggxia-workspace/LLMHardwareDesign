"""Independent route-stage exact functional, RC, graph and endpoint reception."""
import argparse
from common import *
from route_audit import route_audit
from gate_dependency import checked_gate,checked_post97
p=argparse.ArgumentParser();p.add_argument('--target',type=int,choices=[93,97],default=93);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gate',type=Path);p.add_argument('--postgate',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False);src=sources();sm=artifacts(a.stage);need(sm['stage']in('grt','routerepair'),'actual routing stage');previous=Path(sm['previous_directory']);pure=sm['stage']=='grt'
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
if pure and a.postgate is not None:
 postcheck(a.postgate,a.prepared,admit(),previous);r['postphysical_gate_status']=postpass+'_REUSED_EXACT_UNCHANGED_CTS_NETLIST';r['postphysical_gate_receipt_sha256']=sha(a.postgate/'receipt.json');r['executed_gate_stage_manifest_sha256']=sha(previous/'manifest.json')
r['physical_stage_accepted']=r['raw_gate_status']==rawpass and r['postphysical_gate_status']==postpass+('_REUSED_EXACT_UNCHANGED_CTS_NETLIST'if pure else'')and r['all_declared_internal_timing_electrical_closed']is True
put(a.out/'receipt.json',{'schema':'physical98-route-receipt-v1','status':'PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE','source':src,'result':r,'limits':['Purposely nonmanufacturable research library. No actual SRAM/PG/tap/fill/LVS.','All terminal loads and clock propagation retained; external input drive unmodeled.','M2-M10 research routing is not M1-M8-fixed customizable-base qualification.']});print('PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE')
