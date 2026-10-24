"""Small synthetic receiver boundary checks; no model download or server use."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location("issue70_receive", Path(__file__).with_name("receive.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def save_manifest(root, *, kind=None, extra=None):
    rows = [dict(path=p.name, **r.artifact(p)) for p in sorted(root.iterdir()) if p.is_file() and p.name != "manifest.json"]
    data = dict(status="EXECUTED", source={"commit": "a" * 40}, artifacts=rows)
    if kind:
        data["kind"] = kind
    data.update(extra or {})
    r.write_json(root / "manifest.json", data)


def granite_fixture(root):
    cap, numeric = root / "capture", root / "numeric"
    cap.mkdir(); numeric.mkdir()
    np.savez_compressed(cap / "capture.npz", tokens=np.arange(4))
    save_manifest(cap, kind="granite_capture", extra={"model_revision": "b" * 40})
    z = {"common_unit_exp": np.asarray(-8, np.int16)}
    w = dict(dots=[], requants=[], routing=[], merges=[])
    for i in range(32):
        z[f"a{i}"] = np.array([-127, 3, 5], np.int8)
        z[f"w{i}"] = np.array([4, -4, 6], np.int8)
        z[f"acc_{i}"] = np.asarray(-490, np.int64)
        w["dots"].append(dict(a=f"a{i}", w=f"w{i}", acc=f"acc_{i}", bound=1778))
        for key, value in (("v", -3), ("m", 1), ("s", 1), ("q", -2)):
            z[f"{key}{i}"] = np.asarray(value, np.int64)
        w["requants"].append(dict(value=f"v{i}", multiplier=f"m{i}", shift=f"s{i}", out=f"q{i}", bits=32))
    fp = np.tile(np.linspace(2, -2, 40), (8, 1))
    z["router_logits_fp"] = fp
    z["route_ids_fp"] = r.topk(fp, 8)
    def gates(x):
        ids = r.topk(x, 8)
        v = np.take_along_axis(x, ids, 1)
        v = np.exp(v - v.max(1, keepdims=True))
        return v / v.sum(1, keepdims=True)
    z["route_weights_fp"] = gates(fp)
    for activation in ("dynamic_row", "calibration_tensor"):
        q = fp.copy(); q[0, 8] = q[0, 7] + .01
        z["router_logits_q_" + activation] = q
        z["route_ids_q_" + activation] = r.topk(q, 8)
        z["route_weights_q_" + activation] = gates(q)
        w["routing"].append(dict(logits_fp="router_logits_fp", logits_q="router_logits_q_"+activation,
                                 ids_fp="route_ids_fp", ids_q="route_ids_q_"+activation, activation=activation))
        for route in ("route_fixed_diagnostic", "route_recomputed"):
            key = "merge" + str(len(w["merges"]))
            row = dict(label=activation+"__"+route, common_unit_exp=-8, bits=32, gate_shift=15)
            gate = z["route_weights_fp" if route == "route_fixed_diagnostic" else "route_weights_q_"+activation][0]
            gq = np.rint(gate * 32768).astype(np.int64)
            aligned = np.tile(np.arange(1536, dtype=np.int64), (8, 1)) - 400
            weighted = (aligned * gq[:, None]).sum(0)
            for name, value in dict(acc=aligned, multiplier=np.ones_like(aligned), shift=np.zeros_like(aligned),
                                    aligned=aligned, gate_q15=gq, weighted_sum=weighted,
                                    out=np.array([r.rne(v, 15) for v in weighted], np.int64)).items():
                z[key+"_"+name] = value; row[name] = key+"_"+name
            w["merges"].append(row)
    np.savez_compressed(numeric / "witnesses.npz", **z)
    r.write_json(numeric / "witnesses.json", w)
    r.write_json(numeric / "metrics.json", {"cases":[{"route": route} for _ in range(4)
                                                    for route in ("route_fixed_diagnostic", "route_recomputed")]})
    save_manifest(numeric, kind="granite_numeric", extra={"model_revision":"b"*40,
                  "source":{"commit":"a"*40, "capture_manifest_sha256":r.sha(cap/"manifest.json")}})
    return numeric, cap


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rne_ties_signed(self):
        self.assertEqual([r.rne(x, 1) for x in (-7, -5, -3, -1, 1, 3, 5, 7)], [-4,-2,-2,0,0,2,2,4])

    def test_rne_leftshift(self):
        self.assertEqual(r.rne(-3, -4), -48)
        with self.assertRaises(ValueError): r.rne(3, 1025)

    def test_ieee_exact_fixed_rounding_and_sat(self):
        self.assertEqual(r.fixed_from_float(1.25, -1, 8), (2, False))
        self.assertEqual(r.fixed_from_float(-1.75, -1, 8), (-4, False))
        self.assertEqual(r.fixed_from_float(128, 0, 8), (127, True))
        with self.assertRaises(ValueError): r.fixed_from_float(float("inf"), 0, 8)

    def test_paths(self):
        for name in ("../x", "/tmp/x", "C:/x", "a\\b", ""):
            with self.assertRaises(ValueError): r.local_path(self.root, name)

    def test_empty_manifest_rejected(self):
        r.write_json(self.root / "manifest.json", dict(status="PASS", artifacts={}))
        with self.assertRaisesRegex(ValueError, "empty artifact"): r.manifest(self.root)

    def test_artifact_hash_and_duplicate_rejection(self):
        (self.root / "a").write_text("x")
        save_manifest(self.root)
        r.manifest(self.root)
        (self.root / "a").write_text("y")
        with self.assertRaisesRegex(ValueError, "artifact SHA/size"): r.manifest(self.root)
        m=r.read_json(self.root / "manifest.json");m["artifacts"] *= 2;r.write_json(self.root/"manifest.json",m)
        with self.assertRaisesRegex(ValueError, "duplicate"): r.manifest(self.root)

    def test_topk_stable_and_flip(self):
        x=np.zeros((1,40));self.assertEqual(r.topk(x,8).tolist(),[list(range(8))])
        y=x.copy();y[0,39]=1
        z=dict(f=x,q=y,fi=r.topk(x,8),qi=r.topk(y,8))
        self.assertEqual(r.verify_routes(z,dict(logits_fp="f",logits_q="q",ids_fp="fi",ids_q="qi"))["top8_set_flips"],1)
        z["qi"]=z["fi"]
        with self.assertRaisesRegex(ValueError,"must be recomputed"):r.verify_routes(z,dict(logits_fp="f",logits_q="q",ids_fp="fi",ids_q="qi"))

    def test_complete_dot_bound_and_code(self):
        z=dict(a=np.array([-127,127],np.int8),w=np.array([127,127],np.int8),v=np.asarray(0))
        row=dict(a="a",w="w",acc="v",bound=32258,K=2)
        self.assertEqual(r.verify_dots(z,[row]),1)
        z["v"]=np.asarray(1)
        with self.assertRaisesRegex(ValueError,"dot code"):r.verify_dots(z,[row])
        z["v"]=np.asarray(0);row["bound"]=1
        with self.assertRaisesRegex(ValueError,"INT32 bound"):r.verify_dots(z,[row])

    def test_dot_minus128_domain_explicit(self):
        z=dict(a=np.array([-128],np.int8),w=np.array([1],np.int8),v=np.asarray(-128))
        row=dict(a="a",w="w",acc="v")
        with self.assertRaisesRegex(ValueError,"A8 domain"):r.verify_dots(z,[row])
        row["activation_abs_max"]=128;self.assertEqual(r.verify_dots(z,[row]),1)

    def test_rq_wide_product_and_sat(self):
        z={k:np.asarray(v,np.int64) for k,v in dict(v=200,m=1,s=0,q=127).items()}
        row=dict(value="v",multiplier="m",shift="s",out="q",bits=8)
        self.assertEqual(r.verify_requants(z,[row]),1)
        z["m"]=np.asarray(1<<62);z["v"]=np.asarray(4)
        with self.assertRaisesRegex(ValueError,"I64 product"):r.verify_requants(z,[row])

    def test_generic_eight_expert_units(self):
        z=dict(c=np.ones((1,8,2),np.int32),u=np.zeros((1,8),np.int16),w=np.ones((1,8),np.int16),
               s=np.full((1,2),8,np.int64),e=np.full((1,2),-3,np.int16))
        row=dict(codes="c",units="u",weights="w",sum="s",sum_unit="e",weight_fraction=3)
        self.assertEqual(r.verify_merge(z,row)["aligned_values"],2)
        z["e"][0,0]=0
        with self.assertRaisesRegex(ValueError,"shared output unit"):r.verify_merge(z,row)

    def test_granite_complete_fixture_and_actual_rehashed_negatives(self):
        result, cap=granite_fixture(self.root)
        original=r.sha(result/"witnesses.npz")
        received=r.granite(result,cap)
        self.assertEqual(received["dots"],32)
        self.assertEqual(received["merges"][0]["rq_values"],8*1536)
        neg=r.negatives("granite",result,cap,self.root/"negative")
        self.assertEqual([x["status"] for x in neg],["REJECTED","REJECTED"])
        self.assertIn("dot code",neg[0]["reason"])
        self.assertIn("must be recomputed",neg[1]["reason"])
        self.assertEqual(original,r.sha(result/"witnesses.npz"))

    def test_capture_binding_failure(self):
        result,cap=granite_fixture(self.root)
        m=r.read_json(result/"manifest.json");m["source"]["capture_manifest_sha256"]="0"*64;r.write_json(result/"manifest.json",m)
        with self.assertRaisesRegex(ValueError,"capture manifest binding"):r.granite(result,cap)

    def test_source_commit_required(self):
        for value in ("unbound", "a"*39, "A"*40):
            with self.assertRaisesRegex(ValueError,"source commit"):r.source_commit({"source":{"commit":value}})

    def test_mamba_bridge_and_storage_small(self):
        z={}
        for p in ("calibration","evaluation"):
            z.update({p+".a":np.array([.5,.5]),p+".dt":np.array([1.,1.]),p+".x":np.array([[1.,2.],[1.,2.]]),
                      p+".b":np.array([[1.,-1.],[1.,-1.]]),p+".c":np.ones((2,2)),p+".skip":np.asarray(.25),
                      p+".initial_state":np.zeros((2,2))})
            z[p+".fp64_states"]=np.array([[[1.,-1.],[2.,-2.]],[[1.5,-1.5],[3.,-3.]]])
            z[p+".fp64_output"]=np.array([[.25,.5],[.25,.5]])
        self.assertEqual(r.recurrence(z,"evaluation")["steps"],2)
        for bits in (16,32):
            unit=2.**__import__("math").ceil(__import__("math").log2(3/((1<<(bits-1))-1)))
            key="S"+str(bits)
            codes=np.rint(z["evaluation.fp64_states"]/unit).astype("int"+str(bits))
            z.update({key+".unit":np.asarray(unit),key+".unit_exponent":np.asarray(int(__import__("math").log2(unit))),
                      key+".codes":codes,key+".states":codes.astype(float)*unit,key+".output":z["evaluation.fp64_output"],
                      key+".saturations":np.zeros(2,np.int64)})
            self.assertEqual(r.recurrence(z,"evaluation",bits=bits)["saturation_cells"],0)
        z["S32.codes"][0,0,0]+=1
        with self.assertRaisesRegex(ValueError,"stored code replay"):r.recurrence(z,"evaluation",bits=32)

    def test_mamba_coefficient_domain_rejects_nonphysical_decay(self):
        z={"evaluation."+k:v for k,v in dict(a=np.array([1.1]),dt=np.ones(1),x=np.ones((1,1)),
           b=np.ones((1,1)),c=np.ones((1,1)),skip=np.asarray(1.),initial_state=np.zeros((1,1))).items()}
        with self.assertRaisesRegex(ValueError,"coefficient domain"):r.recurrence(z,"evaluation")

    def test_projection_full_k_code_mutation(self):
        z=dict(weight_code=np.ones((16,3),np.int8))
        for s in ("cal_static_tensor","eval_dynamic_row"):
            z[s+"_input_code"]=np.ones((2,3),np.int8)
            z[s+"_accumulator"]=np.full((2,16),3,np.int32)
        self.assertEqual(r.verify_projection(z)["complete_dot_values"],64)
        z["eval_dynamic_row_accumulator"][0,0]=4
        with self.assertRaisesRegex(ValueError,"complete-K dot"):r.verify_projection(z)

    def test_projection_source_encoding_and_scale(self):
        z=dict(weight=np.ones((16,3)),weight_code=np.full((16,3),127,np.int8),
               weight_scale=np.full(16,1/127),calibration_input=np.ones((1,3)),evaluation_input=np.ones((2,3)))
        for s in ("cal_static_tensor","eval_dynamic_row"):
            z[s+"_input_code"]=np.full((2,3),127,np.int8)
            z[s+"_input_scale"]=np.full((2,1),1/127,dtype=np.float64 if s=="cal_static_tensor" else np.float32)
            z[s+"_accumulator"]=np.full((2,16),3*127*127,np.int32)
            z[s+"_dequant"]=z[s+"_accumulator"]*z[s+"_input_scale"]*z["weight_scale"][None,:]
        self.assertEqual(r.verify_projection(z,full=True)["source_encoding_values"],60)
        z["cal_static_tensor_input_scale"][0,0]*=2
        with self.assertRaisesRegex(ValueError,"A scale source"):r.verify_projection(z,full=True)

    def test_dynamic_projection_preserves_fp32_bridge_dtype(self):
        # 1/127 differs between FP32 and FP64. The saved raw source remains an
        # exact FP32->FP64 cast, so its storage dtype does not change quantizer.
        raw=np.ones((2,3),np.float32)
        self.assertNotEqual(float(np.max(raw)/127),float(np.max(raw.astype(np.float64))/127))
        scale=np.maximum(np.max(np.abs(raw),axis=1,keepdims=True),1e-30)/127
        self.assertEqual(scale.dtype,np.float32)
        self.assertEqual((raw/scale).dtype,np.float32)

    def test_descriptor_owner_epoch_and_complete_shapes(self):
        cap={};total=2
        for name,shape in dict(kv_key=(1,2,total,128),kv_value=(1,2,total,128),
                              conv=(1,4608,4),ssm=(1,32,128,256)).items():
            cap["full.final."+name]=np.broadcast_to(np.asarray(0.),shape)
            cap["initial."+name]=np.zeros((1,2,0,128)) if name.startswith("kv_") else cap["full.final."+name]
            for p in ("cached.final","chunk1.final","chunk8.final","chunk16.final"):
                cap[p+"."+name]=cap["full.final."+name]
        report=dict(input={"evaluation_tokens":total},chunk_continuity={})
        for chunk in (1,8,16):
            rows=[]
            for stop in range(min(chunk,total),total+1,min(chunk,total)):
                rows.append(dict(owner="layer0.hybrid",next_position=stop,epoch=0,version=stop,
                     descriptor_is_analysis_metadata_not_native_epoch_enforcement=True,
                     kv_shape=[1,2,stop,128],conv_shape=[1,4608,4],ssm_shape=[1,32,128,256]))
            report["chunk_continuity"][str(chunk)]={"checkpoints":rows}
        self.assertEqual(r.verify_descriptors(report,cap,{})["descriptors_and_shapes"],20)
        report["chunk_continuity"]["8"]["checkpoints"][0]["epoch"]=1
        with self.assertRaisesRegex(ValueError,"epoch/version consistency"):r.verify_descriptors(report,cap,{})

    def test_native_threshold_failure_is_retained(self):
        row=r.float_gate(np.array([1.1]),np.array([1.]),2e-4,1e-2)
        self.assertFalse(row["passed"])
        self.assertGreater(row["relative_l2"],row["relative_limit"])


if __name__ == "__main__":
    unittest.main()
