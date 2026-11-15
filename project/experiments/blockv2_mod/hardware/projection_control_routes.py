"""Actual descriptor signatures of projection_service_cluster's four providers."""
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def profile(topology,controller_ids):
    if type(topology) is not int or not 0<topology<2**32:raise ValueError('topology')
    return {'topology_id':topology,'targets':[
      {'group':owner,'id':identity,'rtl_module':'projection_service_cluster','hard_boundary':False,
       'routes':[
        {'schema':0x314d5347,'abi':0x02500002,'opcode':1,'completions':['service_done']},
        {'schema':0x3152504d,'abi':0x02504d03,'opcode':2,'completions':['scope_committed']},
        {'schema':0x314c5244,'abi':0x02500002,'opcode':1,'completions':['destination_commit_ack']},
        {'schema':0x31535744,'abi':0x02500002,'opcode':1,'completions':['destination_commit_ack']}],
       'scope':'projection/row-transfer controller subset; not a full control-owner implementation'}
      for owner,identity in controller_ids.items()],
      'rtl_sha256':sha256((ROOT/'rtl/control/projection_service_cluster.sv').read_bytes()).hexdigest(),
      'complete_base_admitted':False}
