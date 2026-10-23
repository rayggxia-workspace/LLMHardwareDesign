"""Independent readback: exact input rounding, Decimal compiler and Fraction oracle.

Does not import run/core/fixed/quantize/cache or execute the target kernel.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from common import ROOT, HERE, digest, save
sys.path.insert(0,str(HERE.parent/"kv_scale"))
from oracle import attention


def dyadic(e):
    return Fraction(2**e) if e>=0 else Fraction(1,2**-e)


def rounded_codes(values,exponent):
    scale=dyadic(int(exponent))
    return np.array([max(-127,min(127,round(Fraction(float(x))/scale)))
                     for x in np.asarray(values).flat],dtype=np.int8).reshape(values.shape)


def exponent(values):
    peak=max(Fraction(abs(float(x))) for x in np.asarray(values).flat)
    if not peak:return -24
    e=-120
    while peak>127*dyadic(e):e+=1
    return e


def compile_decimal(qe,ke,d):
    # Independent 80-digit sqrt/compiler, no target frexp/compile_ratio.
    with localcontext() as ctx:
        ctx.prec=80
        ratio=Decimal(2)**(int(qe)+int(ke))*256/Decimal(d).sqrt()
        shift=0
        while ratio*Decimal(2)**shift<Decimal(2)**30:shift+=1
        while ratio*Decimal(2)**shift>=Decimal(2)**31:shift-=1
        m=int((ratio*Decimal(2)**shift).to_integral_value(rounding=ROUND_HALF_EVEN))
        if m==2**31:m//=2;shift-=1
        if not 0<=shift<=63:raise AssertionError("compiler range")
        return m,shift


def checked_manifest(directory):
    m=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    for name,expected in m["artifacts"].items():
        p=directory/name
        assert p.is_file() and p.stat().st_size==expected["bytes"] and digest(p)==expected["sha256"],name
    prod=m["producer"]
    assert not prod["development"] and not prod["source_dirty"]
    for name,record in prod["sources"].items():
        raw=subprocess.check_output(["git","show",prod["commit"]+":"+name],cwd=ROOT)
        assert record["matches_commit"] and hashlib.sha256(raw).hexdigest()==record["sha256"],name
    return m


def audit(capture,numeric,repeat=None):
    cap=checked_manifest(capture);num=checked_manifest(numeric)
    assert cap["status"]=="PASS" and cap["observer_restored"]
    assert num["capture_manifest_sha256"]==digest(capture/"manifest.json")
    assert cap["producer"]["commit"]==num["producer"]["commit"]
    cfg=json.loads((HERE/"experiment.json").read_text(encoding="utf-8"))
    frozen=json.loads((numeric/"frozen-calibration.json").read_text())
    reports=json.loads((numeric/"numeric.json").read_text())
    data=np.load(capture/"gqa-group.npz",allow_pickle=False)
    codes=np.load(numeric/"integers.npz",allow_pickle=False)
    table=json.loads((HERE.parent/"integer_precision/tables.json").read_text())["exp_u32_f24"]
    assert all(v["passed"] for x in cap["full_cached"].values() for v in x.values())
    inputs=json.loads((capture/"inputs.json").read_text(encoding="utf-8"))
    assert len({x["sha256"] for x in inputs.values()})==3
    for record in inputs.values():
        ids=np.asarray(record["token_ids"],dtype=np.int64)
        assert hashlib.sha256(ids.tobytes()).hexdigest()==record["sha256"]
    source_values=0;oracle_values=0;events=0;compiler_values=0
    for p in frozen:
        declared=dict(p);declared.pop("profile_id")
        raw=json.dumps(declared,sort_keys=True,separators=(",",":")).encode()
        assert hashlib.sha256(raw).hexdigest()==p["profile_id"]
        q=data["calibration.q"].astype(np.float64);k=data["calibration.k"].astype(np.float64)
        g=np.zeros(k.shape[1],dtype=np.int8)
        if p["profile"]=="calibrated_shared_QK_static_KV":
            for c in range(k.shape[1]):
                qm=max(float(np.max(abs(q[:,:,c]))),1e-30);km=max(float(np.max(abs(k[:,c]))),1e-30)
                g[c]=max(-8,min(8,round(0.5*math.log2(km/qm))))
        assert np.array_equal(g,p["g"]),"calibration-only shared g"
        assert exponent(k*np.exp2(-g.astype(np.float64)))==p["K_exponent"]
        assert exponent(data["calibration.v"])==p["V_exponent"]
        for name in cfg["evaluation_texts"]:
            prefix=p["profile"]+"."+name+"."
            qa,ki,vi=[codes[prefix+f] for f in ("Q_i8","K_i8","V_i8")]
            qe=codes[prefix+"Q_exponents"]
            tq=data[name+".q"].astype(np.float64)*np.exp2(g.astype(np.float64))
            tk=data[name+".k"].astype(np.float64)*np.exp2(-g.astype(np.float64))
            for field,raw,e in ((ki,tk,p["K_exponent"]),(vi,data[name+".v"],p["V_exponent"])):
                assert np.array_equal(rounded_codes(raw,e),field),"independent input codes"
                source_values+=field.size
            for h in range(len(qa)):
                for t in range(qa.shape[1]):
                    assert exponent(tq[h,t])==qe[h,t]
                    assert np.array_equal(rounded_codes(tq[h,t],qe[h,t]),qa[h,t])
                    source_values+=qa.shape[-1]
            positions=data[name+".positions"]
            assert np.array_equal(positions,np.arange(len(ki)))
            allowed=(np.arange(len(ki))[None,:]<=positions[:,None]).tolist()
            nblocks=(len(ki)+cfg["block_tokens"]-1)//cfg["block_tokens"]
            for h in range(len(qa)):
                params=[]
                for t,e in enumerate(qe[h]):
                    m,r=compile_decimal(e,p["K_exponent"],qa.shape[-1])
                    assert (m,r)==(int(codes[prefix+"score_M_u32"][h,t]),int(codes[prefix+"score_r_u8"][h,t]))
                    params.append([(m,r)]*nblocks);compiler_values+=2
                expected=attention(qa[h].tolist(),ki.tolist(),vi.tolist(),
                    [p["V_exponent"]]*nblocks,params,cfg["block_tokens"],15,allowed,table)
                for t,row in enumerate(expected):
                    for key,stored in (("qk_i32","qk_i32"),("scores_i16_f8","scores_i16"),
                                       ("probabilities","probabilities_i16"),("output_i16_f12","output_i16_f12")):
                        assert np.array_equal(row[key],codes[prefix+stored][h,t]),"oracle "+stored
                        oracle_values+=len(row[key])
            assert np.array_equal(codes[prefix+"output_i16_f12"],codes[prefix+"stream_output_i16_f12"])
            report=next(x for x in reports if x["profile"]==p["profile"] and x["evaluation"]==name)
            assert report["profile_id"]==p["profile_id"]
            for event in report["cache_events"]:
                old=event["begin"]
                assert event["old_payload_rewrite_bytes"]==0 and event["published_epoch"]==old+event["count"]
                assert event["new_payload_bytes"]==event["count"]*ki.shape[1]*2
                raw=ki[:old].tobytes()+vi[:old].tobytes()
                assert hashlib.sha256(raw).hexdigest()==event["old_prefix_sha256"]
                events+=1
    repeated=[]
    if repeat:
        other=checked_manifest(repeat)
        assert other["capture_manifest_sha256"]==num["capture_manifest_sha256"]
        for name in num["artifacts"]:
            assert digest(numeric/name)==digest(repeat/name),"repeat bytes "+name
            repeated.append(name)
    return {"status":"PASS","source_input_codes_checked":source_values,"independent_oracle_values":oracle_values,
        "Decimal_compiler_values":compiler_values,"cache_events":events,"repeat_identical_files":repeated,
        "capture_manifest_sha256":digest(capture/"manifest.json"),"numeric_manifest_sha256":digest(numeric/"manifest.json"),
        "scope":"independent small-slice readback; not all-integer model, hardware port/RTL or throughput proof"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--capture",type=Path,required=True)
    p.add_argument("--numeric",type=Path,required=True);p.add_argument("--repeat",type=Path)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError("refuse overwrite")
    result=audit(a.capture,a.numeric,a.repeat);save(a.output,result);print(json.dumps(result))

if __name__=="__main__":main()
