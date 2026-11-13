"""Lower a selected event program to the existing qualified two-U 64-bit ABI."""
from collections import defaultdict
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from control_backend import images
from solver import Unsupported


def assemble_u64(program, hardware, assemble, compact_image):
    """Use the existing assembler with commands taken from the selected plan."""
    spec = hardware['event_model']
    cap = spec['native_control']
    groups = hardware['control_groups']
    if (cap['profile'] != 'pr214-u64-native-subset' or len(groups) != 2
            or {entry['block_id'] for entry in groups.values()} != {0, 1}
            or {hardware['sites'][entry['site']]['bytes'] for entry in groups.values()} != {16384}):
        raise Unsupported('native event deployment requires the two-target U_64 control profile')
    if program['source']['topology_id'] != hardware['topology_id']:
        raise Unsupported('native program topology differs')
    if set(program['locals']) != groups.keys():
        raise Unsupported('native U_64 deployment requires both participating local controllers')
    if any(command['op'] == 'INDEXED_LOAD' for commands in program['locals'].values() for command in commands):
        raise Unsupported('native U_64 control profile has no token-indexed DDR load with S write ACK')
    if program['external_addresses']:
        raise Unsupported('native U_64 control profile has no DDR event opcode')

    def word(operand, site):
        if (operand['site'] != site or operand['bytes'] != 16 or operand['address'] % 16
                or not 0 <= operand['address'] // 16 < 1024):
            raise Unsupported('native U_64 command requires an aligned local 128-bit S record')
        return operand['address'] // 16

    def local_site(group):
        return groups[group]['site']

    dispatch = program['mother'][:-1]
    pending = {row['sequence']: row for row in dispatch}
    by_sequence = defaultdict(dict)
    for group, commands in program['locals'].items():
        for command in commands:
            by_sequence[command['sequence']][group] = command
    ancestors, previous, resource_last = {}, {}, {}
    result = {group: [] for group in groups}
    opcodes = cap['native_opcodes']
    while pending:
        ready = [row for row in pending.values() if set(row['wait_for']) <= ancestors.keys()]
        if not ready:
            raise Unsupported('native event program has cyclic dispatch dependencies')
        row = min(ready, key=lambda item: (item['estimated_start'], item['sequence']))
        number = row['sequence']
        commands = by_sequence[number]
        if set(commands) != set(row['targets']):
            raise Unsupported('native event dispatch target differs')
        implied = {previous[group] for group in commands if group in previous}
        transitive = implied.union(*(ancestors[parent] for parent in implied))
        if not set(row['wait_for']) <= transitive:
            raise Unsupported(f'event {number} needs a cross-target fence outside the two-U ABI')
        command = next(iter(commands.values()))
        if command['op'] == 'COPY':
            route = spec['routes'][command['route']]
            if route.get('native_transport') != 'u64-stored-link':
                raise Unsupported('route has no qualified U_64 transport encoder: ' + command['route'])
            src, dst = command['read'][0], command['write'][0]
            senders = [group for group, entry in commands.items() if entry['roles'] == ['send']]
            receivers = [group for group, entry in commands.items() if entry['roles'] == ['receive']]
            if len(senders) != 1 or len(receivers) != 1 or senders == receivers:
                raise Unsupported('native U_64 link requires two distinct local targets')
            sender, receiver = senders[0], receivers[0]
            source, target = word(src, local_site(sender)), word(dst, local_site(receiver))
            if command['required_completion'] != 'destination_commit_ack':
                raise Unsupported('native U_64 transfer requires committed-write ACK')
            result[receiver].append({'native_op': opcodes['RESERVE'], 'native0': target})
            result[sender].append({'native_op': opcodes['SEND'], 'native0': source | target << 10})
            result[receiver].append({'native_op': opcodes['RECEIVE']})
            claims = set(route['claims'])
            if 'phases' in route:
                profile = route['phases']
                claims.update(profile['issue']['claims'], profile['ack']['claims'], profile['hold_claims'])
        else:
            if command['op'] != 'EXEC' or len(commands) != 1 or command['required_completion'] != 'service_done':
                raise Unsupported('unsupported native U_64 local command')
            service = spec['services'][command['service']]
            encoding = service.get('native_e')
            if encoding is None or len(command['read']) != 2 or len(command['write']) != 1:
                raise Unsupported('service has no qualified U_64 E encoder: ' + command['service'])
            group = next(iter(commands))
            src0, src1 = (word(value, local_site(group)) for value in command['read'])
            dst = word(command['write'][0], local_site(group))
            op, shift = encoding['op'], encoding['shift']
            if type(op) is not int or type(shift) is not int or not 0 <= op < 16 or not 0 <= shift < 32:
                raise Unsupported('invalid qualified U_64 E encoding')
            result[group].append({'native_op': opcodes['COMMAND'], 'native0': 2 << 2 | 1 << 4 | dst << 5,
                                  'native1': src0 | src1 << 10, 'native2': op | shift << 4})
            claims = service['claims']
        for resource in claims:
            earlier = resource_last.get(resource)
            if earlier is not None and earlier not in transitive:
                raise Unsupported(f'event {number} needs independent arbitration for shared resource {resource}')
            resource_last[resource] = number
        for group in commands:
            previous[group] = number
        ancestors[number] = transitive
        del pending[number]
    for group, rows in result.items():
        limit = cap.get('max_execution_descriptors',32)
        if len(rows) > limit:
            raise Unsupported(f'{group} needs {len(rows)} execution descriptors, capacity {limit}')
    return images({'hardware': hardware, 'capabilities': cap, 'program': result}, assemble, compact_image)



def load_assembler(path, expected_sha256):
    """Load the frozen project's official assembler after checking its bytes."""
    path = Path(path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise Unsupported('native assembler source hash differs')
    source = spec_from_file_location('event_control_assembler', path)
    module = module_from_spec(source)
    original_path = sys.path[:]
    names = ('run', 'image')
    previous = {name: sys.modules.pop(name, None) for name in names}
    sys.path.insert(0, str(path.parent))
    try:
        source.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    return module.assemble


def compact_assembler_image(image):
    path = Path(__file__).resolve().parents[1] / 'pu_leaf_base' / 'compact64.py'
    source = spec_from_file_location('event_compact_isa', path)
    module = module_from_spec(source)
    source.loader.exec_module(module)
    return module.compact_image(image)
