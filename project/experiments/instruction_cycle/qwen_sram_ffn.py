"""SRAM request-chain cost of a Qwen three-P FFN page."""

from struct import unpack_from
from typing import NamedTuple

from qwen_sram_spans import span_beats


WORDS_PER_BURST = 4
CORE_CYCLES_PER_ACKED_BEAT = 3
P_COUNT = 3
GATE_WAVES = 58
DOWN_WAVES = 6


class Scope(NamedTuple):
    first: int
    groups: int
    tiles: int
    input_word: int
    outputs: tuple


def decode_scope(record, ways, target):
    if len(record) != 128 or record[:4] != b"\x01PP\x02":
        raise ValueError("expected a sealed P projection descriptor")
    first, stride, groups, full_k, start_k, end_k, actual_ways, flags, input_word, out, out1 = unpack_from(
        "<IHBxHHHBBHHH", record, 68)
    output_words = (out, out1) if ways == 2 else (out,)
    k_extent = 2048 if ways == 2 else 11008
    if (stride != 24 or first % stride != target * 8 or not 1 <= groups <= 16 or
            (actual_ways, start_k, end_k, full_k, flags) != (ways, 0, k_extent, k_extent, 0) or
            (ways == 1 and out1) or input_word + 16 > 1024 or
            any(word + 2 * groups > 1024 for word in output_words)):
        raise ValueError("unsupported FFN scope or K window")
    return Scope(first, groups, full_k // 128, input_word, output_words)


def ffn_cycles(records, words):
    """Count exposed SRAM cycles and serial Mid arithmetic on one FFN page.

    The mother WAIT observes the critical P chain of each three-CALL wave.
    DDR, controller timing and multi-client queuing belong to the calibrated
    residual, since changing the timing of SRAM requests can perturb overlap.
    """
    if words not in (1, 2, 4) or len(records) != P_COUNT * (GATE_WAVES + DOWN_WAVES):
        raise ValueError("expected one complete three-P FFN page and a supported SRAM width")

    gate, down = [], []
    for wave in range(GATE_WAVES + DOWN_WAVES):
        is_gate = wave < GATE_WAVES
        scopes = tuple(decode_scope(records[wave * P_COUNT + target], 2 if is_gate else 1, target)
                       for target in range(P_COUNT))
        (gate if is_gate else down).append(scopes)

    def projection_beats(scope, activation_word):
        tile_beats = span_beats(activation_word, 16, words) + 2 * span_beats(scope.input_word, 16, words)
        write_beats = sum(span_beats(word + 2 * group, 2, words)
                          for word in scope.outputs for group in range(scope.groups))
        return scope.tiles * tile_beats + write_beats

    gate_beats = sum(max(projection_beats(scope, 512) for scope in wave) for wave in gate)
    down_beats = sum(max(projection_beats(scope, 256) for scope in wave) for wave in down)
    # The Gate/Up providers share the converted activation tile through U.
    quantize_beats = sum(2 * span_beats(32 * k, 32, words) + span_beats(512 + 16 * k, 16, words)
                         for k in range(gate[0][0].tiles))
    activation_beats = sum(span_beats(word, WORDS_PER_BURST, words) for word in range(0, 512, WORDS_PER_BURST))

    fragments = sorted((scope.first + 24 * group, tuple(word + 2 * group for word in scope.outputs))
                       for wave in gate for scope in wave for group in range(scope.groups))
    down_columns = sorted(scope.first + 24 * group
                          for wave in down for scope in wave for group in range(scope.groups))
    if ([column for column, _ in fragments] != list(range(0, 11008, 8)) or
            down_columns != list(range(0, 2048, 8))):
        raise ValueError("FFN output fragments do not match the sealed Gate/Up and Down geometry")

    # Each fragment copies Gate/Up from its owner to P0, then reads both rows
    # back for G. The Mid scratch runs WRITE, scan READ, convert READ, packed
    # WRITE at every 16 fragments. All of this happens after the WAIT barrier.
    staged_beats = 2 * (span_beats(720, 2, words) + span_beats(784, 2, words))
    fragment_beats = sum(staged_beats + sum(span_beats(word, 2, words) for word in output_words)
                         for _, output_words in fragments)
    mid_beats = sum(3 * span_beats(928, 32, words) + span_beats(256 + 16 * (k // P_COUNT), 16, words)
                    for k in range(len(fragments) // 16))
    acked_beats = gate_beats + down_beats + quantize_beats + activation_beats + fragment_beats + mid_beats
    return CORE_CYCLES_PER_ACKED_BEAT * acked_beats + 11 * len(fragments)
