#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent full H1024/Sq2/KV8/Q16/D128 A integer fixtures. Python 3.7+.

Direct mathematics includes complete context, fullK2048 Wo and original-X
residual. No DUT results, FSM or cycle model. Synthetic parameters/inputs do
not establish trained quality, cache/decode, L5, product or physical acceptance.
The bounded AFULL integer mathematical primitives are retained and generalized.
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
from array import array

HERE = Path(__file__).resolve().parent
IDS = ("base", "future_changed", "boundary")
H, D, TOKENS, HEADS, KV = 1024, 128, 2, 16, 8
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
    if len(scores) != 2 or count not in (1, 2): raise ValueError("AFULL causal shape/count")
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
    # 32 head-projection blocks: per KV, K/V/Qeven/Qodd. The first KV block
    # retains the earlier AFULL mathematical pattern; all other blocks differ.
    matrices = [[array('b', (weight(m, n, k) for k in range(H)))
                 for n in range(D)] for m in range(32)]
    matrices.append([array('b', (weight(32, n, k) for k in range(2048)))
                     for n in range(H)])
    return hgamma, qgamma, kgamma, coeff, matrices


def inputs(name):
    rows = [[mix32(0x1937 + t * 100003 + k) % 4097 - 2048 for k in range(H)] for t in range(2)]
    if name == "future_changed":
        rows[1] = [-v + (k % 7 - 3) * 31 for k, v in enumerate(rows[1])]
    elif name == "boundary":
        rows = [[0] * H for _ in range(2)]
        rows[0][33], rows[0][512] = 32767, -1
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


def request_fields(seq):
    if not 0 <= seq < 24576: raise ValueError("AFULL weight request sequence")
    if seq < 16384:
        kv, local = divmod(seq, 2048)
        part, local = divmod(local, 512)
        group, chunk = divmod(local, 32)
        matrix = part if part < 2 else 2
        head = kv if part < 2 else 2 * kv + part - 2
        return matrix, head, group, chunk, 4 * kv + part
    group, chunk = divmod(seq - 16384, 64)
    return 3, 0, group, chunk, 32


def pack_weight_stream(matrices):
    # Native B512: one 64-byte K8 tile contains eight columns of eight K.
    # A request is four such tiles, not eight columns of contiguous K32.
    data = bytearray()
    for seq in range(24576):
        matrix, head, group, chunk, block = request_fields(seq)
        data.extend(matrices[block][8 * group + n][32 * chunk + 8 * tile + k] & 255
                    for tile in range(4) for n in range(8) for k in range(8))
    return bytes(data)


def project(rows, columns, shift=7, factor=1):
    if any(len(row) != len(col) for row in rows for col in columns): raise ValueError("dot shape")
    raw = [[sum(a * b for a, b in zip(row, col)) for col in columns] for row in rows]
    values = [[clip(rne(v * factor, shift)) for v in row] for row in raw]
    return {"raw": raw, "output": [[v for v, sat in row] for row in values],
            "saturated": any(sat for row in values for v, sat in row),
            "clipped_elements": sum(int(s) for row in values for v, s in row)}


def split_half_pair(row):
    if len(row) != D: raise ValueError("AFULL head dimension must remain 128")
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
    projections = [project([r["output"] for r in norm], matrix) for matrix in matrices[:32]]
    kraw = [projections[4 * kv]["output"] for kv in range(KV)]
    v = [projections[4 * kv + 1]["output"] for kv in range(KV)]
    qraw = [projections[4 * (h // 2) + 2 + h % 2]["output"] for h in range(HEADS)]
    krms = [[rms(row, kg) for row in head] for head in kraw]
    qrms = [[rms(row, qg) for row in head] for head in qraw]
    kp = [[split_half_pair(r["output"]) for r in head] for head in krms]
    qp = [[split_half_pair(r["output"]) for r in head] for head in qrms]
    kr = [[rotate(kp[kv][t], coeff[t]) for t in range(2)] for kv in range(KV)]
    qr = [[rotate(qp[h][t], coeff[t]) for t in range(2)] for h in range(HEADS)]
    scores = [project([q["output"] for q in qr[h]],
                      [k["output"] for k in kr[h // 2]], 25, 2896) for h in range(HEADS)]
    sm = [[softmax(scores[h]["output"][t], t + 1) for t in range(2)] for h in range(HEADS)]
    context = [project([r["prob"] for r in sm[h]],
                       [[v[h // 2][0][c], v[h // 2][1][c]] for c in range(D)], 14)
               for h in range(HEADS)]
    context_rows = [[value for h in range(HEADS) for value in context[h]["output"][t]] for t in range(2)]
    wo = project(context_rows, matrices[32])
    added = [[clip(x[t][c] + wo["output"][t][c]) for c in range(H)] for t in range(2)]
    output = [value for row in added for value, sat in row]
    stage = {}
    def put(role, values): stage["stage/" + role + ".hex"] = words_hex(word_values(values))
    put("norm", flatten([r["output"] for r in norm]))
    put("kraw", [a for t in range(2) for kv in range(KV) for a in kraw[kv][t]])
    put("v", [a for t in range(2) for kv in range(KV) for a in v[kv][t]])
    put("qraw", [a for t in range(2) for h in range(HEADS) for a in qraw[h][t]])
    put("k-rms", [a for t in range(2) for kv in range(KV) for a in krms[kv][t]["output"]])
    put("q-rms", [a for t in range(2) for h in range(HEADS) for a in qrms[h][t]["output"]])
    put("k-pair", [a for t in range(2) for kv in range(KV) for a in kp[kv][t]])
    put("q-pair", [a for t in range(2) for h in range(HEADS) for a in qp[h][t]])
    put("k-rope", [a for t in range(2) for kv in range(KV) for a in kr[kv][t]["output"]])
    put("q-rope", [a for t in range(2) for h in range(HEADS) for a in qr[h][t]["output"]])
    put("scores", [a for t in range(2) for h in range(HEADS) for a in scores[h]["output"][t] + [0] * 6])
    for role, key in (("exp", "exp"), ("p", "prob")):
        put(role, [a for t in range(2) for h in range(HEADS) for a in sm[h][t][key] + [0] * 6])
    put("context", flatten(context_rows)); put("wo", flatten(wo["output"])); put("y", output)
    put("raw-x-spool", [a for g in range(128) for t in range(2) for a in x[t][8*g:8*g+8]])
    flags = {"input_RMS": any(r["saturated"] for r in norm),
             "M_K": any(projections[4*k]["saturated"] for k in range(KV)),
             "M_V": any(projections[4*k+1]["saturated"] for k in range(KV)),
             "M_Q": any(projections[4*(h//2)+2+h%2]["saturated"] for h in range(HEADS)),
             "K_head_RMS": any(r["saturated"] for head in krms for r in head),
             "Q_head_RMS": any(r["saturated"] for head in qrms for r in head),
             "E_RoPE": any(r["saturated"] for head in kr + qr for r in head),
             "M_QK": any(r["saturated"] for r in scores),
             "N_Softmax": any(r["saturated"] for head in sm for r in head),
             "M_PV": any(r["saturated"] for r in context), "M_Wo": wo["saturated"],
             "E_residual": any(s for row in added for value, s in row)}
    ingress = word_values(flatten(x) + hg + qg + kg + flatten(coeff))
    expected = word_values(output)
    weights = pack_weight_stream(matrices)
    files = {"input.hex": words_hex(ingress), "input.bin": words_bytes(ingress),
             "weights.bin": weights,
             "weights.hex": words_hex([int.from_bytes(weights[i:i + 16], "little") for i in range(0, len(weights), 16)]),
             "expected-output.hex": words_hex(expected), "expected.bin": words_bytes(expected),
             "expected-saturated.hex": b"1\n" if any(flags.values()) else b"0\n"}
    files.update(stage)
    # Raw dot products are full mathematical reductions, never RTL partial state.
    math_data = {"X": x, "input_RMS": norm, "head_projections_kv_part": projections,
                 "K_head_RMS_kv_token": krms, "Q_head_RMS_head_token": qrms,
                 "K_pair_kv_token": kp, "Q_pair_head_token": qp,
                 "K_RoPE_kv_token": kr, "Q_RoPE_head_token": qr,
                 "QK_head_token_key": scores, "softmax_head_token": sm,
                 "PV_head_token_channel": context, "context_token_channel": context_rows,
                 "Wo": wo, "Y": [list(v for v,s in row) for row in added], "stage_saturated": flags,
                 "expected_done_saturated": any(flags.values())}
    files["math.json"] = jb(math_data)
    return files, math_data


def stage_address_map():
    roles = {}
    def role(name, count, index, address, version):
        roles[name] = {"file":"stage/"+name+".hex", "word_count":count,
                       "word_index":index, "S_address":address, "version":version}
    role("norm",256,"token*128+group","token==0 ? 384+group : group","complete RMS1024")
    for name,base in (("kraw",192),("v",224),("k-rope",192)):
        role(name,256,"(token*8+kv)*16+group","%d+16*token+group (reused for each KV)"%base,name)
    for name in ("qraw","q-rope"):
        role(name,512,"(token*16+head)*16+group","256+16*token+group (reused for each Q head)",name)
    role("k-rms",256,"(token*8+kv)*16+group","288+16*token+group","K RMS128 scratch")
    role("q-rms",512,"(token*16+head)*16+group","288+16*token+group","Q RMS128 scratch")
    role("k-pair",256,"(token*8+kv)*16+group","374","split-half K before E")
    role("q-pair",512,"(token*16+head)*16+group","374","split-half Q before E")
    for name,base in (("scores",368),("exp",370),("p",372)):
        role(name,32,"token*16+head","%d+token (reused for each Q head)"%base,
             "both raw scores retained" if name=="scores" else "U16 EXP count1/2 tailzero" if name=="exp" else "S16 Q14 probability count1/2 tailzero")
    role("context",512,"token*256+head*16+group","512+token*256+head*16+group","complete 8192B context; V original axis")
    role("wo",256,"token*128+group","256+token (reused for each group)","fullK2048 Wo RNE7, before residual")
    role("y",256,"token*128+group","token==0 ? group : 384+group","original X + Wo saturating S16")
    role("raw-x-spool",256,"2*group+token","T[2*group+token], then restored to S258",
         "exact original X, group-interleaved; not normalized X")
    return {"classification":"mathematical role/address/version map, not FSM/cycle/write-order trace",
            "input":{"words0_383":"S[word_index]","words384_447":"S[512+word_index-384]",
                     "relocation":"input384..447 -> S128..191 before context uses S512..1023"},
            "roles":roles,"coefficient_E_source":"S160+16*token+group",
            "T_raw_lease":{"word_count":256,"bytes":4096,"order":"2*group+token"},
            "T_output_lease":{"word_count":256,"bytes":4096,"order":"token*128+group"},
            "lifetime":["raw X T COMMIT before original S overwritten",
                        "all 512 context words exist before first Wo group",
                        "each Wo group finishes all64 K32 chunks before READ7",
                        "T raw capture -> S258 ACK -> E residual destination ACK",
                        "last residual ACK and raw T RELEASE before final T BEGIN",
                        "one S/M/N/E/T resource set; no parallel duplicate tops"],
            "output":"Y tokenmajor256words, S0..127 and384..511; context is not host final output"}

def self_check(root, results, params):
    literals=[(1,1,0),(3,1,2),(5,1,2),(-1,1,0),(-3,1,-2),(-5,1,-2),(32767,0,32767)]
    for v,shift,expected in literals:
        if rne(v,shift)!=expected:raise AssertionError("literal signed RNE")
    for n in [0,1,2,3,4,65535,65536,(1<<64)-1]:
        q=floor_sqrt(n)
        if not q*q<=n<(q+1)*(q+1):raise AssertionError("floor root")
    if rms([0]*1024,[1024]*1024)["output"]!=[0]*1024:raise AssertionError("zero RMS1024")
    if rms([1024,1024],[1024,1024])["output"]!=[1024,1024]:raise AssertionError("literal RMS")
    if softmax([-32768,32767],1)["prob"]!=[16384,0]:raise AssertionError("prefix causal maximum")
    if softmax([0,0],2)["prob"]!=[8192,8192]:raise AssertionError("equal softmax")
    turn=rotate([v for _ in range(64) for v in (1024,-1024)],[v for _ in range(64) for v in (0,16384)])
    if turn["output"]!=[1024]*128:raise AssertionError("quarterturn RoPE")
    add_literals=[(32767,1,32767,True),(-32768,-1,-32768,True),(-16384,-16384,-32768,False),(32767,-32768,-1,False),(1,-2,-1,False)]
    for x,w,y,sat in add_literals:
        if clip(x+w)!=(y,sat):raise AssertionError("literal original residual")
    rejected=0
    for fn in [lambda:rms([1],[1024,1024]),lambda:rms([1],[1024],0),lambda:split_half_pair([1]*8),lambda:softmax([0,0],0),lambda:rne(1,-1),lambda:request_fields(-1),lambda:request_fields(24576)]:
        try:fn()
        except ValueError:rejected+=1
        else:raise AssertionError("negative admission accepted")
    for v in range(-32768,32768):
        d0,d1,d2=v&127,(v>>7)&127,v>>14
        if d0+128*d1+16384*d2!=v:raise AssertionError("S16 digit reconstruction")
        for w in (-128,-1,0,1,127):
            if d0*w+128*d1*w+16384*d2*w!=v*w:raise AssertionError("S16xS8 mapping")
    text=(root/NATIVE[2]).read_text(encoding="utf-8")
    parsed={int(i):int(v) for i,v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+);",text)}
    if parsed!=dict(enumerate(EXP)):raise AssertionError("EXP math/source mismatch")
    anchors={0:(0,0,0,0,0),512:(1,0,0,0,1),1024:(2,0,0,0,2),1536:(2,1,0,0,3),2048:(0,1,0,0,4),16383:(2,15,15,31,31),16384:(3,0,0,0,32),24575:(3,0,127,63,32)}
    for seq,tag in anchors.items():
        if request_fields(seq)!=tag:raise AssertionError("literal request tag")
    if len({request_fields(seq)[:4] for seq in range(24576)})!=24576:raise AssertionError("duplicate request tags")
    stream=results["base"][0]["weights.bin"];matrices=params[4]
    if len(stream)!=6291456:raise AssertionError("full6MiB stream missing")
    # Independent byte-to-column reconstruction, without the producer's loop order.
    decoded=[[array('b',[0])*len(col) for col in matrix] for matrix in matrices]
    for seq in range(24576):
        matrix,head,group,chunk,block=request_fields(seq)
        for offset,encoded in enumerate(stream[256*seq:256*(seq+1)]):
            tile,within=divmod(offset,64);n,k8=divmod(within,8)
            n=8*group+n;k=32*chunk+8*tile+k8
            value=encoded-256 if encoded>=128 else encoded
            if value!=matrices[block][n][k]:raise AssertionError("tile-major byte source mapping")
            decoded[block][n][k]=value
    projection_dots=qk_dots=pv_dots=0
    for name,(files,data) in results.items():
        norm=[r["output"] for r in data["input_RMS"]]
        for block in range(33):
            rows=norm if block<32 else data["context_token_channel"]
            expected=data["head_projections_kv_part"][block] if block<32 else data["Wo"]
            for token,row in enumerate(rows):
                for n,col in enumerate(decoded[block]):
                    if sum(a*b for a,b in zip(row,col))!=expected["raw"][token][n]:raise AssertionError("complete projection/Wo raw dot")
                    projection_dots+=1
        for head in range(16):
            kv=head//2
            for token in range(2):
                for key in range(2):
                    raw=sum(a*b for a,b in zip(data["Q_RoPE_head_token"][head][token]["output"],data["K_RoPE_kv_token"][kv][key]["output"]))
                    if raw!=data["QK_head_token_key"][head]["raw"][token][key]:raise AssertionError("full128 QK raw dot")
                    qk_dots+=1
                pp=data["softmax_head_token"][head][token]["prob"]
                vv=data["head_projections_kv_part"][4*kv+1]["output"]
                for c in range(128):
                    raw=pp[0]*vv[0][c]+pp[1]*vv[1][c]
                    if raw!=data["PV_head_token_channel"][head]["raw"][token][c]:raise AssertionError("PV original V raw dot")
                    pv_dots+=1
            if data["PV_head_token_channel"][head]["output"][0]!=data["head_projections_kv_part"][4*kv+1]["output"][0]:raise AssertionError("causal count1 must return V0")
        for kv in range(8):
            if data["PV_head_token_channel"][2*kv]["output"][1]==data["PV_head_token_channel"][2*kv+1]["output"][1]:raise AssertionError("two Q heads indistinguishable")
        if len({tuple(data["PV_head_token_channel"][2*kv]["output"][0]) for kv in range(8)})!=8:raise AssertionError("KV heads not distinct")
        if not any(flatten(data["Y"])):raise AssertionError("allzero Y false pass")
        if files["weights.bin"]!=stream or len(files["input.bin"])!=7168 or len(files["expected.bin"])!=4096:raise AssertionError("fixed shape/data identity changed")
        raw_x_words=word_values(flatten(data["X"]))
        spool=[raw_x_words[t*128+g] for g in range(128) for t in range(2)]
        if files["stage/raw-x-spool.hex"]!=words_hex(spool):raise AssertionError("exact raw X T permutation")
    a,b=results["base"][1],results["future_changed"][1]
    if a["X"][0]!=b["X"][0] or a["X"][1]==b["X"][1]:raise AssertionError("future fixture input scope")
    if a["context_token_channel"][0]!=b["context_token_channel"][0] or a["Y"][0]!=b["Y"][0]:raise AssertionError("future token affected token0 context/Y")
    # Detect degenerate fixtures, using counterfactual math only, never DUT data.
    if len({tuple(h["output"][1]) for h in a["PV_head_token_channel"]})!=16:raise AssertionError("token1 heads not all distinct")
    wo_values=flatten(a["Wo"]["output"])
    if not any(wo_values) or all(v in (-32768,32767) for v in wo_values):raise AssertionError("Wo collapsed to zero/endpoints")
    def final_from_context(rows):
        changed=project(rows,matrices[32])
        return [clip(a["X"][t][c]+changed["output"][t][c])[0] for t in range(2) for c in range(H)]
    normal_y=flatten(a["Y"])
    swapped=[list(row) for row in a["context_token_channel"]]
    for row in swapped:row[:128],row[256:384]=row[256:384],row[:128]
    order_diff=sum(x!=y for x,y in zip(final_from_context(swapped),normal_y))
    wrong_context=[]
    wrong_heads=[]
    for h in range(16):
        wrong_kv=h%8
        qs=project([r["output"] for r in a["Q_RoPE_head_token"][h]],
                   [r["output"] for r in a["K_RoPE_kv_token"][wrong_kv]],25,2896)
        probs=[softmax(qs["output"][t],t+1)["prob"] for t in range(2)]
        vals=a["head_projections_kv_part"][4*wrong_kv+1]["output"]
        wrong_heads.append(project(probs,[[vals[0][c],vals[1][c]] for c in range(D)],14)["output"])
    wrong_context=[[v for h in range(16) for v in wrong_heads[h][t]] for t in range(2)]
    sharing_diff=sum(x!=y for x,y in zip(final_from_context(wrong_context),normal_y))
    omit_diffs=[]
    for head in range(16):
        start=head*128;difference=0
        for t in range(2):
            segment=a["context_token_channel"][t][start:start+128]
            contributions=[sum(v*w for v,w in zip(segment,col[start:start+128])) for col in matrices[32]]
            if not any(contributions):raise AssertionError("head has no Wo raw contribution")
            for c,part in enumerate(contributions):
                dropped_wo=clip(rne(a["Wo"]["raw"][t][c]-part,7))[0]
                difference+=clip(a["X"][t][c]+dropped_wo)[0]!=a["Y"][t][c]
        omit_diffs.append(difference)
    if not order_diff or not sharing_diff or not all(omit_diffs):raise AssertionError("wrong head/order/omission is not observable")
    if not results["boundary"][1]["expected_done_saturated"]:raise AssertionError("boundary did not saturate")
    return {"literal_RNE":len(literals),"literal_residual_add":len(add_literals),"negative_rejections":rejected,
            "EXP_math_nodes_verified":1025,"S16_digit_values":65536,"S16xS8_product_probes":327680,
            "weight_codes_checked":6291456,"request_tags_unique":24576,"literal_request_anchors":len(anchors),
            "all_head_projection_and_Wo_raw_dots":projection_dots,"all_QK128_raw_dots":qk_dots,"all_PV_raw_dots":pv_dots,
            "head_projection_fullK1024_raw_dots":24576,"Wo_fullK2048_raw_dots":6144,
            "causal_token0_all16_context_and_Y":"PASS","eight_distinct_KV_and_Qpairs":"PASS","T256_raw_X_permutation":"PASS",
            "base_Wo_nonzero_elements":sum(v!=0 for v in wo_values),"base_Wo_clipped":a["Wo"]["clipped_elements"],
            "negative_head_order_swap_Y_changed":order_diff,"negative_wrong_KV_sharing_Y_changed":sharing_diff,
            "negative_each_head_omitted_Y_changed":omit_diffs}

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
        manifest={"schema_version":1,"status":"INDEPENDENT_AFULL_SQ2_INTEGER_NOT_RTL_OR_MODEL_QUALITY",
                  "source_commit_caller_declared":args.source_commit,"builder_sha256":digest(Path(__file__).read_bytes()),
                  "contract_sha256":digest((HERE/"fixture-contract.json").read_bytes()),"source_includes":contract["source_includes"],
                  "python":platform.python_version(),"shape":contract["shape"],"self_checks":checks,"fixtures":entries,
                  "stage_address_map":{"path":"stage-address-map.json","sha256":digest(jb(stage_address_map()))}}
        (out/"fixture-index.json").write_bytes(jb(manifest))
    print(json.dumps({"status":"PASS_AFULL_STATIC_INTEGER_GOLDEN_NOT_RTL","mode":"check" if args.check else "generate",
                      "output":str(out),"self_checks":checks,"fixture_index_sha256":digest((out/"fixture-index.json").read_bytes())},sort_keys=True))


if __name__=="__main__":
    try:main()
    except (ValueError,AssertionError,OSError,KeyError) as error:
        print("FAIL_AFULL_GOLDEN: "+str(error),file=sys.stderr);sys.exit(1)
