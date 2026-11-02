#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent full-H/full-D AH2 integer fixtures. Python 3.7+, no RTL run.

One KV head and adjacent Q0/Q1, two tokens: this is not complete Attention,
Wo/residual/cache, trained-model quality, an RTL state machine or a cycle model.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
IDS = ("base", "future_changed", "boundary")
H, D, TOKENS, HEADS = 1024, 128, 2, 2
EXP = [round(math.exp(-16 + i / 64) * 32768) for i in range(1025)]
NATIVE = ["project/rtl/block_v2/block_v2_m.sv",
          "project/rtl/block_v2/block_v2_n.sv",
          "project/rtl/block_v2/block_v2_n_exp.svh",
          "project/rtl/block_v2/block_v2_e.sv",
          "project/rtl/block_feed_v1/block_feed_loader.sv"]


def digest(data): return hashlib.sha256(data).hexdigest()


def jb(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def rne(v, shift):
    if shift < 0: raise ValueError("negative RNE shift")
    if not shift: return v
    q, rem = divmod(v, 1 << shift)
    return q + int(rem > (1 << (shift - 1)) or
                   (rem == (1 << (shift - 1)) and q & 1))


def clip(v): return max(-32768, min(32767, v)), not -32768 <= v <= 32767


def floor_sqrt(n):
    if n < 0: raise ValueError("negative square root")
    if n < 2: return n
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x: return x
        x = y


def rms(x, gamma, epsilon=1):
    if not x or len(x) != len(gamma) or epsilon < 1:
        raise ValueError("RMS shape/epsilon")
    if any(not -32768 <= v <= 32767 for v in x + gamma):
        raise ValueError("RMS signed16 range")
    rad = (sum(v * v for v in x) << 16) // len(x) + (epsilon << 16)
    root = floor_sqrt(rad)
    factor = (1 << 38) // root
    values = [clip(rne(v * factor * g, 30)) for v, g in zip(x, gamma)]
    return {"output": [v for v, sat in values], "saturated": any(s for v, s in values),
            "clipped_elements": sum(int(s) for v, s in values), "count": len(x),
            "sumsq": sum(v * v for v in x), "radicand": rad, "root": root, "factor": factor}


def exp_code(difference):
    if difference < -16384: return 0
    if difference >= 0: return 32768
    index, frac = divmod(difference + 16384, 16)
    return EXP[index] + rne((EXP[index + 1] - EXP[index]) * frac, 4)


def softmax(scores, count):
    if len(scores) != 2 or count not in (1, 2): raise ValueError("AH2 causal shape/count")
    maximum = max(scores[:count])
    ex = [exp_code(x - maximum) for x in scores[:count]]
    factor = (1 << 44) // sum(ex)
    raw = [rne(x * factor, 30) for x in ex]
    prob = [max(0, min(16384, x)) for x in raw]
    return {"count": count, "maximum": maximum, "exp": ex + [0] * (2 - count),
            "prob": prob + [0] * (2 - count), "factor": factor, "exp_sum": sum(ex),
            "saturated": any(x != y for x, y in zip(raw, prob))}


def mix32(v):
    v &= 0xffffffff
    v = ((v ^ (v >> 16)) * 0x7feb352d) & 0xffffffff
    v = ((v ^ (v >> 15)) * 0x846ca68b) & 0xffffffff
    return (v ^ (v >> 16)) & 0xffffffff


def weight(matrix, n, k):
    return mix32((matrix + 1) * 0x9e3779b9 ^
                 (n + 1) * 0x045d9f3b ^ (k + 1) * 0x27d4eb2d) % 17 - 8


def parameters():
    hgamma = [1024 + (k % 17) * 4 for k in range(H)]
    qgamma = [1024 + ((k * 7) % 33) - 16 for k in range(D)]
    kgamma = [1024 + ((k * 11) % 65) - 32 for k in range(D)]
    coeff = []
    for position in range(2):
        row = []
        for pair in range(64):
            angle = position / (1000000 ** (2 * pair / 128))
            row.extend([round(math.cos(angle) * 16384), round(math.sin(angle) * 16384)])
        coeff.append(row)
    matrices = [[[weight(m, n, k) for k in range(H)] for n in range(D)] for m in range(4)]
    return hgamma, qgamma, kgamma, coeff, matrices


def inputs(name):
    rows = [[mix32(0x1937 + t * 100003 + k) % 4097 - 2048 for k in range(H)] for t in range(2)]
    if name == "future_changed":
        rows[1] = [-v + (k % 7 - 3) * 31 for k, v in enumerate(rows[1])]
    elif name == "boundary":
        rows = [[0] * H for _ in range(2)]
        rows[0][16], rows[0][512] = 32767, -1
        rows[1][1002], rows[1][31] = -32768, 1
    elif name != "base": raise ValueError("fixture name")
    return rows


def word_values(values):
    if len(values) % 8: raise ValueError("whole compact eight-lane words required")
    if any(not -32768 <= v <= 65535 for v in values): raise ValueError("16-bit code range")
    return [sum((v & 65535) << (16 * lane) for lane, v in enumerate(values[i:i + 8]))
            for i in range(0, len(values), 8)]


def words_bytes(words): return b"".join(v.to_bytes(16, "little") for v in words)
def words_hex(words): return ("".join("%032x\n" % v for v in words)).encode("ascii")
def flatten(rows): return [v for row in rows for v in row]


def pack_weight_stream(matrices):
    # Native B512: one 64-byte K8 tile contains eight columns of eight K.
    # A request is four such tiles, not eight columns of contiguous K32.
    return bytes(matrices[m][8 * group + n][32 * chunk + 8 * tile + k] & 255
                 for m in range(4) for group in range(16) for chunk in range(32)
                 for tile in range(4) for n in range(8) for k in range(8))


def project(rows, columns, shift=7, factor=1):
    if any(len(row) != len(col) for row in rows for col in columns): raise ValueError("dot shape")
    raw = [[sum(a * b for a, b in zip(row, col)) for col in columns] for row in rows]
    values = [[clip(rne(v * factor, shift)) for v in row] for row in raw]
    return {"raw": raw, "output": [[v for v, sat in row] for row in values],
            "saturated": any(sat for row in values for v, sat in row),
            "clipped_elements": sum(int(s) for row in values for v, s in row)}


def split_half_pair(row):
    if len(row) != D: raise ValueError("AH2 head dimension must remain 128")
    return [row[p // 2 + (64 if p % 2 else 0)] for p in range(D)]


def rotate(paired, coeff):
    values = []
    for i in range(0, D, 2):
        a, b, c, s = paired[i], paired[i + 1], coeff[i], coeff[i + 1]
        values.extend([clip(rne(a * c - b * s, 14)), clip(rne(b * c + a * s, 14))])
    return {"output": [v for v, sat in values], "saturated": any(s for v, s in values),
            "clipped_elements": sum(int(s) for v, s in values)}


def oracle(name, params):
    hg, qg, kg, coeff, matrices = params
    x = inputs(name)
    norm = [rms(row, hg) for row in x]
    projections = [project([r["output"] for r in norm], matrix) for matrix in matrices]
    kraw, v, q0, q1 = [p["output"] for p in projections]
    krms = [rms(row, kg) for row in kraw]
    qrms = [[rms(row, qg) for row in qraw] for qraw in (q0, q1)]
    kp = [split_half_pair(r["output"]) for r in krms]
    qp = [[split_half_pair(r["output"]) for r in head] for head in qrms]
    kr = [rotate(kp[t], coeff[t]) for t in range(2)]
    qr = [[rotate(qp[h][t], coeff[t]) for t in range(2)] for h in range(2)]
    scores = [project([q["output"] for q in head], [k["output"] for k in kr], 25, 2896) for head in qr]
    sm = [[softmax(scores[h]["output"][t], t + 1) for t in range(2)] for h in range(2)]
    context = [project([r["prob"] for r in sm[h]], [[v[0][c], v[1][c]] for c in range(D)], 14)
               for h in range(2)]
    output = [value for t in range(2) for h in range(2) for value in context[h]["output"][t]]
    stage = {}
    def put(role, values): stage["stage/" + role + ".hex"] = words_hex(word_values(values))
    put("norm", flatten([r["output"] for r in norm]))
    put("kraw", flatten(kraw)); put("v", flatten(v))
    put("qraw", [a for t in range(2) for h in range(2) for a in (q0, q1)[h][t]])
    put("k-rms", flatten([r["output"] for r in krms]))
    put("q-rms", [a for t in range(2) for h in range(2) for a in qrms[h][t]["output"]])
    put("k-pair", flatten(kp)); put("q-pair", [a for t in range(2) for h in range(2) for a in qp[h][t]])
    put("k-rope", flatten([r["output"] for r in kr]))
    put("q-rope", [a for t in range(2) for h in range(2) for a in qr[h][t]["output"]])
    put("scores", [a for t in range(2) for h in range(2) for a in scores[h]["output"][t] + [0] * 6])
    for role, key in (("exp", "exp"), ("p", "prob")):
        put(role, [a for t in range(2) for h in range(2) for a in sm[h][t][key] + [0] * 6])
    put("context", output)
    flags = {"input_RMS": any(r["saturated"] for r in norm),
             "M_K": projections[0]["saturated"], "M_V": projections[1]["saturated"],
             "M_Q0": projections[2]["saturated"], "M_Q1": projections[3]["saturated"],
             "K_head_RMS": any(r["saturated"] for r in krms),
             "Q_head_RMS": any(r["saturated"] for head in qrms for r in head),
             "E_RoPE": any(r["saturated"] for r in kr + [r for head in qr for r in head]),
             "M_QK": any(r["saturated"] for r in scores),
             "N_Softmax": any(r["saturated"] for head in sm for r in head),
             "M_PV": any(r["saturated"] for r in context)}
    ingress = word_values(flatten(x) + hg + qg + kg + flatten(coeff))
    expected = word_values(output)
    weights = pack_weight_stream(matrices)
    files = {"input.hex": words_hex(ingress), "input.bin": words_bytes(ingress),
             "weights.bin": weights,
             "weights.hex": words_hex([int.from_bytes(weights[i:i + 16], "little") for i in range(0, len(weights), 16)]),
             "expected-output.hex": words_hex(expected), "expected.bin": words_bytes(expected)}
    files.update(stage)
    # Raw dot products are full mathematical reductions, never RTL partial state.
    math_data = {"X": x, "input_RMS": norm, "projections_K_V_Q0_Q1": projections,
                 "K_head_RMS": krms, "Q_head_RMS_head_token": qrms,
                 "K_pair": kp, "Q_pair_head_token": qp,
                 "K_RoPE": kr, "Q_RoPE_head_token": qr,
                 "QK_head_token_key": scores, "softmax_head_token": sm,
                 "PV_head_token_channel": context, "stage_saturated": flags,
                 "expected_done_saturated": any(flags.values())}
    files["math.json"] = jb(math_data)
    return files, math_data


def stage_address_map():
    roles = {}
    def role(name, count, index, address, version):
        roles[name] = {"file": "stage/" + name + ".hex", "word_count": count,
                       "word_index": index, "S_address": address, "version": version}
    role("norm", 256, "token*128+group", "token==0 ? 384+group : group", "complete input RMS1024")
    for name, base in (("kraw", 192), ("v", 224), ("k-rope", 192)):
        role(name, 32, "token*16+group", "%d+16*token+group" % base, name)
    for name, base in (("qraw", 256), ("q-rope", 256)):
        role(name, 64, "(token*2+head)*16+group", "%d+16*token+group (reused for each head)" % base, name)
    role("k-rms", 32, "token*16+group", "288+16*token+group", "K RMS128 scratch, before Q reuse")
    role("q-rms", 64, "(token*2+head)*16+group", "288+16*token+group (reused for each head)", "Q RMS128 scratch")
    role("k-pair", 32, "token*16+group", "374 (one gathered block at a time)", "split-half K pair source before E")
    role("q-pair", 64, "(token*2+head)*16+group", "374 (one gathered block at a time)", "split-half Q pair source before E")
    for name, base in (("scores", 368), ("exp", 370), ("p", 372)):
        role(name, 4, "token*2+head", "%d+token (reused for each head)" % base,
             "two scores including future; EXP/P mask by count1/2" if name == "scores" else "U16 EXP" if name == "exp" else "nonnegative S16 Q14 probability")
    role("context", 64, "(token*2+head)*16+group", "512+256*token+16*head+group", "V channel axis, never split-half permuted")
    return {"classification": "mathematical role/address/version map, not an FSM/cycle/write-order trace",
            "input": {"words0_383": "S[word_index]", "words384_447": "S[512+word_index-384]",
                      "relocation": "input words384..447 -> S128..191 after their source lifetimes end"},
            "roles": roles, "coefficient_E_source": "S160+16*token+group; no S375 copy",
            "output": "tokenmajor, then Q0/Q1, then 16 channel groups; S512..543 and S768..799"}


def self_check(root, results, params):
    literal = [(1,1,0),(3,1,2),(5,1,2),(-1,1,0),(-3,1,-2),(-5,1,-2),(32767,0,32767)]
    for v, s, expected in literal:
        if rne(v, s) != expected: raise AssertionError("literal signed RNE")
    for n in [0,1,2,3,4,65535,65536,(1<<64)-1]:
        q = floor_sqrt(n)
        if not q*q <= n < (q+1)*(q+1): raise AssertionError("integer root floor")
    if rms([0]*1024, [1024]*1024)["output"] != [0]*1024: raise AssertionError("zero RMS1024")
    if rms([1024,1024],[1024,1024])["output"] != [1024,1024]: raise AssertionError("literal RMS unit")
    if softmax([-32768,32767],1)["prob"] != [16384,0]: raise AssertionError("future key leaked into prefix")
    if softmax([0,0],2)["prob"] != [8192,8192]: raise AssertionError("literal equal softmax")
    rotated = rotate([v for _ in range(64) for v in (1024,-1024)], [v for _ in range(64) for v in (0,16384)])
    if rotated["output"] != [1024]*128: raise AssertionError("literal quarter-turn RoPE")
    rejected = 0
    for fn in [lambda:rms([1],[1024,1024]),lambda:rms([1],[1024],0),lambda:split_half_pair([1]*8),lambda:softmax([0,0],0),lambda:rne(1,-1)]:
        try: fn()
        except ValueError: rejected += 1
        else: raise AssertionError("negative admission accepted")
    # Reconstruct actual native radix-128 S16 digits mathematically for all codes.
    for v in range(-32768,32768):
        d0, d1, d2 = v & 127, (v >> 7) & 127, v >> 14
        if d0 + 128*d1 + 16384*d2 != v: raise AssertionError("S16 digit reconstruction")
        for w in (-128,-1,0,1,127):
            if d0*w + 128*d1*w + 16384*d2*w != v*w: raise AssertionError("S16xS8 exact source mapping")
    table = (root / NATIVE[2]).read_text(encoding="utf-8")
    parsed = {int(i):int(v) for i,v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+);",table)}
    if parsed != dict(enumerate(EXP)): raise AssertionError("math-generated EXP/native source mismatch")
    stream = results["base"][0]["weights.bin"]
    matrices = params[4]
    if len(stream) != 524288: raise AssertionError("weight stream incomplete")
    for m in range(4):
        for n in range(128):
            for k in range(1024):
                offset = ((m*16+n//8)*32+k//32)*256+64*((k%32)//8)+8*(n%8)+k%8
                encoded=stream[offset]; decoded=encoded-256 if encoded>=128 else encoded
                if decoded != matrices[m][n][k]: raise AssertionError("tile-major B512 pack")
    # A separate stream-coordinate dot recomputes every projection raw dot.
    raw_dots=0
    for name, (files, data) in results.items():
        norm=[r["output"] for r in data["input_RMS"]]
        for m in range(4):
            for token in range(2):
                for n in range(128):
                    total=0
                    for k,a in enumerate(norm[token]):
                        off=((m*16+n//8)*32+k//32)*256+64*((k%32)//8)+8*(n%8)+k%8
                        b=stream[off];b=b-256 if b>=128 else b;total+=a*b
                    if total!=data["projections_K_V_Q0_Q1"][m]["raw"][token][n]:raise AssertionError("full1024 raw dot/stream mismatch")
                    raw_dots+=1
        for h in range(2):
            if data["PV_head_token_channel"][h]["output"][0]!=data["projections_K_V_Q0_Q1"][1]["output"][0]:raise AssertionError("single causal key must reproduce V0")
        if not any(v for h in data["PV_head_token_channel"] for row in h["output"] for v in row):raise AssertionError("all-zero multhead false pass")
        if data["PV_head_token_channel"][0]["output"][1]==data["PV_head_token_channel"][1]["output"][1]:raise AssertionError("Q heads not distinguished at token1")
    a,b=results["base"][1],results["future_changed"][1]
    if a["X"][0]!=b["X"][0] or a["X"][1]==b["X"][1]:raise AssertionError("future fixture must change only X1")
    for h in range(2):
        if a["PV_head_token_channel"][h]["output"][0]!=b["PV_head_token_channel"][h]["output"][0]:raise AssertionError("causal token0 context changed")
    if not results["boundary"][1]["expected_done_saturated"]:raise AssertionError("boundary fixture did not exercise saturation")
    for name,(files,data) in results.items():
        if files["weights.bin"]!=stream:raise AssertionError("fixture weights changed")
        if len(files["input.bin"])!=7168 or len(files["expected.bin"])!=1024:raise AssertionError("real shape bytes changed")
    return {"literal_RNE":len(literal),"negative_rejections":rejected,"EXP_math_nodes_verified":1025,
            "S16_digit_values":65536,"S16xS8_product_probes":327680,"weight_codes_checked":524288,
            "fullK1024_raw_projection_dots_checked":raw_dots,"causal_token0_both_heads":"PASS",
            "two_Q_heads_token1_distinct_nonzero":"PASS","RMS_count_not_8":"PASS"}


def file_entries(files): return {n:{"bytes":len(v),"sha256":digest(v)} for n,v in sorted(files.items())}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=HERE.parents[3])
    ap.add_argument("--output","--output-dir",type=Path,required=True)
    ap.add_argument("--source-commit")
    ap.add_argument("--self-check",action="store_true");ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    if args.source_commit is not None and not re.fullmatch("[0-9a-fA-F]{40}",args.source_commit):ap.error("source commit must be actual 40hex")
    root=args.root.resolve();out=args.output.resolve()
    contract=json.loads((HERE/"fixture-contract.json").read_text(encoding="utf-8"))
    for source,expected in contract["source_includes"].items():
        if digest((root/source).read_bytes())!=expected:raise ValueError("native source differs: "+source)
    params=parameters();results={n:oracle(n,params) for n in IDS}
    checks=self_check(root,results,params) if args.self_check else {"status":"NOT_REQUESTED"}
    for name,(files,data) in results.items():
        if file_entries(files)!=contract["fixtures"][name]["files"]:raise ValueError("frozen fixture bytes changed: "+name)
        if data["expected_done_saturated"]!=contract["fixtures"][name]["expected_done_saturated"]:raise ValueError("saturation contract changed")
    if args.check:
        manifest=json.loads((out/"fixture-index.json").read_text(encoding="utf-8"))
        if manifest["builder_sha256"]!=digest(Path(__file__).read_bytes()) or manifest["contract_sha256"]!=digest((HERE/"fixture-contract.json").read_bytes()):raise ValueError("generator/contract source changed")
        if args.source_commit and manifest["source_commit_caller_declared"]!=args.source_commit:raise ValueError("caller source commit changed")
        for name,(files,data) in results.items():
            for filename,expected in files.items():
                if (out/name/filename).read_bytes()!=expected:raise ValueError("generated file differs: "+name+"/"+filename)
        if (out/"stage-address-map.json").read_bytes()!=jb(stage_address_map()):raise ValueError("address role map changed")
    else:
        if out.exists():raise ValueError("output exists; choose a fresh directory or --check")
        out.mkdir(parents=True)
        entries=[]
        for name,(files,data) in results.items():
            for filename,payload in files.items():
                target=out/name/filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
            entries.append({"id":name,"expected_done_saturated":data["expected_done_saturated"],
                            "stage_saturated":data["stage_saturated"],"files":file_entries(files),
                            "binary_dumps":contract["fixtures"][name]["binary_dumps"]})
        (out/"stage-address-map.json").write_bytes(jb(stage_address_map()))
        manifest={"schema_version":1,"status":"INDEPENDENT_AH2_INTEGER_FIXTURES_NOT_RTL_OR_MODEL_QUALITY",
                  "source_commit_caller_declared":args.source_commit,"builder_sha256":digest(Path(__file__).read_bytes()),
                  "contract_sha256":digest((HERE/"fixture-contract.json").read_bytes()),"source_includes":contract["source_includes"],
                  "python":platform.python_version(),"shape":contract["shape"],"self_checks":checks,"fixtures":entries,
                  "stage_address_map":{"path":"stage-address-map.json","sha256":digest(jb(stage_address_map()))}}
        (out/"fixture-index.json").write_bytes(jb(manifest))
    print(json.dumps({"status":"PASS_AH2_STATIC_INTEGER_GOLDEN_NOT_RTL","mode":"check" if args.check else "generate",
                      "output":str(out),"self_checks":checks,"fixture_index_sha256":digest((out/"fixture-index.json").read_bytes())},sort_keys=True))


if __name__=="__main__":
    try:main()
    except (ValueError,AssertionError,OSError,KeyError) as error:
        print("FAIL_AH2_GOLDEN: "+str(error),file=sys.stderr);sys.exit(1)
