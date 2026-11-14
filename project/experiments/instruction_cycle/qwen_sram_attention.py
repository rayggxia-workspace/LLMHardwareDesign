"""SRAM timing of one non-pipelined ATT1 service."""

from functools import lru_cache
from struct import unpack_from

from qwen_sram_spans import SERIAL_BEAT_CYCLES, span_beats


@lru_cache(maxsize=256)
def attention_beats(count, query, score, work, output, words):
    def span(address, length):
        return span_beats(address, length, words)

    beats = 0
    for first in range(0, count, 8):
        rows = min(8, count - first)
        beats += sum(span(work + 4 * burst, 4) for burst in range(8 * rows))
        beats += span(query, 32) + span(work, 32 * rows) + span(score + first // 4, (rows + 3) // 4)
    score_words = (count + 3) // 4
    # Per-word scale read/write, then three full reads and two full writes.
    beats += 2 * score_words + 5 * span(score, score_words)
    for group in range(16):
        for first in range(0, count, 128):
            rows = min(128, count - first)
            beats += sum(span(work + 2 * row, 2) for row in range(rows))
            beats += span(score + first // 4, (rows + 3) // 4) + span(work, 2 * rows)
        beats += span(output + 2 * group, 2)
    return beats


def attention_cycles(record, step, words):
    count, position, query, score, work, output = unpack_from("<6H", record, 16)
    if record[:4] != b"ATT1" or (count, position) != (512 + step, 511 + step):
        raise ValueError("ATT1 context does not match the sealed Decode phase")
    return SERIAL_BEAT_CYCLES * attention_beats(count, query, score, work, output, words)
