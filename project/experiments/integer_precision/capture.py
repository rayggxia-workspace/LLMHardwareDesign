"""Strict local capture receiver. No network, pickle, or implicit dequantization."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import numpy as np

DTYPES={k:np.dtype(v) for k,v in {"f32":"<f4","f16":"<f2","i8":"i1","u8":"u1","i16":"<i2","u16":"<u2",
        "i32":"<i4","u32":"<u4","i64":"<i8","u64":"<u8"}.items()}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def local_path(root,name):
    if "\\" in name or ":" in name:
        raise ValueError("only relative POSIX paths accepted")
    p=PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("unsafe payload path")
    actual=(root/name).resolve()
    if not actual.is_relative_to(root.resolve()):
        raise ValueError("payload escapes root, including symlink")
    return actual


def validate(root, expected_commit=None, expected_revision=None):
    import jsonschema
    root=Path(root)
    doc=json.loads((root/"capture.json").read_text(encoding="utf-8"))
    schema=json.loads(Path(__file__).with_name("capture.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)
    if expected_commit and doc["producer"]["code_commit"]!=expected_commit:
        raise ValueError("producer commit differs from requested version")
    if expected_revision and doc["model"]["revision"]!=expected_revision:
        raise ValueError("model revision differs from requested version")
    tensors={}; arrays={}; paths=set()
    for t in doc["tensors"]:
        if t["name"] in tensors or t["file"]["path"] in paths:
            raise ValueError("duplicate tensor name or payload path")
        tensors[t["name"]]=t; paths.add(t["file"]["path"])
        if len(t["shape"])!=len(t["axis_names"]):
            raise ValueError("axis rank mismatch")
        if "selection" in t:
            s=t["selection"]
            if len(s["original_shape"])!=len(t["shape"]) or len(s["offsets"])!=len(t["shape"]) or any(
                off+dim>orig for off,dim,orig in zip(s["offsets"],t["shape"],s["original_shape"])):
                raise ValueError("slice exceeds original tensor bounds")
        dtype=DTYPES[t["dtype"]]
        expected=math.prod(t["shape"])*dtype.itemsize
        file=local_path(root,t["file"]["path"])
        if expected!=t["file"]["bytes"] or file.stat().st_size!=expected:
            raise ValueError("payload byte/shape/dtype mismatch")
        data=file.read_bytes()
        if sha(data)!=t["file"]["sha256"]:
            raise ValueError("payload SHA-256 mismatch")
        a=np.frombuffer(data,dtype=dtype).reshape(t["shape"])
        if dtype.kind=="f" and not np.isfinite(a).all():
            raise ValueError("nonfinite floating reference/scale")
        arrays[t["name"]]=a
        e=t["encoding"]; kind=e["kind"]
        if (kind=="reference_float") != (dtype.kind=="f"):
            raise ValueError("floating dtype requires explicit reference_float encoding")
        if kind=="fixed_point" and "fraction_bits" not in e:
            raise ValueError("fixed point requires fractional bits")
        if t["role"]=="requant_multiplier" and (t["dtype"]!="u32" or np.any(a>2147483647)):
            raise ValueError("M must be U31 stored in u32")
        if t["role"]=="requant_shift" and (t["dtype"]!="u8" or np.any(a>63)):
            raise ValueError("RQ shift must be u8 0..63")
    for t in doc["tensors"]:
        e=t["encoding"]
        if e["kind"]=="scaled_accumulator":
            factors=e.get("scale_factor_tensors",[]);axes=e.get("scale_factor_axes",[])
            if not factors or len(factors)!=len(axes):
                raise ValueError("scaled accumulator requires explicit factor tensors and mapped axes")
            for name,ax in zip(factors,axes):
                if name not in tensors or tensors[name]["role"]!="scale" or any(i>=len(t["shape"]) for i in ax):
                    raise ValueError("invalid accumulator scale reference/axis")
                if tensors[name]["shape"]!=[t["shape"][i] for i in ax]:
                    raise ValueError("accumulator scale shape mismatch")
        if t["role"]=="accumulator" and e["kind"] not in ("scaled_accumulator","fixed_point"):
            raise ValueError("accumulator scale cannot be implicit")
        if e["kind"]=="symmetric":
            for key in ("zero_point","group_axes","group_shape","scale_tensor","scale_encoding"):
                if key not in e:
                    raise ValueError("symmetric requires "+key)
            axes=e["group_axes"]; blocks=e.get("block_shape",[1]*len(axes))
            if len(blocks)!=len(axes) or any(i>=len(t["shape"]) for i in axes):
                raise ValueError("group axis/block shape mismatch")
            wanted=[(t["shape"][i]+b-1)//b for i,b in zip(axes,blocks)]
            if wanted!=e["group_shape"]:
                raise ValueError("group shape inconsistent with actual tensor/block")
            scale=tensors.get(e["scale_tensor"])
            if scale is None or scale["name"]==t["name"] or scale["shape"]!=wanted:
                raise ValueError("scale reference/shape mismatch")
            if e["scale_encoding"]=="descriptive_f32":
                if scale["role"]!="scale" or scale["dtype"]!="f32" or np.any(arrays[scale["name"]]<=0):
                    raise ValueError("descriptive scale must be positive f32 scale tensor")
            elif scale["role"]!="dyadic_exponent" or scale["dtype"]!="i16":
                raise ValueError("dyadic scale must refer to i16 exponents")
        for key,role in (("multiplier_tensor","requant_multiplier"),("shift_tensor","requant_shift")):
            if key in e and (e[key] not in tensors or tensors[e[key]]["role"]!=role):
                raise ValueError("requant reference missing/wrong role")
        if ("multiplier_tensor" in e)!=("shift_tensor" in e):
            raise ValueError("RQ multiplier and shift must be paired")
        if "multiplier_tensor" in e:
            ms=tensors[e["multiplier_tensor"]]["shape"]; rs=tensors[e["shift_tensor"]]["shape"]
            if ms!=rs or (ms!=t["shape"] and ms!=[t["shape"][-1]]):
                raise ValueError("RQ parameter shape must be full output or last-channel axis")
    run=doc["run"]
    if run["execution"] in ("integer_kernel","integer_reference"):
        if run["floating_fallbacks"]:
            raise ValueError("integer execution scope cannot conceal float fallbacks")
        # Reference floats and offline scales may coexist; active output/activation cannot be float.
        if any(t["dtype"].startswith("f") and t["role"] not in ("reference_output","scale") for t in doc["tensors"]):
            raise ValueError("integer execution contains active floating tensors")
    return doc,arrays


def tensor(root,name,array,role,axes,encoding,layer=0,node="local"):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    a=np.array(array,copy=True,order="C")
    dtype=next((k for k,v in DTYPES.items() if v==a.dtype),None)
    if dtype is None:
        raise ValueError("unsupported writer dtype")
    file=name+".bin"
    path=local_path(root,file); data=a.tobytes(order="C"); path.write_bytes(data)
    return {"name":name,"role":role,"layer":layer,"node":node,"shape":list(a.shape),"axis_names":axes,
            "dtype":dtype,"byte_order":"little","order":"C","file":{"path":file,"bytes":len(data),"sha256":sha(data)},"encoding":encoding}


def encoding(kind,**extra):
    return {"kind":kind,"contract":"C1-RNE-v0.1","parameter_generation":"static_constants",
            "rounding":"ties_to_even" if kind in ("fixed_point","symmetric","requant_params") else "not_applicable",
            "saturation":"clip" if kind in ("fixed_point","symmetric") else "reject",**extra}


def replay_linear(root):
    """Opt-in QA[M,K] * QW[N,K] + RQ graph, independent Python/Fraction oracle.

    General captures still use validate; this replay intentionally requires
    the explicit example names and does not guess arbitrary model graphs.
    """
    from fractions import Fraction
    d,t=validate(root)
    names=("a_i8","w_i8","acc_i32","M_u32","r_u8")
    if any(k not in t for k in names):raise ValueError("linear replay missing declared inputs")
    a,w,acc,m,r=(t[k] for k in names)
    out=t.get("out_i8",t.get("out_i16"))
    if out is None or a.ndim!=2 or w.ndim!=2 or a.shape[1]!=w.shape[1] or acc.shape!=(a.shape[0],w.shape[0]) or out.shape!=acc.shape:
        raise ValueError("linear replay shape mismatch")
    checked_outputs=0
    for row,col in np.ndindex(acc.shape):
        integer_sum=sum(int(x)*int(y) for x,y in zip(a[row],w[col]))
        if not -(1<<31)<=integer_sum<(1<<31) or int(acc[row,col])!=integer_sum:
            raise ValueError("linear integer accumulation replay failed")
        mi=int(m[row,col] if m.ndim==2 else m[col]);ri=int(r[row,col] if r.ndim==2 else r[col])
        value=round(Fraction(integer_sum*mi,1<<ri));b=out.dtype.itemsize*8
        value=max(-(1<<(b-1)),min((1<<(b-1))-1,value))
        if int(out[row,col])!=value:raise ValueError("linear RNE/saturation replay failed")
        checked_outputs+=1
    return {"integer_outputs_replayed":checked_outputs,"oracle":"Python arbitrary integer dot + Fraction ties-even"}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--expected-commit");p.add_argument("--expected-revision");p.add_argument("--replay-linear",action="store_true"); a=p.parse_args()
    d,t=validate(a.root,a.expected_commit,a.expected_revision)
    print(json.dumps({"schema":d["schema"],"validated_tensors":len(t),"execution":d["run"]["execution"],"replay":replay_linear(a.root) if a.replay_linear else "not requested"}))
