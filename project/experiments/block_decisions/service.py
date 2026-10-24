"""Bounded full-GQA attention service DAG, not measured hardware or quality.

The timed boundary starts with published integer Q/K/V (K key-major, V
feature-major) and fixed scales in backing memory. It includes all heads of one
GQA sharing group, QK, score spill, two exp passes, U64 sum and division, P15
publication/guard, S8 limb PV, final conversion, and a row-sum consumer. Q/K/V
projection, quantization, cache append/layout production and language-model
execution are outside this boundary. Heads and scratch tiles are deliberately
serialized; this is a specified feasible schedule, not an optimal accelerator.

Colocation alone changes nothing. A second, explicitly conditional colocation
profile removes only M<->A packet headers. It retains padded payload, all memory
reads/writes, endpoint credit, the same 128-bit bus and identical active assets.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


_MODEL_PATH = Path(__file__).resolve().parents[1] / "rq_ports" / "model.py"
_SPEC = importlib.util.spec_from_file_location("issue64_rq_service_model", _MODEL_PATH)
_MODEL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODEL)
Graph, audit_schedule, beats, chunks = (
    _MODEL.Graph, _MODEL.audit_schedule, _MODEL.beats, _MODEL.chunks
)


GROUPS = {
    "gemma_local0": {"heads": 2, "dim": 256, "window": 1024},
    "gemma_global5": {"heads": 2, "dim": 256, "window": None},
    "qwen25_global0": {"heads": 8, "dim": 128, "window": None},
    "qwen35_global3": {"heads": 4, "dim": 256, "window": None},
}
ORGANIZATIONS = ("split", "colocated_control", "colocated_stream")


def ceildiv(n, d):
    return (n + d - 1) // d


def lut_bytes(step):
    if step not in (128, 256):
        raise ValueError("supported LUT step is 1/128 or 1/256")
    return (16 * step + 1) * 4


def config(group="gemma_local0", keys=128, queries=1, kv_bits=8,
           exp_ii=1, organization="split", lut_step=128, rom_bytes=20480):
    if group not in GROUPS or keys not in (128, 1024) or queries not in (1, 4):
        raise ValueError("unsupported shape")
    if kv_bits not in (8, 16) or exp_ii not in (1, 8, 32):
        raise ValueError("unsupported numeric/service profile")
    if organization not in ORGANIZATIONS:
        raise ValueError("organization")
    if rom_bytes < lut_bytes(lut_step):
        raise ValueError("LUT_ROM_capacity: closed interval needs " + str(lut_bytes(lut_step)))
    g = GROUPS[group]
    return dict(group=group, keys=keys, queries=queries, kv_bits=kv_bits,
                exp_ii=exp_ii, organization=organization, heads=g["heads"],
                dim=g["dim"], window=g["window"], lut_step=lut_step,
                LUT_ROM_bytes=lut_bytes(lut_step), ROM_capacity_bytes=rom_bytes)


def inventory(c):
    return dict(matrix="one 16x16 S8 array, same QK/PV engine",
                matrix_private_bytes=32768, matrix_PE_register_bytes=2048,
                matrix_private_banks={"MA0": 4096, "MA1": 4096,
                                      "MW0": 8192, "MW1": 8192, "MC": 6144},
                attention_private_bytes=32768, attention_private_port="one 128-bit RW",
                vector_lanes=8, vector_units=1, wide_units=1,
                vector_multipliers="eight S8 multipliers; QK32*M31 uses5 times nonzero U7 multiplier digits",
                operand_pack="conservative scalar byte-enable transpose in AC: one read + digit writes + index/extract ops per element; no free transpose network",
                wide="one checked 64-bit shift/add candidate, two 32-bit limb slots",
                SFU_units=1, LUT_read_ports=1, LUT_ROM_bytes=c["LUT_ROM_bytes"],
                ROM_capacity_bytes=c["ROM_capacity_bytes"],
                S_banks=8, S_bytes_each=32768, S_ports_each="one 128-bit RW",
                link_bits=128, buses=1, fifo_bytes=2048, payload_limit=1984,
                endpoints={"M": "one TX/two RX", "A": "one TX/two RX",
                           "S0..S7": "one TX/one RX", "backing": "one TX"},
                backing="read-only Q/K/V/metadata; one 128-bit read port and same bus",
                exp_service="one ROM lookup per element, II=1/8/32 sensitivity",
                divide_service="one unsigned64 restoring divider,64 cycles/element",
                conditional_capabilities=True)


class AttentionGraph(Graph):
    def __init__(self, c, backing_size):
        super().__init__()
        self.config = copy.deepcopy(c)
        self.sizes.pop("VC")
        self.sizes["AC"] = 32768
        self.sizes["EXT"] = backing_size
        self.streams = []
        self.operations = Counter()
        self.allocations = dict(
            QK=dict(raw=[0, 8192], digits=[8192, 12288],
                    partial=[20480, 1024], score=[21504, 256], meta=[24128, 256],
                    row_state=[24448, 256]),
            softmax=dict(score=[0, 512], exp=[4096, 512], meta=[24128, 256],
                         row_state=[24448, 256]),
            PV=dict(raw_V=[0, 4096], V_digits=[4096, 6144],
                    raw_P=[10240, 1024], P_digits=[11264, 1536],
                    partial=[12800, 2304], meta=[15360, 1024],
                    O=[16384, 8192], output=[24576, 2048], consumer=[28672, 256]))
        for phase in self.allocations.values():
            intervals = sorted((start, start + size) for start, size in phase.values())
            if any(end > 32768 for _, end in intervals) or any(
                    a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
                raise ValueError("private scratch allocation")

    def packet(self, src, dst, n, sp, dp, deps=(), so=0, do=0, kind="data"):
        if n <= 0:
            raise ValueError("empty transfer")
        internal = src in ("M", "A") and dst in ("M0", "M1", "A0", "A1")
        header = 0 if internal and self.config["organization"] == "colocated_stream" else 64
        ends = []
        for off, size in chunks(n):
            read = self.memory(sp, size, so + off, (*deps, self.last_tx.get(src)),
                               label="packet-read " + kind)
            wire_bytes = header + ceildiv(size, 64) * 64
            wire = self.add("stream " + kind if header == 0 else "wire " + kind,
                            wire_bytes // 16, ("bus", src + "TX", dst + "RX"),
                            (read, self.last_rx.get(dst)), kind=kind, payload=size,
                            wire_bytes=wire_bytes, header_bytes=header)
            write = self.memory(dp, size, do + off, (wire,), True,
                                "packet-write " + kind)
            self.last_tx[src] = wire
            self.last_rx[dst] = write
            ends.append(write)
            packet = dict(kind=kind, src=src, dst=dst, payload=size,
                          wire_bytes=wire_bytes, header_bytes=header,
                          read=read, wire=wire, write=write)
            (self.streams if header == 0 else self.packets).append(packet)
            self.bytes["wire"] += wire_bytes
            self.bytes["wire_payload"] += size
            self.bytes["wire_" + kind] += wire_bytes
            self.bytes["header"] += header
        return ends

    def vector(self, label, elements, per_lane_ops, deps):
        self.operations[label + "_elements"] += elements
        return self.add(label, max(1, ceildiv(elements, 8) * per_lane_ops),
                        ("vector",), deps, elements=elements)

    def wide(self, label, elements, slots, deps):
        self.operations[label + "_elements"] += elements
        return self.add(label, max(1, ceildiv(elements, 8) * slots),
                        ("wide",), deps, elements=elements)

    def matrix(self, label, q, k, n, ma, mw, deps, a_offset=0, w_offset=0):
        # Operand ports remain occupied by the array feed for this entire node.
        self.operations["S8_MACs"] += q * k * n
        self.operations["matrix_calls"] += 1
        self.operations["matrix_operand_bytes"] += (q + n) * k
        return self.add(label, k + q + n - 2, ("matrix", ma, mw), deps,
                        rows=q, reduction=k, columns=n,
                        operand_read_bytes=(q + n) * k, a_port=ma, w_port=mw,
                        a_offset=a_offset, w_offset=w_offset)

    def operand_pack(self, label, elements, source_bytes, digits, source_offset,
                     destination_offset, deps):
        """Conservative scalar-indexed transpose/limb packing in single-port AC.

        Each raw element takes one16B read beat and each S8 output digit one
        byte-enabled16B write beat. Index/bit extraction is serialized on the
        same vector/control resources (1 scalar index op for8bit,6 for16bit).
        This deliberately avoids assuming a free multi-lane transpose network.
        It is an uncalibrated explicit implementation profile, not a lower bound.
        """
        read_n, write_n = elements * source_bytes, elements * digits
        if source_offset + read_n > 32768 or destination_offset + write_n > 32768:
            raise ValueError("operand pack capacity")
        scalar_ops = 1 if digits == 1 else 6
        self.bytes["memory_logical"] += read_n + write_n
        self.bytes["memory_physical"] += elements * (1 + digits) * 16
        self.operations[label + "_elements"] += elements
        return self.add(label, elements * (1 + digits + scalar_ops),
                        ("AC", "vector", "control"), deps,
                        pack_source_offset=source_offset, pack_source_bytes=read_n,
                        pack_destination_offset=destination_offset,
                        pack_destination_bytes=write_n,
                        pack_elements=elements, pack_digits=digits,
                        pack_scalar_ops=scalar_ops)


def _exp(g, elements, dependencies):
    g.operations["LUT_reads"] += elements
    # Two signed32 scores can require33 bits for their difference. The existing
    # wide resource performs this before vector clamp/index generation; neither
    # the difference nor the ROM address is supplied for free by the table.
    delta = g.wide("score delta33 subtract", elements, 4, dependencies)
    address = g.vector("exp delta clamp/index", elements, 4, (delta,))
    node = g.add("exp LUT one read port", elements * g.config["exp_ii"],
                 ("sfu", "LUT"), (address,), elements=elements)
    return node


def build(c):
    c = config(**{k: c[k] for k in ("group", "keys", "queries", "kv_bits", "exp_ii",
                                    "organization", "lut_step")}, rom_bytes=c["ROM_capacity_bytes"])
    T, q, H, d, b = c["keys"], c["queries"], c["heads"], c["dim"], c["kv_bits"] // 8
    digits = 1 if b == 1 else 3
    Kbase, Vbase = 0, T * d * b
    Qbase = 2 * T * d * b
    Mbase = Qbase + H * q * d
    meta_stride = 128 + d
    g = AttentionGraph(c, Mbase + H * meta_stride)
    done = None
    for head in range(H):
        start = g.add("head scratch lease begin", 1, ("control",), (done,), head=head)
        meta = g.packet("EXT", "S6", 64 + q * 6, "EXT", "S6", (start,),
                        Mbase + head * meta_stride, 0, "HEAD_META")
        qm = g.packet("S6", "A1", 64 + q * 6, "S6", "AC", meta,
                      0, 24128, "HEAD_META")
        qi = g.packet("EXT", "S7", q * d, "EXT", "S7", (start,),
                      Qbase + head * q * d, 0, "Q8")
        query = g.packet("S7", "M0", q * d, "S7", "MA0", qi, kind="Q8")
        ms = g.memory("AC", q * 4, 24448, (*qm,), True, "initialize score32 row max")
        ls = g.memory("AC", q * 8, 24480, (ms,), True, "initialize sum64 zero")
        previous = g.add("QK phase begin", 0, (), (*query, ls))
        for kb in range(0, T, 16):
            raw = g.packet("EXT", "S0", 16 * d * b, "EXT", "S0", (previous,),
                           Kbase + kb * d * b, 0, "Kraw")
            local = g.packet("S0", "A0", 16 * d * b, "S0", "AC", raw, 0, 0, "Kraw_to_pack")
            packed = g.operand_pack("K transpose/limb scalar pack", 16 * d, b, digits,
                                    0, 8192, local)
            loaded = []
            for digit in range(digits):
                woff = digit * 16 * d
                loaded += g.packet("A", "M1", 16 * d, "AC", "MW" + str(woff // 8192),
                                   (packed,), 8192 + woff, woff % 8192, "K_S8_limb")
            partials = []
            last = previous
            for digit in range(digits):
                mw = "MW" + str((digit * 16 * d) // 8192)
                execute = g.matrix("QK S8 limb", q, d, 16, "MA0", mw, (*loaded, last),
                                   w_offset=(digit * 16 * d) % 8192)
                last = g.memory("MC", q * 16 * 4, digit * q * 16 * 4,
                                (execute,), True, "QK partial write")
                partials.append(last)
            arrived = g.packet("M", "A0", digits * q * 16 * 4, "MC", "AC",
                               partials, 0, 20480, "QK_ACC32")
            read = g.memory("AC", digits * q * 16 * 4, 20480, arrived, label="QK merge read")
            param = g.memory("AC", 64 + q * 6, 24128, (read,), label="QK scale/mask read")
            merge = g.wide("QK limb align/merge64", q * 16, digits * 4, (param,))
            # d<=256 and Q8/K16 symmetric domains give |QK|<=
            # 256*127*32767<2^31. A compiled M31 therefore has a signed64
            # product. d256's coefficient is2^26 and can fuse into an exact
            # RNE shift. d128's M=94906266 has4 nonzero U7 digits;5 signed32
            # input digits give20 S8 products, each4 carry/shift/add slots.
            if d == 256:
                scaled = g.wide("QK power2 coefficient fused shift", q * 16, 4, (merge,))
            else:
                products = g.vector("QK32 M31 S8 limb products", q * 16, 20, (merge,))
                scaled = g.wide("QK M31 product64 combine", q * 16, 80, (products,))
            score = g.vector("score RNE/saturate/mask", q * 16, 4, (scaled,))
            store = g.memory("AC", q * 16 * 4, 21504, (score,), True, "score32Q12 write")
            r = g.memory("AC", q * 16 * 4, 21504, (store,), label="score32 max read")
            old = g.memory("AC", q * 4, 24448, (r,), label="row max32 read")
            maximum = g.vector("row max reduce", q * 16, 2, (old,))
            maximum = g.memory("AC", q * 4, 24448, (maximum,), True, "row max32 write")
            spills = []
            for row in range(q):
                spills += g.packet("A", "S4", 64, "AC", "S4", (store, maximum),
                                   21504 + row * 64, (row * T + kb) * 4, "SCORE32Q12")
            previous = g.add("score tile retired", 0, (), spills)

        # First exp pass accumulates U64/Q30 sums; each valid key is looked up.
        for row in range(q):
            active = T - q + row + 1
            for kb in range(0, active, 128):
                count = min(128, active - kb)
                data = g.packet("S4", "A0", count * 4, "S4", "AC", (previous,),
                                (row * T + kb) * 4, 0, "SCORE_SUM_PASS")
                read = g.memory("AC", count * 4, 0, data, label="sum score32 read")
                maximum = g.memory("AC", 4, 24448 + row * 4, (read,), label="sum max32 read")
                exp = _exp(g, count, (maximum,))
                ew = g.memory("AC", count * 4, 4096, (exp,), True, "exp32 scratch write")
                er = g.memory("AC", count * 4, 4096, (ew,), label="exp32 scratch read")
                sr = g.memory("AC", 8, 24480 + row * 8, (er,), label="sum64 read")
                summed = g.wide("U64 exp sum", count, 4, (sr,))
                previous = g.memory("AC", 8, 24480 + row * 8, (summed,), True, "sum64 write")

        p_stores = []
        for row in range(q):
            active = T - q + row + 1
            reset = g.memory("AC", 4, 24512 + row * 4, (previous,), True, "Psum32 reset")
            previous = reset
            for kb in range(0, active, 128):
                count = min(128, active - kb)
                data = g.packet("S4", "A0", count * 4, "S4", "AC", (previous,),
                                (row * T + kb) * 4, 0, "SCORE_NORMALIZE_PASS")
                read = g.memory("AC", count * 4, 0, data, label="normalize score32 read")
                maximum = g.memory("AC", 4, 24448 + row * 4, (read,), label="normalize max32 read")
                exp = _exp(g, count, (maximum,))
                ew = g.memory("AC", count * 4, 4096, (exp,), True, "normalize exp write")
                er = g.memory("AC", count * 4, 4096, (ew,), label="normalize exp read")
                sr = g.memory("AC", 8, 24480 + row * 8, (er,), label="normalize sum64 read")
                divide = g.add("U64 restoring normalize divide", count * 64, ("sfu", "wide"),
                               (sr,), elements=count, iterations=64)
                g.operations["normalize_divisions"] += count
                rounded = g.vector("P15 RNE/saturate", count, 4, (divide,))
                psr = g.memory("AC", 4, 24512 + row * 4, (rounded,), label="Psum32 read")
                ps = g.wide("Psum32 accumulate", count, 2, (psr,))
                ps = g.memory("AC", 4, 24512 + row * 4, (ps,), True, "Psum32 write")
                out = g.memory("AC", count * 2, 0, (ps,), True, "P15 scratch write")
                published = g.packet("A", "S5", count * 2, "AC", "S5", (out,),
                                     0, (row * T + kb) * 2, "P15_UNCOMMITTED")
                p_stores.extend(published)
                previous = published[-1]
            # q4's causal last tile also has masked tail entries needed by PV.
            if active < T:
                zeros = g.memory("AC", (T - active) * 2, 0, (previous,), True, "masked P15 zero fill")
                z = g.packet("A", "S5", (T - active) * 2, "AC", "S5", (zeros,),
                             0, (row * T + active) * 2, "P15_MASK_ZERO")
                previous = z[-1]
        ps = g.memory("AC", q * 4, 24512, (previous,), label="Psum guard read")
        guard = g.vector("Psum budget compare", q, 2, (ps,))
        accepted = g.add("P15 profile/epoch publish after guard", 1, ("control",),
                         (guard, *p_stores), budget=[32768 + ceildiv(T - q + r + 1, 2) + 1
                                                   for r in range(q)])
        pvmeta = g.packet("S6", "A1", 64 + q * 6, "S6", "AC", (accepted,),
                          0, 15360, "PV_HEAD_META")
        previous = pvmeta[-1]
        for ob in range(0, d, 16):
            # A single complete q x d wide O allocation is reserved even though
            # channel tiles are computed sequentially.
            oo = 16384 + ob * q * 8
            init = g.memory("AC", q * 16 * 8, oo, (previous,), True, "PV O64 initialize")
            previous = init
            for kb in range(0, T, 128):
                p_load = []
                for row in range(q):
                    p_load += g.packet("S5", "A0", 256, "S5", "AC", (previous,),
                                       (row * T + kb) * 2, 10240 + row * 256, "P15")
                pr = g.memory("AC", q * 256, 10240, p_load, label="P15 unpack read")
                pu = g.vector("nonnegative P15 limb unpack", q * 128, 5, (pr,))
                pw = g.memory("AC", 3 * q * 128, 11264, (pu,), True, "P limb write")
                p_m = g.packet("A", "M0", 3 * q * 128, "AC", "MA1", (pw,),
                               11264, 0, "P_S8_limbs")
                v_load = []
                for feature in range(16):
                    v_load += g.packet("EXT", "S2", 128 * b, "EXT", "S2", (previous,),
                                       Vbase + ((ob + feature) * T + kb) * b,
                                       feature * 128 * b, "Vraw_feature_major")
                vl = g.packet("S2", "A0", 2048 * b, "S2", "AC", v_load, 0, 0, "Vraw_to_pack")
                vw = g.operand_pack("V transpose/limb scalar pack", 2048, b, digits, 0, 4096, vl)
                v_m = g.packet("A", "M1", 2048 * digits, "AC", "MW0", (vw,),
                               4096, 0, "V_S8_limbs")
                partials = []
                last = previous
                for pi in range(3):
                    for vi in range(digits):
                        execute = g.matrix("PV S8 limb", q, 128, 16, "MA1", "MW0",
                                           (*p_m, *v_m, last),
                                           a_offset=pi * q * 128, w_offset=vi * 2048)
                        index = pi * digits + vi
                        last = g.memory("MC", q * 16 * 4, index * q * 16 * 4,
                                        (execute,), True, "PV partial write")
                        partials.append(last)
                arrived = g.packet("M", "A0", 3 * digits * q * 16 * 4, "MC", "AC",
                                   partials, 0, 12800, "PV_ACC32")
                read = g.memory("AC", 3 * digits * q * 16 * 4, 12800, arrived,
                                label="PV limb merge read")
                old = g.memory("AC", q * 16 * 8, oo, (read,), label="PV O64 read")
                meta = g.memory("AC", 64 + q * 6, 15360, (old,), label="PV units/guard read")
                merged = g.wide("PV shift/add64", q * 16, 3 * digits * 4, (meta,))
                previous = g.memory("AC", q * 16 * 8, oo, (merged,), True, "PV O64 update")
            # Final scale is selected by the separate numeric contract; metadata
            # and rounding service are present but this DAG computes no values.
            out_meta = g.packet("EXT", "S6", 16, "EXT", "S6", (previous,),
                                Mbase + head * meta_stride + 128 + ob, 128, "O_RQ_META")
            out_meta = g.packet("S6", "A1", 16, "S6", "AC", out_meta,
                                128, 15616, "O_RQ_META")
            r = g.memory("AC", q * 16 * 8, oo, out_meta, label="final O64 read")
            prm = g.memory("AC", 16, 15616, (r,), label="final O dyadic exponent read")
            shifted = g.wide("O64 final dyadic shift", q * 16, 4, (prm,))
            rq = g.vector("O16 final RNE/saturate", q * 16, 4, (shifted,))
            previous = g.memory("AC", q * 16 * 2, 24576 + ob * q * 2,
                                (rq,), True, "attention O16 complete tile")
        read = g.memory("AC", q * d * 2, 24576, (previous,), label="consumer O16 read")
        consumed = g.wide("integer row sum consumer64", q * d, 4, (read,))
        result = g.memory("AC", q * 8, 28672, (consumed,), True, "consumer RESULT64 write")
        done = g.packet("A", "S7", q * 8, "AC", "S7", (result,),
                        28672, 8192 + head * q * 8, "RESULT64")[-1]
        g.leases.append(dict(kind="attention_head", slot=0, start=start, end=done))
    g.add("all GQA heads RESULT complete", 0, (), (done,), heads=H)
    g.expected = dict(heads=H, score_elements=H * q * T,
                      valid_elements=H * sum(T - q + row + 1 for row in range(q)),
                      QK_matrix_calls=H * (T // 16) * digits,
                      PV_matrix_calls=H * (d // 16) * (T // 128) * 3 * digits,
                      K_backing_bytes=H * T * d * b,
                      V_backing_bytes=H * T * d * b,
                      Q_backing_bytes=H * q * d,
                      result_bytes=H * q * 8, output_elements=H * q * d,
                      GQA_KV_reload_factor=H,
                      Psum_guard_bytes_per_active_query=4,
                      exp_passes=2, PV_S8_products=3 * digits)
    return g


def audit(g, scheduled):
    """Base interval audit plus independent mixed-protocol/semantic checks."""
    base = audit_schedule(g, scheduled)
    packets = g.packets + g.streams
    intervals = defaultdict(list)
    for p in packets:
        if not (0 < p["payload"] <= 1984):
            raise AssertionError("payload/credit")
        expected = p["header_bytes"] + ceildiv(p["payload"], 64) * 64
        if p["header_bytes"] not in (0, 64) or p["wire_bytes"] != expected or expected > 2048:
            raise AssertionError("packet length/header/credit")
        if p["header_bytes"] == 0 and not (
                g.config["organization"] == "colocated_stream" and p["src"] in ("A", "M")
                and p["dst"] in ("A0", "A1", "M0", "M1")):
            raise AssertionError("unqualified internal stream")
        read, wire, write = (g.nodes[p[k]] for k in ("read", "wire", "write"))
        if read["bytes"] != p["payload"] or write["bytes"] != p["payload"]:
            raise AssertionError("packet source/destination byte span")
        if wire["duration"] != p["wire_bytes"] // 16 or "bus" not in wire["resources"]:
            raise AssertionError("payload must occupy the shared bus")
        if p["read"] not in wire["deps"] or p["wire"] not in write["deps"]:
            raise AssertionError("packet dependency")
        intervals[(p["src"], "TX")].append((scheduled["trace"][p["read"]][0],
                                           scheduled["trace"][p["wire"]][1]))
        intervals[(p["dst"], "RX")].append((scheduled["trace"][p["wire"]][0],
                                           scheduled["trace"][p["write"]][1]))
    for endpoint, events in intervals.items():
        events.sort()
        if any(a[1] > b[0] for a, b in zip(events, events[1:])):
            raise AssertionError("mixed protocol FIFO credit " + str(endpoint))
    head_leases = [(scheduled["trace"][x["start"]][0], scheduled["trace"][x["end"]][1])
                   for x in g.leases]
    if any(a[1] > b[0] for a, b in zip(head_leases, head_leases[1:])):
        raise AssertionError("head scratch lease")
    c = g.config
    e = g.expected
    actual = Counter()
    for node in g.nodes:
        if "pack_elements" in node:
            if (node["pack_source_offset"] + node["pack_source_bytes"] > 32768
                    or node["pack_destination_offset"] + node["pack_destination_bytes"] > 32768):
                raise AssertionError("scalar operand pack capacity")
            if ("AC" not in node["resources"] or "vector" not in node["resources"]
                    or node["duration"] != node["pack_elements"] *
                    (1 + node["pack_digits"] + node["pack_scalar_ops"])):
                raise AssertionError("operand transpose/packing is not free")
        if "a_port" in node:
            if (node["a_offset"] + node["rows"] * node["reduction"] > g.sizes[node["a_port"]]
                    or node["w_offset"] + node["columns"] * node["reduction"] > g.sizes[node["w_port"]]):
                raise AssertionError("matrix operand capacity")
        if node["label"] == "QK S8 limb":
            actual["QK_matrix_calls"] += 1
        elif node["label"] == "PV S8 limb":
            actual["PV_matrix_calls"] += 1
        elif node["label"] == "exp LUT one read port":
            actual["exp_elements"] += node["elements"]
            if node["duration"] != node["elements"] * c["exp_ii"]:
                raise AssertionError("one ROM read port")
        elif node["label"] == "score delta33 subtract":
            actual["delta_elements"] += node["elements"]
        elif node["label"] == "exp delta clamp/index":
            actual["index_elements"] += node["elements"]
        elif node["label"] == "U64 restoring normalize divide":
            actual["divide_elements"] += node["elements"]
            if node["duration"] != 64 * node["elements"]:
                raise AssertionError("serial unsigned64 division")
    if actual["QK_matrix_calls"] != e["QK_matrix_calls"] or actual["PV_matrix_calls"] != e["PV_matrix_calls"]:
        raise AssertionError("missing GQA heads or S8 limb stages")
    if actual["exp_elements"] != 2 * e["valid_elements"] or actual["divide_elements"] != e["valid_elements"]:
        raise AssertionError("missing softmax pass or head")
    if actual["delta_elements"] != actual["exp_elements"] or actual["index_elements"] != actual["exp_elements"]:
        raise AssertionError("missing exp delta/index service")
    for kind, expected in (("Kraw", e["K_backing_bytes"]),
                           ("Vraw_feature_major", e["V_backing_bytes"]),
                           ("Q8", e["Q_backing_bytes"]), ("RESULT64", e["result_bytes"])):
        values = [p for p in packets if p["kind"] == kind and
                  (p["src"] == "EXT" or kind == "RESULT64")]
        if sum(p["payload"] for p in values) != expected:
            raise AssertionError("backing/result accounting " + kind)
    if sum(p["payload"] for p in packets if p["kind"] == "SCORE32Q12") != e["score_elements"] * 4:
        raise AssertionError("score32 spill accounting")
    for kind in ("SCORE_SUM_PASS", "SCORE_NORMALIZE_PASS"):
        if sum(p["payload"] for p in packets if p["kind"] == kind) != e["valid_elements"] * 4:
            raise AssertionError("score32 two-pass accounting")
    return {**base, "packets": len(packets), "internal_stream_fragments": len(g.streams),
            "mixed_protocol_credit": "PASS", "all_GQA_heads_and_passes": "PASS",
            "scratch_leases": len(head_leases)}


def run_case(c, policy):
    g = build(c)
    result = g.schedule(policy)
    checked = audit(g, result)
    compact = dict(config=c, policy=policy, cycles=result["cycles"],
                   busy=result["busy"], traffic=dict(g.bytes), operations=dict(g.operations),
                   expected=g.expected, audit=checked,
                   hardware_performance_accepted=False, numeric_quality_accepted=False)
    return g, result, compact


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_binding(binding):
    """Verify supplied source SHA values before creating outputs and at finish."""
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    dependency_sha = hashlib.sha256(_MODEL_PATH.read_bytes()).hexdigest()
    if not isinstance(binding, dict):
        raise ValueError("binding must be an object")
    if binding:
        commit = binding.get("source_commit", "")
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            raise ValueError("binding requires a40-hex source_commit")
        supplied_code = binding.get("service_sha256", binding.get("code_sha256"))
        if supplied_code != code_sha:
            raise ValueError("binding service/code SHA256 missing or mismatched")
        if binding.get("dependency_sha256") != dependency_sha:
            raise ValueError("binding dependency SHA256 missing or mismatched")
    return dict(status="VERIFIED" if binding else "NOT_PROVIDED",
                code_sha256=code_sha, dependency_sha256=dependency_sha)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binding", type=Path)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise FileExistsError("new output directory required")
    binding = json.loads(args.binding.read_text(encoding="utf-8-sig")) if args.binding else {}
    if args.binding and not binding:
        raise ValueError("empty supplied binding")
    bound_sources = verify_binding(binding)
    args.out.mkdir(parents=True)
    cases, witnesses, pairs = [], [], []
    for group in GROUPS:
        for T in (128, 1024):
            for q in (1, 4):
                for kv in (8, 16):
                    for ii in (1, 8, 32):
                        by_org = {}
                        for org in ORGANIZATIONS:
                            by_policy = []
                            for policy in ("fifo", "critical"):
                                c = config(group, T, q, kv, ii, org)
                                g, scheduled, summary = run_case(c, policy)
                                cases.append(summary)
                                by_policy.append(summary)
                                if group == "gemma_local0" and T == 128 and q == 1 and kv == 16 and ii == 8 and policy == "critical":
                                    filename = "witness-" + org + ".json"
                                    _write_json(args.out / filename,
                                                dict(config=c, nodes=g.nodes, packets=g.packets,
                                                     streams=g.streams, leases=g.leases,
                                                     sizes=g.sizes, expected=g.expected,
                                                     scheduled=scheduled))
                                    witnesses.append(filename)
                            by_org[org] = min(by_policy, key=lambda x: x["cycles"])
                        a, b, s = (by_org[o] for o in ORGANIZATIONS)
                        if a["cycles"] != b["cycles"] or a["traffic"] != b["traffic"]:
                            raise AssertionError("physical label alone changed the protocol")
                        if a["expected"] != s["expected"] or a["operations"] != s["operations"]:
                            raise AssertionError("colocation changed workload or hardware work")
                        pairs.append(dict(group=group, keys=T, queries=q, kv_bits=kv, exp_ii=ii,
                                          optimized_split=a["cycles"], optimized_control=b["cycles"],
                                          optimized_stream=s["cycles"],
                                          stream_reduction_fraction=(a["cycles"] - s["cycles"]) / a["cycles"],
                                          stream_wire_bytes_saved=a["traffic"]["wire"] - s["traffic"]["wire"],
                                          chosen_policies={o: by_org[o]["policy"] for o in ORGANIZATIONS}))
    _write_json(args.out / "cases.json", cases)
    _write_json(args.out / "pairs.json", pairs)
    _write_json(args.out / "protocol.json", dict(scope=__doc__, groups=GROUPS,
                inventory=inventory(config()), organizations=ORGANIZATIONS,
                unsupported_old_inventory=[dict(step=128, required=lut_bytes(128), capacity=8192,
                                                status="REJECT_LUT_CAPACITY"),
                                            dict(step=256, required=lut_bytes(256), capacity=16384,
                                                 status="REJECT_LUT_CAPACITY")],
                precision="Q8;KV8/16;score I32Q12;exp U32Q30;sum U64Q30;P15;PV64;O16 dyadic;RESULT64",
                score_coefficients={"d128_M_Q30": 94906266, "d128_U7_digits": [26, 79, 32, 45, 0],
                                    "d128_S8_products_per_output": 20,
                                    "d256_M_Q30": 67108864, "d256_power2_fused_shift": True},
                arithmetic_scope="bounded Q8/KV16 symmetric codes; checked-format QK32 then M31 product64; final O uses dyadic exponents; range/epoch guards assumed accepted, no numeric values computed",
                exclusions=["unverified numeric/quality implementation", "RTL/PPA/target timing",
                            "online attention", "KV append/producer layout formation", "full model",
                            "optimized GQA KV reuse; reloaded per head here"],
                scheduler="fifo/critical separately optimized; not globally optimal",
                scratch_allocations=AttentionGraph(config(), 1).allocations))
    files = {}
    for p in sorted(args.out.iterdir()):
        data = p.read_bytes()
        files[p.name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    if verify_binding(binding) != bound_sources:
        raise RuntimeError("source files changed during execution")
    manifest = dict(schema="conditional-attention-service/1", status="PASS", binding=binding,
                    source_commit=binding.get("source_commit", "unverified"),
                    source_verification=bound_sources,
                    code_sha256=bound_sources["code_sha256"],
                    dependency_path="project/experiments/rq_ports/model.py",
                    dependency_sha256=bound_sources["dependency_sha256"],
                    cases=len(cases), optimized_pairs=len(pairs), witnesses=witnesses, files=files,
                    hardware_performance_accepted=False, numeric_quality_accepted=False)
    _write_json(args.out / "manifest.json", manifest)
    print(json.dumps({"status": "PASS", "cases": len(cases), "pairs": len(pairs),
                      "output": str(args.out), "hardware_performance_accepted": False}))


if __name__ == "__main__":
    main()
