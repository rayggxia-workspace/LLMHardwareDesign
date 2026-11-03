# -*- coding: utf-8 -*-
"""Reproduce bounded phase-1 Python checks; never runs RTL/tools/server.

Usage: python -B verify_phase1_mst_reference.py --source-root <frozen checkout>
       --output <independent receipt.json>
Expected vectors are inputs; this script never regenerates expected answers.
"""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import platform
import random
import sys

sys.dont_write_bytecode = True
from phase1_mst_reference import (MReference, TReference, ReferenceDomainError,
                                 digits, encode_exec, decode_exec, loader_descriptor,
                                 loader_plan, pack_a_tile, pack_b_tile, read_formatted,
                                 rne_right)

HERE = Path(__file__).resolve().parent
FROZEN_REF = "643c6012a11cbf461146ac40fbf61485223fe946"
FROZEN_SOURCES = [
    ("project/rtl/block_v2/block_v2_m.sv", "5825adcd3364d4315afd1aa4addae85379fb36df2802ca8ab60026e0b0f44d1e", "5-15,29-35,48-104,116-122,138-145,163-248"),
    ("project/rtl/block_feed_v1/block_feed_loader.sv", "3b8d4643519141232a7297afcf966899cfae3de67be0eba069d54116e66de356", "6-21,31-59,68-108"),
    ("project/rtl/block_feed_v1/block_feed_s16k.sv", "262b193ae007d9a26f310087a6e37e0921f9468cd9884530d8f527d7190f3603", "11-18,24-37"),
    ("project/rtl/block_feed_v1/block_feed_s_macro.sv", "3d105bf4605076e5f806b45c545cb5fdd5658a23d82f0ea4b58c0cd8d2ce18c8", "4-29"),
    ("project/rtl/block_v1/transaction6k.sv", "0b07833dffc28169ba70beafabad3d7503a31989f46fcbdcf03b15ba9026b3ef", "5-39,41-69")
]


def fingerprint(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest(),
            "utf8": bool(raw.decode("utf-8") is not None), "lf_only": b"\r" not in raw}


class Checks:
    def __init__(self):
        self.counts, self.case_ids = {}, []

    def equal(self, group, actual, expected, message):
        if actual != expected:
            raise AssertionError("{}: actual={!r}, expected={!r}".format(message, actual, expected))
        self.counts[group] = self.counts.get(group, 0) + 1

    def domain_error(self, group, action, prefix, message):
        try:
            action()
        except ReferenceDomainError as error:
            self.equal(group, str(error).startswith(prefix), True, message)
        else:
            raise AssertionError("{}: expected ReferenceDomainError".format(message))


def field_word(values, width):
    """Independent host byte encoder; not reference.pack_fields."""
    return int.from_bytes(b"".join(int(v).to_bytes(width // 8, "little", signed=True) for v in values), "little")


def fixture_load(m, segment, bank):
    aa, bb = segment["a"], segment["b_columns"]
    rows, active_n, k = len(aa), len(bb), len(aa[0])
    if not (1 <= rows <= 8 and 1 <= active_n <= 8 and 1 <= k <= 32):
        raise AssertionError("invalid test fixture shape")
    if any(len(row) != k for row in aa + bb):
        raise AssertionError("ragged test fixture")
    tiles, last = (k + 7) // 8, (k - 1) % 8 + 1
    poison = segment.get("poison", 0)
    for tile in range(tiles):
        for row in range(rows):
            values = [aa[row][8 * tile + j] if 8 * tile + j < k else poison for j in range(8)]
            m.load_a(bank, row, tile, segment["fmt_a"], field_word(values, 16 if segment["fmt_a"] else 8))
        values = [bb[n][8 * tile + j] if n < active_n and 8 * tile + j < k else poison
                  for n in range(8) for j in range(8)]
        if segment["fmt_b"]:
            m.load_b(bank, tile, 1, 0, field_word(values[:32], 16))
            m.load_b(bank, tile, 1, 1, field_word(values[32:], 16))
        else:
            m.load_b(bank, tile, 0, 0, field_word(values, 8))
    index = bank << 5
    data = (segment["fmt_a"] | segment["fmt_b"] << 1 | segment["clear"] << 2 |
            last << 4 | active_n << 8 | tiles << 12 | rows << 15)
    return index, data


def test_minimal(vectors, c):
    v = vectors["minimal_mst_profile"]
    memory = {int(k): int(value, 16) for k, value in v["initial_s_words"].items()}
    c.equal("P2_literal", memory[448], field_word(v["a"], 8), "literal A word")
    literal_b = [v["b_column_constants"][n] for n in range(8) for k in range(8)]
    bbytes = b"".join(x.to_bytes(1, "little", signed=True) for x in literal_b)
    c.equal("P2_literal", [memory[x] for x in range(452, 456)],
            [int.from_bytes(bbytes[i:i+16], "little") for i in range(0, 64, 16)], "literal n-major B words")
    p = loader_plan(memory, v["loader"])
    c.equal("P2_literal", [r["wide_addr"] for r in p["reads"]], [113,112], "B then A requests")
    c.equal("P2_literal", len(p["a_beats"]), 1, "one A row")
    c.equal("P2_literal", len(p["b_beats"]), 1, "one S8 B beat")
    m = MReference()
    c.equal("P2_literal", m.command(6)["error"], False, "clear ACK")
    for beat in p["a_beats"]:
        m.load_a(beat["bank"], beat["row"], beat["tile"], beat["wide"], beat["data"])
    for beat in p["b_beats"]:
        m.load_b(beat["bank"], beat["tile"], beat["wide"], beat["half"], beat["data"])
    c.equal("P2_literal", m.command(4, 0, 1)["error"], False, "scale ACK")
    c.equal("P2_literal", m.command(10, 0, 0x9884)["fault_rows"], 0, "EXEC literal word")
    c.equal("P2_literal", m.merged[0], v["result_s64"], "literal nonidentity dot")
    result_words = [m.command(3, pair)["data_hex"] for pair in range(4)]
    c.equal("P2_literal", result_words, v["result_s_words_and_t_payload"], "literal op3 four words")
    # Only the Python intent path is composed here; no S ready/valid cycle model.
    for index, word in enumerate(result_words):
        memory[456 + index] = int(word, 16)
    t = TReference()
    t.tick(begin_valid=1, begin_owner=0, begin_generation=1, begin_words=4)
    for index in range(4):
        c.equal("P2_literal", t.tick(write_valid=1, write_index=index, write_data=memory[456+index])["fires"]["write"], True, "T write intent")
    c.equal("P2_literal", t.tick(commit_valid=1)["after"]["state"], "READ_REQ", "T commit intent")
    t.tick()
    actual = []
    for index in range(4):
        stall = t.tick()
        c.equal("P2_literal", stall["before"]["read_data"], stall["after"]["read_data"], "T Python hold")
        out = t.tick(read_take=1)
        actual.append("0x{:032x}".format(out["before"]["read_data"]))
    c.equal("P2_literal", actual, result_words, "T full batch words")
    c.equal("P2_literal", t.tick(release_valid=1)["after"]["state"], "EMPTY", "T release intent")
    c.case_ids.append(v["id"])


def test_arithmetic(vectors, c):
    for v in vectors["digit_cases"]:
        c.equal("literal_digits", digits(v["value"], v["wide"]), v["expected"], "digit literal")
    for value in range(-32768, 32768):
        ds = digits(value, 1)
        c.equal("S16_digit_reconstruction", ds[0] + 128 * ds[1] + 16384 * ds[2], value, "S16 radix decomposition")
    for v in vectors["rne_cases"]:
        c.equal("literal_RNE", rne_right(v["value"], v["shift"]), v["expected"], "RNE literal")
    # Fraction.__round__ is an independent standard-library exact rational oracle.
    for shift in range(7):
        for value in range(-32768, 32768):
            c.equal("Fraction_RNE", rne_right(value, shift), round(Fraction(value, 1 << shift)), "exact Fraction RNE")
    for shift in range(64):
        values = {-(1 << 63), (1 << 63) - 1, 0, -1, 1}
        if shift:
            half = 1 << (shift - 1)
            for q in (-3, -2, -1, 0, 1, 2, 3):
                values.update(q * (1 << shift) + half + offset for offset in (-1, 0, 1))
        for value in sorted(values):
            if -(1 << 63) <= value < (1 << 63):
                c.equal("Fraction_RNE_S64_boundaries", rne_right(value, shift), round(Fraction(value, 1 << shift)), "S64 Fraction boundary")
    for v in vectors["read_format_cases"]:
        out = read_formatted(v["values"], v["shift"], v["width"])
        for key, expected in (("rounded", v["rounded"]), ("lanes_s32", v["expected"]),
                              ("saturated", v["saturated"]), ("data_hex", v["word"]), ("error", False)):
            c.equal("literal_op5", out[key], expected, v["id"] + "/" + key)
        c.case_ids.append(v["id"])
    c.domain_error("domain_reject", lambda: rne_right(0, 64), "PORT_DOMAIN", "right shift port overflow")
    c.domain_error("domain_reject", lambda: read_formatted([0]*4, 0, 3), "op5 requires", "invalid width")


def test_exec(vectors, c):
    for case in vectors["exec_cases"]:
        m = MReference()
        for seg in case["segments"]:
            index, data = fixture_load(m, seg, case["bank"])
            scale = (seg["factor"] & 65535) | (seg["left_shift"] << 16)
            c.equal("literal_EXEC", m.command(4, 0, scale)["error"], False, "scale accepted")
            out = m.command(10, index, data)
            c.equal("literal_EXEC", out["partials_s40"], seg["expected_partials"], case["id"] + "/partial")
            c.equal("literal_EXEC", [m.merged.get(r) for r in range(len(seg["a"]))], seg["expected_rows"], case["id"] + "/rows")
            c.equal("literal_EXEC", out["fault_rows"], seg["fault_rows"], case["id"] + "/fault mask")
            c.equal("literal_EXEC", out["error"], bool(seg["fault_rows"]), "fault mask/error agreement")
            c.equal("literal_EXEC", out["saturated"], False, "EXEC overflow is not saturated read")
            if "expected_fault_reasons" in seg:
                c.equal("literal_EXEC", out["fault_reasons"], seg["expected_fault_reasons"], "fault reasons")
        for v in case["reads"]:
            out = m.command(v["op"], v["index"], v["data"])
            c.equal("literal_EXEC_read", out["data_hex"], v["word"], "read carrier literal")
            c.equal("literal_EXEC_read", out["saturated"], v["saturated"], "read saturation")
            if "expected_lanes" in v:
                c.equal("literal_EXEC_read", out["lanes_s32"], v["expected_lanes"], "read lanes")
        c.case_ids.append(case["id"])
    # Independent direct dot oracle exercises all four signed-format combinations,
    # multiple tiles and maximum row/column/segment dimensions with exact integers.
    rng = random.Random(151)
    for fa in (0, 1):
        for fb in (0, 1):
            for rows, n, k in ((1,1,1), (2,3,10), (5,7,25), (8,8,32)):
                aa = [[rng.randint(-32768 if fa else -128, 32767 if fa else 127) for j in range(k)] for r in range(rows)]
                bb = [[rng.randint(-32768 if fb else -128, 32767 if fb else 127) for j in range(k)] for col in range(n)]
                seg = {"a":aa,"b_columns":bb,"fmt_a":fa,"fmt_b":fb,"clear":1,"poison":0}
                m = MReference(); index, data = fixture_load(m, seg, 0)
                m.command(4, 0, 2 | (3 << 16))
                out = m.command(10, index, data)
                expected = [[sum(aa[r][j]*bb[col][j] for j in range(k)) * 16 for col in range(n)] + [0]*(8-n) for r in range(rows)]
                c.equal("direct_dot_oracle", out["fault_rows"], 0, "bounded direct dot no overflow")
                c.equal("direct_dot_oracle", [m.merged[r] for r in range(rows)], expected, "direct raw integer dot")


def test_m_rejections(c):
    seg = {"a":[[1]*8],"b_columns":[[1]*8],"fmt_a":0,"fmt_b":0,"clear":1,"poison":0}
    m = MReference(); index, valid = fixture_load(m, seg, 0)
    # Each invalid descriptor uses valid loaded operands, so rejection is not masked
    # by an unrelated missing-bank check. All reject before result modification.
    invalid_data = [valid | 8, valid | (1 << 19), valid & ~(15 << 4),
                    (valid & ~(15 << 4)) | (9 << 4), valid & ~(15 << 8),
                    (valid & ~(15 << 8)) | (9 << 8), valid & ~(7 << 12),
                    (valid & ~(7 << 12)) | (5 << 12), valid & ~(15 << 15),
                    (valid & ~(15 << 15)) | (9 << 15)]
    for data in invalid_data:
        c.equal("M_native_reject", m.command(10, 0, data)["error"], True, "invalid EXEC fields")
        c.equal("M_native_reject", m.merged, {}, "reject does not publish")
    c.equal("M_native_reject", m.command(10, 1, valid)["error"], True, "EXEC reserved index")
    c.equal("M_native_reject", m.command(10, 0, valid & ~4)["error"], True, "append requires old row")
    c.equal("M_native_reject", m.command(10, 32, valid)["error"], True, "unloaded opposite bank")
    c.equal("M_native_reject", m.command(10, 0, valid | 1)["error"], True, "A format mismatch")
    c.equal("M_native_reject", m.command(10, 0, valid | 2)["error"], True, "B format mismatch")
    c.equal("M_native_reject", m.command(3)["error"], True, "invalid result read")
    m.command(10, 0, valid)
    for op, idx, data in ((3,4,0),(3,0,1),(5,2,0),(5,0,64),(5,0,768),(5,0,1024),(4,1,1),(4,0,1<<21),(6,1,0),(11,32,0),(11,0,1),(0,0,0)):
        c.equal("M_native_reject", m.command(op,idx,data)["error"], True, "native invalid op/index/data")
    c.equal("M_native_reject", m.command(10,0,(valid & ~(15<<8) & ~4)|(2<<8))["error"], True, "append N mismatch")
    m.command(4,0,(65534 | (7<<16)))
    m.command(6)
    c.equal("M_clear_semantics", [m.factor,m.left_shift], [-2,7], "CLEAR_ALL preserves scale")
    c.equal("M_clear_semantics", m.command(3)["error"], True, "CLEAR_ALL invalidates result")
    c.domain_error("domain_reject", lambda: m.load_b(0,0,1,1,0), "B_NOT_READY", "S16 half1 without half0")
    m.load_b(0,0,1,0,0)
    c.equal("M_load_valid", m.b_valid[(0,0)], 1, "half0 alone not full B")
    c.domain_error("domain_reject", lambda: m.load_b(0,0,0,1,0), "B_NOT_READY", "S8 half1 not ready")
    c.domain_error("domain_reject", lambda: m.command(12), "NOT_MODELLED", "diagnostic op12 explicitly unsupported")
    c.domain_error("domain_reject", lambda: m.command(10,64,0), "PORT_DOMAIN", "index is a six-bit port")
    # All rows absent at first clear+overflow remain invalid, rather than becoming 0.
    overflow = {"a":[[-32768,-32768]],"b_columns":[[-32768,-32768]],"fmt_a":1,"fmt_b":1,"clear":1,"poison":0}
    m = MReference(); idx,data = fixture_load(m,overflow,0); m.command(4,0,32767 | (31<<16))
    c.equal("M_clear_semantics", m.command(10,idx,data)["fault_rows"], 1, "first clear overflow mask")
    c.equal("M_clear_semantics", m.command(3)["error"], True, "failed first clear leaves row invalid")


def test_loader(vectors,c):
    for v in vectors["loader_cases"]:
        if v.get("domain_error"):
            c.domain_error("loader_domain", lambda:loader_descriptor(v["d"]), "PORT_DOMAIN", v["id"])
            continue
        out = loader_descriptor(v["d"])
        c.equal("loader_descriptor", out["legal"], v["legal"], v["id"])
        c.equal("loader_descriptor", out["done_error"], not v["legal"], "native rejection ACK")
        if v["legal"]:
            c.equal("loader_descriptor", out["a_words"], v["a_words"], "A container budget")
            c.equal("loader_descriptor", out["b_words_read"], v["b_words"], "B half budget")
            plan = loader_plan({i:0 for i in range(1024)}, v["d"])
            c.equal("loader_request_order", [r["wide_addr"] for r in plan["reads"]], v["read_wide_addresses"], v["id"])
            c.equal("loader_request_order", len(plan["a_beats"]), v["d"]["rows"] * v["d"]["tiles"], "real rows only")
        else:
            c.equal("loader_descriptor", loader_plan({},v["d"])["reads"], [], "illegal descriptor reads nothing")
        c.case_ids.append(v["id"])
    l = vectors["layout_cases"]["s16"]
    aw, bw = pack_a_tile(l["a_rows"],1), pack_b_tile(l["b_column_rows"],1)
    c.equal("literal_layout", ["0x{:032x}".format(v) for v in aw], l["a_words"], "S16 A full row containers")
    c.equal("literal_layout", ["0x{:032x}".format(v) for v in bw], l["b_words"], "S16 B n-major words")
    memory = {i:w for i,w in enumerate(aw)}
    memory.update({8+i:w for i,w in enumerate(bw)})
    d = {"bank":0,"rows":5,"tiles":1,"a_wide":1,"b_wide":1,"reuse_b":0,"a_base":0,"b_base":8}
    plan = loader_plan(memory,d)
    c.equal("literal_layout", [r["word_base"] for r in plan["reads"]],l["read_word_bases"],"S16 half then row-group requests")
    for half,beat in enumerate(plan["b_beats"]):
        raw = beat["data"].to_bytes(64,"little")
        values = [int.from_bytes(raw[i:i+2],"little",signed=True) for i in range(0,64,2)]
        c.equal("literal_layout",values,l["b_half_values"][half],"S16 half n-major lane identities")
    c.equal("literal_layout",[b["row"] for b in plan["a_beats"]],[0,1,2,3,4],"padding rows never sent")
    l8 = vectors["layout_cases"]["s8_a"]
    c.equal("literal_layout",["0x{:032x}".format(v) for v in pack_a_tile(l8["rows"],0)],l8["words"],"S8 A high64 zero and group padding")
    c.domain_error("loader_fixture_domain",lambda:loader_plan({},d),"UNINITIALIZED_FIXTURE","Python refuses unknown fixture bytes; RTL has no uninitialized error")


def test_t(vectors,c):
    for seq in vectors["t_sequences"]:
        t = TReference()
        for index,step in enumerate(seq["steps"]):
            out = t.tick(**step["in"])
            for phase in ("before","after"):
                for key,value in step.get(phase,{}).items():
                    c.equal("literal_T_protocol",out[phase][key],value,"{}/{}/{}/{}".format(seq["id"],index,phase,key))
            if out["before"]["read_valid"] and not step["in"].get("read_take") and not step["in"].get("reset"):
                for field in ("read_data","read_index","read_last","read_valid"):
                    c.equal("T_behavioral_hold",out["after"][field],out["before"][field],"Python read holding register")
        c.case_ids.append(seq["id"])
    # Native capacity endpoint; all expected data are an explicit integer sequence.
    t = TReference()
    c.equal("T_capacity",t.tick(begin_valid=1,begin_words=384)["fires"]["begin"],True,"384-word accepted")
    for i in range(384):
        c.equal("T_capacity",t.tick(write_valid=1,write_index=i,write_data=1000+i)["fires"]["write"],True,"sequential fill")
    c.equal("T_capacity",t.tick(commit_valid=1)["after"]["state"],"READ_REQ","full batch commit")
    t.tick()
    for i in range(384):
        out = t.tick(read_take=1)
        c.equal("T_capacity",[out["before"]["read_index"],out["before"]["read_data"],out["before"]["read_last"]],[i,1000+i,i==383],"full batch immutable order")
    c.equal("T_capacity",t.tick(begin_valid=1,begin_words=1)["fires"]["begin"],False,"last take does not release")
    c.equal("T_capacity",t.tick(release_valid=1)["after"]["state"],"EMPTY","explicit release")
    t.tick(reset=1)
    c.equal("T_reset",t.payload[383],1383,"reset does not zero payload storage")
    c.equal("T_reset",t.outputs()[1]["read_valid"],False,"old payload not published after reset")
    c.domain_error("domain_reject",lambda:t.tick(begin_words=1024),"PORT_DOMAIN","T words pin overflow is not native illegal-size response")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",type=Path,default=Path("."))
    ap.add_argument("--vector-file",type=Path,default=HERE/"phase1-mst-vectors.json")
    ap.add_argument("--output",type=Path,default=HERE/"reference-verification.json")
    args = ap.parse_args()
    c = Checks(); sources = []
    for path,sha,lines in FROZEN_SOURCES:
        fp = fingerprint(args.source_root/path)
        c.equal("source_fingerprint",fp["sha256"],sha,path)
        sources.append(dict(fp,path=path,ref=FROZEN_REF,line_evidence=lines,
                            url="https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"+FROZEN_REF+"/"+path))
    vectors = json.loads(args.vector_file.read_text(encoding="utf-8"))
    c.equal("source_fingerprint",vectors["frozen_leaf_ref"],FROZEN_REF,"vector freeze")
    test_minimal(vectors,c); test_arithmetic(vectors,c); test_exec(vectors,c)
    test_m_rejections(c); test_loader(vectors,c); test_t(vectors,c)
    artifacts = []
    for path in (HERE/"phase1_mst_reference.py",args.vector_file,Path(__file__).resolve()):
        fp = fingerprint(path)
        c.equal("artifact_encoding",fp["lf_only"],True,str(path.name)+" LF")
        artifacts.append(dict(fp,name=path.name))
    receipt = {"schema_version":1,"status":"PASS_BOUNDED_PYTHON_REFERENCE_ONLY",
               "issue":"https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151",
               "frozen_leaf_ref":FROZEN_REF,"research_input_ref":"343f4d4775ffab61b2ed2df13de243cc659c157a",
               "tool":{"python":platform.python_version(),"implementation":platform.python_implementation(),"platform":platform.platform(),"third_party_dependencies":[]},
               "reproduction":"python -B verify_phase1_mst_reference.py --source-root <643c6012 source root> --vector-file phase1-mst-vectors.json --output <receipt.json>",
               "check_counts":c.counts,"checks_total":sum(c.counts.values()),"literal_case_ids":c.case_ids,
               "sources":sources,"artifacts":artifacts,
               "source_root_is_local_snapshot_not_git_checkout_claim":True,
               "scope":{"M_atomic_integer_reference":True,"loader_descriptor_layout_reference":True,"T_behavioral_clock_reference":True,
                        "M_pipeline_or_ready_valid_equivalence":False,"S_arbitration_or_loader_queue_cycle_model":False,
                        "RTL_executed":False,"RTL_handshake_passed":False,"system_top_implemented":False,
                        "all_M_opcodes_golden":False,"complete_model_compiled":False,"quantization_quality_validated":False,
                        "SystemC_executed":False,"EDA_executed":False,"server_used":False},
               "future_RTL_cases_NOT_EXECUTED":vectors["future_rtl_cases_not_executed"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print("PASS: {} bounded Python assertions; RTL not executed; receipt={}".format(sum(c.counts.values()),args.output))


if __name__ == "__main__":
    main()
