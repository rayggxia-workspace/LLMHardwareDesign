"""Check that one native P scope gives both backends the same selected plan."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
import zlib

from route_contract import read_base
from event_deploy import route_catalog
from export_native_tlm_pages import write_tlm_page_tables
from link_event_deployment import link_verified_event
from publish_event_handoff import build
from run import compile_event_ir


def run(original, reference, candidate, router, output, *, pm_base):
    sys.path.append(str(router))
    from adapter import bind_request
    from handoff import verify_handoff
    import assemble_cases
    from compile_scope_loops import expand
    import link_native_program as linker
    import export_tlm_mother_program as exporter
    import native_program_runtime as runtime
    from native_tlm_local import descriptor_key
    from replay_tlm_mother import execute
    from make_lc_kernel import kernel
    from native_ffn_scope_provider import ffn_scope_providers

    def read(path):
        return json.loads(path.read_bytes())

    old = read(original)
    base = read_base(candidate / 'base')
    fabric = read(candidate / 'control-fabric')
    old_router = read(candidate / 'algorithm2-input.json')
    rules = {name: old_router[name] for name in ('technology', 'obstacles')}
    scope = read(reference / 'scope.json')
    descriptors = (reference / 'descriptors.bin').read_bytes()
    model, hardware = old['event_ir'], old['resolved_hardware']
    name, = hardware['event_model']['services']
    service = hardware['event_model']['services'][name]
    loop = service['finite_loop']
    controls = tuple(sorted(hardware['control_groups']))
    providers = ffn_scope_providers(scopes=scope, descriptors=descriptors, controls=controls,
                                   task=loop['task_id'], loop=loop)
    template = {'schema': 0x02505001, 'abi': 0x02504d02, 'opcode': 2}
    if (scope['topology'] != hardware['topology_id']
            or scope['descriptor_count'] % len(controls)):
        raise ValueError('archived scope differs from selected participants or topology')
    count = scope['descriptor_count'] // len(controls)
    terminals = ['scope_committed'] * (count - 1) + [loop['completion']]
    hardware['native_provider_contracts'] = {
        control: {'calls': [{**template, 'completion': terminal} for terminal in terminals]}
        for control in controls}
    view = 'P.netlist'
    base['native_service_routes'] = {
        'schema': 'native-rtl-target-routes/1', 'topology_id': scope['topology'],
        'targets': [{'group': group, 'id': hardware['control_groups'][group]['block_id'],
                     'netlist_view': view, 'netlist_sha256': base['views'][view]['sha256'],
                     'routes': [{**template, 'completions': sorted(set(terminals))}]}
                    for group in controls],
    }

    def compile(mapping_base):
        return compile_event_ir(model, hardware, route_base=mapping_base, route_scope='interface',
                                control_fabric=fabric, emit_outputs=True)

    result = compile(base)
    if result['status'] != 'planned':
        raise ValueError(result)
    hw = result['resolved_hardware']
    pack = build(model, hw, result['plan'], route_catalog(hw), base, rules, bind_request,
                 source_outputs=result['outputs'])
    request = pack['native-route-requirements']
    options = {'descriptor_base': scope['descriptor_base'], 'assembler': assemble_cases,
               'expand': expand, 'local_kernel': kernel}
    linked = link_verified_event(result, base, request, providers, linker, **options)
    if (linked['descriptor_image'] != descriptors
            or linked['mother_image'] != (reference / 'mother.bin').read_bytes()
            or set(linked['local_images']) != set(controls)
            or any(image != (reference / 'local.bin').read_bytes()
                   for image in linked['local_images'].values())
            or len(linked['calls']) != scope['descriptor_count']
            or linked['route_request']['sha256'] != pack['handoff']['native_route_request_sha256']):
        raise ValueError('native route identity or executable bytes differ from the sealed scope')

    def expect_rejected(error, action):
        try:
            action()
        except ValueError as exc:
            if error in str(exc):
                return
            raise
        raise ValueError('accepted negative control: ' + error)

    group = controls[0]
    terminal, encode = providers[group]

    def change_completion(command):
        rows = encode(command)
        return (linker.NativeCall(rows[0].descriptor, terminal), *rows[1:])

    def change_signature(command):
        rows = encode(command)
        data = bytearray(rows[0].descriptor)
        struct.pack_into('<H', data, 6, 1)
        struct.pack_into('<I', data, 124, zlib.crc32(data[:124]))
        return (linker.NativeCall(bytes(data), rows[0].terminal), *rows[1:])

    def missing_call(command):
        return encode(command)[1:]

    for method, message in ((change_signature, 'call differs'), (change_completion, 'call differs'),
                            (missing_call, 'call count differs')):
        altered = {**providers, group: (terminal, method)}
        expect_rejected(message, lambda: link_verified_event(result, base, request, altered, linker, **options))
    expect_rejected('route request differs', lambda: link_verified_event(
        result, base, {**request, 'sha256': '0' * 64}, providers, linker, **options))
    disallowed = deepcopy(base)
    target = disallowed['native_service_routes']['targets'][0]
    target['routes'] = []
    target['rejected_routes'] = [{**template, 'reason': 'test exclusion of the selected P service'}]
    rejected = compile(disallowed)
    failure = rejected.get('native_dispatch_issues', {}).get('services', {}).get(name, '')
    if rejected['status'] == 'planned' or 'rejected native signature' not in failure:
        raise ValueError('negative target inventory did not block candidate selection')

    output.mkdir()
    for filename, item in {**pack, 'compile': result, 'base': base}.items():
        (output / (filename + '.json')).write_bytes(linker.canonical_bytes(item))
    admission = verify_handoff(pack['algorithm2-input'], output)
    manifest = linker.write_native_bundle(output / 'native', linked)
    page_tables = output / 'tlm-pages'
    deployment = write_tlm_page_tables(output / 'native', page_tables, pm_base=pm_base, runtime=runtime)
    audit = exporter.audit_calls(page_tables, deployment)
    actual_calls, waits = [], []
    for page in exporter.export(page_tables, deployment, 0):
        def issue(target, slot, registers):
            address = registers[0] | registers[1] << 32
            offset = address - scope['descriptor_base']
            key = descriptor_key(descriptors[offset:offset + 128], scope['topology'])
            actual_calls.append((target, address, tuple(key)))
            return target

        execute(page['instructions'], issue=issue, wait=lambda handles: waits.append(list(handles)),
                max_steps=page['max_steps'], entry_pc=page['entry_pc'])
    expected_calls = [(call['target'], call['address'], tuple(call['service_signature']))
                      for call in linked['calls']]
    expected_waves = [[hardware['control_groups'][group]['block_id'] for group in controls]
                      for _ in scope['barriers']]
    if (audit['pages'] != 1 or actual_calls != expected_calls or waits != expected_waves
            or audit['descriptor_calls'] != len(expected_calls)):
        raise ValueError('PR #260 decoded CALL addresses, targets or WAIT waves differ from the sealed scope')
    manifest_path = output / 'native' / 'deployment.json'
    patched = deepcopy(manifest)
    patched['calls'][0]['sha256'] = '0' * 64
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest_path.write_bytes(linker.canonical_bytes(patched))
        expect_rejected('descriptor identity differs', lambda: write_tlm_page_tables(
            output / 'native', output / 'rejected-pages', pm_base=pm_base, runtime=runtime))
    finally:
        manifest_path.write_bytes(manifest_bytes)
    expect_rejected('overlaps the descriptor arena', lambda: write_tlm_page_tables(
        output / 'native', output / 'overlapping-pages', pm_base=scope['descriptor_base'], runtime=runtime))
    summary = {
        'pr260_page_audit': {**audit, 'wait_waves': len(waits), 'descriptor_bytes_checked': len(descriptors)},
        'scope': 'source-bound Block V2 candidate control endpoints and native P scope bytes',
        'control_topology': base['base_id'], 'selected_controls': controls,
        'source': linked['source'], 'algo2': admission, **pack['handoff']['coverage'],
        'native_route_request_sha256': linked['route_request']['sha256'],
        'native_call_count': len(linked['calls']),
        'machine_images': manifest['payloads'],
        'archive_scope_sha256': sha256((reference / 'scope.json').read_bytes()).hexdigest(),
        'negative_controls': ['descriptor opcode', 'intermediate completion', 'missing call',
                              'changed route request', 'target dispatch disabled',
                              'descriptor provenance', 'overlapping mother and descriptor DDR ranges'],
        'executed': False, 'physical_qualified': False,
    }
    (output / 'summary.json').write_bytes(linker.canonical_bytes(summary))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'reference', 'candidate', 'router', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--pm-base', required=True, type=lambda value: int(value, 0))
    args = parser.parse_args()
    run(args.original, args.reference, args.candidate, args.router, args.output, pm_base=args.pm_base)
