"""Preflight a selected native Algo1 package against its independently supplied base."""

import argparse
from collections import Counter
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from bind_gather_mother_topology import bind as bind_mother
from collect_tlm_call_evidence import collect
from event_native_dispatch import signature
from publish_native_request_handoff import (
    GATHER_ROLE, bind_profiles, hash_file, read, read_seal, require, service_key,
    validate_sealed_request,
)
from route_contract import digest, seal
from tlm_model_registry import model_for
from verify_candidate_algo2 import verify_candidate


def verify_package(request, program):
    """Validate sealed bytes and the handoff's independent reference to them."""
    proof = request / 'proof.sha256'
    require(hash_file(proof) == program['source']['package_proof_sha256'],
            'handoff refers to a different Algo1 package')
    witness, signatures, pages, source_files = validate_sealed_request(request)
    require(source_files == program['source_files'] and pages == program['pages']
            and witness['topology'] == program['source']['topology']
            and sum(row['calls'] for row in signatures) == program['calls'],
            'program index differs from the sealed Algo1 package')
    checked = set(source_files) - {f'phase-{row["step"]}/descriptors.bin'
                                  for row in witness['phases']}
    for name, checksum in read_seal(proof).items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts,
                'invalid sealed artifact path')
        if name not in checked:
            require(hash_file(request / path) == checksum, f'changed request artifact: {name}')
    return witness, signatures


def verify_native_targets(base, fabric, topology):
    """Require each advertised service route to belong to its actual assembly."""
    routes = base['native_service_routes']
    require(routes['schema'] == 'native-rtl-target-routes/1'
            and routes['topology_id'] == topology,
            'base service routes or control fabric use a different topology')
    assemblies = {row['id']: row for row in base['assemblies']}
    ids = set()
    for target in routes['targets']:
        number, group, view = (target[key] for key in ('id', 'group', 'netlist_view'))
        controller = fabric['targets'][group]
        require(type(number) is int and 0 <= number < 256 and number not in ids
                and controller['target_id'] == number
                and assemblies[controller['controller']]['views']['netlist'] == view
                and base['views'][view]['sha256'] == target['netlist_sha256'],
                f'unbound physical service target: {group}')
        ids.add(number)
        supported = set()
        for route in target['routes']:
            key = signature(route)
            completions, demands = route['completions'], route['requires']
            require(key not in supported and isinstance(completions, list) and completions
                    and isinstance(demands, list)
                    and all(isinstance(name, str) and name for name in (*completions, *demands))
                    and len(set(completions)) == len(completions)
                    and len(set(demands)) == len(demands),
                    f'invalid native service route: {group}')
            supported.add(key)
        denied = [signature(route) for route in target.get('rejected_routes', [])]
        require(not supported.intersection(denied) and len(set(denied)) == len(denied),
                f'inconsistent rejected service routes: {group}')


def verify_gather_replacement(request, handoff, witness, program, gather_inputs, expected_calls):
    """Rebuild the installed lowering from the selected archived bytes."""
    from link_gather_request import link

    require(gather_inputs is not None, 'installed Gather rewrite needs its input image and audit')
    local_images, direct_audit = gather_inputs
    with TemporaryDirectory(prefix='tlm-gather-') as scratch:
        rebuilt = Path(scratch) / 'link'
        with redirect_stdout(sys.stderr):
            link(request, local_images, direct_audit, rebuilt)
        report = read(rebuilt / 'request-link.json')
        replacement = program['mother_replacement']
        require(report['pages'] == program['replacement_pages']
                and report['replaced_calls'] == expected_calls
                and report['mother_pm_sha256'] == replacement['source_sha256'],
                'installed Gather page bindings differ from the rebuilt lowering')
        require(replacement['native_topology'] == witness['topology']
                and replacement['path'] == 'gather-mother.pm',
                'replacement mother uses the wrong target topology or artifact')
        expected = bind_mother((rebuilt / 'mother.pm').read_bytes(), replacement['source_sha256'],
                               replacement['native_topology'], replacement['legacy_topology'])
        path = handoff / replacement['path']
        require(path.read_bytes() == expected and hash_file(path) == replacement['sha256'],
                'installed Gather mother differs from the rebuilt lowering')


def match_models(providers, rewrites, models):
    """Use the effective service key after a verified lowering replacement."""
    results = []
    for row in providers:
        archived = row['signature']
        key = service_key(archived)
        effective = {**archived, **rewrites.get(key, {})}
        status = row['status']
        binding = None
        if status == 'candidate_native_route':
            binding = model_for(models, service_key(effective))
            status = 'model_available' if binding else 'missing_tlm_model'
        result = dict(group=row['group'], signature=archived, status=status)
        if effective != archived:
            result['effective_signature'] = effective
        if binding:
            result['model_identity'] = binding.identity
        results.append(result)
    return results


def inspect(request, handoff, base_path, fabric_path, policy_path, control_path,
            *, gather_inputs=None, call_archives=(), models=None):
    spec = read(handoff / 'algorithm2-input.json')
    wiring = verify_candidate(spec, handoff, base_path)
    base, program, receipt = read(base_path), read(handoff / 'program.json'), read(handoff / 'handoff.json')
    source = program['source']
    require(program['kind'] == 'native_request_program_index'
            and digest(program) == receipt['program_sha256']
            and digest(receipt) == wiring['admission']['receipt_sha256']
            and digest(base) == source['base_sha256'] == wiring['admission']['base_sha256'],
            'current program or base differs from the checked handoff')

    witness, signatures = verify_package(request, program)
    fabric, policy, control = read(fabric_path), read(policy_path), read(control_path)
    require(hash_file(fabric_path) == source['control_fabric_sha256']
            and hash_file(policy_path) == source['route_profile_sha256']
            and digest(fabric) == policy['control_fabric_digest']
            and control == seal(control) and control['sha256'] == source['control_projection_sha256']
            and control['source']['package_proof_sha256'] == source['package_proof_sha256']
            and control['source']['service_signatures_sha256'] == program['source_files']['service-signatures.json']
            and control['source']['mother_targets_sha256'] == program['source_files']['mother-targets.tsv'],
            'control projection or rewrite policy refers to different inputs')
    verify_native_targets(base, fabric, witness['topology'])
    required, missing, providers, replacements = bind_profiles(policy, signatures, base, fabric, control)
    require(providers == program['service_providers'] and missing == program['unresolved_services'],
            'service inventory differs from the selected program and base')
    requirements = read(handoff / 'requirements.json')
    require(requirements == seal(requirements)
            and requirements['sha256'] == receipt['request_sha256'],
            'requirements differ from the checked handoff')
    bound_demands = {row['demand_id'] for row in requirements['members']}
    for demand, users in required.items():
        require(demand in bound_demands and all(row in requirements['users'][demand] for row in users),
                f'missing service demand from the selected wiring: {demand}')

    if replacements:
        verify_gather_replacement(request, handoff, witness, program, gather_inputs,
                                  replacements[GATHER_ROLE]['calls'])
    else:
        require(not program.get('mother_replacement') and not program.get('replacement_pages'),
                'program installs a replacement absent from its rewrite policy')
    rewrites = {service_key(row['archived']): row['native'] for row in policy['rewrites']}
    results = match_models(providers, rewrites, {} if models is None else models)
    evidence = collect(request, call_archives) if call_archives else None
    if evidence:
        require(evidence['package_proof_sha256'] == source['package_proof_sha256'],
                'CALL evidence comes from a different program')
        by_signature = {service_key(row['signature']): row for row in results}
        for sample in evidence['signatures']:
            row = by_signature.get(service_key(sample))
            require(row is not None and 0 < sample['covered_calls'] <= row['signature']['calls'],
                    'CALL sample differs from the sealed service inventory')
            row['sample'] = sample['sample']
            row['sampled_calls'] = sample['covered_calls']
    signature_counts = Counter(row['status'] for row in results)
    call_counts = Counter()
    for row in results:
        call_counts[row['status']] += row['signature']['calls']
    return dict(
        schema='native-tlm-preflight/1',
        purpose='selected native plan and candidate base preflight',
        source={**source, 'program_sha256': receipt['program_sha256'],
                'wiring_sha256': receipt['wiring_sha256'],
                'router_input_sha256': receipt['router_input_sha256']},
        phases=[dict(step=row['step'], pages=row['page_count'], graph_sha256=row['graph_sha256'])
                for row in witness['phases']],
        pages=program['pages'], calls=program['calls'], service_signatures=dict(signature_counts),
        service_calls=dict(call_counts), services=results,
        candidate_wiring=wiring, rebuilt_replacement_pages=len(program['replacement_pages']),
        unresolved_feedback=program['unresolved_feedback'],
        call_evidence={key: value for key, value in evidence.items() if key != 'signatures'}
        if evidence else None,
        evaluation_executed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'handoff', 'base_path', 'fabric_path', 'policy_path', 'control_path', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--gather', nargs=2, type=Path, metavar=('LOCAL_IMAGES', 'DIRECT_CALL_AUDIT'))
    parser.add_argument('--call-archive', action='append', nargs=3, default=[],
                        metavar=('STEP', 'FIRST_PAGE', 'TAR'))
    args = parser.parse_args()
    archives = [(int(step), int(page), Path(path)) for step, page, path in args.call_archive]
    result = inspect(args.request, args.handoff, args.base_path, args.fabric_path,
                     args.policy_path, args.control_path, gather_inputs=args.gather,
                     call_archives=archives)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, sort_keys=True, indent=2)
        out.write('\n')


if __name__ == '__main__':
    main()

