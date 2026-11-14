"""Join the planned token feedback to the placed producer and consumer evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from hashlib import sha256

from route_contract import require, seal


def read(path):
    data = path.read_bytes()
    return json.loads(data), sha256(data).hexdigest()


def by_key(rows, key):
    rows = list(rows)
    keys = [key(row) for row in rows]
    require(len(set(keys)) == len(keys), 'duplicate identity')
    return dict(zip(keys, rows))


def build(retirement_path, gather_path, sidecars_path, geometry_path, aux_path):
    retirement, retirement_sha = read(retirement_path)
    gather, gather_sha = read(gather_path)
    sidecars, sidecar_sha = read(sidecars_path)
    geometry, _ = read(geometry_path)
    aux, aux_sha = read(aux_path)
    require(retirement['gather_sha256'] == gather_sha and
            retirement['package_sha256'] == gather['package_sha256'],
            'vocabulary and Gather belong to different request packages')
    require(geometry == seal(geometry), 'route requirements seal differs')
    require(gather['sidecar_sha256'] == geometry['source']['sidecar_sha256'] == sidecar_sha,
            'route and program were emitted from different sidecars')
    require(aux['base_sha256'] == geometry['base_sha256'] and
            aux['vocabulary_link_sha256'] == retirement_sha and
            aux['tile_calls'] == retirement['volume']['calls'],
            'auxiliary terminal inventory belongs to a different placement or request')
    require(geometry['status'] == 'endpoint_binding_complete' and not geometry['unresolved'],
            'feedback transport or DMA receiver endpoints are unresolved')

    decode = (row for row in sidecars if row['input_source']['kind'] == 'previous_retired_token')
    receivers = by_key(decode, lambda row: (row['step'], row['page']))
    replacements = by_key((row for row in gather['pages'] if row['dispatch_prerequisite'] is not None),
                          lambda row: (row['step'], row['page']))
    producers = by_key(retirement['pages'], lambda row: row['step'])
    require(len(producers) == retirement['phases'] and set(producers) == set(range(len(producers))),
            'retirement phases are not contiguous')
    routes = {
        group: by_key(geometry['users'][group], lambda row: row['task_id'])
        for group in ('decode.index.transport', 'gather.U0.dma3')
    }
    members = Counter(row['demand_id'] for row in geometry['members'])
    require(all(members[group] > 0 for group in routes), 'route demand has no signal members')
    require(set(receivers) == set(replacements), 'Gather replacement and receiver coverage differ')
    edges = []
    for step, producer in sorted(producers.items()):
        target = producer['consumer']
        if target is None:
            require(step == len(producers)-1, 'nonterminal vocabulary phase has no receiver')
            continue
        key = (target['step'], target['page'])
        require(target['step'] == step+1 and key in receivers, 'wrong next-step receiver')
        receiver, replacement = receivers[key], replacements[key]
        prerequisite = replacement['dispatch_prerequisite']
        require(receiver['input_source']['retired_step'] == prerequisite['step'] == step and
                prerequisite['terminal_page'] == producer['page'] and
                prerequisite['terminal_source_proof'] == producer['stage_proof'] and
                producer['phase_release'] == 'vocabulary_token_retired' and
                receiver['input_source']['prerequisite'] == replacement['gather_prerequisite'] ==
                'retired_token_sram_commit_ack',
                f'token commit dependency differs at step {step}')
        local_pm = target['local_pm_sha256']
        require(local_pm == replacement['local_pm_sha256'] == receiver['pm_sha256'] and
                receiver['completion'] == replacement['completion'] == 'destination_commit_ack',
                f'receiver program or completion differs at step {step}')
        task = f'decode-index-{target["step"]}'
        require(all(route.get(task, {}).get('binding_id') == local_pm for route in routes.values()),
                f'route consumers do not reference the receiver program at step {step}')
        edges.append(dict(retired_step=step, producer_page=producer['page'],
                          next_step=target['step'], receiver_page=target['page'],
                          receiver_pm_sha256=local_pm, route_task_id=task))
    route_users = {edge['route_task_id'] for edge in edges}
    require(len(edges) == retirement['feedback_edges'] == len(receivers) == len(producers)-1 and
            all(set(route) == route_users for route in routes.values()),
            'route users and token feedback differ')

    endpoint_status = Counter(row['status'] for row in aux['endpoints'])
    by_key(aux['endpoints'], lambda row: row['pin'])
    require(dict(endpoint_status) == aux['counts'] and
            len(aux['endpoints']) == aux['p0_ports'], 'auxiliary pin inventory counts differ')
    missing = [row['pin'] for row in aux['endpoints'] if row['status'] != 'm10_shape_present']
    blocked = ['P0_compute_to_vocabulary_terminal_not_physically_bound',
               'C0_stored_index_producer_not_physically_bound']
    if missing:
        blocked.append('P0_external_terminal_requires_additional_pin_access')
    return seal(dict(schema='block-v2-retirement-placement-handoff/1',
                     scope='program_dependencies_and_route_endpoint_requirements',
                     status='blocked_on_placed_token_provider',
                     request_sha256=retirement['package_sha256'], sidecar_sha256=sidecar_sha,
                     base_sha256=geometry['base_sha256'], gather_sha256=gather_sha,
                     retirement_sha256=retirement_sha, aux_sha256=aux_sha,
                     route_requirements_sha256=geometry['sha256'],
                     terminal_controller=aux['terminal_controller'],
                     route_demands={key: members[key] for key in routes},
                     producer_phases=len(producers), feedback_edges=edges,
                     unresolved_provider_prerequisites=blocked, missing_p0_aux_pins=missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('retirement_path', 'gather_path', 'sidecars_path', 'geometry_path', 'aux_path', 'output'):
        parser.add_argument(name, type=Path)
    args = vars(parser.parse_args())
    output = args.pop('output')
    result = build(**args)
    output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(status=result['status'], sha256=result['sha256'],
                          phases=result['producer_phases'], edges=len(result['feedback_edges']),
                          demands=result['route_demands'], missing=len(result['missing_p0_aux_pins'])),
                     sort_keys=True))


if __name__ == '__main__':
    main()
