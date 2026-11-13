"""Bind request-provided token indices to selected native Gather commands."""

from dataclasses import dataclass
from hashlib import sha256
from struct import unpack_from
from zlib import crc32


@dataclass(frozen=True)
class InputIndex:
    step: int
    page: int
    position: int
    source: str
    burst_address: int
    destination: int
    lane_offset: int

    def tsv(self):
        mode = {'prompt_ddr': 1, 'previous_retired_token': 2}[self.source]
        return (f'{self.step:08x}\t{self.page:08x}\t{self.position:08x}\t{mode}\t'
                f'{self.burst_address:012x}\t{self.destination // 16:03x}\t{self.lane_offset:02x}\n')


def indexed_command(program):
    gathers = [(target, cmd) for target, cmds in program['locals'].items() for cmd in cmds
               if cmd['op'] == 'INDEXED_LOAD']
    if len(gathers) != 1:
        raise ValueError('input staging requires exactly one selected indexed command per page')
    target, command = gathers[0]
    return target, command


def indexed_call(deployment, target, command):
    linked = [(i, call) for i, call in enumerate(deployment['calls'])
              if (call['group'], call['sequence']) == (target, command['sequence'])]
    if len(linked) != 1:
        raise ValueError('indexed staging requires a unique linked local CALL')
    return linked[0]


def indexed_call_address(program, deployment):
    target, command = indexed_command(program)
    _, call = indexed_call(deployment, target, command)
    return call['address']


def gather_input(program, deployment, descriptors, *, step, page, position,
                 prompt_tokens, prompt_base):
    """Derive one #260 staging record from an independently linked graph page."""
    context = (step, page, position, prompt_tokens)
    if any(type(item) is not int or not 0 <= item < 2**32 for item in context) or not prompt_tokens:
        raise ValueError('invalid request position')
    if type(prompt_base) is not int or not 0 <= prompt_base < 2**48 or prompt_base % 64:
        raise ValueError('invalid DDR prompt base')
    if (step == 0 and position >= prompt_tokens
            or step > 0 and position != prompt_tokens + step - 1):
        raise ValueError('index source does not match the request position')
    source = program['source']
    if deployment['source'] != source or deployment['topology'] != source['topology_id']:
        raise ValueError('indexed command and local descriptors belong to different plans')
    target, command = indexed_command(program)
    if (len(command['read']) != 1 or len(command['write']) != 1
            or command['required_completion'] != 'destination_commit_ack'):
        raise ValueError('indexed command lacks a source or confirmed destination')
    operand, = command['read']
    output, = command['write']
    spec = command['indexed_read']
    matching = [dispatch for dispatch in program['mother']
                if dispatch.get('sequence') == command['sequence']]
    if (len(matching) != 1 or matching[0]['targets'] != [target]
            or command.get('roles') != ['execute']
            or operand['site'] != output['site']):
        raise ValueError('indexed command is not dispatched to its operand owner')
    if (spec['index_bits'], spec['indices'], operand['bytes']) != (32, 1, 4):
        raise ValueError('native request index staging requires one 32-bit index')

    calls = deployment['calls']
    number, call = indexed_call(deployment, target, command)
    if len(descriptors) != len(calls) * 128:
        raise ValueError('linked CALLs do not cover the descriptor bytes')
    raw = descriptors[number * 128:(number + 1) * 128]
    schema, size, opcode, abi, topology = unpack_from('<IHHII', raw)
    encoded = unpack_from('<QIHHH', raw, 16)
    table_address, rows, index_offset, out_word, bits = encoded
    if (size != len(raw) or topology != deployment['topology']
            or [schema, abi, opcode] != call['service_signature']
            or crc32(raw[:124]) != unpack_from('<I', raw, 124)[0]
            or sha256(raw).hexdigest() != call['sha256']
            or call['address'] != deployment['descriptor_base'] + number * 128
            or call['binding_id'] != command['binding_id']
            or not call['completes_command']
            or call['required_completion'] != command['required_completion']):
        raise ValueError('indexed CALL identity or completion differs from linked bytes')
    if ((schema, abi, opcode) != (3, 7, 4) or call['target'] != 3
            or any(raw[34:124])):
        raise ValueError('the #260 runtime has no indexed provider for this target and descriptor format')
    if ((table_address, rows, index_offset, out_word * 16, bits) != (
            spec['table_address'], spec['rows'], operand['address'], output['address'], spec['index_bits'])
            or spec['row_words'] != 512 or output['bytes'] != 8192
            or table_address % 64 or rows == 0 or table_address + rows * 8192 > 2**48
            or output['address'] not in (0, 8192) or operand['address'] % 4):
        raise ValueError('linked indexed descriptor differs from the selected operands')

    if step == 0:
        address = prompt_base + 4 * position
        if address >= 2**48:
            raise ValueError('prompt index exceeds DDR address width')
        burst = address & ~63
        offset = address - burst
        kind = 'prompt_ddr'
        span = 64
    else:
        burst, offset, kind, span = 0, 8, 'previous_retired_token', 16
    destination = operand['address'] - offset
    if (destination % 16 or not 0 <= destination <= 16384 - 64
            or (destination < output['address'] + output['bytes']
                and output['address'] < destination + span)):
        raise ValueError('index staging span overlaps the result or exceeds local SRAM')
    return InputIndex(step, page, position, kind, burst, destination, offset)


def input_index_table(rows):
    """Write the existing native request protocol without embedding token values."""
    ordered = list(rows)
    if any((left.step, left.page) >= (right.step, right.page)
           or right.position != left.position + 1 for left, right in zip(ordered, ordered[1:])):
        raise ValueError('duplicate or out-of-order indexed input pages')
    return (f'{len(ordered)}\n' + ''.join(row.tsv() for row in ordered)).encode('ascii')
