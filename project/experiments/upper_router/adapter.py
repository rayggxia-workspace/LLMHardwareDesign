"""Consume #227 endpoint manifest without guessing widths, pins or aliases."""
from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'block_synthesis'))
from route_contract import digest, feedback, require, seal


def bind_request(request, base, technology, obstacles=()):
    require(request == seal(request), 'corrupted request')
    require(request['base_sha256'] == digest(base) and request['base_id'] == base['base_id'], 'stale base')
    require(request.get('status') == 'endpoint_binding_complete' and not request['unresolved'], 'unbound routing input')
    terms = {}
    for endpoint in base['endpoints'].values():
        term = endpoint['odb_term']
        terms.setdefault(term, [])
        for shape in endpoint['m10_shapes']:
            require(shape['layer'] == 'M10', 'not M10')
            if shape['rect_dbu'] not in terms[term]:
                terms[term].append(shape['rect_dbu'])
    pins, nets = {}, []
    for net in request['nets']:
        sinks = sorted(set(net['sinks'])-set(net['fixed_sinks']))
        for term in [net['driver']]+sinks:
            require(term in terms, 'missing physical term')
            pins[term] = deepcopy(terms[term])
        nets.append({'id': net['id'], 'driver': net['driver'], 'sinks': sinks})
    context = {'base_id': base['base_id'], 'base_sha256': request['base_sha256'],
               'request_sha256': request['sha256'], 'dbu_per_micron': base['dbu_per_micron']}
    if 'gds' in base.get('views', {}):
        context['native_gds_sha256'] = base['views']['gds']['sha256']
    if 'native_inventory' in base:
        context['native_inventory'] = deepcopy(base['native_inventory'])
    return {'schema_version': 'upper-router/1', 'units': 'dbu',
            'technology': deepcopy(technology), 'obstacles': deepcopy(list(obstacles)),
            'pins': pins, 'nets': nets, 'context': context}


def failure_feedback(request, result, evidence):
    physical = result.get('physical_routes', result)
    context = physical['context']
    require(context['request_sha256'] == request['sha256'] and
            context['base_sha256'] == request['base_sha256'], 'stale route feedback')
    scope = {'evidence': evidence, 'spec_sha256': physical['spec_sha256'], 'hard_constraint': False}
    return feedback(request, [
        {'category': 'search_not_found', 'phase': 'access' if reason == 'grid_access_not_found' else 'routing',
         'code': reason, 'net_ids': [name], **scope}
        for name, reason in result['failed'].items()])
