"""Static capacity/program proof for one proposed Qwen3 Sq2 S16 Attention island.

Python3.7 standard library only. Does not run RTL, PyTorch, a model or P&R.
M/N/E/S/T roles below are compile-time assertions, not new runtime role packets.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


class InvalidPlan(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InvalidPlan(message)


def fingerprint(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def allocation(name, lo, words):
    return {"name": name, "start_word": lo, "words": words, "end_word_exclusive": lo + words}


def check_allocations(regions, capacity=1024):
    used = {}
    for region in regions:
        lo, end = region["start_word"], region["end_word_exclusive"]
        require(0 <= lo < end <= capacity, "S range outside actual macro: " + region["name"])
        for word in range(lo, end):
            require(word not in used, "simultaneous S alias: %s and %s" % (used.get(word), region["name"]))
            used[word] = region["name"]
    return {"reserved_words": len(used), "reserved_bytes": len(used) * 16,
            "highest_end_word": max(x["end_word_exclusive"] for x in regions)}


class Transaction:
    """Only the real T lifecycle: one fill, immutable sequential drain, release."""
    def __init__(self):
        self.state = "EMPTY"
        self.payload = []
        self.cursor = 0
        self.capacity_words = 384
        self.begin_sizes = []

    def begin(self, words):
        require(self.state == "EMPTY", "T cannot start output while original residual is retained")
        require(1 <= words <= self.capacity_words, "T size exceeds native384 words")
        self.words = words
        self.payload = []
        self.cursor = 0
        self.begin_sizes.append(words)
        self.state = "FILL"

    def write(self, index, value):
        require(self.state == "FILL" and index == len(self.payload), "T write must be sequential")
        self.payload.append(value)
        if len(self.payload) == self.words:
            self.state = "SEALED"

    def commit(self):
        require(self.state == "SEALED", "T commit requires all real writes")
        self.state = "READ_HOLD"

    def take(self, expected_index):
        require(self.state == "READ_HOLD" and expected_index == self.cursor,
                "T is sequential; cannot random-read or skip original residual")
        value = self.payload[self.cursor]
        self.cursor += 1
        if self.cursor == self.words:
            self.state = "RELEASE"
        return value

    def release(self):
        require(self.state == "RELEASE", "T source is not yet fully consumed")
        self.state = "EMPTY"


class RawMGroup:
    def __init__(self, chunks):
        self.required = chunks
        self.executed = 0

    def execute(self, index, clear):
        require(index == self.executed and index < self.required, "M chunk reordered/overrun")
        require(clear == (index == 0), "M raw accumulation cleared inside group")
        self.executed += 1

    def read(self):
        require(self.executed == self.required, "cannot READ before every full-K chunk completes")


def check_gqa(q_head, kv_head):
    require(0 <= q_head < 16 and 0 <= kv_head < 8 and q_head // 2 == kv_head,
            "GQA must reuse adjacent two query heads per KV head")


def check_rope_permutation(permutation):
    require(sorted(permutation) == list(range(128)), "split-half repack is not a bijection")
    for i in range(64):
        require(permutation[2 * i:2 * i + 2] == [i, i + 64], "source RoPE pair must be dimension i/i+64")


def check_complete_context(context):
    require(set(context) == set(range(512, 1024)), "Wo lacks complete512word context")
    for address, lineage in context.items():
        token, head, group = lineage
        require(address == 512 + token * 256 + head * 16 + group, "Wo context head/channel layout mismatch")


def check_head_capacity(sequence, scalar_bytes, keep_X_in_S=False):
    required = sequence * (1024 + 2048) * scalar_bytes + 4096
    if keep_X_in_S:
        required += sequence * 1024 * scalar_bytes
    require(required <= 16384, "S needs%d bytes, exceeds16KiB" % required)
    require(sequence * 1024 * scalar_bytes <= 6144, "raw residual does not fit one T lease")


def check_scale_instance(scale):
    require(scale["native_fields_legal"] and scale["worst_case_S64_safe"],
            "power2 scale is not legal/safe in native M instance")


def N_service(kind, mode, count, src, gamma, exp, dst, identity):
    words = (count + 7) // 8
    require(mode in [0, 1, 2] and 1 <= count <= 1024, "N-long mode/count admission")
    regions = [allocation("src", src, words), allocation("dst", dst, words),
               allocation("EXP" if mode == 0 else "gamma", exp if mode == 0 else gamma, words)]
    check_allocations(regions)
    return {"kind": kind, "identity": identity, "mode": mode, "count": count,
            "src": src, "gamma": gamma, "EXP": exp, "dst": dst, "words": words,
            "native_commands": 3 + 3 * words if mode == 0 else 2 + 2 * words,
            "S_reads": 3 * words, "S_writes": (2 if mode == 0 else 1) * words}


def descriptor(rows, tiles, last_k, n, a_wide, b_wide, clear):
    require(1 <= rows <= 8 and 1 <= tiles <= 4 and 1 <= last_k <= 8 and 1 <= n <= 8,
            "native M shape guard")
    return ((rows << 15) | (tiles << 12) | (n << 8) | (last_k << 4) |
            (int(clear) << 2) | (int(b_wide) << 1) | int(a_wide))


def scale_plan(weight_fin, matrix_k, activation_fin=10, output_fin=10):
    """One per-matrix power2 unit; native capability != current F1024 selection."""
    exponent = activation_fin + weight_fin - output_fin
    right = max(0, exponent)
    left = max(0, -exponent)
    fields_ok = right <= 63 and left <= 31
    raw_bound = matrix_k * 32768 * 128 * (1 << left)
    return {"weight_fin": weight_fin, "factor": 1, "left_shift": left,
            "right_shift": right, "native_fields_legal": fields_ok,
            "worst_case_S64_bound": raw_bound, "worst_case_S64_safe": raw_bound < (1 << 63),
            "READ_S16_hex": hex(0x100 | right) if fields_ok else None,
            "SCALE_hex": hex(1 | (left << 16)) if fields_ok else None,
            "current_F1024_top_selectable": weight_fin == 7,
            "note": "nativeM has these shifts; fixed top literals do not expose matrix scale selection"}


def phase_layouts():
    initial = [allocation("X0", 0, 128), allocation("X1", 128, 128),
               allocation("H_gamma", 256, 128), allocation("head_parameters_staging", 512, 64)]
    head_work = [allocation("Q_gamma", 128, 16), allocation("K_gamma", 144, 16),
                 allocation("RoPE_coeff_positions0_1", 160, 32), allocation("K_rotated_rows", 192, 32),
                 allocation("V_rows", 224, 32), allocation("Q_raw_then_rotated", 256, 32),
                 allocation("head_N_scratch", 288, 32), allocation("Awide", 320, 16),
                 allocation("Bwide_or_B8", 336, 32), allocation("score", 368, 2),
                 allocation("EXP_U16", 370, 2), allocation("P_Q14", 372, 2),
                 allocation("explicit_spare_scratch", 374, 10)]
    return {
        "INPUT_AND_T_SPOOL": initial,
        "RMS0": initial + [allocation("Norm0", 384, 128)],
        "RMS1_AFTER_X0_SPOOLED_AND_RMS0": [allocation("Norm1", 0, 128), allocation("X1", 128, 128),
            allocation("H_gamma", 256, 128), allocation("Norm0", 384, 128),
            allocation("head_parameters_staging", 512, 64)],
        "HEAD_PARAMETER_RELOCATION": [allocation("Norm1", 0, 128), allocation("head_parameters_final", 128, 64),
            allocation("Norm0", 384, 128), allocation("head_parameters_staging", 512, 64)],
        "ALL_HEADS": [allocation("Norm1", 0, 128), allocation("Norm0", 384, 128),
            allocation("complete_context_reserved", 512, 512)] + head_work,
        "WO_AND_RESIDUAL": [allocation("final_token0", 0, 128), allocation("work_reserved", 128, 256),
            allocation("final_token1", 384, 128), allocation("complete_context", 512, 512)],
        "OUTPUT_AFTER_RAW_T_RELEASE": [allocation("final_token0", 0, 128), allocation("final_token1", 384, 128)],
    }


def check_program():
    check_head_capacity(2, 2)
    S = {token * 128 + group: ("X", token, group) for token in range(2) for group in range(128)}
    for i in range(128):S[256 + i] = ("gamma_H", i)
    for i in range(64):S[512 + i] = ("head_parameter", i)
    N_groups = [N_service("inputNorm0", 1, 1024, 0, 256, 0, 384, [0]),
                N_service("inputNorm1", 1, 1024, 128, 256, 0, 0, [1])]
    E_groups = []
    repacks = []
    t = Transaction()
    t.begin(256)
    # Actual S->T capture, deliberately interleaved to match later rows2 Wo.
    for group in range(128):
        for token in range(2):
            t.write(2 * group + token, S[token * 128 + group])
    t.commit()
    require(t.state == "READ_HOLD" and t.cursor == 0, "hold all original residual until Wo")
    # Full-group N0 finishes before N1 may overwrite original X0.
    for i in range(128):
        require(S[i] == ("X", 0, i), "RMS0 source overwritten")
        require(S[256 + i] == ("gamma_H", i), "RMS0 gamma overwritten")
        S[384 + i] = ("Norm", 0, i)
    for i in range(128):
        require(S[128 + i] == ("X", 1, i), "RMS1 source overwritten")
        require(S[256 + i] == ("gamma_H", i), "RMS1 gamma overwritten")
        S[i] = ("Norm", 1, i)
    # These are64 real S read/write copies; staging512 cannot become context yet.
    for i in range(64):
        require(S[512 + i] == ("head_parameter", i), "head parameter relocation source lost")
        S[128 + i] = S[512 + i]
    require(all(S[128 + i] == ("head_parameter", i) for i in range(64)), "head parameters not stored before context")
    for tile in range(4):
        for row in [2, 3]:S[320 + 4 * tile + row] = ("zero_padding",)
    context = {}
    groups = []
    heads = []
    counts = {"M_EXEC": 0, "M_commands": 0, "M_services": 0, "weight_requests": 0,
              "loader_services": 0, "loader_wide_reads": 0, "A128_beats": 0, "B512_beats": 0}

    def m_group(kind, chunks, tiles, last_k, n, b_wide, out_reads, provider, identity):
        first = descriptor(2, tiles, last_k, n, True, b_wide, True)
        later = descriptor(2, tiles, last_k, n, True, b_wide, False)
        # One CLEAR and SCALE, all raw chunks, then only final READs.
        raw = RawMGroup(chunks)
        for chunk in range(chunks):
            d = first if chunk == 0 else later
            raw.execute(chunk, bool(d & 4))
        raw.read()
        counts["M_services"] += 1
        counts["M_EXEC"] += chunks
        counts["M_commands"] += chunks + 2 + out_reads
        counts["weight_requests"] += chunks if provider else 0
        counts["loader_services"] += chunks
        counts["loader_wide_reads"] += chunks * tiles * (1 + (2 if b_wide else 1))
        counts["A128_beats"] += chunks * tiles * 2
        counts["B512_beats"] += chunks * tiles * (2 if b_wide else 1)
        groups.append({"kind": kind, "identity": identity, "chunks": chunks, "rows": 2,
                       "tiles": tiles, "last_k": last_k, "active_N": n,
                       "first_EXEC": hex(first), "later_EXEC": hex(later),
                       "READ_indices": [0, 8] if n == 2 else [0, 1, 8, 9],
                       "READ_only_after_EXEC_count": chunks})

    def head_norm_RoPE(kind, head, base, gamma):
        for token in range(2):
            N_groups.append(N_service(kind + "_headRMS", 1, 128, base + token * 16,
                                      gamma, 0, 288 + token * 16, [token, head]))
        for token in range(2):
            for block in range(16):
                lo = 288 + token * 16 + block // 2
                hi = lo + 8
                lanes = list(range(4 * (block % 2), 4 * (block % 2) + 4))
                pairs = [[4 * block + i, 4 * block + i + 64] for i in range(4)]
                require(288 + token * 16 <= lo < hi < 304 + token * 16, "RoPE gather source range")
                repacks.append({"kind": kind, "head": head, "token": token,
                                "src_words": [lo, hi], "src_lanes_each": lanes, "source_pairs": pairs,
                                "dst": base + token * 16 + block})
                E_groups.append({"kind": "RoPE", "head_kind": kind, "head": head, "token": token,
                                 "op": 9, "shift": 14, "count": 8,
                                 "srcA_dst": base + token * 16 + block,
                                 "srcB_coeff": 160 + token * 16 + block,
                                 "requires": "actual gather writeACK then E complete A/B read before inplacewrite"})

    permutation = [item for i in range(64) for item in (i, i + 64)]
    check_rope_permutation(permutation)

    for kv_head in range(8):
        # K/V projection each completed as real rows2 groups before consumers.
        for kind in ["K", "V"]:
            for group in range(16):
                m_group(kind, 32, 4, 8, 8, False, 4, True, [kv_head, group])
        head_norm_RoPE("K", kv_head, 192, 144)
        for q_head in [2 * kv_head, 2 * kv_head + 1]:
            check_gqa(q_head, kv_head)
            for group in range(16):
                m_group("Q", 32, 4, 8, 8, False, 4, True, [q_head, group])
            head_norm_RoPE("Q", q_head, 256, 128)
            m_group("QK", 4, 4, 8, 2, True, 2, False, [q_head])
            for token in range(2):
                N_groups.append(N_service("causalSoftmax", 0, token + 1, 368 + token, 0,
                                          370 + token, 372 + token, [q_head, token]))
            for group in range(16):
                m_group("PV", 1, 1, 2, 8, True, 4, False, [q_head, group])
                for token in range(2):
                    addr = 512 + token * 256 + q_head * 16 + group
                    require(addr not in context and 512 <= addr < 1024, "context overlap/range")
                    context[addr] = (token, q_head, group)
                    S[addr] = ("context", token, q_head, group)
            heads.append({"Q_head": q_head, "KV_head": kv_head, "causal_prefixes": [1, 2]})
    check_complete_context(context)
    for i in range(128):
        require(S[i] == ("Norm", 1, i) and S[384 + i] == ("Norm", 0, i), "Norm lifetime violated during heads")
    require(t.state == "READ_HOLD" and t.cursor == 0, "original residual prematurely consumed")
    final = {}
    for group in range(128):
        # No M context is kept across a head operation; all context now lives S.
        m_group("Wo", 64, 4, 8, 8, False, 4, True, [group])
        for token in range(2):
            require(t.take(2 * group + token) == ("X", token, group), "wrong original residual lineage")
            # Must really write the captured T word to S258 before E service.
            raw_S258 = ("X", token, group)
            S[258] = raw_S258
            require(raw_S258 == ("X", token, group), "missing T-to-S bridge")
            addr = group if token == 0 else 384 + group
            require(addr not in final, "final overwrite before publication")
            final[addr] = ("Y", token, group)
            S[addr] = final[addr]
            E_groups.append({"kind": "original_residual", "op": 0, "shift": 0, "count": 8,
                             "srcA": 256 + token, "srcB_Tcapture": 258, "dst": addr,
                             "identity": [token, group], "requires": "Ttake -> real S258 writeACK -> E"})
    require(t.state == "RELEASE" and len(final) == 256, "residual source still live")
    t.release()
    t.begin(256)
    for token in range(2):
        for group in range(128):
            addr = group if token == 0 else 384 + group
            require(S[addr] == ("Y", token, group), "output lineage")
            t.write(token * 128 + group, S[addr])
    t.commit()
    for index in range(256):
        require(t.take(index) == ("Y", index // 128, index % 128), "host output order")
    t.release()
    counts.update({"N_services": len(N_groups), "N_commands": sum(x["native_commands"] for x in N_groups),
                   "N_RMS_H1024_groups": 2, "N_RMS_head128_groups": 48, "N_Softmax_prefix_groups": 32,
                   "E_RoPE_services": 48 * 16, "E_residual_services": 256,
                   "E_total_services": len(E_groups),
                   "weight_beats": counts["weight_requests"] * 16,
                   "weight_bytes": counts["weight_requests"] * 256,
                   "context_words_produced_once": len(context), "final_words": len(final),
                   "T_begin_transactions": len(t.begin_sizes), "T_peak_words": max(t.begin_sizes),
                   "T_total_words_written_and_taken_each": sum(t.begin_sizes)})
    counts["head_parameter_real_S_copies"] = 64
    require(counts["M_EXEC"] == 24896 and counts["M_commands"] == 30336, "M full loop count")
    require(len(N_groups) == 82 and counts["N_commands"] == 2340 and len(E_groups) == 1024,
            "head Norm/Softmax/RoPE/residual program missing")
    require(counts["weight_bytes"] == 6 * 1024 * 1024, "missing real projection weights")
    dense_chunks = counts["weight_requests"]
    qk_chunks = sum(x["chunks"] for x in groups if x["kind"] == "QK")
    pv_groups = sum(1 for x in groups if x["kind"] == "PV")
    S_stages = [
        {"stage": "input_X_Hgamma_headparams", "W": 448, "R": 0},
        {"stage": "T_rawX_spool_read", "W": 0, "R": 256},
        {"stage": "RMS_H1024", "W": 256, "R": 768},
        {"stage": "head_parameter_relocation", "W": 64, "R": 64},
        {"stage": "A_rows2_padding8", "W": 8, "R": 0},
        {"stage": "dense_QKV_Wo_chunk_A_and_provider_B", "W": dense_chunks * 24, "R": dense_chunks * 8},
        {"stage": "all_M_group_result_saves", "W": 1824, "R": 0},
        {"stage": "head_RMS128", "W": 48 * 16, "R": 48 * 48},
        {"stage": "fresh_gather2words_plus_RoPE_per_block", "W": len(repacks) * 2, "R": len(repacks) * 4},
        {"stage": "QK_A_and_Bwide_staging", "W": qk_chunks * 40, "R": qk_chunks * 16},
        {"stage": "prefix_Softmax", "W": 64, "R": 96},
        {"stage": "PV_A_and_V_transpose", "W": pv_groups * 10, "R": pv_groups * 4},
        {"stage": "T_original_capture_to_S258", "W": 256, "R": 0},
        {"stage": "E_original_residual", "W": 256, "R": 512},
        {"stage": "T_final_output_read", "W": 0, "R": 256},
    ]
    counts["ordinary_S_W"] = sum(x["W"] for x in S_stages)
    counts["ordinary_S_R"] = sum(x["R"] for x in S_stages)
    counts["ordinary_S_total"] = counts["ordinary_S_W"] + counts["ordinary_S_R"]
    require(counts["ordinary_S_total"] == 806408, "ordinary S recipe count")
    return {"counts": counts, "head_schedule": heads, "M_groups": groups,
            "N_groups": N_groups, "E_groups": E_groups, "real_split_half_repack_blocks": repacks,
            "ordinary_S_recipe": S_stages,
            "ordinary_S_count_scope": "chosen fresh-two-word-gather recipe; not measured RTL; holding reuse optimization requires a new trace/count",
            "split_half_to_adjacent_permutation": permutation,
            "T_lifetime": ["BEGIN256 rawX", "WRITE group-interleaved", "COMMIT",
                           "HOLD through all16heads", "Wo group -> takeX0/writeS258/E then takeX1/writeS258/E",
                           "last residual ACK", "RELEASE", "BEGIN256 final", "WRITE token-major",
                           "COMMIT", "host drain256", "RELEASE"]}


def negative_probes():
    probes = []
    def rejects(name, action):
        try:
            action()
        except InvalidPlan as error:
            probes.append({"id": name, "rejected": True, "reason": str(error)})
        else:
            raise InvalidPlan("negative probe not rejected: " + name)
    rejects("overlapping_live_S", lambda: check_allocations([allocation("Norm", 0, 128), allocation("Q", 64, 32)]))
    rejects("Sq3_same_storeall_schedule", lambda: check_head_capacity(3, 2))
    rejects("FP32_not_covered", lambda: check_head_capacity(2, 4))
    rejects("raw_X_also_in_S_does_not_fit", lambda: check_head_capacity(2, 2, True))
    tx = Transaction();tx.begin(256)
    for i in range(256):tx.write(i, i)
    tx.commit()
    rejects("second_T_begin_before_residual_release", lambda: tx.begin(256))
    rejects("T_random_read_not_available", lambda: tx.take(1))
    rejects("missing_context_before_Wo", lambda: check_complete_context({i: (0, 0, 0) for i in range(512, 1023)}))
    rejects("wrong_GQA_mapping", lambda: check_gqa(3, 0))
    rejects("adjacent_input_not_split_half", lambda: check_rope_permutation(list(range(128))))
    raw = RawMGroup(32)
    for i in range(31):raw.execute(i, i == 0)
    rejects("intermediate_M_quantization", raw.read)
    rejects("legal_fields_but_S64_overflow_scale", lambda: check_scale_instance(scale_plan(-30, 3072)))
    return probes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--model-source", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--research-parent", default="71c819c2")
    ap.add_argument("--emit-trace", action="store_true", help="save all static group/repack records; never an RTL cycle trace")
    a = ap.parse_args()
    require(not a.output_dir.exists(), "use a new independent output directory")
    cfg = json.loads(a.config.read_bytes().decode("utf-8"))
    expected = {"hidden_size": 1024, "intermediate_size": 3072, "num_attention_heads": 16,
                "num_key_value_heads": 8, "head_dim": 128, "rms_norm_eps": 1e-6}
    for key, value in expected.items():require(cfg[key] == value, "wrong actual sample config: " + key)
    theta = cfg.get("rope_parameters", {}).get("rope_theta", cfg.get("rope_theta"))
    require(theta == 1000000 and not cfg.get("attention_bias"), "unexpected RoPE/bias profile")
    rp = cfg.get("rope_parameters", cfg.get("rope_scaling") or {})
    require(rp.get("rope_type", rp.get("type", "default")) == "default", "dynamic/other RoPE needs a new proof")
    model = a.model_source.read_bytes().decode("utf-8")
    for text in ["self.q_norm = Qwen3RMSNorm(self.head_dim", "self.k_norm = Qwen3RMSNorm(self.head_dim",
                 "self.num_key_value_groups = config.num_attention_heads // config.num_key_value_heads",
                 "return torch.cat((-x2, x1), dim=-1)",
                 "emb = torch.cat((freqs, freqs), dim=-1)"]:
        require(text in model, "source semantic anchor absent: " + text)
    phases = phase_layouts()
    budgets = {key: dict(check_allocations(value), regions=value) for key, value in phases.items()}
    program = check_program()
    if not a.emit_trace:
        all_program = program
        program = {key: value for key, value in all_program.items()
                   if key not in ["M_groups", "N_groups", "E_groups", "real_split_half_repack_blocks"]}
        program["checked_record_counts"] = {key: len(all_program[key]) for key in
            ["M_groups", "N_groups", "E_groups", "real_split_half_repack_blocks"]}
        seen = set();examples = []
        for record in all_program["M_groups"]:
            if record["kind"] not in seen:
                seen.add(record["kind"]);examples.append(record)
        program["M_group_examples"] = examples + [all_program["M_groups"][-1]]
        seen = set();examples = []
        for record in all_program["N_groups"]:
            key = (record["kind"], record["count"])
            if key not in seen:
                seen.add(key);examples.append(record)
        program["N_group_examples"] = examples
        program["repack_examples"] = [all_program["real_split_half_repack_blocks"][i] for i in [0, 15, 31, 32, -1]]
        program["full_records"] = "reproducible with --emit-trace; these are static contracts, not hardware instances or RTL cycles"
    probes = negative_probes()
    source_paths = ["project/rtl/block_v2/block_v2_m.sv", "project/rtl/block_v2/block_v2_e.sv",
                    "project/rtl/block_v2/block_v2_n.sv", "project/rtl/block_v1/transaction6k.sv",
                    "project/rtl/block_feed_v1/block_feed_loader.sv",
                    "project/rtl/block_connection_w4/block_w4_n_long_ctrl.sv",
                    "project/rtl/block_connection_w4/block_w4_f1024_top.sv"]
    sources = [dict(path=x, **fingerprint(a.root / x)) for x in source_paths]
    coefficient = round((1 << 15) / math.sqrt(128))
    report = {"schema_version": 1, "status": "STATIC_PROPOSED_CAPACITY_PROGRAM_CHECKED_NOT_RTL",
              "research_parent": a.research_parent, "shape": dict(expected, sequence=2, Q_width=2048, KV_width=1024),
              "config_source": fingerprint(a.config), "upstream_model_source": fingerprint(a.model_source),
              "source_inventory": sources, "phases": budgets, "program": program,
              "negative_probes": probes, "negative_probe_count": len(probes),
              "selected_quantization": {"hidden": "S16 Fin10", "weights": "S8 per-matrix power2 (Fin7 capacity example)",
                    "RoPE_coeff": "S16 Fin14 for positions0/1", "P": "S16 Fin14", "score": "S16 Fin10",
                    "epsilon_code": 1, "epsilon_real": 2 ** -20, "source_epsilon": 1e-6,
                    "QK_factor": coefficient, "QK_factor_Fin": 15, "QK_READ_right": 25,
                    "QK_scale_relative_error": (coefficient / (1 << 15)) * math.sqrt(128) - 1,
                    "PV_READ_right": 14, "model_quality": "UNKNOWN_NOT_ACCEPTED"},
              "macro_candidate": {"M": 1, "N": 1, "E": 1, "G": 0, "R": 0, "S": 1, "T": 1,
                    "choice": "constructive serial subset; not a proven minimal or optimal PPA design",
                    "common_all7_island": "if all7 physically prebuilt, G/R remain present idle; no M11 deletion"},
              "new_active_capabilities_required": ["local complete-head/row/chunk controller and real parameter route",
                    "T rawX spool and T-to-S258 capture/writeACK bridge", "split-half gather to adjacent RoPE pairs",
                    "V/K wide-B staging and all-context materialization", "real weight/gamma/coefficient versioned supply",
                    "phase-valid/reset/error/release guards and finite static numeric command tables"],
              "new_local_FF_candidate": {"layout_holding_bits": 256, "M_half_bits": 64,
                    "note": "explicit proposed holdings; do not assume access to private controller holdings or total CTRL area"},
              "F1024_power2_scale_audit": {"native_M_capable_examples": [scale_plan(f, k) for k in [1024, 3072] for f in [7, 8, 6, -4, -30, 70]],
                    "formula": "R-L = F_A + F_W - F_out for factor1; final one-time RNE, same scale over fullK",
                    "current_top": "SCALE literal1 and READ0x107; weights_version is identity, not numeric selector",
                    "conclusion": "no new native arithmetic needed for legal safe power2 scales, but unchanged F1024 top cannot select them; new prebuilt control/ROM paths and validation are required"},
              "not_claimed": ["new RTL", "RTL simulation", "server access", "L5 implementation", "trained inference quality",
                              "actual physical pins/area/timing", "arbitrary positions/sequence/cache", "FP32 capacity"]}
    a.output_dir.mkdir(parents=True)
    write_json(a.output_dir / "qwen3-attention-plan-checks.json", report)
    print("PASS_STATIC_QWEN3_SQ2_PLAN S_peak=%d T_peak=%d M_EXEC=%d negative_probes=%d; noRTLrun" %
          (max(x["reserved_bytes"] for x in budgets.values()), program["counts"]["T_peak_words"] * 16,
           program["counts"]["M_EXEC"], len(probes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
