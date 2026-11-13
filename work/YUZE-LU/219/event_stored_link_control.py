"""Lower a selected stored-link COPY to its two bounded local PM routines."""

from event_execution import stored_link_operand


ABI = 0x01930001
CAPACITY = 0x17630001
RESERVED, COMMIT_ACK = 'receive_reserved', 'destination_commit_ack'
SEND, RECEIVE, RESERVE = 0x101, 0x102, 0x103
RECORD_CONTRACT = {SEND: (20, COMMIT_ACK), RECEIVE: (0, COMMIT_ACK), RESERVE: (10, RESERVED)}


def routines(commands, route, controllers):
    """The destination arms and takes the reservation in the same LC call.

    Launch both routines in one mother wave. SEND may start reading ahead but
    cannot present data before the matching destination reservation is live.
    Wait for both terminals before reusing either controller.
    """
    roles = {tuple(command.get('roles', ())): command for command in commands}
    if len(commands) != 2 or roles.keys() != {('send',), ('receive',)}:
        raise ValueError('stored COPY requires distinct sender and receiver commands')
    sender, receiver = roles[('send',)], roles[('receive',)]
    shared = ('op', 'route', 'read', 'write', 'sequence', 'binding_id', 'task_id', 'required_completion')
    if (any(sender[key] != receiver[key] for key in shared) or sender['op'] != 'COPY'
            or route.get('transport_abi') != 'u-stored-link'
            or sender['required_completion'] != COMMIT_ACK
            or len(sender['read']) != 1 or len(sender['write']) != 1):
        raise ValueError('selected commands disagree on the stored COPY')
    source, = sender['read']
    destination, = sender['write']
    if (source['site'] != route['src'] or destination['site'] != route['dst']
            or source['site'] == destination['site']
            or source['value'] != destination['value']
            or not all(stored_link_operand(route, obj['address'], obj['bytes'])
                       for obj in (source, destination))):
        raise ValueError('stored COPY requires a single aligned SRAM word and distinct endpoints')
    src, dst = (obj['address'] // 16 for obj in (source, destination))
    source_group = controllers[source['site']]
    destination_group = controllers[destination['site']]
    if source_group == destination_group:
        raise ValueError('stored COPY aliases local controller targets')
    return {
        source_group: [(SEND, src | dst << 10, COMMIT_ACK)],
        destination_group: [(RESERVE, dst, RESERVED), (RECEIVE, 0, COMMIT_ACK)],
    }


def local_image(records, *, topology, image_id, block_type, pack_image):
    """Use the target ISA assembler for a single-task, compact LC PM image."""
    if not all(type(x) is int and 0 < x < 2**32 for x in (topology, image_id)):
        raise ValueError('local image requires a target topology and image identity')
    if type(block_type) is not int or not 0 <= block_type <= 4:
        raise ValueError('local image requires a supported native block type')
    code, execution = [], []
    for index, (opcode, operand, terminal) in enumerate(records):
        if opcode not in RECORD_CONTRACT or type(operand) is not int:
            raise ValueError('invalid stored-link execution record')
        width, completion = RECORD_CONTRACT[opcode]
        if not 0 <= operand < 1 << width or terminal != completion:
            raise ValueError('invalid stored-link operand or completion')
        code.extend(({'op': 'L_EXEC', 'a': 0, 'b': 0, 'c': index}, {'op': 'L_WAIT', 'x': 1}))
        execution.append(dict(resource=0, service=0, native_op=opcode, native_abi_id=ABI, native0=operand))
    operations = tuple(row['native_op'] for row in execution)
    if operations not in ((SEND,), (RESERVE, RECEIVE)):
        raise ValueError('expected a send routine or a matched reserve and receive routine')
    code.append({'op': 'L_END'})
    header = dict(entry_pc=0, max_steps=len(code), resource_mask=1,
                  program_image_id=image_id, topology_id=topology, native_abi_id=ABI,
                  capacity_profile_id=CAPACITY)
    task = dict(block_type=block_type, entry_pc=0, max_steps=len(code), required_resources=1,
                program_image_id=image_id, topology_id=topology, native_abi_id=ABI)
    raw = pack_image('local', code, dict(task=[task], execution=execution), header, instruction_version=2)
    if not 208 <= len(raw) <= 4096 or len(raw) % 16:
        raise ValueError('stored-link PM image exceeds the target frame')
    return raw
