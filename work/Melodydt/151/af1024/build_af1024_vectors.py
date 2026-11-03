#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent synthetic full-A Y -> baseline F1024 Z composition.

Python3.7+. Imports fixed mathematical helpers, not DUT outputs, memory traces,
or RTL FSMs. No trained-quality, generic-network, product or physical claim.
"""
import argparse
from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys

HERE = Path(__file__).resolve().parent
IDS = ("base", "future_changed", "boundary")
F_SEED = 17
REFERENCES = ["work/Melodydt/151/afull/build_afull_vectors.py",
              "work/Melodydt/151/f1024_integer_reference.py",
              "work/Melodydt/151/f16_integer_reference.py"]
NATIVE = ["project/rtl/block_v2/block_v2_m.sv", "project/rtl/block_v2/block_v2_n.sv",
          "project/rtl/block_v2/block_v2_n_exp.svh", "project/rtl/block_v2/block_v2_e.sv",
          "project/rtl/block_feed_v1/block_feed_loader.sv",
          "project/rtl/block_v2/block_v2_g.sv", "project/rtl/block_v2/block_v2_g_tables.svh"]


def sha(data): return hashlib.sha256(data).hexdigest()
def jb(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    # Compile/exec avoids writing bytecode into the read-only reference tree.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def gamma_f(): return [16 + (c * 5) % 17 for c in range(1024)]
def hex_bytes(words): return ("".join(word + "\n" for word in words)).encode("ascii")
def binary_words(words): return b"".join(int(word, 16).to_bytes(16, "little") for word in words)


def f_columns(F):
    return [[array('b', (F.weight(matrix, n, k, F_SEED) for k in range(width)))
             for n in range(outputs)]
            for matrix, outputs, width in ((0,3072,1024),(1,3072,1024),(2,1024,3072))]


def f_stream(F, columns):
    data = bytearray()
    for seq in range(36864):
        matrix, group, chunk = F.request_fields(seq)
        data.extend(columns[matrix][8*group+n][32*chunk+8*tile+k] & 255
                    for tile in range(4) for n in range(8) for k in range(8))
    if len(data) != 9437184: raise AssertionError("F full9MiB stream")
    return bytes(data)


def output_files(name, a_files, a_data, f_rows, f_weights, f_hex, A):
    fg = gamma_f()
    gamma_words = ["%032x" % w for w in A.word_values(fg)]
    a_input = a_files["input.bin"]
    parent_input = a_input + binary_words(gamma_words)
    y_words = a_files["expected-output.hex"]
    z_words = [w for row in f_rows for w in row["words"]["output"]]
    a_sat = a_data["expected_done_saturated"]
    f_sat = [row["done_saturated"] for row in f_rows]
    parent_sat = a_sat or any(f_sat)
    files = {
        "input.bin": parent_input,
        "input.hex": A.words_hex([int.from_bytes(parent_input[i:i+16],"little") for i in range(0,len(parent_input),16)]),
        "a-weights.bin": a_files["weights.bin"], "a-weights.hex": a_files["weights.hex"],
        "f-weights.bin": f_weights, "f-weights.hex": f_hex,
        "f-weights-two-rows.bin": f_weights + f_weights,
        "f-gamma.hex": hex_bytes(gamma_words),
        "expected-a-output.hex": y_words, "expected-a-output.bin": a_files["expected.bin"],
        "expected-output.hex": hex_bytes(z_words), "expected.bin": binary_words(z_words),
        "expected-a-saturated.hex": b"1\n" if a_sat else b"0\n",
        "expected-f-saturated.hex": bytes("".join("1\n" if s else "0\n" for s in f_sat),"ascii"),
        "expected-saturated.hex": b"1\n" if parent_sat else b"0\n",
    }
    for path, data in a_files.items():
        if path.startswith("stage/"): files["stage/a/"+path[6:]] = data
    for role, key in (("norm","norm"),("gate","gate"),("up","up"),("mid","mid"),
                      ("down","down"),("z","output")):
        files["stage/f-"+role+".hex"] = hex_bytes([w for row in f_rows for w in row["words"][key]])
    files["stage/f-y-input.hex"] = y_words
    files["stage/f-input.hex"] = hex_bytes([w for row in f_rows for w in row["ingress_words"]])
    math_data = {"A": a_data, "F_rows": f_rows, "F_gamma": fg, "F_seed": F_SEED,
                 "expected_A_saturated":a_sat, "expected_F_saturated":f_sat,
                 "expected_parent_saturated":parent_sat}
    files["math.json"] = jb(math_data)
    return files, math_data


def stage_map():
    return {
        "classification":"mathematical role/child address/version map, not an FSM or cycle trace",
        "parent_input":{"words0_447":"unchanged fullA input", "words448_575":"independent Fgamma128word bank, 2048B"},
        "A_roles":"stage/a/* retains fixed fullA role indices; child S/T, not parent private arrays",
        "A_Y":{"file":"expected-a-output.hex", "words":256,"index":"token*128+group",
               "transfer":"A T tokenmajor direct accepted stream -> F X128word, then Fgamma128word"},
        "F_roles":{
            "norm":{"file":"stage/f-norm.hex","words":256,"index":"token*128+group","S_address":"256+group, reused each Fjob"},
            "gate":{"file":"stage/f-gate.hex","words":768,"index":"token*384+group","S_address":"928, reused each group"},
            "up":{"file":"stage/f-up.hex","words":768,"index":"token*384+group","S_address":"929, reused each group"},
            "mid":{"file":"stage/f-mid.hex","words":768,"index":"token*384+group","S_address":"384+group, complete3072 before down"},
            "down":{"file":"stage/f-down.hex","words":256,"index":"token*128+group","S_address":"931, reused each group"},
            "z":{"file":"stage/f-z.hex","words":256,"index":"token*128+group","S_address":"768+group"},
            "y_input":{"file":"stage/f-y-input.hex","words":256,"index":"token*128+group","S_address":"group, original Y preserved for F residual"},
            "input_frames":{"file":"stage/f-input.hex","words":512,"index":"token*256+beat","ordering":"Y128 then Fgamma128, repeated for each row"}},
        "lifetime":["Fgamma bank is explicit2048B FF cost; no new4096B Y array",
                    "A T retains second-row index128 across complete F0 job",
                    "F frame requires256 real input write ACKs before start",
                    "F0 output and T RELEASE/DONE consumed before second Fjob",
                    "A completion/source release distinct from F destination storage",
                    "parent task obligation and accepted output prefix survive child timing"],
        "output":"Z tokenmajor256word4096B; not A Y and not concatenated intermediate F stages"}


def self_check(root, A, F, G, a_results, results, params, columns, weights):
    # Re-run the fixed A independent dimensions, causal and non-degenerate probes.
    a_checks = A.self_check(root, a_results, params)
    lut = G.validate_native_table((root/NATIVE[-1]).read_text(encoding="utf-8"))
    beats = 0
    for seq in range(36864):
        matrix, group, chunk = F.request_fields(seq)
        for index in range(16):
            begin = seq*256+index*16
            if weights[begin:begin+16] != F.weight_beat(matrix,group,chunk,index,F_SEED):
                raise AssertionError("full9MiB F provider byte/column mapping")
            beats += 1
    full_dots = 0
    summaries = {}
    for name,(files,data) in results.items():
        if len(data["F_rows"])!=2:
            raise AssertionError("two Frows required")
        per_row = []
        for token, row in enumerate(data["F_rows"]):
            y=data["A"]["Y"][token]
            for matrix, source, raw_name in ((0,row["norm"],"gate_raw"),(1,row["norm"],"up_raw"),(2,row["mid"],"down_raw")):
                for n,col in enumerate(columns[matrix]):
                    if sum(a*b for a,b in zip(source,col)) != row[raw_name][n]:
                        raise AssertionError("F fullK direct dot differs from period math")
                    full_dots += 1
            if binary_words(row["words"]["X"]) != A.words_bytes(A.word_values(y)):
                raise AssertionError("F input was not actual integer A Y")
            values={key:[v for w in row["words"][key] for v in G.unpack(int(w,16),16,8)]
                    for key in ("norm","gate","up","mid","down","output")}
            nz={key:sum(v!=0 for v in vec) for key,vec in values.items()}
            changed=sum(z!=v for z,v in zip(row["final"],y))
            if not all(nz.values()) or not changed or all(v in (-32768,32767) for v in row["final"]):
                raise AssertionError("F degenerate/zero/bypass/allclip fixture")
            per_row.append({"nonzero_elements":nz,"Z_different_from_Y":changed,
                            "Z_endpoint_elements":sum(v in (-32768,32767) for v in row["final"])})
        summaries[name]=per_row
        if len(files["input.bin"])!=9216 or len(files["f-weights-two-rows.bin"])!=18874368 or len(files["expected.bin"])!=4096:
            raise AssertionError("parent actual shape/replay size")
        if files["input.bin"][:7168] != a_results[name][0]["input.bin"]:
            raise AssertionError("parent A input changed")
    base=results["base"][1];future=results["future_changed"][1]
    if base["F_rows"][0]["final"]!=future["F_rows"][0]["final"]:
        raise AssertionError("future X1 changed final causal Z0")
    if base["F_rows"][1]["final"]==future["F_rows"][1]["final"]:
        raise AssertionError("future row influence invisible")
    z=[v for row in base["F_rows"] for v in row["final"]]
    y=base["A"]["Y"]
    def flat_f(rows,gamma,seed):
        return [v for row in rows for v in F.f1024(root,row,gamma,seed)["final"]]
    wrong_gamma=flat_f(y,params[0],F_SEED)
    wrong_weights=flat_f(y,gamma_f(),F_SEED+1)
    swapped=base["F_rows"][1]["final"]+base["F_rows"][0]["final"]
    duplicate=base["F_rows"][0]["final"]*2
    dropped=flat_f([[0]*1024,y[1]],gamma_f(),F_SEED)
    negatives={"wrong_A_gamma_used_in_F":sum(a!=b for a,b in zip(z,wrong_gamma)),
               "wrong_F_weight_seed":sum(a!=b for a,b in zip(z,wrong_weights)),
               "swapped_Y_rows":sum(a!=b for a,b in zip(z,swapped)),
               "duplicated_Y0_as_Y1":sum(a!=b for a,b in zip(z,duplicate)),
               "dropped_Y0":sum(a!=b for a,b in zip(z,dropped))}
    if not all(negatives.values()):raise AssertionError("bad coupling/gamma/weights not detectable")
    return {"A_full_reference_checks":a_checks,"G_math_table":lut,
            "F_fullK_direct_raw_dots":full_dots,"F_full_weight_beats":beats,
            "F_full_weight_codes":len(weights),"per_fixture_nondegenerate":summaries,
            "causal_final_token0_Z":"PASS","negative_coupling_probes_changed_Z":negatives}


def entries(files): return {n:{"bytes":len(d),"sha256":sha(d)} for n,d in sorted(files.items())}


def build(root):
    A,F,G=[load("af1024_ref_"+str(i),root/path) for i,path in enumerate(REFERENCES)]
    params=A.parameters();a_results={name:A.oracle(name,params) for name in IDS}
    columns=f_columns(F);weights=f_stream(F,columns)
    f_hex=A.words_hex([int.from_bytes(weights[i:i+16],"little") for i in range(0,len(weights),16)])
    results={}
    for name,(a_files,a_data) in a_results.items():
        rows=[F.f1024(root,y,gamma_f(),F_SEED) for y in a_data["Y"]]
        results[name]=output_files(name,a_files,a_data,rows,weights,f_hex,A)
    return A,F,G,params,a_results,columns,weights,results


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=HERE.parents[3]);ap.add_argument("--output","--output-dir",type=Path,required=True)
    ap.add_argument("--source-commit");ap.add_argument("--self-check",action="store_true");ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    if args.source_commit is not None and not re.fullmatch("[0-9a-fA-F]{40}",args.source_commit):ap.error("source commit must be actual40hex")
    root=args.root.resolve();out=args.output.resolve();contract=json.loads((HERE/"fixture-contract.json").read_text(encoding="utf-8"))
    for name,expected in contract["dependencies"].items():
        if sha((root/name).read_bytes())!=expected:raise ValueError("source dependency changed: "+name)
    A,F,G,params,a_results,columns,weights,results=build(root)
    checks=self_check(root,A,F,G,a_results,results,params,columns,weights) if args.self_check else {"status":"NOT_REQUESTED"}
    for name,(files,data) in results.items():
        if entries(files)!=contract["fixtures"][name]["files"]:raise ValueError("frozen fixture bytes differ: "+name)
    if args.check:
        index=json.loads((out/"fixture-index.json").read_text(encoding="utf-8"))
        if index["builder_sha256"]!=sha(Path(__file__).read_bytes()) or index["contract_sha256"]!=sha((HERE/"fixture-contract.json").read_bytes()):raise ValueError("builder/contract changed")
        if args.source_commit and index["source_commit_caller_declared"]!=args.source_commit:raise ValueError("source commit changed")
        for name,(files,data) in results.items():
            for path,expected in files.items():
                if (out/name/path).read_bytes()!=expected:raise ValueError("generated output differs: "+name+"/"+path)
        if (out/"stage-address-map.json").read_bytes()!=jb(stage_map()):raise ValueError("role map changed")
    else:
        if out.exists():raise ValueError("fresh output directory required; no overwrite")
        out.mkdir(parents=True)
        for name,(files,data) in results.items():
            for path,payload in files.items():
                dest=out/name/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
        (out/"stage-address-map.json").write_bytes(jb(stage_map()))
        index={"status":"INDEPENDENT_AF1024_INTEGER_GOLDEN_NOT_RTL_OR_TRAINED_QUALITY","source_commit_caller_declared":args.source_commit,
               "builder_sha256":sha(Path(__file__).read_bytes()),"contract_sha256":sha((HERE/"fixture-contract.json").read_bytes()),
               "python":platform.python_version(),"dependencies":contract["dependencies"],"self_checks":checks,
               "fixtures":[{"id":n,"files":entries(v[0]),"expected_done_saturated":v[1]["expected_parent_saturated"],
                            "expected_A_saturated":v[1]["expected_A_saturated"],"expected_F_saturated":v[1]["expected_F_saturated"],
                            "binary_dumps":contract["fixtures"][n]["binary_dumps"]} for n,v in results.items()]}
        (out/"fixture-index.json").write_bytes(jb(index))
    print(json.dumps({"status":"PASS_AF1024_STATIC_GOLDEN_NOT_RTL","mode":"check" if args.check else "generate",
                      "output":str(out),"self_checks":checks,"fixture_index_sha256":sha((out/"fixture-index.json").read_bytes())},sort_keys=True))


if __name__=="__main__":
    try:main()
    except (ValueError,AssertionError,OSError,KeyError) as error:
        print("FAIL_AF1024_GOLDEN: "+str(error),file=sys.stderr);sys.exit(1)
