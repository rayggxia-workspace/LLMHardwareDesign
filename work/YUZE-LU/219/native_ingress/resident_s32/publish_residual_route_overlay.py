"""Bind a request and its C0 residual study against one candidate pin inventory."""
import argparse
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from route_contract import bind_members, digest, read_base, seal
from adapter import bind_request
from verify_candidate_algo2 import verify_candidate


def read(path):
    return json.loads(path.read_bytes())


def verified(folder):
    spec = read(folder / 'algorithm2-input.json')
    report = verify_candidate(spec, folder, folder / 'base.json')
    return (read_base(folder / 'base.json'), spec, read(folder / 'program.json'),
            read(folder / 'requirements.json'), report)


def overlay(request_folder, resident, egress_path, output):
    base, spec, program, req, request_admission = verified(request_folder)
    candidate, local_spec, local, supplement, local_admission = verified(resident)
    proof_path = resident / 'residual-proof.json'
    proof = read(proof_path)
    egress = read(egress_path)
    if (egress['producer'] != local['source'] or proof['placement'] != local_admission
            or proof['source'] != local['control_ir']['source']
            or sha256(proof_path.read_bytes()).hexdigest() != egress['producer_report_sha256']
            or egress['physical_input']['router_input_sha256'] != request_admission['router_input_sha256']
            or egress['physical_input']['demand'] not in req['users']):
        raise ValueError('residual and stored-link proofs refer to different plans')
    for field in ('technology', 'obstacles', 'units'):
        if spec[field] != local_spec[field]:
            raise ValueError(f'different routing rules: {field}')
    if {k: v for k, v in base.items() if k != 'native_service_routes'} != {
            k: v for k, v in candidate.items() if k != 'native_service_routes'}:
        raise ValueError('different physical placement or pin inventory')
    routes = deepcopy(candidate['native_service_routes'])
    new_provider, = [row for row in routes['targets'] if row['group'] == proof['target']]
    routes['targets'].remove(new_provider)
    if routes != base['native_service_routes']:
        raise ValueError('changed whole-graph service definitions')

    members = {row['id']: row for row in req['members']}
    for row in supplement['members']:
        if members.setdefault(row['id'], row) != row:
            raise ValueError('different signal definition for the same demand')
    users = deepcopy(req['users'])
    for demand, added in supplement['users'].items():
        existing = users.setdefault(demand, [])
        for row in added:
            if row not in existing:
                existing.append(row)
    members = sorted(members.values(), key=lambda row: row['id'])
    dependencies = sorted(set(map(tuple, req['dependencies'] + supplement['dependencies'])))
    nets, unresolved = bind_members(members, candidate)
    if unresolved:
        raise ValueError('joint physical endpoints cannot be bound')
    source = dict(program['source'], base_sha256=digest(candidate),
                  parent_request_sha256=req['sha256'], residual_request_sha256=supplement['sha256'],
                  residual_egress_sha256=sha256(egress_path.read_bytes()).hexdigest())
    request = seal(dict(req, source=source, members=members, users=users, nets=nets,
                        dependencies=dependencies, base_sha256=source['base_sha256'],
                        catalog_sha256=digest(dict(request=req['catalog_sha256'],
                                                   residual=supplement['catalog_sha256']))))
    spec = bind_request(request, candidate, spec['technology'], spec['obstacles'])
    program = dict(program, source=source, residual_overlay=dict(
        execution_status='candidate_program_fragment', compute=sha256(proof_path.read_bytes()).hexdigest(),
        egress=source['residual_egress_sha256'], requires=proof['requires']))
    wiring = {key: request[key] for key in ('source', 'users', 'members', 'unresolved')}
    receipt = dict(route_scope='interface', status='interface_ready_for_algorithm_2',
                   source=source, unresolved=[], router_input_sha256=digest(spec),
                   program_sha256=digest(program), wiring_sha256=digest(wiring),
                   request_sha256=request['sha256'], base_sha256=request['base_sha256'],
                   coverage=dict(new_signal_nets=sum(bool(row['sinks']) for row in spec['nets'])),
                   physical_qualified=False)
    output.mkdir()
    files = {'algorithm2-input': spec, 'base': candidate, 'program': program,
             'wiring': wiring, 'requirements': request, 'handoff': receipt}
    for name, value in files.items():
        (output / (name + '.json')).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    mother = (request_folder / 'gather-mother.pm').read_bytes()
    if sha256(mother).hexdigest() != program['mother_replacement']['sha256']:
        raise ValueError('original Gather mother program differs')
    (output / 'gather-mother.pm').write_bytes(mother)
    report = verify_candidate(spec, output, output / 'base.json')
    print(json.dumps(dict(report, before_nets=request_admission['bound_nets'],
                          residual_nets=local_admission['bound_nets'],
                          known_members=len(members), unresolved_services=len(program['unresolved_services'])),
                     sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request_folder', 'resident', 'egress_path', 'output'):
        parser.add_argument(name, type=Path)
    overlay(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
