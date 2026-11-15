"""Translate validated S32 descriptors to a parameterized U local control ABI."""
import struct
import zlib

GAMMA_LOAD = 0x0105
RMS = 0x0106
ADD = 0x0107
STORE = 0x0108
PROJECTION_FEED = 0x0109
FEED_SIGNATURE = (0x44454650, 0x02500002, 1)
ADD_SIGNATURE = (3, 7, 2)
STORE_SIGNATURE = (0x38535744, 0x02500002, 1)
DDR_LOAD_SIGNATURE = (0x384c5244, 0x02500002, 1)
RMS_SIGNATURE = (3, 7, 3)
WINDOW = 8192


def lower_record(call, raw, topology, *, target_id=3):
    signature = tuple(call["service_signature"])
    if call["target"] != target_id or signature not in (DDR_LOAD_SIGNATURE, RMS_SIGNATURE, ADD_SIGNATURE, STORE_SIGNATURE, FEED_SIGNATURE):
        return None
    schema, size, opcode, abi, row_topology = struct.unpack_from("<IHHII", raw)
    if (len(raw) != 128 or size != len(raw) or row_topology != topology
            or (schema, abi, opcode) != signature
            or zlib.crc32(raw[:124]) != int.from_bytes(raw[124:], "little")):
        raise ValueError("invalid native U descriptor")
    if signature == FEED_SIGNATURE:
        source, scratch, destination, tiles = struct.unpack_from("<4H", raw, 16)
        source_end = source + 32 * tiles
        key = int.from_bytes(raw[24:40], "little")
        session = int.from_bytes(raw[40:44], "little")
        if (call["required_completion"] != "service_done" or not 0 < tiles <= 32
                or source_end > 1024 or scratch > 1008 or destination > 1008
                or source < scratch + 16 and scratch < source_end
                or not key or not session or any(raw[44:124])):
            raise ValueError("projection feed descriptor exceeds native SRAM/identity contract")
        return PROJECTION_FEED, struct.unpack_from("<7I", raw, 16)
    if signature == ADD_SIGNATURE:
        left, right, dest, count = struct.unpack_from("<HHHH", raw, 16)
        if (call["required_completion"] != "service_done" or any(raw[24:124])
                or not 0 < count <= 1024
                or any(base + count > 1024 for base in (left, right, dest))
                or any(base != dest and base < dest + count and dest < base + count
                       for base in (left, right))):
            raise ValueError("invalid U0 resident ADD range or overlap")
        return ADD, (left | right << 16, dest | count << 16)
    if signature == STORE_SIGNATURE:
        source, reserved, address, tag = struct.unpack_from("<IIQQ", raw, 16)
        if (call["required_completion"] != "destination_commit_ack" or reserved
                or source > 512 or any(raw[40:124]) or address % 64
                or address + WINDOW > 1 << 64 or tag + 128 > 1 << 64):
            raise ValueError("invalid U0 DDR store range")
        return STORE, (source, address & 0xffffffff, address >> 32,
                       tag & 0xffffffff, tag >> 32)
    if signature == DDR_LOAD_SIGNATURE:
        dest, reserved, address = struct.unpack_from("<IIQ", raw, 16)
        if (call["required_completion"] != "destination_commit_ack"
                or dest not in (0, 512) or reserved or any(raw[32:124])
                or address % 128 or address + WINDOW > 1 << 48):
            raise ValueError("DDR load cannot use the U0 two-beat DMA contract")
        return GAMMA_LOAD, (address & 0xffffffff, address >> 32, 0, dest)
    x, gamma, output, reserved, epsilon, baseline, e_shift, f_shift, g_shift = struct.unpack_from(
        "<HHHHIbbbb", raw, 16)
    if (call["required_completion"] != "service_done" or reserved or any(raw[32:124])
            or sorted((x, gamma)) != [0, 512] or output not in (0, 512)
            or not epsilon or not -32 <= baseline <= 31
            or not all(-63 <= shift <= 63 for shift in (f_shift, g_shift))):
        raise ValueError("RMS cannot use the U0 resident S32 contract")
    layout = (x >> 9) | (gamma >> 9) << 1 | (output >> 9) << 2
    profile = int.from_bytes(struct.pack("<bbbb", baseline, e_shift, f_shift, g_shift), "little")
    return RMS, (layout, epsilon, profile)
