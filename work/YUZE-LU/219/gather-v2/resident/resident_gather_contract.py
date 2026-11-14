"""Lower a selected Gather and describe its physical endpoint requirements."""
from hashlib import sha256
from struct import unpack_from

LINK_ABI = 0x01930001
CAPACITY_ID = 0x17630001
GATHER = 0x0104
COMPLETION = 'destination_commit_ack'
WINDOW_BYTES = 8192
ADDRESS_LIMIT = 1 << 48

DMA = (
    ('req_valid', 1, True), ('req_ready', 1, False), ('req_address', 64, True),
    ('req_tag', 32, True), ('req_channel', 1, True), ('req_record_beats', 5, True),
    ('rsp_valid', 1, False), ('rsp_ready', 1, True), ('rsp_tag', 32, False),
    ('rsp_data', 512, False),
)

def words(command):
    if (command.get('op') != 'INDEXED_LOAD' or command.get('roles') != ['execute']
            or command.get('required_completion') != COMPLETION
            or len(command.get('read', ())) != 1 or len(command.get('write', ())) != 1):
        raise ValueError('expected a selected Gather with a destination commit')
    operand, = command['read']
    output, = command['write']
    spec = command['indexed_read']
    table, rows, offset, dest = spec['table_address'], spec['rows'], operand['address'], output['address']
    if (operand['site'] != output['site'] or
            (spec['indices'], spec['index_bits'], spec['row_words'], operand['bytes'], output['bytes'])
            != (1, 32, WINDOW_BYTES//16, 4, WINDOW_BYTES)):
        raise ValueError('unsupported Gather shape or owner')
    if (any(type(n) is not int for n in (table, rows, offset, dest))
            or not 0 <= table < ADDRESS_LIMIT or table % 128 or not 0 < rows < 1 << 32
            or table + rows*WINDOW_BYTES > ADDRESS_LIMIT
            or not 0 <= offset < 2*WINDOW_BYTES or offset % 4
            or dest not in (0, WINDOW_BYTES) or offset//WINDOW_BYTES == dest//WINDOW_BYTES):
        raise ValueError('Gather operands cannot own disjoint native SRAM windows')
    return table & 0xffffffff, (table >> 32) | offset << 16, rows, dest//16

def local_image(command, *, topology, image_id, pack_image, prompt_address=None):
    if any(type(n) is not int or not 0 < n < 1 << 32 for n in (topology, image_id)):
        raise ValueError('invalid resident U image identity')
    fields = words(command)
    if prompt_address is not None:
        if (type(prompt_address) is not int or not 0 <= prompt_address < ADDRESS_LIMIT
                or prompt_address % 4):
            raise ValueError('invalid native DDR prompt index address')
        fields += (prompt_address & 0xffffffff, (prompt_address >> 32) | (1 << 16))
    code = [{'op': 'L_EXEC', 'a': 0, 'b': 0, 'c': 0}, {'op': 'L_WAIT', 'x': 1}, {'op': 'L_END'}]
    header = {'entry_pc': 0, 'max_steps': len(code), 'resource_mask': 1,
              'program_image_id': image_id, 'topology_id': topology, 'native_abi_id': LINK_ABI,
              'capacity_profile_id': CAPACITY_ID}
    task = {'block_type': 0, 'entry_pc': 0, 'max_steps': len(code), 'required_resources': 1,
            'program_image_id': image_id, 'topology_id': topology, 'native_abi_id': LINK_ABI}
    execution = {'resource': 0, 'service': 0, 'native_op': GATHER, 'native_abi_id': LINK_ABI,
                 **{f'native{i}': value for i, value in enumerate(fields)}}
    return pack_image('local', code, {'task': [task], 'execution': [execution]}, header, instruction_version=2)

def demand(site, client):
    if not site or type(client) is not int or client not in range(3, 9):
        raise ValueError('invalid target or non-available DMA client')
    signals = []
    for name, width, to_dma in DMA:
        # Explicit unit members avoid manufacturing offset-index placeholders.
        for bit in range(width):
            terminal = f'{site}/dma_{name}' + (f'[{bit}]' if width>1 else '')
            dma = f'dma/c_{name}[{client*width+bit}]'
            driver, sink = (terminal, dma) if to_dma else (dma, terminal)
            signals.append({'name': f'{name}.{bit}', 'width': 1, 'driver': driver, 'sinks': [sink]})
    return {'signals': signals, 'requires': []}
