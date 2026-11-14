"""Recompile a graph Add with pre-resident operands and export its C0 plan."""

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from event_deploy import route_catalog
from link_resident_s32_add import NATIVE_ABI, link, operands
from route_contract import read_base
from run import compile_event_ir
from publish_event_handoff import build
from verify_candidate_algo2 import verify_candidate
from adapter import bind_request
from audit_residual_handoff import audit_data_paths


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def source_scope(folder):
    proof = {}
    for row in (folder / 'proof.sha256').read_text().splitlines():
        checksum, name = row.split('  ', 1)
        if name in proof:
            raise ValueError('duplicate source proof member')
        proof[name] = checksum
    paths = [folder / name for name in ('compile.json', 'deployment.json', 'descriptors.bin')]
    for path in paths:
        if sha256(path.read_bytes()).hexdigest() != proof[path.name]:
            raise ValueError(f'changed source asset {path.name}')
    compile_result, deployment = map(read, paths[:2])
    control = compile_result['outputs']['program']
    if (control['source'] != deployment['source']
            or compile_result['verification']['passed'] is not True):
        raise ValueError('source schedule and deployment disagree')
    graph_call, = [row for row in deployment['calls'] if row['service_signature'] == [3, 7, 2]]
    offset = 128 * graph_call['sequence']
    descriptor = paths[2].read_bytes()[offset:offset + 128]
    if sha256(descriptor).hexdigest() != graph_call['sha256']:
        raise ValueError('ADD2 CALL reference differs from descriptor')
    task, = compile_result['event_ir']['tasks']
    stage, = task['bindings'][0]['event_stages']
    return descriptor, compile_result, task, stage


def resident_plan(original, task, stage, base, fabric, group):
    site = group + '.S'
    hardware = deepcopy(original['resolved_hardware'])
    old_site, = hardware['sites']
    hardware['sites'][site] = hardware['sites'].pop(old_site)
    hardware['control_groups'] = {group: {'site': site, 'block_id': fabric['targets'][group]['target_id']}}
    model = hardware['event_model']
    model['routes'] = {}
    model['initial_backing'] = []
    model['initial_copies'] = dict(stage['inputs'])
    del model['recipes']
    for window in model['windows'].values():
        window['site'] = site
    service = model['services'][stage['service']]
    service['control_site'] = site
    service['native_providers'] = {group: 'resident-e32-add'}
    hardware['native_provider_contracts'] = {'resident-e32-add': {'calls': [
        dict(schema=1, abi=NATIVE_ABI, opcode=0x100, completion='service_done')]}}
    target, = [row for row in base['native_service_routes']['targets'] if row['group'] == group]
    view = target['netlist_view']
    if not any(row['schema'] == 1 and row['abi'] == NATIVE_ABI and row['opcode'] == 0x100
               for row in target['routes']):
        raise ValueError('base lacks a resident C E32 command provider')
    task = deepcopy(task)
    task['bindings'][0]['site'] = site
    result = compile_event_ir({'tasks': [task]}, hardware,
                              route_base=base, route_scope='interface', control_fabric=fabric)
    if result['status'] != 'planned':
        raise ValueError(f'C-group resident graph did not compile: {result}')
    return result, view


def read_images(bundle, compact, codec):
    count = 0
    for artifact in bundle['images']:
        raw = artifact['image']
        header = compact.unpack_header(raw[:128])
        n = header['instruction_count']
        code = compact.unpack_program(raw[128:128 + compact.section_size(n, header['version'])],
                                      n, 'local', header['version'])
        expected = [opcode for i in range(artifact['words']) for opcode in ('L_EXEC','L_WAIT')]
        if [row['op'] for row in code] != [*expected, 'L_END']:
            raise ValueError('C task may complete before the last write')
        where = header['execution_offset']
        for i in range(artifact['words']):
            record = codec.unpack_record('execution', raw[where + i*128:where + (i+1)*128])
            k = artifact['first_word'] + i
            left, right, dst = bundle['shape'][:3]
            if (record['native_op'], record['native0'], record['native1'], record['native2'],
                    code[i*2]['c'], code[i*2+1]['x']) != (
                    0x100, 0x8018 | (dst+k)<<5, (left+k) | (right+k)<<10, 0xF0, i, 1):
                raise ValueError('C machine operands differ from selected ADD2')
            count += 1
    if count != bundle['shape'][3]:
        raise ValueError('C image sequence did not cover output words')
    return count



def check_negative_cases(descriptor, command, source, policy, pack_image):
    broken = bytearray(descriptor)
    broken[-1] ^= 1
    shifted = deepcopy(command)
    shifted['read'][0]['address'] += 16
    wrong_site = deepcopy(command)
    wrong_site['read'][0]['site'] = 'other.S'
    cases = (
        ('checksum', broken, command, 'invalid PR260 ADD2 descriptor'),
        ('operand', descriptor, shifted, 'ADD2 descriptor and selected operands disagree'),
        ('site', descriptor, wrong_site, 'selected operands are outside the target private SRAM'),
    )
    for name, data, call, expected in cases:
        try:
            link(data, call, source, policy, pack_image)
        except ValueError as exc:
            if str(exc) != expected:
                raise
        else:
            raise ValueError(f'false acceptance: {name}')
    return [row[0] for row in cases]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'base', 'fabric', 'previous_handoff', 'isa', 'proof', 'output'):
        p.add_argument(name, type=Path)
    args = p.parse_args()
    sys.path.insert(0, str(args.isa))
    from image import codec, compact, pack_image

    descriptor, original, task, stage = source_scope(args.source)
    base = read_base(args.base)
    policy = read(args.proof)
    group = policy['group']
    row, = [x for x in base['assemblies'] if x['id'] == group]
    view = row['views']['netlist']
    if base['views'][view]['sha256'] != policy['netlist_sha256']:
        raise ValueError('C E32 proof belongs to a different view')
    witness = args.proof.parent / policy['rtl_witness']
    if policy['rtl_witness_sha256'] != sha256(witness.read_bytes()).hexdigest():
        raise ValueError('C E32 source witness changed')
    fabric = read(args.fabric)
    data_paths = audit_data_paths(args.base, args.previous_handoff)
    base['native_service_routes']['targets'].append(dict(
        group=group, id=fabric['targets'][group]['target_id'], netlist_view=view,
        netlist_sha256=policy['netlist_sha256'],
        routes=[dict(schema=1, abi=NATIVE_ABI, opcode=0x100, completions=['service_done'])]))
    result, view = resident_plan(original, task, stage, base, fabric, group)
    outputs = result['outputs']
    program = outputs['program']
    command, = program['locals'][group]
    bundle = link(descriptor, command, program['source'], policy, pack_image)
    bundle['shape'] = operands(descriptor)
    bundle['requires']['numerical_contract'] = 'all_signed_s32_sums_in_range'
    bundle['checked_words'] = read_images(bundle, compact, codec)
    bundle['negative_cases'] = check_negative_cases(descriptor, command, program['source'],
                                                   policy, pack_image)

    args.output.mkdir()
    write(args.output / 'base.json', base)
    for artifact in bundle['images']:
        image_path = args.output / f"local-{artifact['image_id']}.bin"
        image_path.write_bytes(artifact.pop('image'))
        artifact['path'] = image_path.name
    rules = read(args.previous_handoff / 'algorithm2-input.json')
    hardware = result['resolved_hardware']
    handoff = build(result['event_ir'], hardware, result['plan'], route_catalog(hardware),
                    base, rules, bind_request, source_outputs=outputs)
    for name, data in handoff.items():
        write(args.output / (name + '.json'), data)
    readback = verify_candidate(handoff['algorithm2-input'], args.output, args.output / 'base.json')
    active = Counter(member['demand_id'] for member in handoff['requirements']['members'])
    write(args.output / 'residual-proof.json', dict(bundle, netlist_view=view,
          netlist_sha256=policy['netlist_sha256'], placement=readback, demands=dict(active),
          original_plan=original['outputs']['program']['source'], proof=policy, data_paths=data_paths,
          scope='C0 resident S32 add with external operand and result handoff still required'))
    print(json.dumps(dict(images=len(bundle['images']), words=bundle['checked_words'],
                          bound_m10_nets=readback['bound_nets'], demands=dict(active)), sort_keys=True))


if __name__ == '__main__':
    main()
