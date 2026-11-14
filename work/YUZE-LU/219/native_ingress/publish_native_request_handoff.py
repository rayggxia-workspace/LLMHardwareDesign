"""Publish one native request's program index and known Algo2 wiring on the same base."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from route_contract import digest, elaborate, read_base, require, seal, verify_requirements
from adapter import bind_request
from geometry import validate
from verify_candidate_algo2 import verify_candidate

from bind_gather_mother_topology import bind as bind_mother


GATHER_COMPLETION = 'destination_commit_ack'
GATHER_ROLE = 'gather'
TOKEN_ROLE = 'token_feedback'
READY = 'endpoint_binding_complete'


def hash_file(path):
    digest = sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(data)
    return digest.hexdigest()


def read_seal(path):
    entries = [line.split('  ', 1) for line in path.read_text(encoding='ascii').splitlines()]
    result = {name: digest for digest, name in entries}
    require(len(result) == len(entries), 'duplicate archive path')
    return result


def read(path):
    return json.loads(path.read_bytes())


def read_checked(path):
    return read(path), hash_file(path)


def service_key(row):
    return tuple(row[k] for k in ('target', 'schema', 'abi', 'opcode', 'completion'))


def validate_sealed_request(request):
    manifest = read_seal(request/'proof.sha256')
    names = ('witness.json', 'service-signatures.json', 'mother-pages.tsv',
             'mother-targets.tsv', 'mother-packed.tsv', 'mother-descriptors.tsv',
             'mother-programs.ddr.bin')
    for name in names:
        require(hash_file(request/name) == manifest[name], f'changed request artifact: {name}')
    witness = read(request/'witness.json')
    signatures = read(request/'service-signatures.json')
    require(witness['schema'] == 'native-graph-request-pages/1' and witness['phases'] and signatures,
            'missing native request phases or services')
    pages = sum(phase['page_count'] for phase in witness['phases'])
    require(all(phase['step'] == step and len(phase['target_masks']) == phase['page_count']
                for step, phase in enumerate(witness['phases'])), 'incomplete page inventory')
    observed_targets = set()
    with (request/'mother-targets.tsv').open(encoding='ascii') as stream:
        require(int(next(stream)) == pages, 'wrong target page count')
        for phase in witness['phases']:
            for page, mask in enumerate(phase['target_masks']):
                fields = next(stream, '').split()
                require(len(fields) == 3 and
                        tuple(int(x, 16) for x in fields) == (phase['step'], page, mask) and mask > 0,
                        'page target differs from witness')
                observed_targets.update(i for i in range(mask.bit_length()) if mask & (1 << i))
        require(next(stream, None) is None, 'unclaimed target page')
    require(observed_targets == {row['target'] for row in signatures} and
            len(signatures) == len({service_key(row) for row in signatures}) and
            all(type(row['calls']) is int and row['calls'] > 0 for row in signatures),
            'service inventory differs from selected packet targets')
    descriptors = tuple(f'phase-{phase["step"]}/descriptors.bin' for phase in witness['phases'])
    return witness, signatures, pages, {name: manifest[name] for name in (*names, *descriptors)}


def bind_profiles(policy, signatures, base, fabric, control):
    provider = base['native_service_routes']
    by_id = {r['id']: r for r in provider['targets']}
    registered = {tuple(row['archived'][key] for key in
                        ('target', 'schema', 'abi', 'opcode', 'completion')): row
                  for row in policy['rewrites']}
    require(len(registered) == len(policy['rewrites']), 'duplicate rewrite signature')
    required = defaultdict(list)
    unresolved = []
    inventory = []
    rewrites = {}
    for entry in signatures:
        key = service_key(entry)
        target = by_id[entry['target']]
        site = target['group']
        switch_site = fabric['targets'][site]
        require(switch_site['target_id'] == entry['target'] and
                key in {service_key(row) for row in control['users'][switch_site['bundles'][0]]},
                'packet requirement and service inventory differ')
        for bundle in switch_site['bundles']:
            required[bundle].append(entry)
        rewrite = registered.get(key)
        effective = entry if rewrite is None else {**entry, **rewrite['native']}
        if rewrite is not None:
            require(rewrite['role'] == GATHER_ROLE, 'unrecognized installed rewrite')
            rewrites[rewrite['role']] = entry
        route = next((item for item in target['routes']
                      if all(item[k] == effective[k] for k in ('schema', 'abi', 'opcode'))
                      and effective['completion'] in item['completions']), None)
        # Existing scoped P routes are still needed when the completion needs
        # a separate provider, such as the vocabulary terminal.
        physical_route = route
        if physical_route is None and rewrite is None:
            physical_route = next((item for item in target['routes']
                                   if all(item[k] == entry[k] for k in ('schema', 'abi', 'opcode'))), None)
        if physical_route is not None:
            for bundle in physical_route['requires']:
                required[bundle].append(entry)
        row = dict(signature=entry, group=site)
        if route is None:
            row['status'] = 'missing_completion_provider' if physical_route else 'missing_native_dispatch'
            unresolved.append(row)
        else:
            row['status'] = 'candidate_native_route'
        inventory.append(row)
    require(len(rewrites) == len(registered), 'rewrite does not identify one request service')
    return required, unresolved, inventory, rewrites


def verify_feedback(placed_feedback, route, gather, programs, locals_dir, placement):
    require(placed_feedback == seal(placed_feedback) and route == seal(route)
            and placed_feedback['route_requirements_sha256'] == route['sha256']
            and placed_feedback['base_sha256'] == route['base_sha256'] == digest(placement),
            'feedback belongs to a different placement or route')
    require(placed_feedback['gather_sha256'] == hash_file(programs/'request-link.json')
            and placed_feedback['request_sha256'] == gather['package_sha256'],
            'feedback belongs to a different program')
    require(gather['replaced_calls'] == len(gather['pages']) and
            len({(page['step'], page['page']) for page in gather['pages']}) == len(gather['pages']),
            'wrong replacement call count')
    topologies = set()
    for name in {page['local_pm_sha256'] for page in gather['pages']}:
        require(len(name) == 64 and all(ch in '0123456789abcdef' for ch in name),
                'invalid replacement local image identity')
        data = (locals_dir/(name+'.pm')).read_bytes()
        require(len(data) >= 144 and sha256(data).hexdigest() == name, 'changed replacement local image')
        topologies.add(unpack_from('<I', data, 64)[0])
    require(len(topologies) == 1, 'replacement images disagree on local topology')
    local_topology, = topologies
    return local_topology


def build(request_dir, base_path, prior_control, p_compiler, geometry_dir, gather_dir,
          feedback_path, local_images, fabric_path, rules_path, policy_path, output):
    from event_deploy import route_catalog

    request_sha = hash_file(request_dir/'proof.sha256')
    witness, signatures, pages, program_files = validate_sealed_request(request_dir)
    control = read(prior_control)
    require(control == seal(control) and control['source']['package_proof_sha256'] == request_sha
            and control['source']['service_signatures_sha256'] == program_files['service-signatures.json']
            and control['source']['mother_targets_sha256'] == program_files['mother-targets.tsv'],
            'packet projection belongs to a different request')

    base = read_base(base_path)
    feedback, feedback_sha = read_checked(feedback_path)
    gather = read(gather_dir/'request-link.json')
    geometry = read(geometry_dir/'geometry-requirements.json')
    local_topology = verify_feedback(feedback, geometry, gather, gather_dir, local_images, base)
    require(gather['package_sha256'] == request_sha and gather['request_pages'] == pages and
            gather['request_calls'] == sum(row['calls'] for row in signatures),
            'Gather program belongs to a different request')
    policy, policy_sha = read_checked(policy_path)
    fabric, fabric_sha = read_checked(fabric_path)
    require(digest(fabric) == policy['control_fabric_digest'],
            'packet fabric differs from the registered profile')
    users, gaps, providers, rewrites = bind_profiles(policy, signatures, base, fabric, control)
    require(rewrites[GATHER_ROLE]['calls'] == gather['replaced_calls'] and
            rewrites[GATHER_ROLE]['completion'] == GATHER_COMPLETION,
            'replacement coverage differs from original service')

    catalog = route_catalog(read(p_compiler)['resolved_hardware'])
    for name, row in fabric['bundles'].items():
        contract = {field: row[field] for field in ('signals', 'requires')}
        require(catalog['demands'].get(name, contract) == contract,
                f'packet fabric and P route catalog disagree: {name}')
        catalog['demands'][name] = contract
    fabric_topology = base['native_service_routes']['topology_id']
    require(witness['topology'] == fabric_topology, 'request topology differs from the packet fabric')
    native_mother = bind_mother((gather_dir/'mother.pm').read_bytes(), gather['mother_pm_sha256'],
                                fabric_topology, local_topology)
    feedback_catalog = read(geometry_dir/'catalog.json')
    require(geometry['catalog_sha256'] == digest(feedback_catalog), 'changed feedback route catalog')
    for name, row in feedback_catalog['demands'].items():
        require(name not in catalog['demands'], 'duplicate feedback demand')
        catalog['demands'][name] = row
        users[name].extend(geometry['users'][name])
    # Prompt uses the same physical U0 DMA3 interface as decode.
    users[policy[TOKEN_ROLE]['gather_route']].extend(
        dict(step=row['step'], page=row['page'], position=row['position'],
             local_pm_sha256=row['local_pm_sha256'])
        for row in gather['pages'] if row['dispatch_prerequisite'] is None)

    all_calls = sum(row['calls'] for row in signatures)
    source = dict(package_proof_sha256=request_sha, topology=witness['topology'],
                  base_sha256=digest(base), control_projection_sha256=control['sha256'],
                  feedback_placement_sha256=feedback_sha, route_profile_sha256=policy_sha,
                  control_fabric_sha256=fabric_sha)
    route = elaborate(users, catalog, base, source)
    verify_requirements(route, users, catalog, base, source)
    require(route['status'] == READY, 'unbound endpoints in the selected known wiring')
    prior_rules = read(rules_path)
    spec = bind_request(route, base, prior_rules['technology'], prior_rules.get('obstacles', []))
    validate(spec)
    program = dict(source=source, kind='native_request_program_index',
                   execution_status='missing_product_providers',
                   pages=pages, calls=all_calls, source_files=program_files,
                   mother_replacement=dict(path='gather-mother.pm', sha256=sha256(native_mother).hexdigest(),
                                           native_topology=fabric_topology, legacy_topology=local_topology,
                                           source_sha256=gather['mother_pm_sha256']),
                   replacement_pages=gather['pages'], service_providers=providers,
                   unresolved_services=gaps,
                   unresolved_feedback=feedback['unresolved_provider_prerequisites'],
                   native_execution_qualified=False)
    wiring = {k: route[k] for k in ('source', 'users', 'members', 'unresolved')}
    receipt = dict(route_scope='interface', status='interface_ready_for_algorithm_2',
                   source=source, unresolved=[], router_input_sha256=digest(spec),
                   program_sha256=digest(program), wiring_sha256=digest(wiring),
                   request_sha256=route['sha256'], base_sha256=route['base_sha256'],
                   coverage=dict(new_signal_nets=sum(bool(net['sinks']) for net in spec['nets'])),
                   physical_qualified=False)
    output.mkdir()
    for name, data in (('base', base), ('algorithm2-input', spec), ('program', program),
                       ('wiring', wiring), ('requirements', route), ('handoff', receipt)):
        (output/(name+'.json')).write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')
    (output/'gather-mother.pm').write_bytes(native_mother)
    readback = verify_candidate(spec, output, base_path)
    report = dict(source=source, pages=pages, calls=all_calls,
                  known_demands=dict(Counter(row['demand_id'] for row in route['members'])),
                  known_nets=len(spec['nets']), terminals=len(spec['pins']),
                  unresolved_service_calls=sum(row['signature']['calls'] for row in gaps),
                  unresolved_service_signatures=len(gaps),
                  feedback_edges=len(feedback['feedback_edges']),
                  replacements=len(gather['pages']), admission=readback['admission'],
                  candidate_readback=readback,
                  mother_replacement=program['mother_replacement'],
                  execution_status=program['execution_status'])
    (output/'summary.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request_dir', 'base_path', 'prior_control', 'p_compiler', 'geometry_dir',
                 'gather_dir', 'feedback_path', 'local_images', 'fabric_path', 'rules_path', 'policy_path', 'output'):
        parser.add_argument(name, type=Path)
    build(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
