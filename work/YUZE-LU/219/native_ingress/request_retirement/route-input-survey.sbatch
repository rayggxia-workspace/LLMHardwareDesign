#!/usr/bin/env bash
set -euo pipefail
cd "$1"
framework=$2
router=$3
handoff=$4
prior=$5
out="$PWD/route-survey-$SLURM_JOB_ID.json"
PYTHONPATH="$framework:$router" python3 -B - "$handoff" "$prior" "$out" <<'PY'
from collections import Counter,defaultdict
from hashlib import sha256
import json,sys
from pathlib import Path
from handoff import verify_handoff
from check import digest, verify
from geometry import NativePins, Occupancy, access_points, via_shapes
from search import route_shapes

handoff,prior,out=map(Path,sys.argv[1:])
spec=json.loads((handoff/'algorithm2-input.json').read_bytes())
req=json.loads((handoff/'requirements.json').read_bytes())
result=json.loads(prior.read_bytes())
admission=verify_handoff(spec,handoff)
assert result['admission']['scope']==admission['scope'] and result['admission']['base_sha256']==admission['base_sha256']
# Store both receipts because the later program rebound changes the handoff digest.
if digest(spec) != result['spec_sha256']:
    raise ValueError('route result was evaluated under a different technology')
geometry = verify(spec, result)
technology = spec['technology']
native = NativePins(spec)
fixed = Occupancy(technology)
fixed.add([(o['layer'], o['rect']) for o in spec.get('obstacles', ())], None)
routed = fixed.fork()
for name, route in result['routes'].items():
    routed.add(route_shapes(route, technology), name)
members={m['id']:m for m in req['members']}
classifications=defaultdict(Counter)
critical={}
for n in req['nets']:
    group=tuple(sorted({members[m]['demand_id'] for m in n['members']}))
    status='geometry_checked' if n['id'] in result['routes'] else result['failed'][n['id']]
    classifications[group][status]+=1
    if status=='grid_access_not_found':
        terminals = [n['driver'], *n['sinks']]
        pins = []
        for pin in terminals:
            grid = access_points(spec['pins'][pin], technology)
            exclusive = [point for point in grid if native.exclusive(point, set(terminals))]
            static = [point for point in exclusive
                      if fixed.legal(via_shapes('via10', point, technology), n['id'])]
            free = [point for point in static
                    if routed.legal(via_shapes('via10', point, technology), n['id'])]
            pins.append(dict(pin=pin, on_grid=len(grid), exclusive=len(exclusive),
                             available_before_routes=len(static), available_after_routes=len(free)))
        critical[n['id']] = pins
summary=dict(request_sha256=req['sha256'],routing_spec_sha256=digest(spec),admission=admission,
             algorithm2_result_sha256=sha256(prior.read_bytes()).hexdigest(), routed_admission=result['admission'],
             static_bits=len(members),nets=len(spec['nets']),geometry_checked=geometry['nets_checked'],
             geometry_spec_sha256=digest(spec),
             nonhard_observations=sum(not x['hard_constraint'] for x in result['feedback']['observations']),
             groups=[dict(demands=ids,status=dict(count)) for ids,count in sorted(classifications.items())],
             no_access=critical)
out.write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(out)
PY
sha256sum "$out"
