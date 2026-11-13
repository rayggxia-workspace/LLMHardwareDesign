"""Verify PM lowering from a selected C/U plan, preserving the two handoffs' identity."""
import argparse
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from event_deploy import emit
from event_stored_link_control import local_image, routines
from route_contract import digest, verify_requirements
from verify_cover_frontier import verify


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return sha256(data).hexdigest()


def inspect(image, topology, block_type, image_id):
    import codec
    import compact

    header = compact.unpack_header(image[:128])
    code_end = header['task_offset']
    record_start = header['execution_offset']
    assert (header['role'], header['version'], header['total_bytes'], header['topology_id'],
            header['program_image_id'], header['native_abi_id'], header['capacity_profile_id'],
            header['resource_mask'], header['task_count'], header['transfer_count']) == (
                1, 2, len(image), topology, image_id, 0x01930001, 0x17630001, 1, 1, 0)
    code = compact.unpack_program(image[128:code_end], header['instruction_count'], 'local', 2)
    task = codec.unpack_record('task', image[code_end:record_start])
    assert (task['block_type'], task['entry_pc'], task['max_steps'], task['required_resources'],
            task['program_image_id'], task['topology_id'], task['native_abi_id']) == (
                block_type, 0, len(code), 1, image_id, topology, 0x01930001)
    table = []
    assert code[-1] == {'op': 'L_END'} and len(code) == 2*header['execution_count']+1
    for position, row in enumerate(range(record_start, len(image), 128)):
        assert code[2*position] == {'op': 'L_EXEC', 'a': 0, 'b': 0, 'c': position}
        assert code[2*position+1] == {'op': 'L_WAIT', 'x': 1}
        record = image[row:row+128]
        operation, = unpack_from('<H', record, 4)
        operand, = unpack_from('<I', record, 64)
        assert record[:4] == b'\1\0\0\0' and record[6:8] == b'\0\0'
        assert record[8:12] == b'\xff'*4 and record[20:26] == b'\xff'*6
        assert not any(record[80:])
        table.append((operation, operand))
    return tuple(table)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('handoff', 'reference', 'out'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    # Use the same assembler sources as the archived stored-link execution.
    from image import pack_image
    from handoff import verify_handoff
    from native_tlm_local import descriptor_key

    handoff = args.handoff
    result = read(handoff/'compile.json')
    base = read(handoff/'base.json')
    requirements = read(handoff/'native-route-requirements.json')
    p = result['outputs']['program']
    events = defaultdict(dict)
    model, hardware, plan = (result[name] for name in ('event_ir', 'resolved_hardware', 'plan'))
    assert verify(model['tasks'], hardware, model.get('covers', ()), plan,
                  wire_budget=result['wire_budget'])['passed']
    regenerated = emit(model['tasks'], hardware, model.get('covers', ()), plan, physical_base_sha256=digest(base))
    assert regenerated == result['outputs']
    assert read(handoff/'program.json')['control_ir'] == p
    wiring = regenerated['wiring']
    verify_requirements(requirements, wiring['users'], read(handoff/'catalog.json'), base, p['source'])
    submitted = read(handoff/'algorithm2-input.json')
    verified = verify_handoff(submitted, handoff, None)
    assert requirements['sha256'] == read(handoff/'handoff.json')['native_route_request_sha256']
    assert p['source']['plan_sha256'] == read(handoff/'handoff.json')['source']['plan_sha256']
    controllers = {meta['site']: group for group, meta in hardware['control_groups'].items()}

    identities = {'C0': (int('01930010', 16), 2), 'U0': (int('02500031', 16), 0)}
    for group, group_commands in p['locals'].items():
        for command in group_commands:
            events[command['sequence']][group] = command
    blobs, skipped = {}, []
    images_by_group = defaultdict(set)
    rejected_mutations = 0
    handoff_manifest = []
    rejected_tlm_records = 0
    for dispatch in p['mother'][:-1]:
        number = dispatch['sequence']
        local = events[number]
        assert set(dispatch['targets']) == local.keys()
        commands = list(local.values())
        if commands[0]['op'] != 'COPY':
            skipped.append({'sequence': number, 'service': commands[0]['service']})
            continue
        route = hardware['event_model']['routes'][commands[0]['route']]
        legs = routines(commands, route, controllers)
        assert legs.keys() == local.keys()
        if not handoff_manifest:
            for field, value in (('roles', commands[0]['roles']), ('required_completion', 'issued')):
                invalid = deepcopy(commands)
                invalid[1][field] = value
                try:
                    routines(invalid, route, controllers)
                except ValueError:
                    rejected_mutations += 1
                else:
                    raise AssertionError(f'{field} mismatch must reject the COPY')
            invalid = deepcopy(commands)
            for command in invalid:
                command['write'][0]['address'] += 1
            try:
                routines(invalid, route, controllers)
            except ValueError:
                rejected_mutations += 1
            else:
                raise AssertionError('a misaligned destination must reject the COPY')
        for group, records in legs.items():
            topology, block_type = identities[group]
            image_id = 1+len(blobs)
            image = local_image(records, topology=topology, image_id=image_id, block_type=block_type,
                                pack_image=pack_image)
            assert (inspect(image, topology, block_type, image_id) ==
                    tuple((opcode, word) for opcode, word, _ in records))
            record_start, = unpack_from('<I', image, 44)
            for offset in range(record_start, len(image), 128):
                try:
                    descriptor_key(image[offset:offset+128], p['source']['topology_id'])
                except ValueError:
                    rejected_tlm_records += 1
                else:
                    raise AssertionError('a legacy local record was accepted by the typed #260 codec')
            hash_value = sha(image)
            blobs[hash_value] = image
            images_by_group[group].add(hash_value)
            target_id = hardware['control_groups'][group]['block_id']
            handoff_manifest.append({'sequence': number, 'target': group, 'target_id': target_id,
                                     'pm_sha256': hash_value, 'pm_bytes': len(image),
                                     'wait_for': dispatch['wait_for']})
    original = {}
    ref_hashes = {name: checksum for checksum, name in
                  (line.split() for line in (args.reference/'results.sha256').read_text().splitlines())}
    for group, n in (('C0', 0), ('U0', 1)):
        name = f'normal/local{n}.mem'
        raw = (args.reference/name).read_bytes()
        assert sha(raw) == ref_hashes[name]
        packed = b''.join(int(word, 16).to_bytes(16, 'little') for word in raw.decode().splitlines())
        commands = inspect(packed, 0x01930010, identities[group][1], 19301+n)
        assert (commands[1] if group == 'C0' else commands[0]) == (
            (0x101, 40 | 40 << 10) if group == 'C0' else (0x103, 40))
        original[group] = ref_hashes[name]
    assert len(handoff_manifest) == 1024 and len(skipped) == 512 and rejected_tlm_records == 1536
    assert rejected_mutations == 3 and all(len(images) > 1 for images in images_by_group.values())
    args.out.mkdir()
    for hash_value, blob in blobs.items():
        (args.out/f'{hash_value}.pm').write_bytes(blob)
    manifest = {'source': p['source'], 'routes_sha256': requirements['sha256'], 'algo2': verified,
                'parts': handoff_manifest, 'unmapped_dispatches': skipped,
                'native_execution_qualified': False}
    report = {'program_source': p['source'], 'route_request_sha256': requirements['sha256'],
              'original_component_image_sha256': original, 'copy_commands': len(handoff_manifest)//2,
              'assembled_pm_images': len(blobs), 'maximum_image_bytes': max(map(len, blobs.values())),
              'local_exec_records_rejected_by_pinned_tlm': rejected_tlm_records,
              'remaining_noncopy_dispatches': len(skipped),
              'rejected_mutations': rejected_mutations,
              'distinct_local_images': {group: len(images) for group, images in images_by_group.items()},
              'scope': 'target local PM encoding/readback and independent Algo2 admission',
              'published_to_full_request': False}
    for name, data in (('report', report), ('stored-link-pm-manifest', manifest)):
        (args.out/f'{name}.json').write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
