"""Bounded transactions for the native timing sensitivity experiment."""

def stream(count, depth, issue, done):
    """Reserve a slot until its tagged completion, allowing reordered responses."""
    next_index = 0
    active = set()

    def advance():
        nonlocal next_index
        while next_index < count and len(active) < depth:
            index = next_index
            next_index += 1
            active.add(index)
            issue(index, lambda index=index: acknowledged(index))

    def acknowledged(index):
        active.remove(index)
        if next_index == count and not active:
            done()
        else:
            advance()

    if count:
        advance()
    else:
        done()


def span(sram, start, words, edge, done, payload=None):
    """Issue at most two beats before their responses, through the same S port."""
    slices = []
    offset = 0
    while offset < words:
        size = sram.beat_words(start + offset, words - offset)
        slices.append((offset, size))
        offset += size
    parts = [None] * len(slices)

    def issue(index, ack):
        offset, size = slices[index]
        data = None if payload is None else payload[16*offset:16*(offset+size)]

        def returned(value):
            parts[index] = value
            edge(ack)

        sram.access_beat(start + offset, size, returned, data)

    stream(len(slices), 2, issue, lambda: done(b"".join(parts)))
