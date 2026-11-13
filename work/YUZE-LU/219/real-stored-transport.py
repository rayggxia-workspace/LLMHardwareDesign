"""Check the declared C/U transport granularity on actual Algo2 route inputs."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from publish_event_handoff import build
from adapter import bind_request
from handoff import verify_handoff
from run import compile_event_ir


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'row', 'audit', 'out'):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()

    def load(name):
        return json.loads(name.read_bytes())

    bundle = args.bundle
    data = load(bundle / 'compile.json')
    result = load(bundle / 'algorithm2-input.json')
    admission = verify_handoff(result, bundle, None)
    base = load(bundle / 'base.json')
    hardware, ir = data['resolved_hardware'], data['event_ir']
    spec = hardware['event_model']
    word = compile_event_ir(ir, hardware, route_base=base, route_scope='interface', emit_outputs=True)
    assert word['outputs'] == data['outputs'], 'existing physical word handoff changed'
    gather = load(args.row / 'compile.json')['event_ir']['tasks'][0]
    gather_cfg = load(args.row / 'compile.json')['resolved_hardware']['event_model']
    last_stage = gather['bindings'][0]['event_stages'][-1]
    row_value, = last_stage['outputs'].values()
    row_bytes = gather_cfg['value_bytes'][row_value]
    audit = load(args.audit)
    assert row_bytes == audit['path'][1]['bytes']
    route, = [r for r in spec['routes'].values() if (r['src'], r['dst']) == ('C0', 'U0')]
    assert route['transport_abi'] == 'u-stored-link'
    value, = spec['initial_copies'].values()
    larger = deepcopy(hardware)
    large = larger['event_model']
    large['value_bytes'][value] = row_bytes
    for window in ('C0', 'U0'):
        large['windows'][window].update(offset=0, bytes=row_bytes)
    small = compile_event_ir(ir, larger, route_base=base, route_scope='interface', emit_outputs=True)
    assert small['status'] == 'no_plan_in_bounded_search', 'one reservation carried more than one word'
    # A control run proves that the 8 KiB windows fit and that it was the ABI,
    # not the planner's capacity, that rejected the single-transfer mapping.
    for record in large['routes'].values():
        record.pop('transport_abi', None)
    hypothetical = compile_event_ir(ir, larger, route_base=base, route_scope='interface', emit_outputs=True)
    assert hypothetical['status'] == 'planned'
    bits = audit['path'][3]['bits']
    word_bytes = audit['path'][3]['bytes_per_live_reservation']
    rows = row_bytes // word_bytes
    split = deepcopy(hardware)
    split_spec = split['event_model']
    split_spec['windows'] = {
        f'{site}.{i}': {'site': site, 'offset': i*word_bytes, 'bytes': word_bytes}
        for site in ('C0', 'U0') for i in range(rows)
    }
    split_spec['routes'] = {name: record for name, record in split_spec['routes'].items()
                            if {record['src'], record['dst']} <= {'C0', 'U0'}}
    split_spec['value_bytes'] = {f'word-{i}': word_bytes for i in range(rows)}
    split_spec['initial_copies'] = {f'C0.{i}': f'word-{i}' for i in range(rows)}
    split_spec['live_out'] = list(split_spec['value_bytes'])
    node = deepcopy(ir['tasks'][0])
    node['id'] = 'consume-fragments'
    binding, = node['bindings']
    binding['id'] = 'one-reservation-per-word'
    service = binding['event_stages'][0]['service']
    binding['event_stages'] = [
        {'service': service, 'inputs': {f'U0.{i}': f'word-{i}'}, 'outputs': {},
         'input_policy': 'any'}
        for i in range(rows)
    ]
    fragmented = compile_event_ir({'tasks': [node]}, split, route_base=base,
                                  route_scope='interface', emit_outputs=True)
    assert fragmented['status'] == 'planned' and fragmented['verification']['passed']
    program = fragmented['outputs']['program']
    wiring = fragmented['outputs']['wiring']
    assert program['source'] == wiring['source']
    assert wiring['members'] == word['outputs']['wiring']['members']
    for site, role in (('C0', 'send'), ('U0', 'receive')):
        copies = [cmd for cmd in program['locals'][site] if cmd['op'] == 'COPY']
        assert len(copies) == rows
        for i, cmd in enumerate(copies):
            src, = cmd['read']
            dst, = cmd['write']
            assert cmd['roles'] == [role] and cmd['required_completion'] == 'destination_commit_ack'
            assert src['address'] == dst['address'] == i*word_bytes
            assert src['bytes'] == dst['bytes'] == word_bytes
            if site == 'U0':
                consumer = program['mother'][cmd['sequence'] + 1]
                assert cmd['sequence'] in consumer['wait_for']
    target = args.out.parent / f'{args.out.stem}-handoff'
    target.mkdir()
    catalog = load(bundle / 'catalog.json')
    rules = {'technology': result['technology'], 'obstacles': result.get('obstacles', [])}
    files = build(fragmented['event_ir'], fragmented['resolved_hardware'], fragmented['plan'],
                  catalog, base, rules, bind_request, source_outputs=fragmented['outputs'])
    for name, record in dict(files, base=base, catalog=catalog, compile=fragmented).items():
        (target / f'{name}.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
    submitted = files['algorithm2-input']
    fragment_admission = verify_handoff(submitted, target, None)
    assert files['program']['source'] == files['wiring']['source'] == files['handoff']['source']
    assert files['program']['control_ir']['source'] == program['source']
    assert files['handoff']['coverage'] == load(bundle / 'handoff.json')['coverage']
    assert not files['program']['native_execution_qualified']
    (args.out.parent/f'{args.out.stem}-fragments.json').write_text(
        json.dumps(fragmented, indent=2, sort_keys=True)+'\n')
    report = {
        'source': word['outputs']['wiring']['source'], 'admission': admission, 'transport_wire_bits': bits,
        'native_word_bytes': word_bytes, 'gather_row_bytes': row_bytes, 'reservations_required': row_bytes//word_bytes,
        'word_plan': word['status'], 'row_single_reservation': small['status'],
        'fragmented_plan': fragmented['status'], 'fragment_copy_commands': rows,
        'fragment_static_members': len(wiring['members']), 'fragment_source': program['source'],
        'fragment_admission': fragment_admission, 'fragment_handoff': files['handoff'],
        'row_if_word_contract_is_removed': hypothetical['status'],
        'archived_gather_program_sha256': sha256((args.row/'descriptors.bin').read_bytes()).hexdigest(),
        'boundary': 'Main C/U endpoint handoff and independent schedule validation. No indexed row provider or runtime execution.',
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
