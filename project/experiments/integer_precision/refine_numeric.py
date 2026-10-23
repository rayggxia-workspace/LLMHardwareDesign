"""Controlled refinement of observed clipping; never a full-model quality claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from quantize import linear,symmetric,error
from record import digest,provenance,save


def main():
    p=argparse.ArgumentParser();p.add_argument("--inputs",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    receipt=json.loads((a.inputs/"capture-record.json").read_text(encoding="utf-8"));file=a.inputs/receipt["file"]["path"]
    if digest(file)!=receipt["file"]["sha256"]:raise ValueError("actual capture changed")
    data=np.load(file,allow_pickle=False);rows=[];kv=[]
    for module in ("self_attn.q_proj","mlp.gate_proj","mlp.down_proj"):
        w=data["weight__"+module];calib=data["prefill64__"+module+"__A"][:8]
        for phase in ("prefill16","prefill32","prefill64","decode64"):
            raw=data[phase+"__"+module+"__A"];evaluate=raw[8:] if phase.startswith("prefill") else raw
            for mode in ("static_tensor","dynamic_row"):
                for output_bits in (8,16):
                    r,_=linear(evaluate,w,calib,mode,output_bits)
                    r.update(module=module,phase=phase,output_payload_bytes=evaluate.shape[0]*16*(output_bits//8))
                    rows.append(r)
    for name in ("K","V"):
        calib=data["prefill64__"+name][:,:8,:]
        for bits in (8,16):
            limit=(1<<(bits-1))-1
            for length in (16,32,64):
                raw=data[f"prefill{length}__{name}"]
                for profile in ("static_first8","static_first8_headroom2","dynamic_block16"):
                    decoded=np.empty(raw.shape,np.float64);clips=0;scales=[]
                    blocks=range(0,length,16) if profile=="dynamic_block16" else (0,)
                    for start in blocks:
                        end=min(length,start+16) if profile=="dynamic_block16" else length
                        source=raw[:,start:end,:] if profile=="dynamic_block16" else calib
                        scale=np.maximum(np.max(abs(source),axis=(1,2),keepdims=True)/limit,1e-12)
                        if profile=="static_first8_headroom2":scale*=2
                        scales.append(scale[:,0,0])
                        x=raw[:,start:end,:];q=symmetric(x,scale,bits);decoded[:,start:end,:]=q.astype(np.float64)*scale
                        # Only held-out token>=8 contributes clipping/error.
                        eval_start=max(8-start,0)
                        clips+=int(np.count_nonzero(abs(x[:,eval_start:,:])/scale>limit+.5))
                    metadata=sum(s.size for s in scales)*4
                    physical=sum(((raw[h].size*(bits//8)+63)//64)*64 for h in range(raw.shape[0]))+((metadata+63)//64)*64
                    kv.append({"tensor":name,"length":length,"bits":bits,"profile":profile,"evaluation":"tokens8:end",
                               **error(decoded[:,8:,:],raw[:,8:,:]),"clip_count":clips,"payload_bytes":raw.size*(bits//8),
                               "scale_bytes":metadata,"physical_bytes_64B":physical,"scale_generation":"offline_float", "integer_dynamic_scale_hardware":False,
                               "caveat":"dynamic scale uses current block extrema, an exploration with runtime scale-generation cost not implemented" if profile=="dynamic_block16" else "calibration first8 only"})
    save(a.output,{"producer":provenance("refine_numeric.py"),"input_sha256":digest(file),"linear":rows,"kv":kv,
                   "limits":"Same captured input, W8A8/INT32. Output8/16 and KV profiles are different numerical contracts, not a partition-only speedup. Descriptive scales offline float. No end-to-end quality."})
    print({"linear":len(rows),"kv":len(kv)})


if __name__=="__main__":main()
