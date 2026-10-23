"""Small fixed-point and real captured tensor experiments, numerical-only."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from fixed import sat,mul_i16_i8
from vectors import silu_i16_f12,rms_i16_f12,softmax_fixed,recurrent_delta
from tables import load
from quantize import linear,error,symmetric
from record import provenance,save,digest,HERE
from capture import tensor,encoding


def operator_cases():
    t=load();rng=np.random.default_rng(3305);counts=Counter()
    x=np.arange(-32768,32768,17,dtype=np.int64)
    actual=np.array([silu_i16_f12(int(a),t["sigmoid_u16_f16"],counts) for a in x])/4096
    xf=x/4096;reference=xf/(1+np.exp(-xf))
    silu={**error(actual,reference),"samples":len(x),"counts":dict(counts)}
    rms=[]
    for length in (16,64,256):
        x=np.clip(np.rint(rng.normal(0,.7,length)*4096),-32768,32767).astype(np.int64)
        gamma=[16384]*length;eps=round(length*1e-6*4096**2);gain=round(math.sqrt(length)*(1<<20));c=Counter()
        y,trace=rms_i16_f12(list(map(int,x)),gamma,eps,gain,c)
        rms.append({"length":length,**error(np.array(y)/4096,(x/4096)/np.sqrt(np.mean((x/4096)**2)+eps/(length*4096**2))),"counts":dict(c),"trace":trace})
    sm=[]
    for length in (16,64,128,256,512):
        for profile in ("uniform","random"):
            scores=np.zeros(length,dtype=np.int64) if profile=="uniform" else np.rint(rng.normal(0,1,length)*256).astype(np.int64)
            e=np.exp(scores/256-np.max(scores/256));pref=e/e.sum()
            values=rng.integers(-127,128,(length,4),dtype=np.int16)
            for bits in (7,15):
                c=Counter();p,trace=softmax_fixed(list(map(int,scores)),t["exp_u32_f24"],bits,counts=c)
                # P7/V8 native signed8; P15/V8 decomposed into three partials.
                out=[]
                for col in range(4):
                    total=0
                    for i,pi in enumerate(p):
                        total+=int(pi)*int(values[i,col]) if bits==7 else mul_i16_i8(int(pi),int(values[i,col]),c)
                    out.append(total/((1<<bits)-1))
                if bits==7:c["native_mul8"]+=length*4
                sm.append({"length":length,"profile":profile,"probability_bits":bits,"all_zero":not any(p),
                           "probability_mass":sum(p)/((1<<bits)-1),"probability_l1":float(np.sum(abs(np.array(p)/((1<<bits)-1)-pref))),
                           "pv_error":error(out,pref@values),"counts":dict(c),"trace":trace})
    # Post-normalized Q/K Gated DeltaNet core only; integer and FP64 use the
    # same quantized input values. No hidden float in the integer recurrence.
    kd,vd=4,4;state=[[0]*vd for _ in range(kd)];fp=np.zeros((kd,vd));rec=[];c=Counter()
    for step in range(1,257):
        q=rng.normal(size=kd);q/=np.linalg.norm(q);k=rng.normal(size=kd);k/=np.linalg.norm(k)
        qi=np.rint(q*16384).astype(np.int64);ki=np.rint(k*16384).astype(np.int64)
        vi=np.rint(rng.normal(0,.3,vd)*4096).astype(np.int64);beta=24000;decay=32600
        out,state=recurrent_delta(list(map(int,qi)),list(map(int,ki)),list(map(int,vi)),beta,decay,state,c)
        qf=qi/16384;kf=ki/16384;vf=vi/4096;fp*=decay/32768
        delta=(vf-kf@fp)*(beta/32768);fp+=np.outer(kf,delta);fo=qf@fp
        if step in (16,64,128,256):
            rec.append({"length":step,"state_error":error(np.array(state)/2**20,fp),"output_error":error(np.array(out)/4096,fo),
                        "max_abs_state_integer":int(np.max(abs(np.array(state,dtype=np.int64)))),"counts":dict(c)})
    return {"silu":silu,"rms":rms,"softmax":sm,"recurrence":rec,
            "limits":"Independent candidate operators, not llaccel replay or complete integer attention/GDN/model. Quantized q/k/beta/decay generated offline with float."}


def actual_cases(inputs,output):
    data=np.load(inputs/"qwen3_layer0.npz",allow_pickle=False)
    source=json.loads((inputs/"capture-record.json").read_text(encoding="utf-8"))
    if digest(inputs/source["file"]["path"])!=source["file"]["sha256"]:raise ValueError("capture SHA changed")
    linear_rows=[];kv_rows=[];example=None
    for module in ("self_attn.q_proj","mlp.gate_proj","mlp.down_proj"):
        w=data["weight__"+module];calib=data["prefill64__"+module+"__A"][:8]
        for phase in ("prefill16","prefill32","prefill64","decode64"):
            raw=data[phase+"__"+module+"__A"];a=raw[8:] if phase.startswith("prefill") else raw
            for mode in ("static_tensor","dynamic_row"):
                result,payload=linear(a,w,calib,mode)
                result.update(module=module,phase=phase,evaluation_rows="8:end, excluding calibration" if phase.startswith("prefill") else "teacher-forced new token")
                result["fp32_framework_vs_fp64_matmul"]=error(data[phase+"__"+module+"__Y"][8:] if phase.startswith("prefill") else data[phase+"__"+module+"__Y"],a.astype(np.float64)@w.astype(np.float64).T)
                linear_rows.append(result)
                if module=="self_attn.q_proj" and phase=="prefill16" and mode=="dynamic_row":example=payload
    for name in ("K","V"):
        calibration=data["prefill64__"+name][:,:8,:]
        for bits in (8,16):
            limit=(1<<(bits-1))-1
            scale=np.maximum(np.max(abs(calibration),axis=(1,2),keepdims=True)/limit,1e-12)
            for length in (16,32,64):
                raw=data[f"prefill{length}__{name}"];evaluate=raw[:,8:,:]
                q=symmetric(evaluate,scale,bits)
                metadata=4*raw.shape[0]
                payload=raw.size*(bits//8)
                # Per-head independent span and separate scale span, 64B aligned.
                physical=sum(((raw[h].size*(bits//8)+63)//64)*64 for h in range(raw.shape[0]))+((metadata+63)//64)*64
                kv_rows.append({"tensor":name,"length":length,"format":f"i{bits}","shape":list(raw.shape),"granularity":"per-head static from first8 tokens",
                                **error(q.astype(np.float64)*scale,evaluate),"input_clip_count":int(np.count_nonzero(abs(evaluate)/scale>limit+.5)),
                                "payload_bytes":payload,"scale_bytes":metadata,"physical_64B_bytes":physical})
    # A small valid strict interchange package of real integer-reference output,
    # with descriptive float scales. Its active kernel has no float fallback;
    # upstream model and parameter generation remain explicitly outside scope.
    package=output/"capture-example";ts=[]
    for key,role,axes in (("a_i8","activation",["token","K"]),("w_i8","weight",["channel","K"]),
                          ("acc_i32","accumulator",["token","channel"]),("out_i8","output",["token","channel"]),
                          ("M_u32","requant_multiplier",["token","channel"]),("r_u8","requant_shift",["token","channel"]),
                          ("sa_f32","scale",["token","one"]),("sw_f32","scale",["channel"]),("sy_f32","scale",["channel"]),
                          ("reference_f32","reference_output",["token","channel"])):
        e=encoding("reference_float" if key.endswith("f32") else "unquantized_integer")
        if key=="a_i8":e=encoding("symmetric",parameter_generation="offline_float",zero_point=0,group_axes=[0],group_shape=[8],scale_tensor="sa_f32",scale_encoding="descriptive_f32")
        if key=="w_i8":e=encoding("symmetric",parameter_generation="offline_float",zero_point=0,group_axes=[0],group_shape=[16],scale_tensor="sw_f32",scale_encoding="descriptive_f32")
        if key=="out_i8":e=encoding("symmetric",parameter_generation="offline_float",zero_point=0,group_axes=[1],group_shape=[16],scale_tensor="sy_f32",scale_encoding="descriptive_f32",multiplier_tensor="M_u32",shift_tensor="r_u8")
        if key in ("M_u32","r_u8"):e=encoding("requant_params",parameter_generation="offline_float")
        if key=="acc_i32":e=encoding("scaled_accumulator",parameter_generation="offline_float",scale_factor_tensors=["sa_f32","sw_f32"],scale_factor_axes=[[0],[1]])
        if key=="sa_f32":example[key]=example[key].reshape(8);axes=["token"]
        ts.append(tensor(package,key,example[key],role,axes,e,node="layer0.q_proj.first16channels"))
    cfg=source["model"]["model_files"]
    manifest_hash=lambda d:hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    doc={"schema":"llm-precision-capture/1","producer":provenance("run_numeric.py"),
         "model":{"model_id":source["model"]["model_id"],"revision":source["model"]["revision"],"config_sha256":cfg["config.json"]["sha256"],
                  "weights_manifest_sha256":manifest_hash({"model.safetensors":cfg["model.safetensors"]}),
                  "tokenizer_manifest_sha256":manifest_hash({k:v for k,v in cfg.items() if k in ("tokenizer.json","tokenizer_config.json","merges.txt","vocab.json")})},
         "run":{"phase":"operator","batch":1,"prefix_tokens":16,"new_tokens":8,"input_ids_sha256":source["input_ids_sha256"],
                "data_version":"qwen3_trace public prompt, captured layer0 first16 output channels, fullK; token8:16",
                "calibration_split":"first8 tokens of prefill64","evaluation_split":"tokens8:16 of prefill16",
                "execution":"integer_reference","token_mode":"teacher_forced","backend":"NumPy integer GEMM + C1 Python integer RQ; offline_float scales outside kernel",
                "floating_fallbacks":[],"measurement_scope":"numerical_only"},"tensors":ts}
    save(package/"capture.json",doc)
    return {"capture_file_sha256":source["file"]["sha256"],"linear":linear_rows,"kv":kv_rows,
            "scope":"Actual layer0 slices only; no full-model quantized accuracy/speed. Offline floating calibration not integer hardware support."}


def main():
    p=argparse.ArgumentParser();p.add_argument("--inputs",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    report={"producer":provenance("run_numeric.py"),"operators":operator_cases(),"actual":actual_cases(a.inputs,a.output)}
    save(a.output/"numerical.json",report)
    print({"linear_cases":len(report["actual"]["linear"]),"kv_cases":len(report["actual"]["kv"])})


if __name__=="__main__":main()
