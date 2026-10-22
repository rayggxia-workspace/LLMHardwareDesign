"""Explicit storage/transfer ledger, not a cycle, area, or power simulator.

Two fixed banks and one matrix plus one vector engine. Joining the blocks only
changes whether their transfers cross a boundary; it grants no extra storage,
compute, port, overlap, or free data movement. Repeated equal-size tiles are
represented once with a multiplicity, preserving exact bytes and peak liveness.
"""
from contextlib import contextmanager
from collections import Counter


class Ledger:
    def __init__(self):
        self.active = {}
        self.live = Counter(matrix=0, vector=0)
        self.peak = Counter(matrix=0, vector=0)
        self.peak_total = 0
        self.counts = Counter()
        self.factor = 1
        self.events = []
        self.max_transfer = 0

    @contextmanager
    def repeat(self, count):
        if not isinstance(count, int) or count < 1:
            raise ValueError("positive integer repeat required")
        before = dict(self.active)
        self.factor *= count
        try:
            yield
        finally:
            self.factor //= count
        if before != self.active:
            raise ValueError("repeated section must restore buffer names and sizes")

    def event(self, kind, **fields):
        self.events.append(dict(kind=kind, multiplicity=self.factor, **fields))

    def alloc(self, name, bank, size):
        if name in self.active or bank not in ("matrix", "vector"):
            raise ValueError("duplicate buffer or unknown bank")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("positive integer allocation required")
        self.active[name] = (bank, size)
        self.live[bank] += size
        self.peak[bank] = max(self.peak[bank], self.live[bank])
        self.peak_total = max(self.peak_total, sum(self.live.values()))
        self.event("alloc", name=name, bank=bank, size=size)

    def free(self, name):
        bank, size = self.active.pop(name)
        self.live[bank] -= size
        self.event("free", name=name, bank=bank, size=size)

    def traffic(self, kind, size):
        if not isinstance(size, int) or size < 0:
            raise ValueError("nonnegative integer byte count required")
        self.counts[kind] += size * self.factor

    def load(self, name):
        bank, size = self.active[name]
        self.traffic("external_read", size)
        self.traffic(bank + "_write", size)
        self.event("load", name=name, size=size)

    def store(self, name):
        bank, size = self.active[name]
        self.traffic("external_write", size)
        self.traffic(bank + "_read", size)
        self.event("store", name=name, size=size)

    def copy(self, source, target):
        src, n = self.active[source]
        dst, m = self.active[target]
        if src == dst or n != m:
            raise ValueError("cross-bank copy requires equal existing buffers")
        self.traffic(src + "_read", n)
        self.traffic(dst + "_write", n)
        self.traffic(src + "_to_" + dst, n)
        self.max_transfer = max(self.max_transfer, n)
        self.event("copy", source=source, target=target, size=n)

    def compute(self, bank, read, write, macs=0, label=""):
        if bank not in ("matrix", "vector"):
            raise ValueError("unknown engine")
        for suffix, n in (("read", read), ("write", write)):
            self.traffic(bank + "_" + suffix, n)
        self.traffic("macs", macs)
        self.event("compute", bank=bank, read=read, write=write,
                   macs=macs, label=label)

    def finish(self):
        if self.active or sum(self.live.values()):
            raise ValueError("unreleased buffers")
        c = dict(self.counts)
        c["engine_transfer_bytes"] = c.get("matrix_to_vector", 0) + c.get("vector_to_matrix", 0)
        c["external_bytes"] = c.get("external_read", 0) + c.get("external_write", 0)
        c["sram_access_bytes"] = sum(c.get(b + "_" + op, 0)
                                     for b in ("matrix", "vector") for op in ("read", "write"))
        return dict(counts=c, peak_bank_bytes=dict(self.peak),
                    peak_total_bytes=self.peak_total,
                    max_copy_burst_bytes=self.max_transfer, events=self.events)


def tile_classes(length, tile):
    if not isinstance(length, int) or not isinstance(tile, int) or min(length, tile) < 1:
        raise ValueError("positive integer dimensions required")
    whole, tail = divmod(length, tile)
    return ([(tile, whole)] if whole else []) + ([(tail, 1)] if tail else [])


def ffn(tokens, hidden, intermediate, tile, schedule, scalar_bytes=4):
    """SwiGLU, two input projections then SiLU*up then down projection.

    All weights stream once. X stays resident until no longer required. The
    streaming schedule retains its output accumulator while traversing F.
    All tensors use the declared scalar width, without implicit quantization.
    """
    if schedule not in ("materialized", "streaming"):
        raise ValueError("unknown schedule")
    t, h, f, b = tokens, hidden, intermediate, scalar_bytes
    for v in (t, h, f, b):
        if not isinstance(v, int) or v < 1:
            raise ValueError("positive dimensions/byte width required")
    parts = tile_classes(f, tile)
    l = Ledger()
    l.alloc("x", "matrix", t*h*b); l.load("x")
    if schedule == "materialized":
        l.alloc("up_all", "matrix", t*f*b)
        l.alloc("gate_all", "matrix", t*f*b)
        for width, count in parts:
            with l.repeat(count):
                for projection in ("up", "gate"):
                    l.alloc("weight", "matrix", h*width*b); l.load("weight")
                    l.compute("matrix", (t*h + h*width)*b, t*width*b,
                              t*h*width, projection)
                    l.free("weight")
        l.free("x")
        for src, dst in (("up_all", "up_v"), ("gate_all", "gate_v")):
            l.alloc(dst, "vector", t*f*b); l.copy(src, dst); l.free(src)
        l.compute("vector", 3*t*f*b, 2*t*f*b, label="SiLU in place then multiply in place")
        l.free("up_v")
        l.alloc("z", "matrix", t*f*b); l.copy("gate_v", "z"); l.free("gate_v")
        l.alloc("out", "matrix", t*h*b)
        l.compute("matrix", 0, t*h*b, label="zero accumulator")
        for width, count in parts:
            with l.repeat(count):
                l.alloc("weight", "matrix", width*h*b); l.load("weight")
                l.compute("matrix", (t*width + width*h + t*h)*b, t*h*b,
                          t*width*h, "down accumulation")
                l.free("weight")
        l.free("z")
    else:
        l.alloc("out", "matrix", t*h*b)
        l.compute("matrix", 0, t*h*b, label="zero accumulator")
        for width, count in parts:
            with l.repeat(count):
                for projection in ("up", "gate"):
                    l.alloc(projection, "matrix", t*width*b)
                    l.alloc("weight", "matrix", h*width*b); l.load("weight")
                    l.compute("matrix", (t*h + h*width)*b, t*width*b,
                              t*h*width, projection)
                    l.free("weight")
                for src, dst in (("up", "up_v"), ("gate", "gate_v")):
                    l.alloc(dst, "vector", t*width*b); l.copy(src, dst); l.free(src)
                l.compute("vector", 3*t*width*b, 2*t*width*b, label="SiLU/multiply in place")
                l.free("up_v")
                l.alloc("z", "matrix", t*width*b); l.copy("gate_v", "z"); l.free("gate_v")
                l.alloc("weight", "matrix", width*h*b); l.load("weight")
                l.compute("matrix", (t*width + width*h + t*h)*b, t*h*b,
                          t*width*h, "down accumulation")
                l.free("weight"); l.free("z")
        l.free("x")
    l.store("out"); l.free("out")
    return l.finish()


def attention(queries, keys, query_heads, kv_heads, head_dim, qtile, ktile,
              schedule, scalar_bytes=4):
    """GQA attention core with a matrix bank and a vector softmax/state bank.

    QK and PV are dense even for causal masks. Full-score and online variants
    read identical Q/K/V bytes under the same group/tile order. KV is persistent
    external state, not silently omitted from the device's capacity requirement.
    Online O accumulation occurs on the vector engine: tile O therefore crosses
    the matrix/vector interface. No free row-rescale engine is assumed.
    """
    if schedule not in ("materialized", "streaming"):
        raise ValueError("unknown schedule")
    q, k, nh, nk, d, b = queries, keys, query_heads, kv_heads, head_dim, scalar_bytes
    if any(not isinstance(v, int) or v < 1 for v in (q,k,nh,nk,d,b)) or nh % nk:
        raise ValueError("positive dimensions and divisible GQA required")
    if q > k:
        raise ValueError("queries cannot exceed cached keys in this causal experiment")
    qp, kp = tile_classes(q, qtile), tile_classes(k, ktile)
    group = nh // nk
    l = Ledger()
    if schedule == "materialized":
        l.alloc("scores_all", "matrix", nh*q*k*b)
        with l.repeat(nk):
            for qt, qcount in qp:
                with l.repeat(qcount):
                    l.alloc("Q", "matrix", group*qt*d*b); l.load("Q")
                    for kt, kcount in kp:
                        with l.repeat(kcount):
                            l.alloc("K", "matrix", kt*d*b); l.load("K")
                            l.compute("matrix", (group*qt*d + kt*d)*b, group*qt*kt*b,
                                      group*qt*kt*d, "QK including masked positions")
                            l.free("K")
                    l.free("Q")
        l.alloc("P_vector", "vector", nh*q*k*b)
        l.copy("scores_all", "P_vector"); l.free("scores_all")
        l.alloc("row_state", "vector", 2*nh*q*b)
        l.compute("vector", (3*nh*q*k+2*nh*q)*b, (2*nh*q*k+2*nh*q)*b,
                  label="three passes: max; exp/sum; normalize; row state in vector bank")
        l.free("row_state")
        l.alloc("P_matrix", "matrix", nh*q*k*b)
        l.copy("P_vector", "P_matrix"); l.free("P_vector")
        with l.repeat(nk):
            for qt, qcount in qp:
                with l.repeat(qcount):
                    l.alloc("O", "matrix", group*qt*d*b)
                    l.compute("matrix", 0, group*qt*d*b, label="zero O")
                    for kt, kcount in kp:
                        with l.repeat(kcount):
                            l.alloc("V", "matrix", kt*d*b); l.load("V")
                            l.compute("matrix", (group*qt*kt + kt*d + group*qt*d)*b,
                                      group*qt*d*b, group*qt*kt*d, "PV accumulation")
                            l.free("V")
                    l.store("O"); l.free("O")
        l.free("P_matrix")
    else:
        with l.repeat(nk):
            for qt, qcount in qp:
                with l.repeat(qcount):
                    l.alloc("Q", "matrix", group*qt*d*b); l.load("Q")
                    l.alloc("state", "vector", 2*group*qt*b)
                    l.alloc("O_vector", "vector", group*qt*d*b)
                    l.compute("vector", 0, group*qt*(d+2)*b, label="initialize online state")
                    for kt, kcount in kp:
                        with l.repeat(kcount):
                            l.alloc("K", "matrix", kt*d*b); l.load("K")
                            l.alloc("scores", "matrix", group*qt*kt*b)
                            l.compute("matrix", (group*qt*d + kt*d)*b, group*qt*kt*b,
                                      group*qt*kt*d, "QK including masked positions")
                            l.free("K")
                            l.alloc("P_vector", "vector", group*qt*kt*b)
                            l.copy("scores", "P_vector"); l.free("scores")
                            l.alloc("alpha", "vector", group*qt*b)
                            l.compute("vector", (3*group*qt*kt + 2*group*qt)*b,
                                      (group*qt*kt + 3*group*qt)*b,
                                      label="online softmax state and rescale")
                            l.alloc("P_matrix", "matrix", group*qt*kt*b)
                            l.copy("P_vector", "P_matrix"); l.free("P_vector")
                            l.alloc("V", "matrix", kt*d*b); l.load("V")
                            l.alloc("tile_O", "matrix", group*qt*d*b)
                            l.compute("matrix", (group*qt*kt + kt*d)*b, group*qt*d*b,
                                      group*qt*kt*d, "PV tile")
                            l.free("V"); l.free("P_matrix")
                            l.alloc("tile_O_vector", "vector", group*qt*d*b)
                            l.copy("tile_O", "tile_O_vector"); l.free("tile_O")
                            l.compute("vector", group*qt*(2*d+1)*b, group*qt*d*b,
                                      label="rescale and accumulate O")
                            l.free("tile_O_vector"); l.free("alpha")
                    l.compute("vector", group*qt*(d+1)*b, group*qt*d*b,
                              label="normalize O by final denominator")
                    l.store("O_vector"); l.free("O_vector"); l.free("state"); l.free("Q")
    result = l.finish()
    result["persistent_external_kv_bytes"] = 2*nk*k*d*b
    result["scope"] = "attention core only; projections/RoPE/FFN omitted, dense causal computation"
    return result


def qualify(result, matrix_capacity, vector_capacity, reserve_percent, partition):
    """Capacity and declared interface demand only; no physical qualification."""
    if partition not in ("split", "joined") or not 0 <= reserve_percent < 100:
        raise ValueError("invalid partition or reserve")
    if min(matrix_capacity, vector_capacity) <= 0:
        raise ValueError("positive bank capacities required")
    caps = {"matrix": matrix_capacity, "vector": vector_capacity}
    failures = []
    for bank, cap in caps.items():
        if result["peak_bank_bytes"][bank]*100 > cap*(100-reserve_percent):
            failures.append(bank + " capacity with declared reserve exceeded")
    transfer = result["counts"]["engine_transfer_bytes"]
    return dict(partition=partition, selected_schedule_fits=not failures, failures=failures,
                headroom={bank: 1-result["peak_bank_bytes"][bank]/cap for bank, cap in caps.items()},
                cross_block_bytes=transfer if partition == "split" else 0,
                local_interengine_bytes=transfer if partition == "joined" else 0,
                required_resources="same two banks and engines; joined does not pool banks",
                physical_qualified=False)


def ffn_workload(tokens, hidden, intermediate, token_tile, feature_tile, schedule,
                 scalar_bytes=4):
    """Independent token tiles reload weights; never count a free global cache."""
    counts = Counter()
    peak = Counter(matrix=0, vector=0)
    peak_total = burst = 0
    events = []
    for t, multiplicity in tile_classes(tokens, token_tile):
        r = ffn(t, hidden, intermediate, feature_tile, schedule, scalar_bytes)
        for name, value in r["counts"].items():
            counts[name] += value * multiplicity
        for bank, value in r["peak_bank_bytes"].items():
            peak[bank] = max(peak[bank], value)
        peak_total = max(peak_total, r["peak_total_bytes"])
        burst = max(burst, r["max_copy_burst_bytes"])
        events.extend([dict(e, multiplicity=e["multiplicity"]*multiplicity)
                       for e in r["events"]])
    return dict(counts=dict(counts), peak_bank_bytes=dict(peak),
                peak_total_bytes=peak_total, max_copy_burst_bytes=burst,
                events=events,
                scope="SwiGLU core; independent token tiles reload all weights; no global weight cache")
