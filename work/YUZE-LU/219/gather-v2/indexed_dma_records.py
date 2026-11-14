"""Encode the two 64 B requests of a v45 DMA record for a Gather provider."""
from dataclasses import dataclass

CHANNEL_ADDRESS_BIT = 11
BEAT_BYTES = 64
RECORD_BEATS = 2
RECORD_BYTES = BEAT_BYTES * RECORD_BEATS
ROW_BYTES = 8192
ADDRESS_LIMIT = 1 << 48

@dataclass(frozen=True)
class Beat:
    address: int
    channel: int
    tag: int
    record_beats: int = RECORD_BEATS

def pair(address, record_id):
    """The two requests share a descriptor. Acceptance of beat 1 auto-closes it."""
    if (type(address) is not int or not 0 <= address <= ADDRESS_LIMIT - RECORD_BYTES
            or address % RECORD_BYTES):
        raise ValueError('DMA pair must be aligned and fit the address space')
    if type(record_id) is not int or not 0 <= record_id < 1 << 31:
        raise ValueError('DMA record identity exceeds the client tag base')
    channel = address >> CHANNEL_ADDRESS_BIT & 1
    tag = record_id << 1
    return Beat(address, channel, tag), Beat(address + BEAT_BYTES, channel, tag + 1)

def prompt_pair(burst_address, record_id):
    """Read the aligned record containing a 64 B prompt burst."""
    if type(burst_address) is not int or burst_address % BEAT_BYTES or burst_address < 0:
        raise ValueError('prompt burst must be 64 B aligned')
    address = burst_address - burst_address % RECORD_BYTES
    return pair(address, record_id), (burst_address - address) // BEAT_BYTES

def row_pairs(table, rows, index, *, first_record):
    """Build row records only once the input index has been read."""
    if (type(table) is not int or table < 0 or table % RECORD_BYTES
            or type(rows) is not int or not 0 < rows < 1 << 32
            or table + rows * ROW_BYTES > ADDRESS_LIMIT):
        raise ValueError('invalid DMA-backed embedding table')
    if type(index) is not int or not -rows <= index < rows:
        raise ValueError('embedding index outside its table')
    count = ROW_BYTES // RECORD_BYTES
    if type(first_record) is not int or not 0 <= first_record <= (1 << 31) - count:
        raise ValueError('embedding row needs distinct live DMA records')
    start = table + (index % rows) * ROW_BYTES
    return tuple(pair(start + offset*RECORD_BYTES, first_record + offset)
                 for offset in range(count))
