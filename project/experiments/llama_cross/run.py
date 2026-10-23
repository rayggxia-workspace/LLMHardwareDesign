"""E1 local slice: calibration-only shared QK, immutable KV and integer replay."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from common import ROOT,HERE,digest,save,npz,provenance
from cache import ImmutableKV
sys.path.insert(0,str(HERE.parent/"kv_scale"))
from core import integer_attention
from oracle import attention as independent_attention
from quantize import compile_ratio,error
from tables import load


def exponent(array):
    peak=float(np.max(abs(array)))
    return max(-120,math.ceil(math.log2(peak/127))) if peak else -24

def quantize(array,e):
    z=np.rint(np.asarray(array,dtype=np.float64)/2.0**e)
    count=int(np.count_nonzero((z < -127)|(z > 127)))
    return np.clip(z,-127,127).astype(np.int8),count

def calibrate(q,k,v,profile):
    g=np.zeros(k.shape[1],dtype=np.int8)
    if profile=="calibrated_shared_QK_static_KV":
        qmax=np.maximum(np.max(abs(q),axis=(0,1)),1e-30)
        kmax=np.maximum(np.max(abs(k),axis=0),1e-30)
        g=np.clip(np.rint(0.5*np.log2(kmax/qmax)),-8,8).astype(np.int8)
    elif profile!="direct_static_KV":raise ValueError("unknown profile")
    ek=exponent(k*np.exp2(-g.astype(np.float64))[None,:]);ev=exponent(v)
    parameters={"schema":"frozen-shared-GQA-KV/1","profile":profile,"g":g.tolist(),"K_exponent":ek,
        "V_exponent":ev,"calibration_only":True,"Q_scale":"per current row; offline compiler, no future rows",
        "transform_boundary":"post norm/RoPE","group_query_heads":list(range(len(q))),"KV_head":0}
    raw=json.dumps(parameters,sort_keys=True,separators=(",",":")).encode()
    parameters["profile_id"]=hashlib.sha256(raw).hexdigest()
    return parameters

def prepare(q,k,v,parameters):
    g=np.array(parameters["g"],dtype=np.float64)
    tq=q.astype(np.float64)*np.exp2(g)[None,None,:]
    tk=k.astype(np.float64)*np.exp2(-g)[None,:]
    ki,kclip=quantize(tk,parameters["K_exponent"]);vi,vclip=quantize(v,parameters["V_exponent"])
    qa=np.empty(q.shape,dtype=np.int8);qe=[];qclip=0
    for h in range(len(q)):
        head=[]
        for t in range(q.shape[1]):
            e=exponent(tq[h,t]);qa[h,t],clip=quantize(tq[h,t],e);qclip+=clip;head.append(e)
        qe.append(head)
    return qa,ki,vi,qe,{"Q":qclip,"K":kclip,"V":vclip}

def execute(qa,ki,vi,qe,parameters,positions,cfg,table):
    block=cfg["block_tokens"];nblocks=(len(ki)+block-1)//block
    ek,ev=parameters["K_exponent"],parameters["V_exponent"]
    allowed=(np.arange(len(ki))[None,:]<=np.asarray(positions)[:,None]).tolist()
    rows=[];counts=Counter();params=[]
    for h in range(len(qa)):
        p=[[compile_ratio(2.0**(e+ek)/math.sqrt(qa.shape[-1])*256)]*nblocks for e in qe[h]]
        head,c=integer_attention(qa[h].tolist(),ki.tolist(),vi.tolist(),[ek]*nblocks,[ev]*nblocks,
            p,block,15,allowed,table)
        rows.append(head);counts.update(c);params.append(p)
    return rows,dict(counts),params,allowed

def outputs(rows):return np.array([[r["output_i16_f12"] for r in h] for h in rows],dtype=np.int16)

def one_case(name,q,k,v,reference,cached,parameters,cfg,table):
    qa,ki,vi,qe,clipped=prepare(q,k,v,parameters)
    positions=list(range(len(k)))
    full,counts,params,allowed=execute(qa,ki,vi,qe,parameters,positions,cfg,table)
    out=outputs(full);checked_values=0
    for h in range(len(qa)):
        oracle=independent_attention(qa[h].tolist(),ki.tolist(),vi.tolist(),
            [parameters["V_exponent"]]*len(params[h][0]),params[h],cfg["block_tokens"],15,allowed,table)
        for row,ref in zip(full[h],oracle):
            for field,expected in ref.items():
                if row[field]!=expected:raise AssertionError("independent integer mismatch")
                checked_values+=len(expected)
    # Shared g keeps each real Q_head*K product unchanged for the entire selected group.
    g=np.array(parameters["g"],dtype=np.float64)
    transform_error=max(float(np.max(abs((q[h].astype(np.float64)*np.exp2(g))
        @(k.astype(np.float64)*np.exp2(-g)).T-q[h].astype(np.float64)@k.astype(np.float64).T))) for h in range(len(q)))
    if transform_error>1e-9:raise AssertionError("shared transform changed real QK")
    cache=ImmutableKV(cfg["cache_capacity_tokens"],k.shape[1],parameters["profile_id"])
    stream=np.empty_like(out)
    for t in range(len(k)):
        cache.append([t],ki[t:t+1],vi[t:t+1],t,parameters["profile_id"])
        kk,vv=cache.read(t+1)
        step,_,_,_=execute(qa[:,t:t+1],kk,vv,[[qe[h][t]] for h in range(len(q))],
                           parameters,[t],cfg,table)
        stream[:,t:t+1]=outputs(step)
    if not np.array_equal(stream,out):raise AssertionError("token/batch integer output mismatch")
    chunk=ImmutableKV(cfg["cache_capacity_tokens"],k.shape[1],parameters["profile_id"])
    start=0
    for end in (8,16,32,len(k)):
        chunk.append(range(start,end),ki[start:end],vi[start:end],start,parameters["profile_id"]);start=end
    ck,cv=chunk.read(len(k))
    if not (np.array_equal(ck,ki) and np.array_equal(cv,vi)):raise AssertionError("chunk cache bits mismatch")
    future_checks=0
    for prefix in (16,32):
        short,_,_,_=execute(qa[:,:prefix],ki[:prefix],vi[:prefix],
            [head[:prefix] for head in qe],parameters,list(range(prefix)),cfg,table)
        mutated_k=ki.copy();mutated_v=vi.copy()
        mutated_k[prefix:]=-mutated_k[prefix:];mutated_v[prefix:]=-mutated_v[prefix:]
        future,_,_,_=execute(qa[:,:prefix],mutated_k,mutated_v,[head[:prefix] for head in qe],
            parameters,list(range(prefix)),cfg,table)
        for actual in (outputs(short),outputs(future)):
            if not np.array_equal(actual,out[:,:prefix]):raise AssertionError("future changed published prefix")
            future_checks+=actual.size
    cqa,cki,cvi,cqe,cclip=prepare(cached["q"],cached["k"],cached["v"],parameters)
    cached_codes={"Q":int(np.count_nonzero(cqa!=qa)),"K":int(np.count_nonzero(cki!=ki)),"V":int(np.count_nonzero(cvi!=vi))}
    if not any(cached_codes.values()):
        cached_output_mismatch=0
    else:
        cr,_,_,_=execute(cqa,cki,cvi,cqe,parameters,positions,cfg,table)
        cached_output_mismatch=int(np.count_nonzero(outputs(cr)!=out))
    report={"evaluation":name,"profile":parameters["profile"],"profile_id":parameters["profile_id"],
        "shape_Q":list(q.shape),"shape_KV":list(k.shape),"g_shared_real_QK_max_abs":transform_error,
        "clipping_counts":clipped,"integer_values_checked":checked_values,
        "stream_batch_output_values_checked":out.size,"future_output_values_checked":future_checks,
        "source_full_cached_code_mismatch":cached_codes,"source_full_cached_output_mismatch":cached_output_mismatch,
        "local_head_error":error(out.astype(np.float64)/4096,reference),"counts":counts,
        "cache_events":cache.events,"chunk_events":chunk.events,
        "cache_storage_bytes":cfg["cache_capacity_tokens"]*k.shape[1]*2,
        "scale_balance_metadata_bytes":len(parameters["g"])+2,
        "current_row_Q_scale_exponent_bytes":len(q)*q.shape[1],
        "compiled_score_M_r_bytes_if_cached_per_current_row":len(q)*q.shape[1]*5,
        "QK_transform_elements":int(q.size+k.size) if parameters["profile"]!="direct_static_KV" else 0,
        "logical_KV_bytes_at_length":ki.nbytes+vi.nbytes,
        "naive_group_KV_duplication_bytes":len(q)*(ki.nbytes+vi.nbytes),
        "online_frontend_implemented":False,"model_quality_measured":False,
        "scope":"canonical full-capture tensors streamed under frozen calibration; actual source full/cached code differences reported separately"}
    payload={"Q_i8":qa,"K_i8":ki,"V_i8":vi,"Q_exponents":np.array(qe,dtype=np.int8),
        "score_M_u32":np.array([[p[0][0] for p in head] for head in params],dtype="<u4"),
        "score_r_u8":np.array([[p[0][1] for p in head] for head in params],dtype="u1"),
        "qk_i32":np.array([[r["qk_i32"] for r in h] for h in full],dtype="<i4"),
        "scores_i16":np.array([[r["scores_i16_f8"] for r in h] for h in full],dtype=np.int16),
        "probabilities_i16":np.array([[r["probabilities"] for r in h] for h in full],dtype=np.int16),
        "output_i16_f12":out,"stream_output_i16_f12":stream}
    return report,payload

def main():
    p=argparse.ArgumentParser();p.add_argument("--capture",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--development",action="store_true");a=p.parse_args()
    if a.output.exists():raise ValueError("refuse overwrite")
    prod=provenance(a.development);cfg=json.loads((HERE/"experiment.json").read_text())
    cap=json.loads((a.capture/"manifest.json").read_text())
    if cap["status"]!="PASS":raise ValueError("failed capture")
    if not a.development and cap["producer"]["development"]:raise ValueError("formal run cannot use development capture")
    for name,record in cap["artifacts"].items():
        if digest(a.capture/name)!=record["sha256"]:raise ValueError("capture SHA mismatch")
    data=np.load(a.capture/"gqa-group.npz",allow_pickle=False)
    inputs=json.loads((a.capture/"inputs.json").read_text())
    if any(inputs["calibration"]["sha256"]==inputs[n]["sha256"] for n in cfg["evaluation_texts"]):
        raise ValueError("calibration/evaluation overlap")
    table=load()["exp_u32_f24"];reports=[];payload={};frozen=[]
    for profile in cfg["profiles"]:
        parameters=calibrate(data["calibration.q"],data["calibration.k"],data["calibration.v"],profile)
        frozen.append(parameters)
        before=json.dumps(parameters,sort_keys=True)
        for name in cfg["evaluation_texts"]:
            report,arrays=one_case(name,*[data[name+"."+f] for f in ("q","k","v","reference")],
                {f:data[name+".cached_"+f] for f in ("q","k","v")},parameters,cfg,table)
            reports.append(report)
            for field,value in arrays.items():payload[profile+"."+name+"."+field]=value
        if before!=json.dumps(parameters,sort_keys=True):raise AssertionError("evaluation changed frozen calibration")
    a.output.mkdir(parents=True)
    save(a.output/"frozen-calibration.json",frozen);save(a.output/"numeric.json",reports)
    npz(a.output/"integers.npz",payload)
    summary={"cases":len(reports),"integer_values_checked":sum(r["integer_values_checked"] for r in reports),
        "stream_batch_values_checked":sum(r["stream_batch_output_values_checked"] for r in reports),
        "future_values_checked":sum(r["future_output_values_checked"] for r in reports),
        "input_clips":sum(sum(r["clipping_counts"].values()) for r in reports),
        "scope":"short one-GQA-group local reference; not full-model quality, DMA, RTL or speed"}
    save(a.output/"summary.json",summary)
    save(a.output/"manifest.json",{"producer":prod,"capture_manifest_sha256":digest(a.capture/"manifest.json"),
        "artifacts":{p.name:{"bytes":p.stat().st_size,"sha256":digest(p)} for p in a.output.iterdir() if p.is_file()}})
    print(json.dumps(summary))

if __name__=="__main__":main()
