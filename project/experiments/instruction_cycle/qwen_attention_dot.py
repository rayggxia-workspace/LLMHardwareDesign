"""Timing model for the 105530 short-context ATT1 dot and softmax datapath."""

from collections import deque
from dataclasses import dataclass

from qwen_drl1_cycle import gated_edge
from qwen_native_ddr import require
from qwen_post_projection import _s128
from qwen_prompt_cycle import SRAM_ACCEPT_TO_ACK


DOT_BEGIN_TO_CHUNK = 8
DOT_MULTIPLY_STAGES = 4
DOT_FINALIZE_STAGES = 4


@dataclass
class DotTile:
    reads: tuple
    steps: int
    accepted: int = 0
    returned: int = 0
    sent: int = 0


def _tile_reads(index, length, columns, layout, left, right):
    if layout:
        words = tuple(right + 2 * (index + row) + half for row in range(length) for half in (0, 1))
    else:
        words = tuple(right + column * 32 + index // 4 for column in range(columns))
    return (left + index // 4, *words)


def dot_chunk(command, mode, length, columns, layout, left, right, target):
    """Run a final single-row dot chunk with the real two SRAM/input slots."""
    require(mode in (0, 1) and ((length, columns, layout) in ((128, 3, False), (3, 8, True))),
            "unsupported short ATT1 dot geometry")
    waiting = deque(DotTile(_tile_reads(offset, min(4, length - offset), columns, layout, left, right),
                            min(4, length - offset) * (2 if columns > 4 else 1))
                    for offset in range(0, length, 4))
    slots = deque()
    memory = deque()
    fill = compute = None
    registered_s = None
    cycle = command + 1
    final_offer = None
    result_offered = result_acked = 0
    reads, stores, math = [], [], []

    while True:
        require(cycle - command < 8192, "short ATT1 dot stalled")
        # An SRAM credit freed by a true response also admits one new
        # registered request on that edge. Both ports use the P AUX gates.
        pop = bool(memory and memory[0][0] <= cycle and gated_edge(cycle, mode, 11, 4) == cycle)
        push = registered_s is not None and (len(memory) < 2 or pop) and gated_edge(cycle, mode, 7, 2) == cycle
        final_reads = push and registered_s[0] is not None and fill.accepted + 1 == len(fill.reads)
        allocate = (fill is None or final_reads) and len(slots) < 2 and waiting
        start_compute = compute is None and slots and slots[0].returned == len(slots[0].reads)
        final_visible = final_offer is not None and cycle >= final_offer
        retire = final_visible and result_acked == 2 and not memory and registered_s is None
        if retire:
            return {"command": command, "sram_reads": reads, "operand_steps": math,
                    "result_stores": stores, "reply": cycle + 1}

        if pop:
            _, tile, event = memory.popleft()
            event["ack"] = cycle
            if tile is None:
                result_acked += 1
            else:
                tile.returned += 1
        if push:
            tile, word = registered_s
            event = {"word": word, "accept": cycle}
            (stores if tile is None else reads).append(event)
            memory.append((cycle + SRAM_ACCEPT_TO_ACK, tile, event))
            if tile is None:
                result_offered += 1
            else:
                tile.accepted += 1
            registered_s = None

        if compute is not None:
            compute.sent += 1
            math.append(cycle)
            if compute.sent == compute.steps:
                slots.popleft()
                compute = None
                if not waiting and not slots:
                    # The last input crosses the four product stages, carry
                    # propagation and RNE/pack before registered result VALID.
                    final_offer = cycle + DOT_MULTIPLY_STAGES + DOT_FINALIZE_STAGES + 1
        elif start_compute:
            compute = slots[0]

        if final_reads:
            fill = None
        if allocate:
            fill = waiting.popleft()
            slots.append(fill)
        if registered_s is None:
            if final_visible and result_offered < 2:
                registered_s = None, target + result_offered
            elif fill is not None and fill.accepted < len(fill.reads):
                registered_s = fill, fill.reads[fill.accepted]
        cycle += 1


def score_scale_and_softmax(offer, mode, word):
    """Scale and normalize a single three-lane score word."""
    # E64 PRODUCT reads two operands over four flits, processes two
    # six-stage halves, and returns two flits before STORE.
    scale_read = _s128(offer, word, mode)
    scale_write = _s128(scale_read["ack"] + 19, word, mode)
    # N_START, FIND_MAX read+WORD_MAX, then exp/read/write pass.
    max_read = _s128(scale_write["ack"] + 2, word, mode)
    exp_read = _s128(max_read["ack"] + 2, word, mode)
    exp_write = _s128(exp_read["ack"] + 7, word, mode)
    # DIV_START, 64 restoring-divider steps, response ACK, and DIV_ROUND.
    probability_read = _s128(exp_write["ack"] + 68, word, mode)
    probability_write = _s128(probability_read["ack"] + 4, word, mode)
    return {"scale_read": scale_read, "scale_write": scale_write, "max_read": max_read,
            "exp_read": exp_read, "exp_write": exp_write, "probability_read": probability_read,
            "probability_write": probability_write, "av_dot_begin": probability_write["ack"] + 2}
