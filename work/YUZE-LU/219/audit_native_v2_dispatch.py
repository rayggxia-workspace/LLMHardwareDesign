"""Check actual native CALLs and direct descriptor admission on the V2 source paths."""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
from zlib import crc32

from assemble_cases import OPS
from compile_scope_loops import expand
from event_native_dispatch import qualify_native_dispatch
from route_contract import digest, read_base
from run import compile_event_ir


def hash_file(path):
    checksum = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def seal(path):
    entries = [line.split('  ', 1) for line in path.read_text(encoding='ascii').splitlines()]
    hashes = {name: checksum for checksum, name in entries}
    if len(entries) != len(hashes):
        raise ValueError(f'duplicate seal entry in {path.name}')
    return hashes


def guard_sources(source):
    hashes = seal(source / 'source.sha256')
    if any(hash_file(source / name) != expected for name, expected in hashes.items()):
        raise ValueError('main RTL source digest differs')
    texts = {name: (source / name).read_text(encoding='utf-8') for name in hashes}
    p_chain = {
        'p0_native_ffn_coplacement.sv': 'p_native_lc_coplacement #(',
        'p_native_lc_coplacement.sv': 'p_native_coplacement_node #(',
        'p_native_coplacement_node.sv': 'p_stream_scope_node #(',
        'p_stream_scope_node.sv': ".NATIVE_STREAM_A16(1'b1)",
        'p_scope_range_service.sv': 'p_scope128_decode #(.ALLOW_STREAM_A16(',
        'wrapper.sv': 'u_n32_controlled_64 local_group (',
        'u_n32_controlled_64.sv': "pu_native_lc #(.ENABLE_NATIVE(1'b1)",
    }
    if any(fragment not in texts[name] for name, fragment in p_chain.items()):
        raise ValueError('main P or U ingress path has changed')
    p = texts['p_scope128_decode.sv']
    u = texts['pu_native_lc.sv']
    p_header = re.search(r"scope_data\[0\+:32\]!=32'h([0-9a-f]+)\s*\|\|\s*"
                         r"scope_data\[32\+:16\]!=16'd(\d+)\s*\|\|\s*"
                         r"scope_data\[64\+:32\]!=32'h([0-9a-f]+)", p, re.I)
    u_header = re.search(r'wire exec_ok\s*=\s*ENABLE_NATIVE\s*\?\s*'
                         r'\(exec_desc\[0\+:32\]==(\d+)\s*&&', u)
    if p_header is None or u_header is None or int(p_header[2]) != 128:
        raise ValueError('main native header guard has changed')
    return (int(p_header[1], 16), int(p_header[3], 16)), int(u_header[1]), hashes


def unpack_mother(raw, topology):
    if (raw[:8] != b'LBCISA01' or struct.unpack_from('<HBBI', raw, 8) != (3, 0, 8, len(raw))
            or struct.unpack_from('<II', raw, 64) != (topology, 0x02500002)):
        raise ValueError('invalid archived mother header')
    count, offset = struct.unpack_from('<II', raw, 20)
    if count < 1 or offset != 128 or offset + count * 8 > len(raw):
        raise ValueError('invalid archived mother code extent')
    names = {opcode: name for name, opcode in OPS.items() if name != 'EVENT'}
    instructions = [(names[word >> 56], (word >> 48) & 255, (word >> 40) & 255,
                     (word >> 32) & 255, word & 0xffffffff)
                    for (word,) in struct.iter_unpack('<Q', raw[offset:offset + count * 8])]
    limit, = struct.unpack_from('<I', raw, 52)
    return expand(instructions, limit)[0]


def audit(package, base, source, fabric):
    p_header, u_header, sources = guard_sources(source)
    hashes = seal(package / 'proof.sha256')

    def checked(name):
        path = package / name
        if hash_file(path) != hashes.get(name):
            raise ValueError(f'archived member hash differs: {name}')
        return path

    witness = json.loads(checked('witness.json').read_bytes())
    topology = witness['topology']
    groups = {item['id']: item for item in base['assemblies']}
    ids = {item['target_id']: item['controller'] for item in fabric['targets'].values()}
    signatures = json.loads(checked('service-signatures.json').read_bytes())
    expected = Counter()
    for row in signatures:
        expected[row['target'], row['schema'], row['abi'], row['opcode']] += row['calls']
    observed, statuses, examples = Counter(), {}, {}
    descriptor_header = struct.Struct('<IHHII')
    word = struct.Struct('<I')
    page_total = 0
    with ExitStack() as stack:
        streams = {name: stack.enter_context(checked(name).open(encoding='ascii'))
                   for name in ('mother-pages.tsv', 'mother-targets.tsv', 'mother-descriptors.tsv')}
        tables = list(streams.values())
        counts = [int(next(table)) for table in tables]
        if len(set(counts)) != 1:
            raise ValueError('archived page table counts differ')
        packed = stack.enter_context(checked('mother-programs.ddr.bin').open('rb'))
        packed_meta = checked('mother-packed.tsv').read_text(encoding='ascii').strip().split()
        packed_base, packed_size = map(int, packed_meta[:2])
        if packed_meta[2:] != ['mother-programs.ddr.bin']:
            raise ValueError('unexpected archived mother image arena')
        for step, phase in enumerate(witness['phases']):
            if phase['step'] != step:
                raise ValueError('archived phase order differs')
            path = checked(f'phase-{step}/descriptors.bin')
            with path.open('rb') as descriptors:
                for page in range(phase['page_count']):
                    entries = [next(table).split() for table in tables]
                    if any(tuple(int(v, 16) for v in entry[:2]) != (step, page) for entry in entries):
                        raise ValueError(f'archived page identities differ at {step}/{page}')
                    addr, size, crc, padded, offset, asset = entries[0][2:]
                    address, size, padded = int(addr, 16), int(size), int(padded)
                    if (asset != packed_meta[2] or int(offset) != 0 or padded != (size + 63) // 64 * 64
                            or address != packed_base + packed.tell()):
                        raise ValueError(f'archived mother asset extent differs at {step}/{page}')
                    data = packed.read(padded)
                    image = data[:size]
                    if len(data) != padded or any(data[size:]) or crc32(image) != int(crc, 16):
                        raise ValueError(f'archived mother bytes differ at {step}/{page}')
                    calls = unpack_mother(image, topology)
                    start, length = int(entries[2][2], 16), int(entries[2][3])
                    mask = sum(1 << target for target in {call['target'] for call in calls})
                    if (start != phase['descriptor_base'] + descriptors.tell() or length != len(calls) * 128
                            or mask != int(entries[1][2], 16) or mask != phase['target_masks'][page]):
                        raise ValueError(f'archived descriptor or target extent differs at {step}/{page}')
                    payload = descriptors.read(length)
                    if len(payload) != length:
                        raise ValueError(f'truncated descriptor bytes at {step}/{page}')
                    for i, call in enumerate(calls):
                        offset = i * 128
                        record = payload[offset:offset + 128]
                        schema, size, opcode, abi, owner = descriptor_header.unpack_from(record)
                        if (call['reference'] != start + offset or size != 128 or owner != topology
                                or crc32(record[:124]) != word.unpack_from(record, 124)[0]):
                            raise ValueError(f'archived CALL identity differs at {step}/{page}/{i}')
                        key = call['target'], schema, abi, opcode
                        if key not in statuses:
                            view = groups[ids[call['target']]]['views']['netlist']
                            if view == 'P.netlist' and (schema, abi) != p_header:
                                status = 'rejected_by_p_scope_header'
                            elif view == 'U.netlist' and schema != u_header:
                                status = 'rejected_by_u_exec_header'
                            elif view in ('P.netlist', 'U.netlist'):
                                status = 'header_matches_unqualified'
                            else:
                                status = 'unaudited'
                            statuses[key] = status
                            examples[key] = {'step': step, 'page': page, 'descriptor_index': i,
                                             'descriptor_sha256': sha256(record).hexdigest()}
                        observed[key] += 1
                    page_total += 1
                if descriptors.tell() != phase['descriptor_bytes'] or descriptors.read(1):
                    raise ValueError(f'unconsumed descriptor bytes at step {step}')
        if (page_total != counts[0] or packed.tell() != packed_size or packed.read(1)
                or any(next(table, None) is not None for table in tables) or observed != expected):
            raise ValueError('archived CALL coverage differs from its seal')
    entries = []
    targets = defaultdict(list)
    totals = Counter()
    for key, calls in sorted(observed.items()):
        target, schema, abi, opcode = key
        group = ids[target]
        view = groups[group]['views']['netlist']
        status = statuses[key]
        entry = dict(target=target, group=group, schema=schema, abi=abi, opcode=opcode,
                     calls=calls, status=status, first=examples[key])
        entries.append(entry)
        totals[status] += calls
        if status.startswith('rejected'):
            targets[target].append(dict(schema=schema, abi=abi, opcode=opcode, reason=status))
    inventory = dict(schema='native-rtl-target-routes/1', topology_id=topology, targets=[
        dict(id=target, group=ids[target], netlist_view=groups[ids[target]]['views']['netlist'],
             netlist_sha256=base['views'][groups[ids[target]]['views']['netlist']]['sha256'],
             routes=[], rejected_routes=targets[target]) for target in sorted({key[0] for key in observed})])
    report = dict(schema='native-v2-direct-descriptor-audit/1', pages=page_total, calls=sum(observed.values()),
                  package_proof_sha256=hash_file(package / 'proof.sha256'), base_sha256=digest(base),
                  main_rtl_sha256=sources, counts=totals, signatures=entries,
                  scope='main source header rejection for direct descriptor reuse; header matches lack service qualification')
    return report, inventory


def check_admission(report, target_base, compile_result, fabric):
    hardware = compile_result['resolved_hardware']
    inventory = target_base['native_service_routes']
    active = inventory['targets']
    # Exercise the diagnostic and admission logic against each exact signature.
    probe = {
        'topology_id': inventory['topology_id'],
        'control_groups': {row['group']: {'site': row['group'], 'block_id': row['id']} for row in active},
        'native_provider_contracts': {},
        'event_model': {'routes': {}, 'services': {}},
    }
    for i, row in enumerate(report['signatures']):
        group = row['group']
        name = str(i)
        probe['native_provider_contracts'][name] = {'calls': [
            {**{key: row[key] for key in ('schema', 'abi', 'opcode')}, 'completion': 'service_done'}]}
        probe['event_model']['services'][name] = {'control_site': group, 'native_providers': {group: name}}
    issues = qualify_native_dispatch(probe, target_base)['event_model']['native_dispatch_issues']['services']
    for i, row in enumerate(report['signatures']):
        issue = issues[str(i)]
        if row['status'].startswith('rejected'):
            if not issue.endswith(': ' + row['status']):
                raise ValueError('physical rejection is missing from Algo1')
        elif 'no physical service route' not in issue:
            raise ValueError('header match must remain unqualified')
    service, = hardware['event_model']['services'].values()
    provider = service['native_providers']['U0']
    hardware['native_provider_contracts'] = {provider: {'calls': [
        dict(schema=3, abi=7, opcode=4, completion='destination_commit_ack')]}}
    result = compile_event_ir(compile_result['event_ir'], hardware, route_base=target_base,
                              control_fabric=fabric, route_scope='interface')
    if result['status'] != 'no_plan_in_bounded_search' or not any(
            message.endswith(': rejected_by_u_exec_header')
            for message in result['native_dispatch_issues']['services'].values()):
        raise ValueError('actual Gather candidate did not surface the V2 incompatibility')
    return result['native_dispatch_issues'], hardware


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'candidate', 'source', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    base_path = args.candidate / 'base'
    base = read_base(base_path)
    fabric = json.loads((args.candidate / 'control-fabric').read_bytes())
    report, inventory = audit(args.package, base, args.source, fabric)
    views = {name: {**view, 'path': str((base_path.parent / view['path']).absolute())}
             for name, view in base['views'].items()}
    target_base = {**base, 'views': views, 'native_service_routes': inventory}
    compile_result = json.loads((args.candidate / 'compile').read_bytes())
    issues, hardware = check_admission(report, target_base, compile_result, fabric)
    report['algo1_native_dispatch_issues'] = issues
    report['admission_base_sha256'] = digest(target_base)
    args.output.mkdir()
    artifacts = {
        'report.json': report,
        'rejected-routes.json': inventory,
        'base-with-native-rejections.json': target_base,
        'gather-hardware.json': hardware,
        'gather-event-ir.json': compile_result['event_ir'],
    }
    for name, obj in artifacts.items():
        (args.output / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({name: report[name] for name in ('pages', 'calls', 'counts', 'algo1_native_dispatch_issues')},
                     sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
