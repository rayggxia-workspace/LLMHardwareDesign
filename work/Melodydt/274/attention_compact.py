"""ATT1 arithmetic with one V read per row in an eight-row SRAM window."""
from struct import pack, unpack, unpack_from
from collections import Counter

from native_tlm_attention import softmax_lut
from native_tlm_timing import Transfer
from native_tlm_u import rne, s32
from check_softmax import reference


class TiledAttention:
    def __init__(self, projection, width, *, pipeline=False):
        if width not in (64, 128):
            raise ValueError("unsupported tiled attention head dimension")
        self.proj = projection
        self.ram = projection.target
        self.width = width
        self.pipeline = pipeline
        self.stats = Counter()

    def bind(self, record):
        count, position, query_word, score, work, output, scale, key, value = unpack_from("<6HIQQ", record, 16)
        width = self.width
        row_bytes = width*4
        row_words = width//4
        row_beats = width//16
        vector = f"<{width}i"
        spans = sorted(((query_word, row_words), (score, (count+3)//4), (work, 8*row_words), (output, row_words)))
        if (count != position+1 or not 1 <= count <= 514 or not 0 < scale <= 1 << 30 or
                (key | value) % 64 or abs(key-value) < count*row_bytes or any(record[48:124]) or
                any(a+n > b for (a,n),(b,_) in zip(spans, spans[1:])) or sum(spans[-1]) > 1024):
            raise ValueError("invalid compact attention extent")
        proj, ram = self.proj, self.ram
        operand = None
        if self.pipeline:
            from attention_refill import PipelinedOperands
            operand = PipelinedOperands(proj, work, row_words, 4, self.stats)

        def execute(done):
            def refill(base, first, rows, finished):
                beats = rows*row_beats
                issued = written = 0
                ready = {}
                writing = False

                def fill():
                    nonlocal issued
                    while issued < beats and issued-written < 8:
                        word = issued
                        address = base+first*row_bytes+64*word
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
                        proj.read_span(ram, work, rows*row_words, finished)
                    else:
                        fill()
                        drain()

                fill()

            def scores(first, rows, query, raw, finished, tile_cycles):
                values = [s32(rne(sum(a*b for a,b in zip(query, row)), 16))
                          for row in (unpack_from(vector, raw, i*row_bytes) for i in range(rows))]
                values.extend([0]*(-rows%4))
                data = pack(f"<{len(values)}i", *values)
                proj.edge(lambda: proj.write_span(ram, score+first//4, data, finished), tile_cycles)

            def qk(first, query):
                if first == count:
                    normalize()
                    return
                rows = min(8, count-first)
                refill(key, first, rows, lambda raw:
                       scores(first, rows, query, raw, lambda: qk(first+rows, query), 128))

            def start_query(raw):
                query = unpack(vector, raw)
                if operand is None:
                    qk(0, query)
                else:
                    def consume(first, rows, word, finished):
                        operand.read(word, rows*row_words, lambda data:
                                     scores(first, rows, query, data, finished, 64))
                    operand.replay(key, count, consume, normalize)

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
                              proj.edge(lambda: proj.write_span(ram, score, values, start_av), 64))),
                              words*9)

                proj.read_span(ram, score, words, softmax)

            def av(first, totals):
                if first == count:
                    output_av(totals)
                    return
                rows = min(8, count-first)

                def probabilities(raw):
                    p = unpack(f"<{len(raw)//4}i", raw)

                    refill(value, first, rows, lambda values:
                           dot_values(values, p, rows, totals, lambda: av(first+rows, totals)))

                proj.read_span(ram, score+first//4, (rows+3)//4, probabilities)

            def dot_values(values, probabilities, rows, totals, finished):
                for row in range(rows):
                    for lane, v in enumerate(unpack_from(vector, values, row_bytes*row)):
                        totals[lane] += probabilities[row]*v
                proj.edge(finished, rows*(width//8))

            def output_av(totals):
                data = pack(vector, *(s32(rne(v, 16)) for v in totals))
                proj.write_span(ram, output, data, done)

            def start_av():
                totals = [0]*width
                if operand is None:
                    av(0, totals)
                else:
                    def consume(first, rows, word, finished):
                        def probabilities(raw):
                            p = unpack(f"<{len(raw)//4}i", raw)
                            operand.read(word, rows*row_words, lambda values:
                                         dot_values(values, p, rows, totals, finished))

                        operand.read(score+first//4, (rows+3)//4, probabilities)
                    operand.replay(value, count, consume, lambda: output_av(totals))

            proj.read_span(ram, query_word, row_words, start_query)
        return execute
