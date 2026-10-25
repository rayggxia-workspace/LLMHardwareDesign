"""Route-stage independent gate dependency and RC/geometry reception."""
import argparse
from common import *
from receive_physical import audit,library
from route_audit import route_audit
from gate_dependency import checked_gate
from admission93 import admit
p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gate',type=Path);p.add_argument('--postgate',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False);src=sources();sm=artifacts(a.stage);need(sm['stage']=='grt','only actual pure global routing');previous=Path(sm['previous_directory']);r=audit(a.stage,a.prepared,a.out,a.gate);net=load(a.stage/'final.json')['modules']['chain93'];ra=route_audit(a.stage,previous,net,library(LIB));r['routing']=ra
if a.postgate is not None:
 checked_gate(a.postgate,a.prepared,admit(),previous);r['postphysical_gate_status']='PASS_COMPLETE_POSTPHYSICAL_GATE_REUSED_EXACT_UNCHANGED_CTS_NETLIST';r['postphysical_gate_receipt_sha256']=sha(a.postgate/'receipt.json');r['executed_gate_stage_manifest_sha256']=sha(previous/'manifest.json')
r['physical_stage_accepted']=r['raw_gate_status']=='PASS_COMPLETE_RAW_GATE'and r['postphysical_gate_status']=='PASS_COMPLETE_POSTPHYSICAL_GATE_REUSED_EXACT_UNCHANGED_CTS_NETLIST'and r['all_declared_internal_timing_electrical_closed']is True
put(a.out/'receipt.json',{'schema':'physical98-route-receipt-v1','status':'PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE','source':src,'result':r,'limits':['Purposely nonmanufacturable research library. No actual SRAM/PG/tap/fill/LVS.','All terminal loads and clock propagation retained; external input drive unmodeled.','M2-M10 research routing is not M1-M8-fixed customizable-base qualification.']});print('PASS_RECEPTION_OF_ROUTE_EVIDENCE_NOT_AUTOMATIC_CLOSURE')
