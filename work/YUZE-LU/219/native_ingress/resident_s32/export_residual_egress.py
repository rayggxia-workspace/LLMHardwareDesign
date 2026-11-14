"""Compile the committed output COPY from a residual to its next graph consumer."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from audit_residual_handoff import audit_data_paths
from event_stored_link_control import ABI, CAPACITY, COMMIT_ACK, RECEIVE, RESERVE, SEND
from event_stored_link_control import local_image, routines
from route_contract import digest


def read(path):
    return json.loads(path.read_bytes())


def successor_operand(folder, value):
    sha, = [line.split('  ', 1)[0] for line in (folder / 'proof.sha256').read_text().splitlines()
            if line.endswith('  compile.json')]
    raw = (folder / 'compile.json').read_bytes()
    if sha256(raw).hexdigest() != sha:
        raise ValueError('changed successor compile')
    result = json.loads(raw)
    if result['verification']['passed'] is not True:
        raise ValueError('unverified successor')
    commands = [c for group in result['outputs']['program']['locals'].values() for c in group
                if c['op'] == 'EXEC' and any(row['value'] == value for row in c['read'])]
    command, = commands
    operand, = [row for row in command['read'] if row['value'] == value]
    return command['task_id'], operand, result['outputs']['program']['source']


def inspect(raw, records, target, image_id, codec, compact):
    topology, block_type, _ = target
    h = compact.unpack_header(raw[:128])
    if (h['version'], h['role'], h['native_abi_id'], h['capacity_profile_id'],
            h['topology_id'], h['program_image_id'], h['execution_count'], h['task_count'],
            h['transfer_count']) != (2, 1, ABI, CAPACITY, topology, image_id, len(records), 1, 0):
        raise ValueError('stored-link image header differs')
    code = compact.unpack_program(raw[128:h['task_offset']], h['instruction_count'], 'local', 2)
    task = codec.unpack_record('task', raw[h['task_offset']:h['execution_offset']])
    if (task['block_type'], task['max_steps']) != (block_type, len(code)):
        raise ValueError('stored-link task record differs')
    expected = []
    for index, (op, operand, _) in enumerate(records):
        start = h['execution_offset'] + 128 * index
        row = codec.unpack_record('execution', raw[start:start + 128])
        if (row['native_op'], row['native0'], row['native_abi_id']) != (op, operand, ABI):
            raise ValueError('stored-link execution record differs')
        expected.extend((dict(op='L_EXEC', a=0, b=0, c=index), dict(op='L_WAIT', x=1)))
    if code != [*expected, dict(op='L_END')]:
        raise ValueError('missing local completion wait')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('residual', 'successor', 'previous_handoff', 'gather_image', 'isa', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--gather-sha256', required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.isa))
    from image import codec, compact, pack_image

    proof = read(args.residual / 'residual-proof.json')
    program = read(args.residual / 'program.json')
    if program['control_ir']['source'] != proof['source']:
        raise ValueError('producer image source and selected plan disagree')
    command, = program['control_ir']['locals'][proof['target']]
    src, = command['write']
    consumer, dst, consumer_plan = successor_operand(args.successor, src['value'])
    if ((src['site'], dst['site']) != ('C0.S', 'U0.S')
            or src['bytes'] != dst['bytes'] or not src['bytes'] or src['bytes'] % 16):
        raise ValueError('graph values do not match the stored-link path')
    previous = args.previous_handoff
    access = audit_data_paths(previous / 'base.json', previous)
    if access != proof['data_paths']:
        raise ValueError('stored-link access belongs to a different placement')
    gather = args.gather_image.read_bytes()
    if sha256(gather).hexdigest() != args.gather_sha256:
        raise ValueError('reference U0 local image differs')
    u0_topology = compact.unpack_header(gather[:128])['topology_id']
    targets = {'C0': (proof['proof']['topology_id'], 2, 5), 'U0': (u0_topology, 0, 3)}
    sites = {src['site']: 'C0', dst['site']: 'U0'}
    route = dict(src=src['site'], dst=dst['site'], transport_abi='u-stored-link')
    images = proof['images']
    words = src['bytes'] // 16
    if [k for row in images for k in range(row['first_word'], row['first_word'] + row['words'])] != list(range(words)):
        raise ValueError('producer image words do not cover the consumer window')
    for row in images:
        if sha256((args.residual / row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('changed producer image')
    args.output.mkdir()
    waves = []
    for index in range(words):
        a, b = [dict(row, address=row['address'] + 16 * index, bytes=16) for row in (src, dst)]
        copy = dict(route=access['outbound']['demand'], read=[a], write=[b], op='COPY',
                    sequence=index, binding_id=command['binding_id'], task_id=command['task_id'],
                    required_completion=COMMIT_ACK)
        roles = routines([dict(copy, roles=[role]) for role in ('send', 'receive')], route, sites)
        source_word, target_word = a['address'] // 16, b['address'] // 16
        if roles != {'C0': [(SEND, source_word | target_word << 10, COMMIT_ACK)],
                     'U0': [(RESERVE, target_word, 'receive_reserved'), (RECEIVE, 0, COMMIT_ACK)]}:
            raise ValueError('stored-link records do not match the graph slices')
        controls = []
        for number, (target, records) in enumerate(roles.items()):
            topology, block_type, target_id = targets[target]
            image_id = 22000 + index * len(roles) + number
            payload = local_image(records, topology=topology, image_id=image_id, block_type=block_type,
                                  pack_image=pack_image)
            inspect(payload, records, targets[target], image_id, codec, compact)
            path = args.output / f'copy-{image_id}.bin'
            path.write_bytes(payload)
            controls.append(dict(target=target, target_id=target_id, image_id=image_id,
                                 bytes=len(payload), path=path.name, sha256=sha256(payload).hexdigest()))
        waves.append(dict(copy, images=controls, wait_for_wave=index - 1 if index else None))
    result = dict(format='algo1-resident-result-egress/1', producer=program['source'],
                  producer_terminal_image=images[-1]['image_id'],
                  producer_report_sha256=sha256((args.residual / 'residual-proof.json').read_bytes()).hexdigest(),
                  physical_input=access['outbound'], consumer=consumer, consumer_plan=consumer_plan,
                  consumer_operand=dst, consumer_requires=dict(wave=waves[-1]['sequence'], completion=COMMIT_ACK),
                  execution_status='local_images_and_dispatch_dependencies_only', waves=waves)
    (args.output / 'egress.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(waves=len(waves), consumer=consumer, images=sum(len(x['images']) for x in waves),
                          manifest_sha256=digest(result)), sort_keys=True))


if __name__ == '__main__':
    main()
