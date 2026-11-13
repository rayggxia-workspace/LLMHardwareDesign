from collections import Counter, defaultdict
from pathlib import Path
import argparse
import json
import re

from event_physical_contract import qualify_hardware
from publish_event_handoff import build
from route_contract import bind_members, digest, read_base, verify_requirements
from run import compile_event_ir
from adapter import bind_request
from geometry import access_points, validate
from handoff import verify_handoff

ROLES = (
    ('data', 128, 'outgoing_data', 'rx_data', False),
    ('address', 10, 'outgoing_addr', 'rx_addr', False),
    ('valid', 1, 'outgoing_valid', 'rx_valid', False),
    ('ready', 1, 'outgoing_ready', 'rx_ready', True),
    ('stored_ack', 1, 'outgoing_ack', 'rx_stored', True),
    ('ack_ready', 1, 'outgoing_ack_ready', 'rx_stored_ready', False),
    ('reserved', 1, 'peer_reserved', 'rx_reserved', True),
    ('reserved_address', 10, 'peer_addr', 'rx_reserved_addr', True),
)
U_PORTS = {
    'rx_data': 'incoming_data', 'rx_addr': 'incoming_addr',
    'rx_valid': 'incoming_valid', 'rx_ready': 'incoming_ready',
    'rx_stored': 'incoming_ack', 'rx_stored_ready': 'incoming_ack_ready',
    'rx_reserved': 'link_rx_reserved', 'rx_reserved_addr': 'link_rx_addr',
    'peer_reserved': 'peer_rx_reserved', 'peer_addr': 'peer_rx_addr',
}
RECT = re.compile(r'\+ LAYER metal10\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*'
                  r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', re.I)
POSITION = re.compile(r'\+ (?:FIXED|PLACED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)')

def make_signals(src, dst):
    for role, width, src_pin, dst_pin, reverse in ROLES:
        if src.startswith('U'):
            src_pin = U_PORTS.get(src_pin, src_pin)
        if dst.startswith('U'):
            dst_pin = U_PORTS.get(dst_pin, dst_pin)
        suffix = '[{bit}]' if width > 1 else ''
        source = f'{src}/{src_pin}{suffix}'
        target = f'{dst}/{dst_pin}{suffix}'
        if reverse:
            source, target = target, source
        yield dict(name=role, role=role, width=width, driver=source, sinks=[target])

def def_ports(path, needed):
    records = {}
    with Path(path).open(encoding='ascii') as stream:
        for line in stream:
            if line.startswith('PINS '):
                break
        record = []
        for line in stream:
            if line.startswith('END PINS'):
                break
            if line.lstrip().startswith('- '):
                name = line.split()[1].replace('\\', '')
                record = [line] if name in needed else []
            elif record:
                record.append(line)
            if not record or ';' not in line:
                continue
            text = ''.join(record)
            net = re.search(r'\+ NET (\S+)', text)[1].replace('\\', '')
            direction = re.search(r'\+ DIRECTION (\w+)', text)[1]
            shapes = []
            for port in re.split(r'\+ PORT\b', text):
                rects = RECT.findall(port)
                if rects:
                    position = POSITION.findall(port)
                    if len(position) != 1 or position[0][2] != 'N':
                        raise ValueError(f'{name}: unknown M10 port transform')
                    x, y = map(int, position[0][:2])
                    shapes.extend([int(n)+offset for n, offset in zip(r, (x, y, x, y))]
                                  for r in rects)
            records[name] = direction, net, shapes
            record = []
    return records

def bit_terminals(signals):
    for signal in signals:
        for bit in range(signal['width']):
            yield signal['role'], signal['driver'].format(bit=bit), signal['sinks'][0].format(bit=bit)

def read_json(path):
    return json.loads(path.read_bytes())

def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description='Bind one stored-link tile to actual Block V2 BTerms.')
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--access-pitch', type=int, default=400, help='Algo2 study access grid, in DBU')
    args = parser.parse_args()
    base = read_base(args.candidate / 'base')
    source_digest = digest(base)
    fabric = read_json(args.candidate / 'control-fabric')
    tech = read_json(args.candidate / 'algorithm2-input.json')['technology']
    tech['access_pitch'] = args.access_pitch
    sites = ('C0', 'U0', 'U1')
    links = [(src, dst) for src in sites for dst in sites if src != dst and 'C0' in (src, dst)]
    candidates = {f'stored:{src}->{dst}': (src, dst, list(make_signals(src, dst)))
                  for src, dst in links}
    needed = defaultdict(set)
    for _, _, signals in candidates.values():
        for _, driver, sink in bit_terminals(signals):
            for endpoint in (driver, sink):
                owner, pin = endpoint.split('/')
                needed[owner].add(pin)

    failures, endpoint_meta = {}, {}
    for owner, required in needed.items():
        assembly = next(a for a in base['assemblies'] if a['id'] == owner)
        source = base['views'][assembly['views']['def']]['path']
        dx, dy = assembly['translation_dbu']
        records = def_ports(source, required)
        for pin in sorted(required):
            key = f'{owner}/{pin}'
            if pin not in records:
                failures[key] = 'no DEF BTerm'
                continue
            direction, net, shapes = records[pin]
            if not shapes:
                failures[key] = 'DEF BTerm has no M10 conductor'
                continue
            endpoint_meta[key] = dict(assembly=owner, odb_term=key, native_net=f'{owner}/{net}',
                                      role={'INPUT': 'sink', 'OUTPUT': 'driver'}[direction],
                                      m10_shapes=[dict(layer='M10', object=f'{key}/M10/{i}',
                                                       rect_dbu=[n+o for n,o in zip(r,(dx,dy,dx,dy))])
                                                  for i,r in enumerate(shapes)])
    audit = {}
    for name, (src, dst, signals) in candidates.items():
        missing = {}
        for role, driver, sink in bit_terminals(signals):
            for endpoint, required_role in ((driver, 'driver'), (sink, 'sink')):
                reason = failures.get(endpoint)
                if reason or endpoint_meta[endpoint]['role'] != required_role:
                    missing[endpoint] = (role, reason or 'DEF BTerm direction differs')
        audit[name] = {'bits': sum(s['width'] for s in signals),
                       'missing_by_role': dict(Counter(role for role, _ in missing.values())),
                       'missing_endpoints': missing}

    chosen = 'stored:C0->U0'
    assert not audit[chosen]['missing_endpoints'], audit[chosen]
    assert not audit['stored:C0->U1']['missing_endpoints'], audit['stored:C0->U1']
    assert audit['stored:U0->C0']['missing_by_role'] == {'data': 128}
    assert audit['stored:U1->C0']['missing_by_role'] == {'data': 128}
    base['endpoints'].update(endpoint_meta)
    base['provenance']['scope'] = 'translated control and stored-link BTerms in candidate source views'
    routes = {name: dict(src=src, dst=dst, setup=4, bytes_per_tick=16,
                         claims={src+'.S': 1, dst+'.S': 1},
                         nets=[name], transport_width_bits=128, transport_abi='u-stored-link')
              for name, (src, dst, _) in candidates.items()}
    nets = {name: dict(cost=sum(s['width'] for s in signals), signals=signals)
            for name, (_,_,signals) in candidates.items()}
    hardware = dict(topology_id=25001, resources={s+'.S': 1 for s in sites},
                    sites={s: {'bytes': 16384, 'words': 1024} for s in sites},
                    nets=nets, event_model=dict(kind='qualified-event-model-v1', routes=routes,
                    services={'consume-tile': dict(ticks=1, claims={'U0.S': 1}, control_site='U0')},
                    windows={s: dict(site=s, offset=640, bytes=16) for s in sites},
                    value_bytes={'x': 16}, initial_copies={'C0': 'x'}, live_out=['x']))
    event_ir = {'tasks': [dict(id='consume', after=[], bindings=[dict(
        id='consume-one-word', site='U0', ticks=1, resources=[], nets=[], scratch_words=0,
        event_stages=[dict(service='consume-tile', inputs={'U0': 'x'}, outputs={},
                           input_policy='any')])])]}
    # Both directions are declared. Endpoint admission must remove the absent reverse pad.
    result = compile_event_ir(event_ir, hardware, route_base=base, route_scope='interface',
                              control_fabric=fabric)
    assert result['status'] == 'planned', result
    assert result['verification']['passed']
    hw = result['resolved_hardware']
    issues = qualify_hardware(hw, base)['event_model']['physical_interface_issues']
    assert chosen not in issues['routes'], issues
    assert 'data' in issues['routes']['stored:U0->C0'], issues
    moves = [e for row in result['plan']['tasks'] for e in row['evaluation']['events']
             if e['kind'] == 'move']
    assert len(moves) == 1 and moves[0]['route'] == chosen, moves
    catalog = dict(schema_version='route-contract/1', demands={
        name: {k: item[k] for k in ('signals', 'requires') if k in item}
        for name,item in hw['nets'].items()
    })
    handoff = build(event_ir, hw, result['plan'], catalog, base, {'technology':tech},
                    bind_request, source_outputs=result['outputs'])
    validate(handoff['algorithm2-input'])
    data_members = [m for m in handoff['requirements']['members'] if m['demand_id'] == chosen]
    assert len(data_members) == audit[chosen]['bits']
    args.output.mkdir()
    for name,data in {**handoff, 'base':base, 'compile':result, 'catalog':catalog,
                      'endpoint-audit':audit}.items():
        write_json(args.output / (name + '.json'), data)
    receipt = dict(
        prior_base_sha256=source_digest, plan_sha256=handoff['handoff']['source']['plan_sha256'],
        route=chosen, data_link_bits=len(data_members),
        data_bus_bits=sum(m['signal']=='data' for m in data_members),
        new_signal_nets=handoff['handoff']['coverage']['new_signal_nets'],
        unqualified_routes=issues['routes'],
        scope='source-view endpoint mapping only; resident test input and modeled service latency')
    # Algo2's interface verifier reads the package. Grouped source views have
    # no whole-chip GDS. Independently rebind every bit from the hashed views.
    spec = read_json(args.output / 'algorithm2-input.json')
    request = read_json(args.output / 'requirements.json')
    native_request = read_json(args.output / 'native-route-requirements.json')
    sealed_base = read_base(args.output / 'base.json')
    assert digest(sealed_base) == request['base_sha256']
    rebound, unresolved = bind_members(request['members'], sealed_base)
    assert not unresolved and rebound == request['nets']
    assert bind_request(request, sealed_base, spec['technology'], spec['obstacles']) == spec
    verify_requirements(native_request, handoff['wiring']['users'], catalog, sealed_base,
                        native_request['source'])
    assert native_request['members'] == request['members']
    assert native_request['source']['plan_sha256'] == request['source']['plan_sha256']
    assert native_request['source']['hardware_sha256'] == request['source']['hardware_sha256']
    admission = verify_handoff(spec, args.output)

    access = {pin for pin, rectangles in spec['pins'].items()
              if access_points(rectangles, spec['technology'])}
    accessible = {net['id'] for net in spec['nets']
                  if {net['driver'], *net['sinks']} <= access}
    members = {member['id'] for member in data_members}
    data_nets = {net['id'] for net in request['nets'] if members.intersection(net['members'])}
    receipt.update(
        admission=admission, access_pitch_dbu=args.access_pitch,
        endpoints_with_access=len(access), endpoints=len(spec['pins']),
        nets_with_access=len(accessible), nets=len(spec['nets']),
        data_nets_with_access=len(data_nets & accessible), data_nets=len(data_nets))
    write_json(args.output / 'readback.json', receipt)
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
