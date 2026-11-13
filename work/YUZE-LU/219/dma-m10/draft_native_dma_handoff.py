"""Compile the same P program and wire requirements with staged DMA M10 landings."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

from route_contract import read_base, require
from run import compile_event_ir
from event_deploy import route_catalog
from publish_event_handoff import build

router, work, pin_source, output = map(Path, sys.argv[1:])
sys.path.insert(1, str(router))
from adapter import bind_request
from geometry import access_points, validate
from handoff import verify_handoff


def read(path):
    return json.loads(path.read_bytes())


def checksum(path):
    with path.open('rb') as stream:
        state = sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            state.update(chunk)
        return state.hexdigest()


def write(name, value):
    (output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


base = read_base(work / 'p-v2-direct-m10-109804/base.json')
underlay = work / 'native-dma-prerequisites-109781'
original = read(work / 'native-same-plan-109741/compile.json')
hardware = read(underlay / 'hardware.json')
rules = read(work / 'native-same-plan-109741/algorithm2-input.json')
required_landings = pin_source / 'landings.tsv'
geometry = pin_source / 'geometry.tsv'
die = next(tuple(map(int, row.split('\t')[1:])) for row in geometry.read_text().splitlines()
           if row.startswith('die\t'))
require(die == (0, 0, 3920000, 3920000), 'DMA die changed since the fit study')
dx, dy = 9576000, 0
old_bounds = base['bounds_dbu']
require(old_bounds == rules['technology']['bounds'], 'original routing extent differs')
base['bounds_dbu'] = [*old_bounds[:2], dx + die[2] + 100000, old_bounds[3]]
rules['technology']['bounds'] = base['bounds_dbu']
rules['technology'].update(access_pitch=400, access_radius=16000)
base['base_id'] += '-staged-dma-east'
# This is an interface-only geometry preview. The DMA has no routed and
# sealed GDS at this point. The real candidate manifest must bind that view.
base['assembly_state'] = 'staged_source_views'
# The source ODB and landing plan are deliberately distinct artifacts.
source_sha, source_odb = (work.parent / 'joint-ddr-4C8sHe/dma-placed-odb.sha256').read_text().strip().split('  ', 1)
require(checksum(Path(source_odb)) == source_sha, 'DMA source ODB changed')
base['views']['DMA.odb'] = {'path': source_odb, 'sha256': source_sha}
base['views']['DMA.endpoint_plan'] = {'path': str(required_landings.resolve()),
                                      'sha256': checksum(required_landings)}
base['assemblies'].append({'id': 'dma', 'state': 'staged', 'translation_dbu': [dx, dy],
                           'views': {'odb': 'DMA.odb', 'endpoint_plan': 'DMA.endpoint_plan'}})

placed_pins = work / 'native-dma-pin-access-109786/dma.tsv'
with placed_pins.open() as stream:
    source = {row['logical_pin']: row for row in csv.DictReader(stream, delimiter='\t')}
landings = {}
for line in required_landings.read_text().splitlines():
    name, role, *rect = line.split('\t')
    require(name in source and name not in landings and source[name]['direction'] == role,
            'unexpected DMA pin in landing plan')
    require(source[name]['native_net'] == name, 'DMA pin is not the audited native component')
    terminal = 'dma/' + name
    landings[name] = terminal
    base['endpoints'][terminal] = {
        'assembly': 'dma', 'odb_term': terminal, 'native_net': terminal,
        'role': 'driver' if role == 'OUTPUT' else 'sink',
        'm10_shapes': [{'layer': 'M10', 'object': terminal + '/M10/0',
                        'rect_dbu': [int(v) + offset for v, offset in zip(rect, (dx, dy, dx, dy))]}],
    }
require(len(landings) == len(source) == 4344, 'incomplete staged DMA interface')

result = compile_event_ir(original['event_ir'], hardware, route_base=base, route_scope='interface',
                          emit_outputs=True, control_fabric=hardware['event_model']['control_fabric'])
require(result['status'] == 'planned', str(result.get('native_dispatch_issues')))
hw = result['resolved_hardware']
pack = build(result['event_ir'], hw, result['plan'], route_catalog(hw), base, rules, bind_request,
             source_outputs=result['outputs'])
spec = pack['algorithm2-input']
validate(spec)
no_access = [pin for pin, rects in spec['pins'].items() if not access_points(rects, spec['technology'])]
output.mkdir()
for name, item in pack.items():
    write(name + '.json', item)
write('compile.json', result)
write('base.json', base)
admission = verify_handoff(spec, output)
summary = {'admission': admission, 'physical_qualified': False, 'staged_landings': len(landings),
           'physical_nets': len(spec['nets']), 'terminals': len(spec['pins']),
           'without_grid_access': len(no_access),
           'no_access_by_assembly': {name: sum(pin.startswith(name + '/') for pin in no_access)
                                     for name in {pin.split('/')[0] for pin in no_access}},
           'scope': 'same Algo1 plan and staged DMA M10 interface trial; lower route open'}
write('summary.json', summary)
print(json.dumps(summary))
