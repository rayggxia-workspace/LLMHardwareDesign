"""Independent exact oracles and fault cases, rather than self-comparison."""
import copy
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import tempfile
import unittest
import numpy as np
import fixed as f
import reference as oracle
import vectors as v
from tables import load,build
import capture


class Arithmetic(unittest.TestCase):
    def test_quantizer_output16_and_static_metadata(self):
        from quantize import linear
        a=np.array([[.1,-.3,.7],[.2,.1,-.2],[.15,-.2,.5]],np.float32)
        w=np.array([[.3,-.4,.2],[-.2,.5,-.1]],np.float32)
        for bits in (8,16):
            result,data=linear(a,w,a[:2],"static_tensor",bits)
            self.assertEqual(result["rq_parameter_sets"],2)
            self.assertEqual(data[f"out_i{bits}"].dtype,np.dtype("i1" if bits==8 else "<i2"))
            self.assertTrue(np.all(data["M_u32"][0]==data["M_u32"][1]))
    def test_rounding_ties_sign_and_extremes(self):
        for r in range(64):
            half=0 if r==0 else 1<<(r-1)
            for q in (0,1,2,3,63,127,32767):
                for d in (-1,0,1):
                    x=(q<<r)+half+d
                    for sign in (-1,1):
                        self.assertEqual(f.rne_shift(x*sign,r),oracle.right_shift(x*sign,r))
        self.assertEqual(f.rne_shift(-3,1),-2);self.assertEqual(f.rne_shift(-5,1),-2)
        with self.assertRaises(ValueError):f.rne_shift(1,64)

    def test_mul_exact_and_operation_budget(self):
        rng=random.Random(3301)
        for ab,bb,unsigned in ((16,16,False),(32,31,True),(32,16,False),(32,32,True),(33,16,True)):
            lo=-(1<<(ab-1));hi=(1<<(ab-1))-1
            blo=0 if unsigned else -(1<<(bb-1));bhi=(1<<bb)-1 if unsigned else (1<<(bb-1))-1
            pairs=[(a,b) for a in (lo,-1,0,1,hi) for b in (blo,0,bhi)]
            pairs += [(rng.randint(lo,hi),rng.randint(blo,bhi)) for _ in range(200)]
            for a,b in pairs:
                c=Counter()
                if not -(1<<63)<=a*b<(1<<63):
                    with self.assertRaises(OverflowError):f.mul_radix7(a,b,ab,bb,c,unsigned)
                else:
                    self.assertEqual(f.mul_radix7(a,b,ab,bb,c,unsigned),a*b)
                    self.assertEqual(c["mul8_partial_products"],math.ceil(ab/7)*math.ceil(bb/7))
        for a in (-32768,-1,0,32767):
            for b in range(-128,128):self.assertEqual(f.mul_i16_i8(a,b),a*b)

    def test_requant_independent_fraction(self):
        rng=random.Random(3302)
        pairs=[(a,m,r) for a in (-(1<<31),-257,-255,-5,-3,0,3,5,255,257,(1<<31)-1)
               for m in (0,1,3,(1<<31)-1) for r in (0,1,2,16,31,32,63)]
        pairs += [(rng.randint(-(1<<31),(1<<31)-1),rng.randrange(1<<31),rng.randrange(64)) for _ in range(1500)]
        for a,m,r in pairs:
            for b in (8,16):self.assertEqual(f.requant(a,m,r,b),oracle.requant(a,m,r,b))
        for a,m,r in ((1<<31,1,0),(0,1<<31,0),(0,-1,0)):
            with self.assertRaises(OverflowError):f.requant(a,m,r)
        self.assertEqual(f.requant(255,1,1),127) # 127.5 ->128, then clip

    def test_div_sqrt_and_rejection(self):
        rng=random.Random(3303)
        for bits in (32,64):
            for n,d in [(0,1),((1<<bits)-1,1),((1<<bits)-1,(1<<bits)-1)]+[(rng.randrange(1<<bits),rng.randrange(1,1<<bits)) for _ in range(200)]:
                self.assertEqual(f.udiv_restoring(n,d,bits),divmod(n,d))
                self.assertEqual(f.div_rne_unsigned(n,d,bits),round(Fraction(n,d)))
            with self.assertRaises(ZeroDivisionError):f.udiv_restoring(1,0,bits)
        for n in (0,1,2,3,4,(1<<48)-1,*[rng.randrange(1<<48) for _ in range(500)]):
            self.assertEqual(f.isqrt48(n),math.isqrt(n))
        with self.assertRaises(OverflowError):f.isqrt48(1<<48)

    def test_accumulator_prefix_bound_and_partition(self):
        a=np.full((1,131071),-128,dtype=np.int8)
        self.assertEqual(int(f.gemm_i8(a,a)[0,0]),131071*16384)
        with self.assertRaises(OverflowError):f.gemm_i8(np.full((1,131072),-128,np.int8),np.full((1,131072),-128,np.int8))
        rng=np.random.default_rng(33);a=rng.integers(-128,128,(7,35),dtype=np.int8);w=rng.integers(-128,128,(9,35),dtype=np.int8)
        full=f.gemm_i8(a,w)
        tiled=sum(f.gemm_i8(a[:,i:i+8],w[:,i:i+8]).astype(np.int64) for i in range(0,35,8))
        np.testing.assert_array_equal(full,tiled)
        # Early rounding changes the operation, even absent overflow/saturation.
        self.assertNotEqual(f.requant(1+1,1,1),f.requant(1,1,1)+f.requant(1,1,1))


class Vectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tables=load()
    def test_lut_reproducibility_monotonic_endpoints(self):
        self.assertEqual(self.tables,build())
        s=self.tables["sigmoid_u16_f16"];e=self.tables["exp_u32_f24"]
        self.assertEqual(s[128],32768);self.assertEqual(e[0],1<<24)
        self.assertTrue(all(a<=b for a,b in zip(s,s[1:])))
        self.assertTrue(all(a>=b for a,b in zip(e,e[1:])))

    def test_silu_integer_interpolation_independent(self):
        table=self.tables["sigmoid_u16_f16"]
        for x in range(-32768,32768,17):
            i=x//256+128;frac=x%256
            sg=table[i]+((table[i+1]-table[i])*frac//256)
            expected=max(-32768,min(32767,round(Fraction(x*sg,1<<16))))
            self.assertEqual(v.silu_i16_f12(x,table),expected)

    def test_rms_exact_wide_and_zero(self):
        x=[-12000,4000,2000,500];g=[16384]*4
        gain=round(math.sqrt(4)*(1<<20));eps=4
        actual,trace=v.rms_i16_f12(x,g,eps,gain)
        root=math.isqrt(sum(y*y for y in x)+eps);inv=gain//max(root,1)
        expected=[max(-32768,min(32767,round(Fraction(y*16384*inv,1<<22)))) for y in x]
        self.assertEqual(actual,expected)
        self.assertEqual(v.rms_i16_f12([0]*4,g,0,gain)[0],[0]*4)
        self.assertEqual(trace["sum_u48"],sum(y*y for y in x)+eps)

    def test_softmax_length_failure_mask_cutoff(self):
        e=self.tables["exp_u32_f24"]
        self.assertEqual(v.softmax_fixed([0]*256,e,7)[0],[0]*256)
        self.assertGreater(sum(v.softmax_fixed([0]*256,e,15)[0]),0)
        self.assertEqual(v.softmax_fixed([0,-5000],e,7)[0],[127,0])
        self.assertEqual(v.softmax_fixed([32767,-32768],e,7,[False,True])[0],[0,127])
        with self.assertRaises(ValueError):v.softmax_fixed([1],e,7,[False])

    def test_recurrence_fraction_oracle(self):
        # Independent equations, all per-stage rounding specified as Fraction.
        q=[7000,-9000];k=[4000,10000];values=[2000,-500];s=[[123456,-345678],[987654,222222]];beta=19000;decay=32000
        round_shift=lambda x,r: round(Fraction(x,1<<r))
        decayed=[[round_shift(y*decay,15) for y in row] for row in s]
        delta=[round_shift(((values[j]<<8)-round_shift(sum(decayed[i][j]*k[i] for i in range(2)),14))*beta,15) for j in range(2)]
        expected=[[decayed[i][j]+round_shift(delta[j]*k[i],14) for j in range(2)] for i in range(2)]
        out=[round_shift(sum(expected[i][j]*q[i] for i in range(2)),22) for j in range(2)]
        self.assertEqual(v.recurrent_delta(q,k,values,beta,decay,s),(out,expected))


class Capture(unittest.TestCase):
    def setUp(self):
        base=Path("D:/Projects/Codex/int8-contract-20261023/receiver-tests");base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.tmp.name)
        z="0"*64
        self.doc={"schema":"llm-precision-capture/1","producer":{"code_commit":"0"*40,"source_dirty":False,"source_sha256":{"example.py":z},"script":"example.py","arguments":[],"tool_versions":{"python":"test"},"hardware":{"host":"local synthetic"}},
                  "model":{"model_id":"synthetic/receiver-test","revision":"v1","config_sha256":z,"weights_manifest_sha256":z,"tokenizer_manifest_sha256":z},
                  "run":{"phase":"operator","batch":1,"prefix_tokens":0,"new_tokens":1,"input_ids_sha256":z,"data_version":"synthetic-v1","calibration_split":"static constants","evaluation_split":"receiver","execution":"integer_reference","backend":"Python integer","floating_fallbacks":[],"measurement_scope":"numerical_only"},"tensors":[]}
        self.doc["tensors"].append(capture.tensor(self.root,"scale",np.array([.1,.2],dtype="<f4"),"scale",["channel"],capture.encoding("reference_float")))
        self.doc["tensors"].append(capture.tensor(self.root,"q",np.ones((3,2),dtype=np.int8),"activation",["token","channel"],capture.encoding("symmetric",zero_point=0,group_axes=[1],group_shape=[2],scale_tensor="scale",scale_encoding="descriptive_f32")))
    def tearDown(self):self.tmp.cleanup()
    def write(self,d): (self.root/"capture.json").write_text(json.dumps(d),encoding="utf-8")
    def test_valid_and_expected_versions(self):
        self.write(self.doc);capture.validate(self.root,"0"*40,"v1")
        with self.assertRaises(ValueError):capture.validate(self.root,"1"*40)
        with self.assertRaises(ValueError):capture.validate(self.root,expected_revision="stale")
    def test_semantic_faults(self):
        changes=[lambda d:d["tensors"][1]["file"].update(sha256="f"*64),
                 lambda d:d["tensors"][1].update(shape=[2,3]),
                 lambda d:d["tensors"][1].update(axis_names=["one"]),
                 lambda d:d["tensors"][1]["encoding"].update(group_axes=[2]),
                 lambda d:d["tensors"][1]["encoding"].update(scale_tensor="missing"),
                 lambda d:d["tensors"][1]["encoding"].pop("zero_point"),
                 lambda d:d["tensors"][1]["encoding"].update(group_shape=[1]),
                 lambda d:d["tensors"][1]["file"].update(path="../outside.bin"),
                 lambda d:d["tensors"][1]["file"].update(path="D:/outside.bin"),
                 lambda d:d["run"].update(floating_fallbacks=["hidden norm"]),
                 lambda d:d["tensors"].append(copy.deepcopy(d["tensors"][0]))]
        for change in changes:
            d=copy.deepcopy(self.doc);change(d);self.write(d)
            with self.assertRaises((ValueError,FileNotFoundError)):
                capture.validate(self.root)
    def test_block_scale_and_invalid_parameter_values(self):
        d=copy.deepcopy(self.doc);d["tensors"][1]["encoding"].update(group_axes=[0],group_shape=[2],block_shape=[2])
        self.write(d);capture.validate(self.root)
        for role,dtype,value in (("requant_multiplier","<u4",1<<31),("requant_shift","u1",64)):
            d=copy.deepcopy(self.doc);d["tensors"].append(capture.tensor(self.root,"param",np.array([value],dtype=dtype),role,["p"],capture.encoding("requant_params")));self.write(d)
            with self.assertRaises(ValueError):capture.validate(self.root)
    def test_integer_replay_rejects_validly_rehashed_wrong_result(self):
        self.doc["tensors"]=[]
        for name,role,array,axes in (
            ("a_i8","activation",np.array([[1,2],[-3,4]],np.int8),["token","K"]),
            ("w_i8","weight",np.array([[2,-1]],np.int8),["channel","K"]),
            ("acc_i32","accumulator",np.array([[0],[-10]],dtype="<i4"),["token","channel"]),
            ("out_i8","output",np.array([[0],[-5]],np.int8),["token","channel"]),
            ("M_u32","requant_multiplier",np.array([1],dtype="<u4"),["channel"]),
            ("r_u8","requant_shift",np.array([1],dtype="u1"),["channel"])):
            self.doc["tensors"].append(capture.tensor(self.root,name,array,role,axes,capture.encoding("fixed_point",fraction_bits=0)))
        self.write(self.doc);self.assertEqual(capture.replay_linear(self.root)["integer_outputs_replayed"],2)
        file=self.root/"out_i8.bin";file.write_bytes(bytes([1,251]))
        self.doc["tensors"][3]["file"]["sha256"]=capture.sha(file.read_bytes());self.write(self.doc)
        capture.validate(self.root)
        with self.assertRaises(ValueError):capture.replay_linear(self.root)


if __name__=="__main__":unittest.main(verbosity=2)
