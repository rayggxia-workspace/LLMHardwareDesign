"""Adapt #272's bounded ATT1 refill and shared-S reads to other head layouts."""
from collections import Counter

from native_tlm_timing import Transfer
from native_tlm_pipeline import span


class PipelinedOperands:
    def __init__(self, projection, start, row_words, rows, stats=None):
        self.proj = projection
        self.ram = projection.target
        self.start = start
        self.row_words = row_words
        self.rows = rows
        self.stats = Counter() if stats is None else stats

    def read(self, start, words, done):
        span(self.ram, start, words, self.proj.edge, done)

    def refill(self, address, word, words, done):
        if address % 64 or word % 4 or words % 4:
            raise ValueError("unaligned pipelined attention refill")
        expected = words//4
        issued = returned = scheduled = committed = active = 0
        payloads = {}

        def pump():
            nonlocal issued, scheduled, active
            while issued < expected and issued-returned < 8 and issued-committed < 16:
                index = issued
                issued += 1
                at = address+64*index
                self.stats["ddr_issued"] += 1
                self.stats["ddr_peak_inflight"] = max(self.stats["ddr_peak_inflight"], issued-returned)
                self.stats["reply_slots_peak"] = max(self.stats["reply_slots_peak"], issued-committed)
                self.proj.dram.submit(Transfer(at), lambda i=index,a=at: receive(i,a), channel=1)
            while active < 4 and scheduled in payloads:
                index = scheduled
                scheduled += 1
                active += 1
                self.stats["s_write_peak"] = max(self.stats["s_write_peak"], active)
                payload = payloads.pop(index)
                self.proj.edge(lambda i=index, v=payload:
                               span(self.ram, word+4*i, 4, self.proj.edge, acknowledge, v))

        def receive(index, address):
            nonlocal returned
            returned += 1
            self.stats["ddr_returned"] += 1
            if index < scheduled or index in payloads:
                raise ValueError("duplicate pipelined attention response")
            payloads[index] = self.proj.memory(address)
            pump()

        def acknowledge(_):
            nonlocal active, committed
            active -= 1
            committed += 1
            self.stats["s_write_acks"] += 1
            if committed == expected:
                if active or payloads or issued != returned:
                    raise ValueError("attention operand refill did not drain")
                done()
            else:
                pump()

        pump()

    def replay(self, address, count, consume, done):
        """Alternate disjoint S half windows, preserving tile retirement order."""
        next_fill = next_take = 0
        buffers = {}
        filling = taking = False
        row_bytes = self.row_words*16

        def pump():
            nonlocal next_fill, filling, taking
            if not filling and next_fill < count:
                first = next_fill
                bank = (first//self.rows) % 2
                if bank not in buffers:
                    rows = min(self.rows, count-first)
                    word = self.start + bank*self.rows*self.row_words
                    buffers[bank] = (first, rows, word, False)
                    next_fill += rows
                    filling = True
                    self.refill(address+first*row_bytes, word, rows*self.row_words, lambda b=bank: loaded(b))
            if not taking and next_take < count:
                bank = (next_take//self.rows) % 2
                tile = buffers.get(bank)
                if tile is not None and tile[0] == next_take and tile[3]:
                    first, rows, word, _ = tile
                    taking = True
                    if filling:
                        self.stats["overlapped_tiles"] += 1
                    consume(first, rows, word, lambda: consumed(bank, rows))

        def loaded(bank):
            nonlocal filling
            buffers[bank] = (*buffers[bank][:3], True)
            filling = False
            pump()

        def consumed(bank, rows):
            nonlocal next_take, taking
            del buffers[bank]
            next_take += rows
            taking = False
            if next_take == count:
                if filling or buffers:
                    raise ValueError("attention pipeline did not drain")
                done()
            else:
                pump()

        pump()
