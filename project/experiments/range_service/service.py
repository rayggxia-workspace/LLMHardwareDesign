"""Finite V/R/S event schedules; conditional CPU model, never target PPA.

All arithmetic profiles have eight TOTAL S8 lanes and one shared sqrt/divider.
Full-hidden input norm and recurrent update are independent captured streams.
Fixed slots, packet FIFOs, single RW ports and external backing are explicit.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import sys


SCHEMA = "issue68-service/1"
LANES = {"shared8": (8, 8), "shared2_6": (2, 6), "shared4_4": (4, 4), "shared6_2": (6, 2), "split2_6": (2, 6),
         "split4_4": (4, 4), "split6_2": (6, 2)}
K = V = 128
H = 2560
PACKET = 1984
HEADER = 32


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def descriptor(p):
    p = Path(p)
    return {"bytes": p.stat().st_size, "sha256": sha(p)}


def ceildiv(a, b):
    return (a + b - 1) // b


def beats(n):
    return ceildiv(n, 16)


def mulslots(d1, d2):
    """One S8 product plus ten lane slots for each checked64 merge."""
    products = d1 * d2
    return products + (products - 1) * 10


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def config(organization="shared8", tile=16, norm_route="reread", ext_ii=1,
           strategy="fifo", state_bits=32):
    if organization not in LANES or tile not in (16, 32):
        raise ValueError("unsupported organization/tile")
    if norm_route not in ("reread", "spill") or ext_ii not in (1, 16):
        raise ValueError("unsupported norm/backing profile")
    if strategy not in ("fifo", "critical") or state_bits not in (16, 32):
        raise ValueError("unsupported strategy/precision")
    return dict(organization=organization, tile=tile, norm_route=norm_route,
                ext_ii=ext_ii, strategy=strategy, state_bits=state_bits)


def inventory(c):
    vl, rl = LANES[c["organization"]]
    caps = {"BUS": 1, "SFU": 1, "CTRL": 1, "MATRIX": 1}
    sizes = {"V": 16384, "R": 32768, "M": 32768,
             **{"S" + str(i): 32768 for i in range(8)},
             "EXT": 128 * 1024 * 1024}
    for bank in sizes:
        caps["PORT:" + bank] = 1
        for direction in ("TX", "RX"):
            caps["EP:" + bank + ":" + direction] = 1
            caps["FIFO:" + bank + ":" + direction] = 2048
    for i in range(8):
        caps["LANE:" + str(i)] = 1
    return dict(capacities=caps, bank_sizes=sizes, bus_bits=128,
                bank_ports="one 128-bit RW, cannot read and write together",
                total_S8_lanes=8, V_lanes=vl, R_lanes=rl,
                S8_lowering="signed16=3 signed8 digits; signed32/unsigned32=5; checked64=10; each product after first requires10-slot checked64 shift/add merge; each RNE/shift/add/compare10 slots",
                SFU="one shared instance, sqrt32/div64 iteration slots",
                active_contexts=2,
                lane_fairness="sharedX_Y and splitX_Y identical static lane assignments, routes and two contexts; shared8 uses a separate coarse8-lane issue granularity",
                matrix="one16x16 S8 auxiliary proxy,32KiB scratch",
                external_beat_cycles=c["ext_ii"],
                external_timing="declared sensitivity, not measured latency/bandwidth",
                FIFO_bytes_each=2048, payload_limit=PACKET, header_bytes=HEADER,
                finite_backing_bytes=sizes["EXT"],
                commit="double-buffered backing generation; all heads/tile writes and full-head output barrier precede pointer flip",
                physical_claim=False)


class Graph:
    def __init__(self, c):
        self.config = copy.deepcopy(c)
        self.inventory = inventory(c)
        self.nodes = []
        self.allocations = []
        self.stream_tail = {}
        self.counters = Counter()
        self._slots()

    def slot(self, name, bank, offset, size):
        if size <= 0 or offset < 0 or offset + size > self.inventory["bank_sizes"][bank]:
            raise ValueError("buffer capacity: " + name)
        for a in self.allocations:
            if a["bank"] == bank and max(a["offset"], offset) < min(a["offset"] + a["bytes"], offset + size):
                raise ValueError("buffer overlap: " + name)
        self.allocations.append(dict(id=name, bank=bank, offset=offset, bytes=size,
                                     lifetime="whole schedule; conservative fixed slot"))

    def _slots(self):
        b = self.config["state_bits"] // 8
        tile = self.config["tile"]
        n = K * tile * b
        self.slot("V.X16", "V", 0, H * 2)
        self.slot("V.gamma_tile", "V", 5120, 512)
        self.slot("V.norm_tile", "V", 5632, 2048)
        self.slot("V.meta", "V", 7680, 1024)
        self.slot("V.A8", "V", 8704, 2752)
        self.slot("V.proxy", "V", 11456, 4096)
        self.slot("R.old", "R", 0, n)
        self.slot("R.aux", "R", 16384, 8192)
        if n * 2 + 8192 <= 32768 and n <= 8192:
            self.slot("R.new", "R", 8192, n)
            self.new_bank = "R"
            self.new_slot = "R.new"
        else:
            self.slot("R.new_shadow", "S4", 0, n)
            self.new_bank = "S4"
            self.new_slot = "R.new_shadow"
        self.slot("source.mixed", "S0", 0, 25600)
        self.slot("source.meta", "S0", 25600, 2048)
        self.slot("source.gamma", "S1", 0, 10240)
        self.slot("aligned.spill", "S1", 10240, 20480)
        self.slot("R.stage_old", "S2", 0, 16384)
        self.slot("R.stage_new", "S3", 0, 16384)
        self.slot("R.output", "S5", 0, 2048)
        self.slot("proxy.source", "S6", 0, 16384)
        self.slot("proxy.result", "S7", 0, 16384)
        self.slot("M.proxy", "M", 0, 32768)
        # Full model state lives here; only two heads are actively paged.
        model_bytes = 24 * 32 * K * V * b
        self.slot("backing.model_old", "EXT", 0, model_bytes)
        self.slot("backing.proposal", "EXT", model_bytes, 2 * K * V * b)
        self.slot("backing.trial", "EXT", model_bytes + 2 * K * V * b, 2 * K * V * b)
        self.slot("backing.consumer_input", "EXT", model_bytes + 4 * K * V * b, 32 * 25600 + 10240)
        self.slot("backing.R_inputs", "EXT", model_bytes + 4 * K * V * b + 32 * 25600 + 10240, 256 * 2048)
        self.slot("backing.descriptor", "EXT", model_bytes + 4 * K * V * b + 32 * 25600 + 10240 + 256 * 2048, 256)
        self.slot("backing.raw_initial", "EXT", model_bytes + 4 * K * V * b + 32 * 25600 + 10240 + 256 * 2048 + 256, 2 * K * V * b)
        self.committed_slot = "backing.model_old"
        self.proposal_slot = "backing.proposal"

    def add(self, kind, deps=(), duration=1, reservations=(), meta=None):
        duration = int(duration)
        if duration < 1 or any(d >= len(self.nodes) or d < 0 for d in deps):
            raise ValueError("node duration/dependency")
        r = [dict(x) for x in reservations]
        for x in r:
            if x["offset"] < 0 or x["duration"] < 1 or x["offset"] + x["duration"] > duration:
                raise ValueError("reservation bounds")
            if not 0 < x["amount"] <= self.inventory["capacities"][x["resource"]]:
                raise ValueError("resource request")
        i = len(self.nodes)
        self.nodes.append(dict(id=i, kind=kind, deps=sorted(set(deps)), duration=duration,
                               reservations=r, meta=meta or {}))
        self.counters[kind] += 1
        return i

    @staticmethod
    def res(resource, offset, duration, amount=1):
        return dict(resource=resource, offset=offset, duration=duration, amount=amount)

    def control(self, kind, deps, meta=None, cycles=1):
        return self.add(kind, deps, cycles, [self.res("CTRL", 0, cycles)], meta)

    def descriptor_update(self, kind, deps, count, meta=None):
        rw = beats(count)
        cycles = 20
        return self.add(kind, deps, 2 * rw + cycles,
                        [self.res("PORT:R", 0, rw), self.res("CTRL", rw, cycles),
                         self.res("PORT:R", rw + cycles, rw)],
                        dict(meta or {}, descriptor_bytes=count, descriptor_object="R.aux",
                             descriptor_object_offset=4096,
                             descriptor_read_beats=rw, descriptor_write_beats=rw))

    def packet(self, src, dst, n, deps=(), meta=None, src_object=None, dst_object=None):
        if src == dst or n <= 0:
            raise ValueError("packet route/bytes")
        tail = list(deps)
        parts = []
        for offset in range(0, n, PACKET):
            payload = min(PACKET, n - offset)
            a = beats(payload) * (self.config["ext_ii"] if src == "EXT" else 1)
            wire = beats(payload + HEADER)
            z = beats(payload) * (self.config["ext_ii"] if dst == "EXT" else 1)
            dur = a + wire + z
            requests = [self.res("PORT:" + src, 0, a), self.res("BUS", a, wire),
                        self.res("PORT:" + dst, a + wire, z)]
            for bank, direction in ((src, "TX"), (dst, "RX")):
                requests += [self.res("EP:" + bank + ":" + direction, 0, dur),
                             self.res("FIFO:" + bank + ":" + direction, 0, dur, payload)]
            m = dict(meta or {}, src=src, dst=dst, payload_bytes=payload,
                     wire_bytes=beats(payload + HEADER) * 16,
                     object_offset=offset, src_object=src_object, dst_object=dst_object)
            m["src_offset"] = m.get("src_object_offset", 0) + offset
            m["dst_offset"] = m.get("dst_object_offset", 0) + offset
            node = self.add("packet", tail, dur, requests, m)
            tail = [node]
            parts.append(node)
            self.counters["payload_bytes"] += payload
            self.counters["wire_bytes"] += beats(payload + HEADER) * 16
        return parts[-1]

    def math(self, domain, operation, work, read_bytes, write_bytes, deps,
             meta=None, bank=None, sfucycles=0):
        bank = bank or domain
        vl, rl = LANES[self.config["organization"]]
        lanes = vl if domain == "V" else rl
        if self.config["organization"] == "shared8":
            lane_ids = list(range(8))
        else:
            lane_ids = list(range(vl)) if domain == "V" else list(range(vl, 8))
        rd, wr = beats(read_bytes), beats(write_bytes)
        compute = max(1, ceildiv(work, lanes))
        sfu = sfucycles
        duration = rd + compute + sfu + wr
        r = []
        if rd:
            r.append(self.res("PORT:" + bank, 0, rd))
        for lane in lane_ids:
            r.append(self.res("LANE:" + str(lane), rd, compute))
        if sfu:
            r.append(self.res("SFU", rd + compute, sfu))
        if wr:
            r.append(self.res("PORT:" + bank, rd + compute + sfu, wr))
        m = dict(meta or {}, domain=domain, operation=operation, lane_work=work,
                 lanes=lanes, read_bytes=read_bytes, write_bytes=write_bytes,
                 SFU_iterations=sfucycles, bank=bank)
        return self.add("math", deps, duration, r, m)


def build_norm(g, row, deps):
    m = dict(stream="norm", row=row, hidden=H, precision="X16/normQ20/A8K128",
             scale_epoch="saved dynamic row units; actual integer norms03 units fingerprinted")
    tail = list(deps)
    # Input backing contains separate code/unit planes. Explicitly pack each
    # K128 block into S0 as [128*I64,128*I16], charging both packets and address
    # generation. No contradictory SoA scan / AoS contiguous read assumption.
    for tile in range(20):
        p = g.control("norm_source_layout_address", tail, dict(m, tile=tile), cycles=2)
        p = g.packet("EXT", "S0", 1024, [p],
                     dict(m, tile=tile, operation="load_mixed_code_plane",
                          src_object_offset=row * 25600 + tile * 1024,
                          dst_object_offset=tile * 1280), "backing.consumer_input", "source.mixed")
        p = g.packet("EXT", "S0", 256, [p],
                     dict(m, tile=tile, operation="load_mixed_unit_plane",
                          src_object_offset=row * 25600 + 20480 + tile * 256,
                          dst_object_offset=tile * 1280 + 1024), "backing.consumer_input", "source.mixed")
        tail = [p]
    tail = tail[-1]
    # The row's finest unit must be known BEFORE any aligned tile is spilled.
    # S0 layout is20 K128 blocks: [128*I64 codes,128*I16 units].
    # This common unit-only prepass is real SRAM/bus/lane traffic, not free
    # future knowledge used to align a tile that has already left V.
    for tile in range(20):
        tail = g.packet("S0", "V", 256, [tail],
                        dict(m, tile=tile, operation="unit_prepass", src_object_offset=tile * 1280 + 1024),
                        "source.mixed", "V.norm_tile")
        tail = g.math("V", "unit_min_scan", 128 * 10, 256, 16, [tail], dict(m, tile=tile))
    tail = g.control("full_hidden_finest_unit", [tail], m)
    # A scan is a complete H dependency. It may stream through a fixed tile.
    for tile in range(20):
        tail = g.packet("S0", "V", 1280, [tail], dict(m, tile=tile, operation="max_scan", src_object_offset=tile * 1280), "source.mixed", "V.norm_tile")
        tail = g.math("V", "align_max", 128 * 20, 1280,
                      1024 if g.config["norm_route"] == "spill" else 16,
                      [tail], dict(m, tile=tile))
        if g.config["norm_route"] == "spill":
            tail = g.packet("V", "S1", 1024, [tail], dict(m, tile=tile, operation="aligned_spill", dst_object_offset=tile * 1024), "V.norm_tile", "aligned.spill")
    tail = g.control("full_hidden_max", [tail], m)
    for tile in range(20):
        if g.config["norm_route"] == "reread":
            tail = g.packet("S0", "V", 1280, [tail], dict(m, tile=tile, operation="reread_mixed", src_object_offset=tile * 1280), "source.mixed", "V.norm_tile")
            work = 128 * (20 + 10 + mulslots(3, 3) + 10)
        else:
            tail = g.packet("S1", "V", 1024, [tail], dict(m, tile=tile, operation="read_aligned", src_object_offset=tile * 1024), "aligned.spill", "V.norm_tile")
            work = 128 * (10 + mulslots(3, 3) + 10)
        tail = g.math("V", "X16_RNE_square_sum", work, (1280 if g.config["norm_route"] == "reread" else 1024) + 16,
                      256, [tail], dict(m, tile=tile))
    tail = g.math("V", "U64_den_sqrt_div", 100, 32, 16, [tail], m, sfucycles=96)
    for tile in range(20):
        tail = g.packet("S1", "V", 512, [tail], dict(m, tile=tile, operation="gamma_stream", src_object_offset=tile * 512), "source.gamma", "V.gamma_tile")
        tail = g.math("V", "norm_gamma", 128 * (mulslots(3, 5) + mulslots(5, 5) + 20), 256 + 512 + 32, 512,
                      [tail], dict(m, tile=tile))
        tail = g.math("V", "fresh_A8K128", 128 * 30, 512, 128 + 1, [tail], dict(m, tile=tile))
    tail = g.packet("V", "M", H + H // 128 + 32, [tail],
                    dict(m, operation="publish_fresh_A8", codes_bytes=H, exponent_bytes=H // 128, descriptor_bytes=32), "V.A8", "M.proxy")
    # One bounded FFN GEMM and one attention proxy, same work for all candidates.
    tail = g.packet("S6", "M", 4096, [tail], dict(m, operation="FFN_proxy_weight"), "proxy.source", "M.proxy")
    tail = g.add("matrix_proxy", [tail], 4096, [g.res("MATRIX", 0, 4096), g.res("PORT:M", 0, 4096)],
                 dict(m, operations="16x16x4096 S8 MAC; bounded proxy only"))
    tail = g.packet("M", "V", 4096, [tail], dict(m, operation="FFN_proxy_output"), "M.proxy", "V.proxy")
    tail = g.math("V", "FFN_requant_proxy", 1024 * 30, 4096, 1024, [tail], m)
    tail = g.math("V", "attention_reduction_proxy", 1024 * 20, 4096, 1024, [tail], m,
                  sfucycles=64)
    return g.packet("V", "S7", 2048, [tail], dict(m, operation="proxy_sink"), "V.proxy", "proxy.result")


def recurrent_tile(g, token, attempt, head, tile, deps, do_output=False, epoch=0):
    tv = g.config["tile"]
    b = g.config["state_bits"] // 8
    cells = K * tv
    n = cells * b
    ds = 5 if b == 4 else 3
    m = dict(stream="R", token=token, attempt=attempt, head=head, tile=tile,
             K=K, Vtile=tv, state_bits=b * 8, decay_bits=31,
             scale_epoch=epoch, complete_K=True,
             proposal_arithmetic="checked I64 then immediate per-cell range flag OR",
             proposal_storage_bits=b * 8,
             invalid_cell_storage="saturate only unpublished shadow; whole token discarded on failed group guard; never consumed by output")
    backing_offset = (head * K * V + tile * cells) * b
    tail = g.packet("EXT", "S2", n, deps, dict(m, operation="page_committed_or_trial_old", src_object_offset=backing_offset),
                    g.committed_slot if attempt == 0 else "backing.trial", "R.stage_old")
    tail = g.packet("S2", "R", n, [tail], dict(m, operation="load_old_tile"), "R.stage_old", "R.old")
    tail = g.math("R", "decay_RNE_completeK_pred", cells * (mulslots(ds, 5) + mulslots(ds, 3) + 20) + tv * 10, n + 512 + 16, n + tv * 8,
                  [tail], m)
    tail = g.math("R", "delta_beta_RNE", tv * (mulslots(10, 3) + 30), tv * 16, tv * 8, [tail], m)
    if g.new_bank == "R":
        tail = g.math("R", "outer_RNE_guard", cells * (mulslots(3, 10) + 30), n + tv * 8 + 256, n,
                      [tail], m)
    else:
        # The proposed V32 tile cannot coexist with old+aux in R. Generate
        # <=1KiB fragments in the declared aux slot and pay the bus to S4.
        for chunk in range(ceildiv(cells, 256)):
            cc = min(256, cells - chunk * 256)
            tail = g.math("R", "outer_RNE_guard_fragment", cc * (mulslots(3, 10) + 30), cc * b + tv * 8 + 256,
                          cc * b, [tail], dict(m, chunk=chunk))
            tail = g.packet("R", "S4", cc * b, [tail], dict(m, chunk=chunk, operation="shadow_fragment", src_object_offset=6144, dst_object_offset=chunk * 256 * b),
                            "R.aux", "R.new_shadow")
    tail = g.control("tile_guard_checked", [tail], m)
    if do_output:
        raise ValueError("output cannot precede the full-group range guard")
    if g.new_bank == "R":
        tail = g.packet("R", "S3", n, [tail], dict(m, operation="stage_proposal"), "R.new", "R.stage_new")
    else:
        tail = g.packet("S4", "S3", n, [tail], dict(m, operation="stage_proposal"), "R.new_shadow", "R.stage_new")
    return g.packet("S3", "EXT", n, [tail], dict(m, operation="write_uncommitted_backing_generation", dst_object_offset=backing_offset),
                    "R.stage_new", g.proposal_slot)


def output_tile(g, token, attempt, head, tile, deps, epoch):
    tv = g.config["tile"]
    b = g.config["state_bits"] // 8
    cells = K * tv
    n = cells * b
    ds = 5 if b == 4 else 3
    m = dict(stream="R", token=token, attempt=attempt, head=head, tile=tile,
             K=K, Vtile=tv, state_bits=b * 8, scale_epoch=epoch, complete_K=True)
    p = g.packet("EXT", "S2", n, deps, dict(m, operation="page_guarded_new_for_output", src_object_offset=(head * K * V + tile * cells) * b), g.proposal_slot, "R.stage_old")
    p = g.packet("S2", "R", n, [p], m, "R.stage_old", "R.old")
    p = g.math("R", "new_state_completeK_output", cells * (mulslots(ds, 3) + 10) + tv * 10, n + 256, tv * 8, [p], m)
    return g.packet("R", "S5", tv * 8, [p], dict(m, operation="uncommitted_output", src_object_offset=3072, dst_object_offset=(head * V + tile * tv) * 8), "R.aux", "R.output")


def build_rescale(g, token, attempt, heads, deps, epoch):
    tail = list(deps)
    b = g.config["state_bits"] // 8
    if attempt == 0:
        # Retry operates on a complete trial generation; unchanged heads must
        # exist too. Do not initialize only overflowing heads and read garbage.
        for head in range(2):
            for tile in range(V // g.config["tile"]):
                n = K * g.config["tile"] * b
                off = (head * K * V + tile * K * g.config["tile"]) * b
                m = dict(stream="R", token=token, attempt=attempt, head=head, tile=tile,
                         scale_epoch=epoch - 1, operation="clone_full_committed_trial")
                p = g.packet("EXT", "S2", n, tail, dict(m, src_object_offset=off), g.committed_slot, "R.stage_old")
                p = g.packet("S2", "EXT", n, [p], dict(m, dst_object_offset=off), "R.stage_old", "backing.trial")
                tail = [p]
    for head in heads:
        for tile in range(V // g.config["tile"]):
            n = K * g.config["tile"] * b
            off = (head * K * V + tile * K * g.config["tile"]) * b
            m = dict(stream="R", token=token, attempt=attempt, head=head, tile=tile,
                     scale_epoch=epoch, operation="full_head_trial_RNE_shift1", state_bits=b * 8)
            p = g.packet("EXT", "S2", n, tail, dict(m, src_object_offset=off), "backing.trial", "R.stage_old")
            p = g.packet("S2", "R", n, [p], m, "R.stage_old", "R.old")
            p = g.math("R", "rescale_RNE_shift1", K * g.config["tile"] * 20, n, n, [p], m)
            p = g.packet("R", "S3", n, [p], m, "R.old", "R.stage_new")
            p = g.packet("S3", "EXT", n, [p], dict(m, dst_object_offset=off), "R.stage_new", "backing.trial")
            tail = [p]
    p = g.descriptor_update("trial_scale_epoch_update", tail, len(heads) + 4,
                            dict(stream="R", token=token, attempt=attempt, heads=heads, scale_epoch=epoch, published=False))
    return p


def graph(task, c):
    if task["precision"]["state_bits"] != c["state_bits"]:
        raise ValueError("task/config precision mismatch")
    if len(task["tokens"]) > 256 or task["norm_rows"] > 32:
        raise ValueError("bounded input inventory")
    g = Graph(c)
    start = g.control("start", [], dict(task_fingerprint=hashlib.sha256(canonical(task)).hexdigest()))
    gamma = g.packet("EXT", "S1", 10240, [start], {"stream": "norm", "operation": "initial_gamma", "src_object_offset": 32 * 25600},
                     "backing.consumer_input", "source.gamma")
    qkv = g.packet("EXT", "R", 2048, [start], {"stream": "R", "operation": "initial_QKV_gate_metadata"},
                   "backing.R_inputs", "R.aux")
    vtail = gamma
    for row in range(task["norm_rows"]):
        vtail = build_norm(g, row, [vtail])
    rtail = qkv
    # Explicit one-time row-major -> candidate tile-major state packing. The
    # strided source rows are16B-aligned; address generation is paid on lanes.
    for head in range(2):
        for tile in range(V // c["tile"]):
            cells = K * c["tile"]
            n = cells * (c["state_bits"] // 8)
            m = dict(stream="R", operation="initial_state_layout", head=head, tile=tile,
                     rows=K, row_bytes=c["tile"] * 4, row_stride_bytes=V * 4,
                     strided_source_base=(head * K * V + tile * c["tile"]) * 4)
            rtail = g.packet("EXT", "R", n, [rtail], m, "backing.raw_initial", "R.old")
            rtail = g.math("R", "initial_state_pack_address", cells * 10 + K * 10, n, n, [rtail], m)
            rtail = g.packet("R", "S3", n, [rtail], m, "R.old", "R.stage_new")
            rtail = g.packet("S3", "EXT", n, [rtail], dict(m, dst_object_offset=(head * K * V + tile * cells) * 4), "R.stage_new", "backing.model_old")
    for t, token in enumerate(task["tokens"]):
        g.committed_slot = "backing.model_old" if t % 2 == 0 else "backing.proposal"
        g.proposal_slot = "backing.proposal" if t % 2 == 0 else "backing.model_old"
        # Q/K/V/gates and units are immutable published inputs, 2048B/token.
        rtail = g.packet("EXT", "R", 2048, [rtail], {"stream": "R", "token": t, "operation": "token_QKV_gate_metadata", "src_object_offset": t * 2048},
                         "backing.R_inputs", "R.aux")
        for a, attempt in enumerate(token["attempts"]):
            tails = []
            rbefore = rtail
            for head in range(2):
                htail = rbefore
                for tile in range(V // c["tile"]):
                    htail = recurrent_tile(g, t, a, head, tile, [htail], epoch=attempt["epoch"])
                tails.append(htail)
                # Same R scratch: serialize heads, not duplicate free buffers.
                rbefore = htail
            rtail = g.control("attempt_guard_barrier", tails, dict(stream="R", token=t, attempt=a,
                                                                  accepted=attempt["accepted"], scale_epoch=attempt["epoch"]))
            if not attempt["accepted"]:
                rtail = g.control("abort_unpublished_generation", [rtail], dict(stream="R", token=t,
                                                                             attempt=a, committed_state_unchanged=True))
                if attempt.get("rescale_heads"):
                    rtail = build_rescale(g, t, a, attempt["rescale_heads"], [rtail], attempt["epoch"] + 1)
            else:
                for head in range(2):
                    for tile in range(V // c["tile"]):
                        rtail = output_tile(g, t, a, head, tile, [rtail], attempt["epoch"])
                rtail = g.control("fullV_head_output_barrier", [rtail], dict(stream="R", token=t,
                                                                           heads=2, V=128, nonlinear_gated_norm="outside numeric contract"))
                rtail = g.descriptor_update("atomic_group_commit", [rtail], 70,
                                           dict(stream="R", token=t, attempt=a, scale_epoch=attempt["epoch"],
                                                old_generation=g.committed_slot, new_generation=g.proposal_slot,
                                                includes=["state", "output", "units", "epoch", "version"]))
    g.control("finish", [rtail, vtail], {"R_tokens": len(task["tokens"]), "norm_rows": task["norm_rows"]})
    return g


def schedule(g):
    nodes = g.nodes
    followers = [[] for _ in nodes]
    indeg = []
    for n in nodes:
        indeg.append(len(n["deps"]))
        for d in n["deps"]:
            followers[d].append(n["id"])
    critical = [n["duration"] for n in nodes]
    for n in reversed(nodes):
        critical[n["id"]] += max((critical[i] for i in followers[n["id"]]), default=0)
    ready = [i for i, d in enumerate(indeg) if not d]
    calendars = defaultdict(list)
    done = {}
    scheduled = []
    while ready:
        if g.config["strategy"] == "critical":
            ready.sort(key=lambda i: (-critical[i], i))
        else:
            ready.sort()
        i = ready.pop(0)
        n = copy.deepcopy(nodes[i])
        t = max((done[d] for d in n["deps"]), default=0)
        # Every reservation asks a full exclusive lane pool or an exclusive
        # endpoint; FIFO credit co-reserves that endpoint. Thus no partial
        # capacity packing assumption is hidden in the scheduler.
        while True:
            bumped = t
            for r in n["reservations"]:
                lo, hi = t + r["offset"], t + r["offset"] + r["duration"]
                cal = calendars[r["resource"]]
                j = bisect.bisect_left(cal, (lo, -1, -1))
                if j and cal[j - 1][1] > lo:
                    j -= 1
                while j < len(cal) and cal[j][0] < hi:
                    if cal[j][1] > lo:
                        bumped = max(bumped, cal[j][1] - r["offset"])
                        break
                    j += 1
            if bumped == t:
                break
            t = bumped
        n.update(start=t, end=t + n["duration"])
        done[i] = n["end"]
        scheduled.append(n)
        for r in n["reservations"]:
            bisect.insort(calendars[r["resource"]], (t + r["offset"], t + r["offset"] + r["duration"], i))
        for f in followers[i]:
            indeg[f] -= 1
            if indeg[f] == 0:
                ready.append(f)
    if len(scheduled) != len(nodes):
        raise ValueError("dependency cycle")
    scheduled.sort(key=lambda n: n["id"])
    return dict(schema=SCHEMA, config=g.config, inventory=g.inventory,
                allocations=g.allocations, nodes=scheduled, makespan=max(done.values(), default=0),
                operation_counters=dict(g.counters), optimization_scope="minimum of predeclared fifo/critical only, no global-optimum claim")


def audit(w):
    """Producer guard; independent receiver separately reconstructs formulas."""
    caps = w["inventory"]["capacities"]
    events = defaultdict(list)
    nodes = w["nodes"]
    if [n["id"] for n in nodes] != list(range(len(nodes))):
        raise ValueError("node ids")
    for n in nodes:
        if n["end"] != n["start"] + n["duration"]:
            raise ValueError("duration")
        if any(nodes[d]["end"] > n["start"] for d in n["deps"]):
            raise ValueError("dependency")
        for r in n["reservations"]:
            events[r["resource"]].append((n["start"] + r["offset"], r["amount"]))
            events[r["resource"]].append((n["start"] + r["offset"] + r["duration"], -r["amount"]))
    high = {}
    for resource, es in events.items():
        used = peak = 0
        for _, delta in sorted(es):
            used += delta
            peak = max(peak, used)
            if used < 0 or used > caps[resource]:
                raise ValueError("resource capacity: " + resource)
        high[resource] = peak
    memory = Counter()
    for a in w["allocations"]:
        memory[a["bank"]] += a["bytes"]
        if a["offset"] + a["bytes"] > w["inventory"]["bank_sizes"][a["bank"]]:
            raise ValueError("buffer capacity")
    if any(n > w["inventory"]["bank_sizes"][b] for b, n in memory.items()):
        raise ValueError("buffer sum")
    return dict(status="PASS", resource_high_water=high, resident_bytes=dict(memory))


def verify_manifest(root, names=None):
    root = Path(root)
    p = root / "manifest.json"
    m = load_json(p)
    artifacts = m.get("artifacts", {})
    selected = list(artifacts) if names is None else list(names)
    for name in selected:
        if Path(name).name != name:
            raise ValueError("unsafe artifact name")
        desc = artifacts.get(name)
        if not isinstance(desc, dict) or not {"bytes", "sha256"} <= set(desc):
            raise ValueError("unindexed artifact: " + name)
        f = root / name
        if not f.is_file() or descriptor(f) != {k: desc[k] for k in ("bytes", "sha256")}:
            raise ValueError("artifact mismatch: " + str(f))
    return m, descriptor(p)


def inputs(root, range_root=None, norm_stage="norm03"):
    root = Path(root)
    # Numeric NPZ arrays are not replayed by a timing service. Actual producer
    # manifests and records are SHA-bound, not treated as mathematical oracles.
    smeta, sm = verify_manifest(root / "state01", ["state-results.json"])
    nmeta, nm = verify_manifest(root / norm_stage, ["norm.json"])
    ss = load_json(root / "state01" / "state-results.json")
    ns = load_json(root / norm_stage / "norm.json")
    s = next(x for x in ss if x["id"] == "evaluation.S32.D31")
    n = next(x for x in ns if x["id"] == "decode.tile16_delta_ACT8")
    sa = s["artifact"]
    if {k: sa[k] for k in ("bytes", "sha256")} != smeta["artifacts"].get(sa["name"]):
        raise ValueError("state record/manifest mismatch")
    verify_manifest(root / "state01", [sa["name"]])
    verify_manifest(root / norm_stage, [n["id"] + ".npz", "constants.npz"])
    steps = s["integer_steps"]
    task = dict(id="native32.S32D31.static", precision=s["format"],
                R_input_manifest=sm, norm_input_manifest=nm,
                state_record_sha256=hashlib.sha256(canonical(s)).hexdigest(),
                norm_record_sha256=hashlib.sha256(canonical(n)).hexdigest(),
                norm_rows=n["rows"], tokens=[{"attempts": [{"accepted": True, "epoch": 0}]} for _ in range(steps)],
                commit_contract="saturating numeric reference, double-buffer group atomic commit",
                streams="independent norm32 captured decode rows and R32 capture; not a complete chained model",
                numeric_quality_accepted=False)
    if n["hidden"] != H or n["rows"] != 32 or steps != 32 or s["format"]["state_bits"] != 32:
        raise ValueError("unexpected frozen task shape")
    tasks = [task]
    if range_root is not None:
        # The exact event schema is versioned. Never silently infer attempts
        # from a producer error metric or from a different numeric profile.
        rr = Path(range_root)
        rm, rmd = verify_manifest(rr, ["range-results.json"])
        if rm.get("schema") != "issue68-range/1" or rm.get("status") != "PASS":
            raise ValueError("unsupported range source")
        rp = rr / "range-results.json"
        selected = {"native.evaluation.S32.D31.guard_rescale",
                    "legacy.layer0-end8192.S32.D31.guard_rescale"}
        for record in load_json(rp):
            if record["id"] not in selected:
                continue
            f = record["format"]
            if f["state_bits"] != 32 or f["decay_fraction"] != 31:
                raise ValueError("range precision mismatch")
            td = record["transaction_trace"]
            art = record["artifact"]
            for d in (td, art):
                if {k: d[k] for k in ("bytes", "sha256")} != rm["artifacts"].get(d["name"]):
                    raise ValueError("range record/manifest mismatch")
            verify_manifest(rr, [td["name"], art["name"]])
            tp = rr / td["name"]
            if descriptor(tp) != {k: td[k] for k in ("bytes", "sha256")}:
                raise ValueError("range trace mismatch")
            original = load_json(tp)
            tokens = []
            for token in original["tokens"]:
                attempts = []
                for a in token["attempts"]:
                    if a["outcome"] == "ABORT_WIDTH":
                        raise ValueError("width-aborted service work is unqualified")
                    waves = [e for e in original["rescale_events"]
                             if e["token"] == token["token"] and e["after_attempt"] == a["attempt"]]
                    if len(waves) > 1:
                        raise ValueError("duplicate rescale wave")
                    attempts.append(dict(accepted=a["outcome"] == "COMMIT", epoch=a["epoch"],
                                         units=a["units"], guard_count=a["guard_count"],
                                         rescale_heads=waves[0]["heads"] if waves else [],
                                         source_attempt_sha256=hashlib.sha256(canonical(a)).hexdigest()))
                tokens.append(dict(attempts=attempts, source_before=token["before"],
                                   source_commit=token.get("commit"), outcome=token["outcome"]))
            y = copy.deepcopy(task)
            # A legacy R window must not inherit the native32 source label.
            # Keep the independent norm stream, replace every R provenance.
            y.pop("R_input_manifest")
            y.pop("state_record_sha256")
            y.update(id=record["id"], tokens=tokens, precision=f,
                     range_events=descriptor(rp), range_manifest=rmd, range_transaction=td,
                     R_original_source_artifact=record["source_artifact"],
                     R_original_source_id=record["source_id"], R_role=record["role"],
                     range_record_sha256=hashlib.sha256(canonical(record)).hexdigest(),
                     source_range_cost=record["cost"],
                     commit_contract="causal guard/rescale, no failed-token publication, atomic state/output/units/epoch/version commit",
                     streams="independent actual norm32 stream and exact range R token events; R length may differ")
            tasks.append(y)
    return tasks


def run(root, out, binding, range_root=None, ext_profiles=(1, 16), task_ids=None, norm_stage="norm03",
        organizations=None, tiles=None, routes=None, strategies=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    actual = sha(__file__)
    if binding.get("service_sha256") != actual or not binding.get("commit"):
        raise ValueError("source binding mismatch")
    tasks = inputs(root, range_root, norm_stage)
    organizations = list(organizations or LANES)
    tiles, routes = list(tiles or (16, 32)), list(routes or ("reread", "spill"))
    strategies = list(strategies or ("fifo", "critical"))
    if any(len(set(x)) != len(x) for x in (organizations, tiles, routes, strategies, ext_profiles)):
        raise ValueError("duplicate configuration")
    if task_ids:
        tasks = [t for t in tasks if t["id"] in task_ids]
        if len(tasks) != len(task_ids):
            raise ValueError("unknown or duplicate task id")
    results = []
    artifacts = {}
    for ti, task in enumerate(tasks):
        for ext in ext_profiles:
            for org in organizations:
                for tile in tiles:
                    for route in routes:
                        candidates = []
                        for strategy in strategies:
                            c = config(org, tile, route, ext, strategy)
                            g = graph(task, c)
                            w = schedule(g)
                            w["task"] = task
                            w["task_fingerprint"] = hashlib.sha256(canonical(task)).hexdigest()
                            w["producer_audit"] = audit(w)
                            name = f"task{ti}.{org}.tile{tile}.{route}.ext{ext}.{strategy}.json.gz"
                            payload = canonical(w)
                            (out / name).write_bytes(gzip.compress(payload, mtime=0))
                            artifacts[name] = descriptor(out / name)
                            candidates.append(dict(strategy=strategy, cycles=w["makespan"], witness=name,
                                                   nodes=len(w["nodes"]), memory=w["producer_audit"]["resident_bytes"],
                                                   payload_bytes=g.counters["payload_bytes"], wire_bytes=g.counters["wire_bytes"]))
                        best = min(candidates, key=lambda a: (a["cycles"], a["strategy"]))
                        results.append(dict(task=task["id"], task_fingerprint=hashlib.sha256(canonical(task)).hexdigest(),
                                            state_bits=32, commit_contract=task["commit_contract"],
                                            organization=org, tile=tile, norm_route=route, ext_ii=ext,
                                            best=best, strategies=candidates))
    metrics = dict(schema=SCHEMA, status="PASS_CONDITIONAL_SCHEDULE", results=results,
                   refused=[{"profile": "in_place", "reason": "no proof of identical abort/rollback semantics; excluded from main ranking"}],
                   boundary="published quantized QKV/gates and norm residual sums to raw R output/full-head barrier and fresh A8; excludes integer gated norm/SiLU/QK L2norm and full language model",
                   fairness="same eight total S8 lanes, scratch/banks/backing/ports/bus/SFU; independent task precision+contract groups only",
                   source=binding)
    (out / "metrics.json").write_bytes(canonical(metrics))
    artifacts["metrics.json"] = descriptor(out / "metrics.json")
    manifest = dict(schema=SCHEMA, source=binding, config=dict(ext_profiles=list(ext_profiles), lane_profiles=organizations,
                                                            tiles=tiles, norm_routes=routes, strategies=strategies),
                    environment={"python": sys.version, "platform": platform.platform()}, artifacts=artifacts,
                    input_validation="SHA of manifests/metrics, baseline S32D31 NPZ, selected norm NPZ/constants, selected range NPZ/transaction; unrelated conditions not rehashed; full numeric input audit separate",
                    input_root=str(root), range_root=str(range_root) if range_root else None)
    (out / "manifest.json").write_bytes(canonical(manifest))
    return metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--range")
    p.add_argument("--out", required=True)
    p.add_argument("--binding", required=True)
    p.add_argument("--ext-ii", type=int, nargs="+", default=[1, 16], choices=[1, 16])
    p.add_argument("--task", action="append")
    p.add_argument("--norm-stage", default="norm03")
    p.add_argument("--organization", action="append", choices=list(LANES))
    p.add_argument("--tile", action="append", type=int, choices=[16, 32])
    p.add_argument("--norm-route", action="append", choices=["reread", "spill"])
    p.add_argument("--strategy", action="append", choices=["fifo", "critical"])
    a = p.parse_args()
    r = run(a.root, a.out, load_json(a.binding), a.range, tuple(a.ext_ii), a.task, a.norm_stage,
            a.organization, a.tile, a.norm_route, a.strategy)
    print(json.dumps({"status": r["status"], "configurations": len(r["results"])}))


if __name__ == "__main__":
    main()
