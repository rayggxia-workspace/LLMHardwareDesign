"""Read back a generated PM and independently project the missing physical members."""
from copy import deepcopy
import json
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
import sys

import compact
from image import pack_image
from resident_gather_contract import local_image, demand, GATHER, LINK_ABI, CAPACITY_ID
from route_contract import VERSION, bind_members, expand, read_base

linked, base_path, out = map(Path, sys.argv[1:])
out.mkdir()
source = json.loads((linked/'compile.json').read_bytes())['outputs']['program']
old = (linked/'descriptors.bin').read_bytes()
proof = dict(reversed(row.split('  ',1)) for row in (linked/'proof.sha256').read_text().splitlines())
assert proof['descriptors.bin']==sha256(old).hexdigest()
command, = source['locals']['embedding']
table, rows, offset, dest, index_bits = unpack_from('<QIHHH', old, 16)
assert index_bits==32
# The audited U0 module's existing local control image topology.
topology = 0x02500031
image = local_image(command, topology=topology, image_id=1, pack_image=pack_image)
header = compact.unpack_header(image[:128])
expected_header = {'topology_id': topology, 'native_abi_id': LINK_ABI, 'capacity_profile_id': CAPACITY_ID,
                   'resource_mask': 1, 'execution_count': 1, 'task_count': 1}
assert all(header[k]==v for k,v in expected_header.items())
code = compact.unpack_program(image[128:header['task_offset']], header['instruction_count'], 'local', 2)
assert code==[{'op':'L_EXEC','a':0,'b':0,'c':0},{'op':'L_WAIT','x':1},{'op':'L_END'}]
execution = image[header['execution_offset']:]
assert len(execution)==128 and unpack_from('<H',execution,4)[0]==GATHER
new_table, new_offset, new_rows, new_dest = unpack_from('<6sHII', execution, 64)
assert (int.from_bytes(new_table,'little'),new_offset,new_rows,new_dest)==(table,offset,rows,dest)

for changed in ('required_completion', 'read', 'write', 'indexed_read'):
    broken = deepcopy(command)
    if changed=='required_completion':
        broken[changed]='issued'
    elif changed=='read':
        broken[changed][0]['address']=0
    elif changed=='write':
        broken[changed][0]['bytes']=4096
    else:
        broken[changed]['table_address']+=64
    try:
        local_image(broken, topology=topology, image_id=1, pack_image=pack_image)
    except ValueError:
        continue
    raise AssertionError(f'{changed} accepted')

base = read_base(base_path)
name = 'gather.U0.dma3'
catalog = {'schema_version': VERSION, 'demands': {name: demand('U0',3)}}
user = {'task_id':command['task_id'],'binding_id':command['binding_id']}
_, _, members, missing_templates = expand({name:[user]},catalog)
nets, missing_endpoints = bind_members(members,base)
assert not missing_templates and len(members)==650
assert not nets and len(missing_endpoints)==650
assert all(len(e['endpoints'])==1 and e['endpoints'][0].startswith('U0/dma_') for e in missing_endpoints)
(out/'local.pm').write_bytes(image)
(out/'demand.json').write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n')
(out/'unbound.json').write_text(json.dumps(missing_endpoints,indent=2,sort_keys=True)+'\n')
report = {'source_plan':source['source']['plan_sha256'],'pm_bytes':len(image),'native_op':GATHER,
          'local_topology':topology,'completion':command['required_completion'],'table':table,
          'index_offset':offset,'output_word':dest,'rows':rows,'bound_dma_members':650,
          'missing_u_members':650,'malformed_candidates_rejected':4,
          'qualified_two_sided_nets':len(nets),'same_plan_whole_graph':False}
(out/'summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,sort_keys=True))
