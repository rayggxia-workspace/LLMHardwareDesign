"""Predict the serial P0 DRL1 service in the frozen 105530 fixture."""

import struct

from qwen_native_ddr import require
from qwen_prompt_cycle import BURST_BYTES, SRAM_ACCEPT_TO_ACK, SRAM_WORD_BYTES


DRL1 = int.from_bytes(b"DRL1", "little")
PROVIDER_ABI = 0x02500002
PAYLOAD_BYTES = 512
TYPED_CLIENT = 5


def gated_edge(cycle, mode, period, blocked):
    if mode and cycle % period < blocked:
        return cycle + blocked - cycle % period
    return cycle


def run_drl1(fabric, call, service_accept):
    """Predict one noncontended P0 service from its accepted start edge.

    The caller supplies the same typed DMA fabric used for MC/LC descriptor
    reads. All core cycles use the pre-edge DDR bridge count. The provider
    emits one read at a time and returns success only after the last SRAM ACK.
    """
    raw = bytes.fromhex(call["descriptor_hex"])
    ticket = call["ticket"]
    require(len(raw) == 128 and (call["target"], call["schema"], call["provider_abi"], call["operation"])
            == (0, DRL1, PROVIDER_ABI, 1), "unsupported 105530 DRL1 route")
    require(type(service_accept) is int and service_accept >= 0 and 0 < ticket < 1 << 24,
            "invalid DRL1 service edge or ticket")
    destination, = struct.unpack_from("<H", raw, 16)
    source, = struct.unpack_from("<Q", raw, 24)
    require(struct.unpack_from("<IHHII", raw) == (DRL1, 128, 1, PROVIDER_ABI, 25001)
            and not any(raw[18:24]) and not any(raw[32:124]) and destination <= 992
            and source % (2 * BURST_BYTES) == 0 and source <= (1 << 64) - PAYLOAD_BYTES,
            "descriptor does not match the frozen DRL1 provider and typed fabric")

    mode = fabric.mode
    require(mode in (0, 1), "unsupported 105530 DRL1 gate mode")
    reads, writes = [], []
    read_offer = service_accept + 1
    for beat in range(PAYLOAD_BYTES // BURST_BYTES):
        address = source + beat * BURST_BYTES
        transfer = fabric.read_serial(read_offer, TYPED_CLIENT, (ticket << 7) | beat, address)
        reads.append(transfer)
        # The range loader consumes the DMA skid response before offering the
        # first 16-byte store. The P0 AUX request gate is separate from DDR.
        store_offer = transfer["client_response"] + 1
        for word in range(BURST_BYTES // SRAM_WORD_BYTES):
            write_cycle = gated_edge(store_offer, mode, 7, 2)
            ack_cycle = gated_edge(write_cycle + SRAM_ACCEPT_TO_ACK, mode, 11, 4)
            word_address = destination + beat * (BURST_BYTES // SRAM_WORD_BYTES) + word
            writes.append({"word": word_address, "bank": word_address & 3, "row": word_address >> 2,
                           "accept": write_cycle, "ack": ack_cycle})
            store_offer = ack_cycle + 1
        read_offer = store_offer
    # Loader REPORT and service REPORT each advance on their own core edge.
    return {"target": 0, "ticket": ticket, "service_accept": service_accept,
            "service_retire": writes[-1]["ack"] + 2, "status": 0,
            "read_bytes": PAYLOAD_BYTES, "write_bytes": PAYLOAD_BYTES,
            "ddr_reads": reads, "sram_writes": writes}
