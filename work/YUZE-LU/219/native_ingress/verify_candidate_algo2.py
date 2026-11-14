"""Independently replay Algo1 candidate bindings and check Algo2 admission."""

import argparse
import json
from pathlib import Path

from route_contract import bind_members, digest, read_base, require
from adapter import bind_request
from geometry import validate
from handoff import verify_handoff


def verify_candidate(spec, folder, base_path):
    """Read independently supplied candidate views and rebuild all router pins."""
    admission = verify_handoff(spec, folder)
    require(admission['scope'] == 'interface', 'expected an interface handoff')
    base = read_base(base_path)
    require(base['state'] == 'candidate', 'expected a candidate base')
    require(digest(base) == admission['base_sha256'], 'candidate base fingerprint differs')

    request = json.loads((folder / 'requirements.json').read_bytes())
    nets, unresolved = bind_members(request['members'], base)
    require(not unresolved and nets == request['nets'], 'candidate net bindings differ')

    rebound = bind_request(request, base, spec['technology'], spec.get('obstacles', []))
    for key, value in rebound.items():
        require(spec.get(key) == value, f'candidate router {key} differs')
    validate(spec)
    return {
        'admission': admission,
        'assembly_state': base.get('assembly_state'),
        'router_input_sha256': digest(spec),
        'bound_nets': len(nets),
        'bound_m10_terminals': len(rebound['pins']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('handoff', type=Path)
    parser.add_argument('candidate_base', type=Path)
    args = parser.parse_args()
    spec = json.loads((args.handoff / 'algorithm2-input.json').read_bytes())
    print(json.dumps(verify_candidate(spec, args.handoff, args.candidate_base), indent=2))


if __name__ == '__main__':
    main()
