"""Predict the first Q projection weight offer in the 105530 fixture.

The input is the accepted ticket-3 P_SCOPE in a drained P0/M instance.
Cycles use the DDR bridge's pre-edge count. The endpoint is the registered
M leaf offer to typed DMA. Subsequent record beats, COPY and EXEC are outside
this model.
"""

import struct

from qwen_drl1_cycle import gated_edge
from qwen_native_control import P_SCOPE, TOPOLOGY, service_spans
from qwen_native_ddr import require
from qwen_prompt_cycle import BURST_BYTES, SRAM_ACCEPT_TO_ACK, SRAM_WORD_BYTES


PROVIDER_ABI = 0x02504D02
TILE_ELEMENTS = 128
WORDS_S32 = TILE_ELEMENTS * 4 // SRAM_WORD_BYTES
WORDS_A16 = TILE_ELEMENTS * 2 // SRAM_WORD_BYTES
WEIGHT_CLIENT = 9


def first_weight_offer(call, service_accept, mode):
    """Return source-derived activation and first weight launch milestones."""
    raw = bytes.fromhex(call["descriptor_hex"])
    require(type(service_accept) is int and service_accept >= 0 and mode in (0, 1),
            "invalid P_SCOPE edge or testbench mode")
    require(len(raw) == 128 and (call["target"], call["ticket"], call["schema"],
                                 call["provider_abi"], call["operation"]) == (0, 3, P_SCOPE, PROVIDER_ABI, 2)
            and struct.unpack_from("<IHHII", raw) == (P_SCOPE, 128, 2, PROVIDER_ABI, TOPOLOGY),
            "unsupported 105530 first Q projection route")
    columns, first, stride, groups, context, full_k, k_begin, k_end, ways, head = struct.unpack_from(
        "<IIHBBHHHBB", raw, 64)
    require((columns, first, stride, groups, context, full_k, k_begin, k_end, ways, head)
            == (256, 0, 8, 16, 0, 2048, 0, 2048, 1, 0),
            "unsupported first Q projection weight layout")
    weight = service_spans(raw[:4], call["operation"], raw)[0]

    # The accepted job registers its first iterator record and the window
    # sequencer observes NEED at +2. QUANT_REQ fires at +3 and its first S32
    # read at +4. The prompt source allows one live SRAM access. On the U
    # side a read ACK arrives at +2 and the following request is at +3.
    first_scan_read = service_accept + 4
    source_stride = SRAM_ACCEPT_TO_ACK + 1
    last_scan_ack = first_scan_read + (WORDS_S32 - 1) * source_stride + SRAM_ACCEPT_TO_ACK

    # CHOOSE uses one edge after the last maximum scan ACK. In CONVERT the
    # priority packed write follows each pair of S32 rereads. P.S scratch
    # requests and ACKs use the P0 AUX mode gates; U.S reads do not.
    first_convert_read = last_scan_ack + 2
    next_pair = first_convert_read
    for _ in range(WORDS_A16):
        write = gated_edge(next_pair + 2 * source_stride, mode, 7, 2)
        write_ack = gated_edge(write + SRAM_ACCEPT_TO_ACK, mode, 11, 4)
        next_pair = write_ack + 1

    quant_done = write_ack + 1  # All writes drained, so the quantizer raises DONE.
    lease = quant_done + 2  # Sequencer consumes DONE, then accepts the idle lease.
    header_publish = lease + 4  # Header start, phase 0, its ACK, phase 1.
    record_accept = header_publish + 1  # Matching published metadata opens A_first.

    # BEGIN sends eight flits, then M processes and registers a two-flit
    # reply. P enters CTX_PUSH one edge after its received reply.
    begin_last_flit = record_accept + 8
    begin_ack = begin_last_flit + 4
    context_flit = begin_ack + 3  # BEGIN_WAIT, CTX_PUSH, CONTEXT command.
    context_ack = context_flit + 4  # RF command, M reply register, two reply flits.
    allocate_last_flit = context_ack + 3  # CTX_WAIT and two ALLOC flits.
    weight_allocated = allocate_last_flit + 1
    weight_table_installed = weight_allocated + 1
    weight_source_offer = weight_table_installed + 2  # Lock request, then registered valid.

    return {"target": call["target"], "ticket": call["ticket"], "service_accept": service_accept,
            "first_scan_read": first_scan_read, "last_scan_ack": last_scan_ack,
            "first_convert_read": first_convert_read, "last_packed_write": write,
            "last_packed_write_ack": write_ack, "quant_done": quant_done,
            "header_publish": header_publish, "first_record_accept": record_accept,
            "weight_allocated": weight_allocated, "weight_table_installed": weight_table_installed,
            "weight_source_offer": weight_source_offer, "weight_client": WEIGHT_CLIENT,
            "weight_address": weight["address"], "weight_record_beats": weight["bytes"] // BURST_BYTES}
