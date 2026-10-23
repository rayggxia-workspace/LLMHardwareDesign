"""Offline floating calibration, followed by separate exact integer execution."""
import math
import numpy as np
from fixed import requant, gemm_i8


def symmetric(x,scale,bits=8):
    limit=(1<<(bits-1))-1
    return np.clip(np.rint(np.asarray(x,dtype=np.float64)/scale),-limit,limit).astype(np.int8 if bits==8 else np.int16)


def compile_ratio(ratio):
    if not math.isfinite(ratio) or ratio<=0:
        raise ValueError("positive finite offline ratio required")
    m,e=math.frexp(ratio); multiplier=round(m*(1<<31)); shift=31-e
    if multiplier==(1<<31):
        multiplier>>=1;shift-=1
    if not 0<=shift<=63:
        raise ValueError("ratio outside C1 range; conversion cannot be hidden")
    return multiplier,shift


def error(y,reference):
    y=np.asarray(y,dtype=np.float64);reference=np.asarray(reference,dtype=np.float64)
    delta=y-reference; denom=float(np.sqrt(np.mean(reference**2)))
    return {"max_abs":float(np.max(abs(delta))),"rmse":float(np.sqrt(np.mean(delta**2))),
            "relative_rmse":float(np.sqrt(np.mean(delta**2)))/max(denom,1e-30)}


def linear(a,w,calibration,mode,output_bits=8):
    """Per-output static W scale; static or offline per-row A scale. W[N,K]."""
    from collections import Counter
    sw=np.maximum(np.max(abs(w),axis=1)/127,1e-12)
    sa=np.max(abs(calibration))/127 if mode=="static_tensor" else np.max(abs(a),axis=1,keepdims=True)/127
    sa=np.maximum(sa,1e-12)
    qw=symmetric(w,sw[:,None]); qa=symmetric(a,sa)
    # Output scale uses calibration rows only, with declared 2x headroom.
    if output_bits not in (8,16):raise ValueError("output i8/i16 only")
    limit=(1<<(output_bits-1))-1
    sy=np.maximum(2*np.max(abs(calibration.astype(np.float64)@w.astype(np.float64).T),axis=0)/limit,1e-12).astype(np.float32)
    # Compile from the exact descriptive f32 payload values, in offline f64.
    ratios=np.broadcast_to(np.asarray(sa,dtype=np.float64),(a.shape[0],1))*sw.astype(np.float64)[None,:]/sy.astype(np.float64)[None,:]
    # Static parameters are stored only once, not one duplicate per token.
    params=np.array([[compile_ratio(float(r)) for r in row] for row in ratios],dtype=np.int64)
    acc=gemm_i8(qa,qw); counts=Counter(); out=np.empty(acc.shape,dtype=np.int8 if output_bits==8 else np.int16)
    for index in np.ndindex(acc.shape):
        out[index]=requant(int(acc[index]),int(params[index][0]),int(params[index][1]),output_bits,counts)
    reference=a.astype(np.float64)@w.astype(np.float64).T
    result=error(out.astype(np.float64)*sy[None,:],reference)
    integer_real=acc.astype(np.float64)*np.broadcast_to(np.asarray(sa,dtype=np.float64),(a.shape[0],1))*sw.astype(np.float64)[None,:]
    result["matrix_only_error"]=error(integer_real,reference)
    result["requant_only_error"]=error(out.astype(np.float64)*sy[None,:],integer_real)
    result.update({"mode":mode,"output_bits":output_bits,"shape_a":list(a.shape),"shape_w":list(w.shape),"calibration_rows":len(calibration),
                   "output_scale_headroom":2,"input_out_of_calibration":int(np.count_nonzero(abs(a)/sa>127.5)),
                   "integer_counts":dict(counts),"max_abs_acc":int(np.max(abs(acc.astype(np.int64)))),
                   "rq_parameter_sets":w.shape[0] if mode=="static_tensor" else acc.size,
                   "hardware_online_scale_implemented":False,"execution":"integer_reference; offline_float calibration/scale compilation"})
    return result,{"a_i8":qa,"w_i8":qw,"acc_i32":acc,f"out_i{output_bits}":out,"M_u32":params[:,:,0].astype("<u4"),
                   "r_u8":params[:,:,1].astype("u1"),"sa_f32":np.asarray(sa,dtype="<f4"),
                   "sw_f32":sw.astype("<f4"),"sy_f32":sy.astype("<f4"),"reference_f32":reference.astype("<f4")}
