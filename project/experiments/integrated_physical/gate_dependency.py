"""Reject empty or detached gate PASS receipts at the final physical admission gate."""
from common import *
from admission93 import INPUT

def checked_gate(folder,prepared,admission,physical=None):
 q=load(folder/'receipt.json');post=physical is not None;status='PASS_POSTPHYSICAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION'if post else'PASS_ACTUAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION';need(q['schema']==('gate98-postphysical-v1'if post else'gate98-receipt-v1')and q['status']==status and q['admission']==admission and q['prepared_manifest_sha256']==sha(prepared/'manifest.json'),'same exact schema/source gate receipt')
 need(type(q.get('results'))is list and len(q['results'])==2,'two actual full gate conditions');dep=Path(q['dependency_prepared_directory']);build=Path(q['build_directory']);bm=artifacts(build);artifacts(dep);need(q['prepared_directory']==str(prepared)and q['build_manifest_sha256']==sha(build/'manifest.json')and bm['prepared_manifest_sha256']==sha(dep/'manifest.json')and sha(build/'obj/Vchain93')==bm['binary_sha256'],'same gate prepared/source/binary chain')
 need(bm['status']==('POSTPHYSICAL93_GATE_BUILT_NOT_EXECUTED'if post else'ACCEPTED93_GATE_BUILT_NOT_EXECUTED'),'correct actual gate binary type')
 if not post:need(dep==prepared,'raw gate prepared directory')
 for stall,row in enumerate(q['results']):
  need(type(row['stall'])is int and row['stall']==stall and type(row['records'])is int and row['records']==51 and row['status']=='PASS_ALL_COMPLETE_GATE_INTEGER_OUTPUTS_AND_DECLARED_PROTOCOL'and type(row['outcomes'])is list and len(row['outcomes'])==51,'full typed gate condition and count');run=Path(row['run_directory']);rm=artifacts(run);need(row['run_manifest_sha256']==sha(run/'manifest.json')and rm['build_manifest_sha256']==sha(build/'manifest.json')and rm['prepared_manifest_sha256']==sha(dep/'manifest.json')and rm['input_manifest_sha256']==sha(INPUT/'manifest.json')and type(rm['stall'])is int and rm['stall']==stall,'actual gate run links');need(rm['status']==('POSTPHYSICAL93_GATE_EXECUTED_NOT_RECEIVED'if post else'ACCEPTED93_GATE_EXECUTED_NOT_RECEIVED'),'actual simulation terminal status');need(len((run/'actual.jsonl').read_text().splitlines())==51 and row['protocol']==load(run/'actual.jsonl.protocol.json'),'complete actual output/protocol evidence')
 if post:need(q['postphysical']['physical_stage_manifest_sha256']==sha(physical/'manifest.json')and q['postphysical']['physical_final_verilog_sha256']==sha(physical/'final.v'),'precise postphysical netlist gate')
 return q
