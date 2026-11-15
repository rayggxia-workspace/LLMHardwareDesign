"""PR260 projection service progression, explicitly bound to one declared M/S_P.

Integer vectorization changes neither record ordering nor rounding boundaries.
Local source staging is supplied by macro_projection_service, never a U/P link.
Timing remains a service model pending RTL calibration.
"""

from collections import Counter, deque
from struct import pack, unpack, unpack_from

from native_tlm_timing import Transfer
from macro_numeric import rne


def accumulate(weights, activation, shift, prefix, head16):
    # The native record packing and per-K128 rounding are preserved.
    # Only the exact integer dot arithmetic is vectorized; schedules are not cached.
    import numpy as np
    payload=np.frombuffer(weights,dtype=np.int8,count=1024).astype(np.int64).reshape(8,8,16)
    activation=np.asarray(activation,dtype=np.int64).reshape(8,16)
    products=(payload*activation[:,None,:]).sum(axis=2)
    steps=8 if head16 else 1
    scales=unpack_from("<"+"H"*(steps*8),weights,1024)
    if not head16 and any(weights[1040:]):
        raise ValueError("nonzero ordinary projection record padding")
    for step in range(steps):
        values=products[step] if head16 else products.sum(axis=0)
        for lane in range(8):
            bits=scales[8*step+lane];exponent=bits>>10
            if not 0<bits<0x7c00:raise ValueError("invalid projection weight scale")
            scaled=rne(int(values[lane])*((bits&1023)+(1024 if exponent else 0)),
                       25-max(exponent,1)-shift)
            prefix[lane]+=scaled
            if not -(1<<31)<=scaled<1<<31 or not -(1<<31)<=prefix[lane]<1<<31:
                raise ValueError("native projection overflow")


class Projection:
    def __init__(self, clock, dram, memory, source, target, *, source_word, scratch_word,
                 scratch_sram=None):
        self.clock, self.dram, self.memory = clock, dram, memory
        self.source, self.target = source, target
        self.source_word, self.scratch_word = source_word, scratch_word
        self.scratch_sram = source if scratch_sram is None else scratch_sram
        self.stats = Counter()
        self.busy = False
        self.fetch_queue=deque();self.fetch_pending=0;self.fetch_scheduled=False

    def edge(self, action, cycles=1):
        period = self.target.core_ps
        self.clock.after(cycles * period - self.clock.now % period, action)

    def provider(self, record, *, packed_tile=None):
        weight0, weight1, columns, first, stride, groups, context, full_k, start, end, ways, flags = (
            unpack_from("<QQIIHBBHHHBB", record, 48))
        input_s, out, out1, scratch, snapshot, reserved, bias0, bias1 = unpack_from("<6HQQ", record, 84)
        bases = (weight0,) if ways == 1 else (weight0, weight1)
        outputs = (out,) if ways == 1 else (out, out1)
        spans = sorted([(input_s, 16), *((word, 2 * groups) for word in outputs)])
        if (any(base % 64 for base in bases) or stride < 8 or stride % 8 or first % 8 or
                not 1 <= groups <= 16 or context + groups * ways > 16 or
                first + (groups - 1) * stride >= columns or ways not in (1, 2) or
                flags > 1 or start or end != full_k or not full_k or full_k % 128 or
                sum(spans[-1]) > 1024 or any(a + size > b for (a, size), (b, _) in zip(spans, spans[1:])) or
                (ways == 1 and (weight1 or out1)) or reserved or bias0 or bias1 or any(record[112:124])):
            raise ValueError("unsupported native service-2 projection extent")
        overlaps_source = self.scratch_sram is self.source and not (
            self.scratch_word + 16 <= self.source_word or
            self.source_word + full_k // 4 <= self.scratch_word)
        overlaps_target = self.scratch_sram is self.target and any(
            word < self.scratch_word + 16 and self.scratch_word < word + width for word, width in spans)
        if packed_tile is None and (
                ways != 1 or scratch or snapshot or self.source_word + full_k // 4 > 1024 or
                not 0 <= self.scratch_word <= 1008 or overlaps_source or overlaps_target):
            raise ValueError("unbound projection feeder windows")
        head16 = bool(flags)
        size = 1152 if head16 else 1088
        tiles = full_k // 128

        def execute(done):
            if self.busy:
                raise ValueError("P projection already owns the feeder and M contexts")
            self.busy = True
            prefixes = [[0] * 8 for _ in range(groups * ways)]

            def tile(k):
                if k == tiles:
                    write_output(0)
                    return
                if packed_tile is not None:
                    packed_tile(k, lambda payload, shift: stage(k, payload, shift))
                    return
                start_word = self.source_word + k * 32

                def scan(data):
                    peak = max(abs(value) for value in unpack("<128i", data))
                    shift = next(s for s in range(18) if peak <= 32767 << s)

                    def convert(raw):
                        packed = pack("<128h", *(rne(v, shift) for v in unpack("<128i", raw)))
                        self.write_span(self.scratch_sram, self.scratch_word, packed, lambda: self.read_span(
                            self.scratch_sram, self.scratch_word, 16, lambda staged: stage(k, staged, shift)))

                    self.edge(lambda: self.read_span(self.source, start_word, 32, convert))

                self.read_span(self.source, start_word, 32, scan)

            def stage(k, packed, shift):
                def published():
                    if packed_tile is not None and k+1<tiles:
                        packed_tile.prefetch(k+1)
                    self.read_span(self.target,input_s,16,
                        lambda data:run_records(k,unpack("<128h",data),shift))
                if packed_tile is None:
                    self.write_span(self.target,input_s,packed,published)
                else:
                    if packed_tile.ready_in_sram is not True:
                        raise ValueError('packed activation must be committed in target SRAM')
                    published()

            def run_records(k, activation, shift):
                slots = {}
                next_fetch, next_run, executing = 0, 0, False

                def advance():
                    nonlocal next_fetch, executing
                    while len(slots) < 4 and next_fetch < groups * ways:
                        entry = next_fetch
                        next_fetch += 1
                        slots[entry] = None
                        group, way = divmod(entry, ways)
                        index = ((first + group * stride) // 8) * tiles + k
                        address = bases[way] + size * index
                        self.fetch(address, size, lambda data, e=entry: ready(e, data))
                    if next_run == groups * ways:
                        self.edge(lambda: tile(k + 1))
                    elif not executing and slots[next_run] is not None:
                        executing = True
                        # W-first stream is 8 x 128 B for K128. The completion
                        # includes a modeled scale/result drain per M group.
                        self.edge(finish_group, 8 + 8 * (8 if head16 else 1))

                def ready(group, data):
                    slots[group] = data
                    advance()

                def finish_group():
                    nonlocal next_run, executing
                    data = slots.pop(next_run)
                    accumulate(data, activation, shift, prefixes[next_run], head16)
                    self.stats["weight_records_consumed"] += 1
                    next_run += 1
                    executing = False
                    advance()

                advance()

            def write_output(index):
                if index == groups * ways:
                    self.busy = False
                    done()
                    return
                group, way = divmod(index, ways)
                self.write_span(self.target, outputs[way] + 2 * group, pack("<8i", *prefixes[index]),
                                lambda: write_output(index + 1))

            self.edge(lambda: tile(0))
        return execute

    def read_span(self, sram, start, words, done):
        parts = [None] * words
        issued = returned = pending = 0
        scheduled = False
        def schedule():
            nonlocal scheduled
            if not scheduled and issued < words and pending < 2:
                scheduled = True
                self.edge(issue, 2)
        def issue():
            nonlocal issued, pending, scheduled
            scheduled = False
            if issued == words or pending == 2:
                return
            index = issued
            issued += 1
            pending += 1
            def complete(data):
                nonlocal pending, returned
                if parts[index] is not None:
                    raise ValueError('duplicate A SRAM return')
                parts[index] = data
                pending -= 1
                returned += 1
                if returned == words:
                    done(b''.join(parts))
                else:
                    schedule()
            sram.access(start + index, complete)
            schedule()
        schedule()

    def write_span(self, sram, start, data, done):
        def step(offset):
            if offset == len(data):
                done()
                return
            sram.access(start + offset // 16, lambda _: self.edge(lambda: step(offset + 16)),
                        data[offset:offset + 16])
        step(0)

    def fetch(self, base, size, done):
        """M weight banks issue tagged beats without waiting for previous returns."""
        if size not in (1088,1152) or base%64:raise ValueError("weight record extent")
        request={"base":base,"parts":[None]*(size//64),"next":0,"returned":0,"done":done}
        self.fetch_queue.append(request)
        self._schedule_fetch()

    def _schedule_fetch(self):
        if self.fetch_queue and self.fetch_pending<32 and not self.fetch_scheduled:
            self.fetch_scheduled=True
            self.edge(self._issue_fetch)

    def _issue_fetch(self):
        self.fetch_scheduled=False
        if not self.fetch_queue or self.fetch_pending>=32:return
        request=self.fetch_queue.popleft()
        index=request["next"];request["next"]+=1
        if request["next"]<len(request["parts"]):self.fetch_queue.append(request)
        address=request["base"]+index*64
        self.fetch_pending+=1
        self.stats["weight_read_peak_outstanding"]=max(
            self.stats["weight_read_peak_outstanding"],self.fetch_pending)
        def returned():
            if request["parts"][index] is not None:raise ValueError("duplicate weight response")
            request["parts"][index]=self.memory(address)
            request["returned"]+=1;self.fetch_pending-=1
            self.stats["weight_read_returns"]+=1
            if request["returned"]==len(request["parts"]):
                request["done"](b"".join(request["parts"]))
            self._schedule_fetch()
        self.dram.submit(Transfer(address),returned,channel=(request["base"]>>11)&1)
        self._schedule_fetch()
