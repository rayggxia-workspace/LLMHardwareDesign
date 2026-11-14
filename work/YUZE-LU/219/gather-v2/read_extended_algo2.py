from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

from event_deploy import route_catalog
from publish_event_handoff import build
from route_contract import digest, read_base, require
from run import compile_event_ir
from adapter import bind_request
from handoff import verify_handoff


import sys
root, base_path, output = map(Path, sys.argv[1:])
prior = root/'draft-native-dma-handoff-109815'
base = read_base(base_path)
original = json.loads((prior/'compile.json').read_bytes())
rules = json.loads((prior/'algorithm2-input.json').read_bytes())
sealed = {'dma-detail.odb': base['views']['DMA.odb']}
hardware = original['resolved_hardware']
result = compile_event_ir(original['event_ir'], hardware, route_base=base, route_scope='interface', emit_outputs=True)
require(result['status']=='planned' and result['plan']==original['plan'], 'lower evidence changed selected plan')
result_pl_sha = digest(result['plan'])
bundle = build(result['event_ir'],result['resolved_hardware'],result['plan'],route_catalog(result['resolved_hardware']),
               base,rules,bind_request,source_outputs=result['outputs'])
actual = bundle['algorithm2-input']
require(all(actual[k]==rules[k] for k in ('pins','nets','technology','obstacles')), 'lower route shifted Algo2 geometry')
output.mkdir()
for k,v in {**bundle,'compile':result,'base':base}.items():
    (output/(k+'.json')).write_text(json.dumps(v, indent=2,sort_keys=True)+'\n')
receipt = verify_handoff(actual,output)
summary = {'plan_sha256':result_pl_sha,'nets':len(actual['nets']),'lower_ports':5028,
           'admission':receipt,'base_view':sealed['dma-detail.odb']['sha256']}
(output/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,sort_keys=True))
