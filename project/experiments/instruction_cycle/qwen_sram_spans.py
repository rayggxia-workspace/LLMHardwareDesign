"""Count serialized SRAM operations in the unpipelined Qwen TLM services."""

from struct import unpack_from


WIDTH_WORDS = (1, 2, 4)
ACK_CYCLES = 2
SERIAL_BEAT_CYCLES = ACK_CYCLES + 1
BURST_WORDS = 4
PROJECTION = b"\x01PP\x02"
DMA_BURSTS = {b"DRL1": 8, b"DWS1": 8, b"KVR1": 8, b"DRL8": 128, b"DWS8": 128}


def span_beats(start, length, words):
    """Count contiguous SRAM beats without crossing an aligned port group."""
    if words not in WIDTH_WORDS or start < 0 or length < 0:
        raise ValueError("unsupported SRAM span or port width")
    if not length:
        return 0
    return (start % words + length + words - 1) // words


def projection_cycles(record, words, vocabulary=False):
    """Return ordered SRAM cycles for one non-FFN P_SCOPE descriptor."""
    if len(record) != 128 or record[:4] != PROJECTION:
        raise ValueError("expected a P_SCOPE descriptor")
    groups = record[74]
    full_k, first_k, end_k, ways, flags = unpack_from("<HHHBB", record, 76)
    input_word, output_word = unpack_from("<HH", record, 84)
    if (not full_k or full_k % 128 or first_k != 0 or end_k != full_k or ways != 1
            or not 1 <= groups <= 16 or flags != int(vocabulary) or vocabulary and groups != 16):
        raise ValueError("unsupported serial projection descriptor")

    # Every activation tile starts on the same alignment modulo port width.
    tile_beats = 2 * (span_beats(512, 32, words) + span_beats(1008, 16, words)
                      + span_beats(input_word, 16, words))
    beats = (full_k // 128) * tile_beats
    beats += sum(span_beats(output_word + 2 * group, 2, words) for group in range(groups))
    if vocabulary:
        beats += span_beats(output_word, 32, words)
    return beats * SERIAL_BEAT_CYCLES


def dma_cycles(record, words):
    """Return ordered SRAM cycles for a non-pipelined native DMA descriptor."""
    if len(record) != 128:
        raise ValueError("expected a complete native DMA descriptor")
    schema = record[:4]
    start, = unpack_from("<H", record, 16)
    if schema == b"FDS8":
        if start != 0:
            raise ValueError("unsupported FFN Down gather start")
        # Every 64-byte DDR beat covers two distinct groups. Each group of
        # two words comes from its own P bank and cannot merge with the next.
        beats = 256 * span_beats(0, 2, words)
    elif schema in DMA_BURSTS:
        beats = DMA_BURSTS[schema] * span_beats(start, BURST_WORDS, words)
    else:
        raise ValueError("unsupported native DMA schema: {!r}".format(schema))
    return beats * SERIAL_BEAT_CYCLES


def embedding_cycles(record, words):
    """Return SRAM cycles for one embedding, including its index read."""
    if len(record) != 128 or record[:4] != b"\x03\x00\x00\x00" or record[6] != 4:
        raise ValueError("expected an embedding descriptor")
    output_word, = unpack_from("<H", record, 30)
    # The embedding returns directly to the next store at ACK. Its index
    # is a one-word read regardless of the selected port width.
    beats = 1 + 128 * span_beats(output_word, BURST_WORDS, words)
    return beats * ACK_CYCLES


def pm_cycles(image_bytes, words):
    """Return PM write cycles, excluding DDR reads and the fixed byte scan."""
    if words not in WIDTH_WORDS or image_bytes <= 0:
        raise ValueError("unsupported PM image size or port width")
    full, tail = divmod(image_bytes, 64)
    return ACK_CYCLES * (full * BURST_WORDS // words + span_beats(0, (tail + 15) // 16, words))
