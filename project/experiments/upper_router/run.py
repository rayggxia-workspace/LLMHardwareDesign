"""Generic upper routing CLI. Inputs are geometry or a bound #227 manifest."""
import argparse
import hashlib
import json
from pathlib import Path

from check import verify
from geometry import need
from search import route


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='standalone spec, or #227 request with --base/--technology')
    p.add_argument('output', type=Path)
    p.add_argument('--base', type=Path)
    p.add_argument('--technology', type=Path, help='object with technology and optional obstacles')
    p.add_argument('--frozen-base', type=Path, help='verify handoff against original native views')
    p.add_argument('--native-gds', type=Path, help='bind actual native GDS for physical readback')
    p.add_argument('--handoff', type=Path, help='directory containing Algorithm 1 provenance files')
    p.add_argument('--bundles', type=Path, help='optional net grouping and capacity hints')
    p.add_argument('--repeaters', type=Path, help='independent optional repeater and load model inventory')
    p.add_argument('--previous', type=Path, help='previous checked repeater result for repair')
    p.add_argument('--measurements', type=Path, help='extracted violations bound to --previous')
    p.add_argument('--max-repeaters', type=int, default=1, help='per-net maximum number of repeater stages')
    p.add_argument('--candidate-limit', type=int, default=12)
    p.add_argument('--access-pitch', type=int)
    p.add_argument('--access-radius', type=int)
    p.add_argument('--emit-def', type=Path, help='emit a checked upper interconnect DEF for backend readback')
    p.add_argument('--via-resistance-ohm', type=float)
    p.add_argument('--dbu-per-micron', type=int)
    p.add_argument('--rounds', type=int, default=8)
    p.add_argument('--max-expansions', type=int, default=100000, help='per-candidate per-round node budget')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--check', type=Path, help='verify existing route instead of searching')
    a = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    if bool(a.previous) != bool(a.measurements) or (a.previous and (not a.repeaters or a.check)):
        p.error('repair requires --previous, --measurements and --repeaters')
    request = None
    spec = read(a.input)
    if a.base or a.technology:
        from adapter import bind_request
        from route_contract import read_base
        if not (a.base and a.technology):
            p.error('--base and --technology must be supplied together')
        request = spec
        rules = read(a.technology)
        spec = bind_request(request, read_base(a.base), rules['technology'], rules.get('obstacles', []))
    if a.frozen_base and not a.handoff:
        p.error('--frozen-base requires --handoff')
    if a.handoff:
        from handoff import verify_handoff
        admission = verify_handoff(spec, a.handoff, a.frozen_base)
        if admission['scope'] == 'product' and a.emit_def and not (a.frozen_base and a.native_gds):
            p.error('product DEF handoff requires --frozen-base and --native-gds')
    else:
        admission = None
    if a.native_gds:
        hasher = hashlib.sha256()
        with a.native_gds.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                hasher.update(block)
        context = spec.setdefault('context', {})
        checksum = hasher.hexdigest()
        need(context.get('native_gds_sha256', checksum) == checksum, 'native GDS fingerprint differs')
        if admission:
            need(admission.get('native_gds_sha256', checksum) == checksum, 'native GDS differs from frozen base')
        context['native_gds_sha256'] = checksum
    spec['technology'].update({k: v for k, v in {'access_pitch': a.access_pitch,
                              'access_radius': a.access_radius}.items() if v is not None})
    if a.bundles:
        bundles = read(a.bundles)
        need(bundles['schema_version'] == 'upper-bundles/1', 'unsupported bundle hints')
        spec['bundles'] = bundles['bundles']
    data = read(a.repeaters) if a.repeaters else None
    if a.check:
        existing = read(a.check)
        if data is not None:
            from repeaters import check_allocations
            result = check_allocations(spec, data, existing)
        else:
            result = verify(spec, existing)
        physical_spec, physical_routes = spec, existing
    elif data is not None:
        from resource_search import route_resources
        options = {'rounds': a.rounds, 'max_expansions': a.max_expansions,
                   'seed': a.seed, 'candidate_limit': a.candidate_limit, 'max_repeaters': a.max_repeaters}
        if a.previous:
            from repair import repair
            result = repair(spec, data, read(a.previous), read(a.measurements), **options)
        else:
            result = route_resources(spec, data, **options)
        physical_spec, physical_routes = result['physical_spec'], result['physical_routes']
    else:
        result = route(spec, rounds=a.rounds, max_expansions=a.max_expansions, seed=a.seed)
        if request:
            from adapter import failure_feedback
            result['feedback'] = failure_feedback(request, result, str(a.output))
        physical_spec, physical_routes = spec, result
    if admission:
        result['admission'] = admission
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    if not a.check and result['failed']:
        raise SystemExit(2)
    if a.emit_def:
        from backend import emit
        need(not a.check, 'DEF export requires a new route')
        need(not result.get('used_virtual'), 'virtual repeaters cannot enter physical DEF handoff')
        emit(physical_spec, physical_routes, a.emit_def,
             a.dbu_per_micron or physical_spec.get('context', {}).get('dbu_per_micron'),
             via_resistance_ohm=a.via_resistance_ohm)
        if data is not None:
            topology = {k: result[k] for k in ('allocations', 'used_virtual', 'physical_qualified')}
            (a.emit_def/'logical-topology.json').write_text(json.dumps(topology, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
