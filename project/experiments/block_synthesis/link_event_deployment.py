"""Link the verified Algo1 plan with the target's declared native calls."""
import struct

from event_deploy import bind_routes, emit, fixed_connections_present, route_catalog
from event_native_dispatch import qualify_native_dispatch, signature
from route_contract import digest, elaborate, require, verify_requirements
from verify_cover_frontier import verify


def checked_provider(linker, provider, calls, key):
    terminal, encode = provider
    expected = tuple((signature(call), call['completion']) for call in calls)

    def checked_encode(command):
        records = encode(command)
        if isinstance(records, bytes):
            records = (linker.NativeCall(records, terminal),)
        label = f"{key[0]}/{command['sequence']}/{key[3]}"
        require(isinstance(records, tuple) and len(records) == len(expected),
                f'{label}: encoded native call count differs from the selected contract')
        for index, (record, contract) in enumerate(zip(records, expected, strict=True)):
            require(isinstance(record, linker.NativeCall) and isinstance(record.descriptor, bytes)
                    and len(record.descriptor) == 128, f'{label}/{index}: invalid native descriptor')
            schema, size, opcode, abi = struct.unpack_from('<IHHI', record.descriptor)
            require(size == len(record.descriptor)
                    and ((schema, abi, opcode), record.terminal) == contract,
                    f'{label}/{index}: encoded native call differs from the selected contract')
        return records

    return terminal, checked_encode


def link_verified_event(result, base, request, library, linker, *,
                        descriptor_base, assembler, expand, local_kernel, allow_pages=False):
    """Supply the pinned native linker with source-bound calls and endpoints."""
    require(result.get('status') == 'planned', 'native linking requires a selected plan')
    base_hash = digest(base)
    require(result.get('physical_base_sha256') == base_hash
            and 'native_service_routes' in base, 'native linking requires the selected target inventory')
    model, hardware, plan = (result[name] for name in ('event_ir', 'resolved_hardware', 'plan'))
    scope = result.get('route_scope')
    if scope == 'product':
        from event_physical_contract import qualify_hardware

        require(base['state'] == 'frozen' and qualify_hardware(hardware, base) == hardware,
                'product native linking requires the selected frozen interfaces')
    else:
        require(scope == 'interface' and qualify_native_dispatch(hardware, base) == hardware,
                'schedule lacks native dispatch qualification for the selected base')
    tasks, covers = model['tasks'], model.get('covers', ())
    proof = verify(tasks, hardware, covers, plan, wire_budget=result['wire_budget'])
    require(proof['passed'] is True, 'selected plan failed verification')
    outputs = emit(tasks, hardware, covers, plan, physical_base_sha256=base_hash)
    require(outputs == result['outputs'], 'native program or wiring differs from the selected plan')
    catalog = route_catalog(hardware)
    wiring = outputs['wiring']
    verified_request = bind_routes(wiring, hardware, base, elaborate, verify_requirements, catalog=catalog)
    require(request == verified_request and request['status'] == 'endpoint_binding_complete',
            'native route request differs from the selected plan')

    if scope == 'product':
        require(fixed_connections_present(request, hardware, base),
                'product native linking requires the declared fixed connections')

    program = outputs['program']
    encoders, target_ids = linker.select_native_providers(program, hardware, library)
    inventory = {target['group']: target for target in base['native_service_routes']['targets']
                 if target['group'] in target_ids}
    spec = hardware['event_model']
    contracts = hardware['native_provider_contracts']
    for key, provider in encoders.items():
        group, _, op, name, _ = key
        table = 'routes' if op == 'COPY' else 'services'
        contract_id = spec[table][name]['native_providers'][group]
        issues = spec['native_dispatch_issues'][table]
        require(name not in issues and group in inventory,
                f'{group}/{name}: selected command has no qualified native dispatch')
        encoders[key] = checked_provider(linker, provider, contracts[contract_id]['calls'], key)
    routes = {target_ids[group]: [signature(route) for route in target['routes']]
              for group, target in inventory.items()}
    return linker.link_algo1_result(
        {**result, 'verification': proof}, encoders, target_ids, base=descriptor_base,
        topology=hardware['topology_id'], assembler=assembler, expand=expand,
        local_kernel=local_kernel, allow_pages=allow_pages, service_routes=routes,
        route_binding=(request, catalog, base, verify_requirements))
