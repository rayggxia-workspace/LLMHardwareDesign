"""Version-2 fetch port pinned to PR180 b54531b3359167668f8e696c97bd5882a7bee473.

Native-service semantics stay at the qualified #195 baseline. This does not
import the newer controller's additional instructions or native profiles.
"""
from pathlib import Path
import struct


def controller64(text):
    replacements = {
        "wire [63:0] fetch_address = {32'b0,inst_offset} + ({32'b0,pc} << 4);":
            '`include "instruction_fetch64.svh"',
        "wire [63:0] fetch_address={32'b0,inst_offset}+({32'b0,pc}<<4);":
            '`include "instruction_fetch64.svh"',
        'header[64+:16]==1': 'instruction_version_ok',
        "64'd128+({32'b0,inst_count}<<4)": 'instruction_end',
        'ireg<=pm_rsp_data_i': 'ireg<=fetch_instruction',
        'else cfg_read_data<=pm_rsp_data_i;':
            'else begin cfg_read_data<=pm_rsp_data_i; '
            'if (bad_instruction_padding) cfg_status<=5; end',
    }
    hits = {}
    for old, new in replacements.items():
        hits[old] = text.count(old)
        text = text.replace(old, new)
    keys = list(replacements)
    if (sum(hits[k] for k in keys[:2]) != 1 or
            hits[keys[2]] != 1 or hits[keys[5]] != 1 or
            hits[keys[4]] not in (1, 2) or hits[keys[3]] not in (1, 2)):
        raise ValueError('compact fetch baseline drift: ' + str(hits))
    return text


def compact_image(image):
    """Losslessly pack supported legacy words; preserve descriptor bytes/PCs."""
    if struct.unpack_from('<H', image, 8)[0] != 1:
        raise ValueError('expected version-1 assembler output')
    count, start = struct.unpack_from('<II', image, 20)
    if not 0 < count <= 256 or start != 128:
        raise ValueError('instruction bounds')
    packed = bytearray()
    for i in range(count):
        word = int.from_bytes(image[start+16*i:start+16*i+16], 'little')
        op = word >> 120
        if op not in (0x10, 0x11, 0x12, 0x13, 0x1f,
                      0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x49, 0x4a, 0x4f):
            raise ValueError('unsupported compact opcode: ' + hex(op))
        short = (op << 56) | (((word >> 88) & 0xffffff) << 32) | ((word >> 32) & 0xffffffff)
        expanded = (op << 120) | (((short >> 32) & 0xffffff) << 88) | ((short & 0xffffffff) << 32)
        if expanded != word:
            raise ValueError('instruction is not losslessly compactable')
        packed.extend(short.to_bytes(8, 'little'))
    if count & 1:
        packed.extend(bytes(8))
    old_end = start + count * 16
    delta = count * 16 - len(packed)
    header = bytearray(image[:128])
    struct.pack_into('<H', header, 8, 2)
    struct.pack_into('<I', header, 12, len(image)-delta)
    for offset in (36, 40, 44, 48, 76):
        value = struct.unpack_from('<I', header, offset)[0]
        if value:
            if value < old_end:
                raise ValueError('overlapping descriptor table')
            struct.pack_into('<I', header, offset, value-delta)
    return bytes(header + packed + image[old_end:])


def stage_fetch(directory):
    import shutil
    shutil.copyfile(Path(__file__).with_name('instruction_fetch64.svh'),
                    directory / 'instruction_fetch64.svh')
