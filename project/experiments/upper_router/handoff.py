"""Admission checks for the model-independent Algorithm 1 handoff."""
import json

from check import digest
from geometry import need


def verify_handoff(spec, folder, base_path=None):
    def read(name):
        return json.loads((folder / (name + '.json')).read_text(encoding='utf-8'))

    receipt = read('handoff')
    scope = receipt['route_scope']
    ready = {'interface': 'interface_ready_for_algorithm_2', 'product': 'ready_for_algorithm_2'}
    need(scope in ready and receipt['status'] == ready[scope] and receipt['unresolved'] == [],
         'unresolved or invalid routing handoff')
    need(digest(spec) == receipt['router_input_sha256'], 'router input changed after handoff')
    program, wiring, request = read('program'), read('wiring'), read('requirements')
    need(all(receipt['source'] == a['source'] for a in (program, wiring, request)), 'mixed plan provenance')
    need(digest(program) == receipt['program_sha256'] and digest(wiring) == receipt['wiring_sha256'],
         'control program or wiring fingerprint differs')
    request_hash = digest({k: v for k, v in request.items() if k != 'sha256'})
    context = spec['context']
    need(request.get('status') == 'endpoint_binding_complete' and request['unresolved'] == [],
         'unbound requirements')
    need(request_hash == request['sha256'] == receipt['request_sha256'] == context['request_sha256'],
         'endpoint request fingerprint differs')
    need(request['base_sha256'] == receipt['base_sha256'] == context['base_sha256']
         and request['base_id'] == context['base_id'], 'frozen base fingerprint differs')
    need(wiring['members'] == request['members'] and wiring['users'] == request['users']
         and wiring['unresolved'] == [], 'wiring and requirements describe different demands')
    logical_members = {m['id'] for m in request['members']}
    claimed = [m for net in request['nets'] for m in net['members']]
    need(len(logical_members) == len(request['members']) == len(claimed)
         and logical_members == set(claimed), 'static net bit coverage differs from wiring')
    need(all(set(net['fixed_sinks']) <= set(net['sinks']) for net in request['nets']),
         'unrecognized fixed sink')
    nets = {n['id']: (n['driver'], sorted(n['sinks'])) for n in spec['nets']}
    expected = {n['id']: (n['driver'], sorted(set(n['sinks'])-set(n['fixed_sinks']))) for n in request['nets']}
    need(nets == expected and len(nets) == len(spec['nets']) == len(request['nets']),
         'routing does not cover the bound static netlist')
    need(sum(bool(sinks) for _, sinks in nets.values()) == receipt['coverage']['new_signal_nets'],
         'handoff misstates new signal count')
    admission = {'scope': scope, 'receipt_sha256': digest(receipt), 'base_sha256': context['base_sha256']}
    if base_path is not None:
        from adapter import bind_request
        from route_contract import bind_members, read_base
        base = read_base(base_path)
        need(scope != 'product' or base['state'] == 'frozen', 'product requires frozen native views')
        rebound, unresolved = bind_members(request['members'], base)
        need(not unresolved and rebound == request['nets'], 'physical bindings or fixed sinks differ from frozen base')
        expected_spec = bind_request(request, base, spec['technology'], spec.get('obstacles', []))
        need(expected_spec['pins'] == spec['pins'], 'M10 geometry differs from frozen native views')
        admission['native_gds_sha256'] = base['views']['gds']['sha256']
    return admission
