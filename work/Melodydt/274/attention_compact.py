"""ATT1 arithmetic with packed 64-element K/V rows and an eight-row S window."""
from struct import pack, unpack, unpack_from

from native_tlm_attention import softmax_lut
from native_tlm_timing import Transfer
from native_tlm_u import rne, s32
from check_softmax import reference


class CompactAttention64:
    def __init__(self, projection):
        self.proj = projection
        self.ram = projection.target

    def bind(self, record):
        count, position, query_word, score, work, output, scale, key, value = unpack_from("<6HIQQ", record, 16)
        spans = sorted(((query_word, 16), (score, (count+3)//4), (work, 128), (output, 16)))
        if (count != position+1 or not 1 <= count <= 514 or not 0 < scale <= 1 << 30 or
                (key | value) % 64 or abs(key-value) < count*256 or any(record[48:124]) or
                any(a+n > b for (a,n),(b,_) in zip(spans, spans[1:])) or sum(spans[-1]) > 1024):
            raise ValueError("invalid compact attention extent")
        proj, ram = self.proj, self.ram

        def execute(done):
            def refill(base, first, rows, finished):
                beats = rows*4
                issued = written = 0
                ready = {}
                writing = False

                def fill():
                    nonlocal issued
                    while issued < beats and issued-written < 8:
                        word = issued
                        address = base+first*256+64*word
                        issued += 1
                        proj.dram.submit(Transfer(address), lambda i=word,a=address: received(i,a), channel=1)

                def received(index, address):
                    ready[index] = proj.memory(address)
                    drain()

                def drain():
                    nonlocal writing
                    if not writing and written in ready:
                        writing = True
                        proj.write_span(ram, work+4*written, ready.pop(written), acknowledged)

                def acknowledged():
                    nonlocal written, writing
                    written += 1
                    writing = False
                    if written == beats:
                        proj.read_span(ram, work, rows*16, finished)
                    else:
                        fill()
                        drain()

                fill()

            def qk(first, query):
                if first == count:
                    normalize()
                    return
                rows = min(8, count-first)

                def dot(raw):
                    scores = [s32(rne(sum(a*b for a,b in zip(query, row)), 16))
                              for row in (unpack_from("<64i", raw, i*256) for i in range(rows))]
                    scores.extend([0]*(-rows%4))
                    data = pack(f"<{len(scores)}i", *scores)
                    proj.edge(lambda: proj.write_span(ram, score+first//4, data,
                              lambda: qk(first+rows, query)), 128)

                refill(key, first, rows, dot)

            def normalize():
                words = (count+3)//4

                def softmax(raw):
                    scaled = [s32(rne(v*scale, 30)) for v in unpack(f"<{words*4}i", raw)[:count]]
                    exp, probs = reference(scaled, softmax_lut())
                    exp.extend([0]*(words*4-count))
                    probs.extend([0]*(words*4-count))
                    values = pack(f"<{words*4}i", *probs)
                    proj.edge(lambda: proj.write_span(ram, score, pack(f"<{words*4}i", *exp),
                              lambda: proj.read_span(ram, score, words, lambda _:
                              proj.edge(lambda: proj.write_span(ram, score, values, lambda: av(0, [0]*64)), 64))),
                              words*9)

                proj.read_span(ram, score, words, softmax)

            def av(first, totals):
                if first == count:
                    data = pack("<64i", *(s32(rne(v, 16)) for v in totals))
                    proj.write_span(ram, output, data, done)
                    return
                rows = min(8, count-first)

                def probabilities(raw):
                    p = unpack(f"<{len(raw)//4}i", raw)

                    def multiply(values):
                        for row in range(rows):
                            for lane, v in enumerate(unpack_from("<64i", values, 256*row)):
                                totals[lane] += p[row]*v
                        proj.edge(lambda: av(first+rows, totals), rows*8)

                    refill(value, first, rows, multiply)

                proj.read_span(ram, score+first//4, (rows+3)//4, probabilities)

            proj.read_span(ram, query_word, 16, lambda raw: qk(0, unpack("<64i", raw)))
        return execute
