"""Early independent postphysical wrapper proof; not a completed gate receipt."""
import argparse
from common import *
from admission93 import admit
from post_audit import audit_post
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
pm,cert,proof=audit_post(a.original,a.prepared,a.out/'wrapper',admit())
put(a.out/'receipt.json',{'status':'PASS_WRAPPER_STRUCTURE_ONLY_GATE_STILL_PENDING','source':sources(),'resources':resource_snapshot(),'proof':proof,'structure':cert});print('PASS_WRAPPER_STRUCTURE_ONLY_GATE_STILL_PENDING')
