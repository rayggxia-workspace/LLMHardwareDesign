"""Link the same staged DMA interface used by the Algo2 handoff."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import assemble_cases
from compile_scope_loops import expand
import export_tlm_mother_program as exporter
from export_native_tlm_pages import write_tlm_page_tables
from link_event_deployment import link_verified_event
import link_native_program as linker
from make_lc_kernel import kernel
import native_program_runtime as runtime
from native_ffn_scope_provider import ffn_scope_providers
from native_tlm_local import descriptor_key
from replay_tlm_mother import execute
from route_contract import read_base, require


def read(path):
    return json.loads(path.read_bytes())


selected, reference, output = map(Path, sys.argv[1:])
base = read_base(selected / 'base.json')
result = read(selected / 'compile.json')
handoff = read(selected / 'handoff.json')
request = read(selected / 'native-route-requirements.json')
require(handoff['native_route_request_sha256'] == request['sha256'],
        'routing and native linking received different requirements')
hardware = result['resolved_hardware']
name, = hardware['event_model']['services']
loop = hardware['event_model']['services'][name]['finite_loop']
scope = read(reference / 'scope.json')
descriptors = (reference / 'descriptors.bin').read_bytes()
controls = tuple(sorted(hardware['control_groups']))
providers = ffn_scope_providers(scopes=scope, descriptors=descriptors, controls=controls,
                               task=loop['task_id'], loop=loop)
linked = link_verified_event(result, base, request, providers, linker,
                             descriptor_base=scope['descriptor_base'],
                             assembler=assemble_cases, expand=expand, local_kernel=kernel)
require(linked['descriptor_image'] == descriptors
        and linked['mother_image'] == (reference / 'mother.bin').read_bytes()
        and all(image == (reference / 'local.bin').read_bytes() for image in linked['local_images'].values()),
        'native command bytes changed')
output.mkdir()
linker.write_native_bundle(output / 'native', linked)
pages = output / 'tlm-pages'
deployment = write_tlm_page_tables(output / 'native', pages, pm_base=0x10000000, runtime=runtime)
pages_audit = exporter.audit_calls(pages, deployment)
observed, waits = [], []
for page in exporter.export(pages, deployment, 0):
    def issue(target, slot, registers):
        address = registers[0] | registers[1] << 32
        offset = address - scope['descriptor_base']
        observed.append((target, address, tuple(descriptor_key(descriptors[offset:offset+128],
                                                               scope['topology']))))
        return target
    execute(page['instructions'], issue=issue, wait=lambda handles: waits.append(list(handles)),
            max_steps=page['max_steps'], entry_pc=page['entry_pc'])
require(observed == [(item['target'], item['address'], tuple(item['service_signature']))
                    for item in linked['calls']], 'PR260 CALL or address readback differs')
require(waits == [[hardware['control_groups'][group]['block_id'] for group in controls]
                  for wave in scope['barriers']], 'PR260 WAIT wave readback differs')
summary = {'audit': pages_audit, 'wait_waves': len(waits), 'source': linked['source'],
           'descriptors_sha256': sha256(descriptors).hexdigest(),
           'routing_request_sha256': request['sha256'], 'physical_qualified': False,
           'scope': 'archived native bytes and PR260 CALL/WAIT readback on staged DMA interface'}
(output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
