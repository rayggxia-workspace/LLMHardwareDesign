"""Independent small Fraction arithmetic and state-transaction boundary tests."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from state import (StateLease,bridge_codes,cost,execute,float_reference,format_bounds,head_units,
                   rne,run_integer,save,save_npz,sha,state_bounds,step)


def fraction_step(s,q,k,v,d,b,su,vu,bits,df):
    h,dim,width=s.shape;lo,hi=state_bounds(bits)
    new=np.empty(s.shape,dtype=np.int64);out=np.empty((h,width),dtype=np.int64)
    for a in range(h):
        dec=[[round(Fraction(int(s[a,i,j])*int(d[a]),1<<df)) for j in range(width)] for i in range(dim)]
        pred=[round(Fraction(sum(dec[i][j]*int(k[a,i]) for i in range(dim)),32768)) for j in range(width)]
        aligned=[round(Fraction(int(v[a,j]))*Fraction(2)**(int(vu[a])-int(su[a]))) for j in range(width)]
        delta=[round(Fraction((aligned[j]-pred[j])*int(b[a]),32768)) for j in range(width)]
        for i in range(dim):
            for j in range(width):new[a,i,j]=max(lo,min(hi,dec[i][j]+round(Fraction(int(k[a,i])*delta[j],32768))))
        for j in range(width):out[a,j]=round(Fraction(sum(int(new[a,i,j])*int(q[a,i]) for i in range(dim)),32768))
    return new,out


class IntegerState(unittest.TestCase):
    def test_signed_rne_ties_left_shift(self):
        for x in [-(1<<54)-7,-129,-7,-5,-3,-1,0,1,3,5,7,129,(1<<54)+7]:
            for shift in [-3,0,1,2,7,15,31,62]:
                self.assertEqual(int(rne(np.array([x]),shift)[0]),round(Fraction(x)*Fraction(2)**-shift))
        with self.assertRaises(OverflowError):rne(np.array([1<<62]),-2)
        with self.assertRaises(OverflowError):rne(np.array([-(1<<63)]),1)

    def test_full_fraction_step_every_value_and_format(self):
        rng=np.random.default_rng(266)
        for bits in (16,32):
            for df in (15,31):
                initial=rng.integers(-1000,1001,(2,4,3),dtype=np.int64)
                q=rng.integers(-15000,15001,(2,4),dtype=np.int64);k=rng.integers(-16000,16001,(2,4),dtype=np.int64)
                v=rng.integers(-2000,2001,(2,3),dtype=np.int64);d=np.array([1<<df,(1<<df)-17],dtype=np.int64);b=np.array([32768,11111])
                su=np.array([-10,-11])-(16 if bits==32 else 0);vu=np.array([-10,-11])
                got,y,stats=step(initial,q,k,v,d,b,su,vu,bits,df)
                wanted,out=fraction_step(initial,q,k,v,d,b,su,vu,bits,df)
                self.assertTrue(np.array_equal(got,wanted));self.assertTrue(np.array_equal(y,out))
                self.assertIn('prediction_dot',stats['observed_signed_bits'])

    def test_exact_one_U32_decay_never_signed_overflows(self):
        s=np.array([[[1<<30,-(1<<30)]]],dtype=np.int64)
        new,out,stats=step(s,np.zeros((1,1)),np.zeros((1,1)),np.zeros((1,2)),np.array([1<<31],dtype=np.uint32),np.array([0]),np.array([-20]),np.array([-10]),32,31)
        self.assertTrue(np.array_equal(new,s));self.assertEqual(stats['saturations'],0)
        self.assertGreaterEqual(stats['observed_signed_bits']['decay_product'],62)

    def test_same_physical_state_endpoints_and_scale_compiler(self):
        lo16,hi16=state_bounds(16);lo32,hi32=state_bounds(32)
        self.assertEqual(lo16,lo32/65536);self.assertEqual(hi16,hi32/65536)
        unit=head_units(np.ones((2,4,3))*.1,32767,0)
        self.assertEqual(unit.shape,(2,));self.assertTrue(np.all(unit>=-26))
        a,clips=bridge_codes(np.array([1.0]),-15,0,32768)
        self.assertEqual(int(a[0]),32768);self.assertEqual(clips,0)

    def test_prediction_cannot_round_partial_K_early(self):
        products=[16384,16384]
        full=round(Fraction(sum(products),32768));early=sum(round(Fraction(v,32768)) for v in products)
        self.assertEqual(full,1);self.assertEqual(early,0)
        s=np.ones((1,2,1),dtype=np.int64);q=np.zeros((1,2),dtype=np.int64);k=np.array([[16384,16384]])
        new,_,_=step(s,q,k,np.array([[0]]),np.array([32768]),np.array([32768]),np.array([0]),np.array([0]),16)
        # Full prediction=1; delta=-1; each update=-0.5 rounds to0.
        self.assertTrue(np.array_equal(new,s))

    def test_K_tiles_must_share_original_prediction_and_new_state_output(self):
        s=np.zeros((1,4,1),dtype=np.int64);k=np.full((1,4),16384,dtype=np.int64);q=k.copy()
        new,out,_=step(s,q,k,np.array([[16384]]),np.array([32768]),np.array([32768]),np.array([-15]),np.array([-14]),16)
        self.assertTrue(np.array_equal(new,np.full_like(s,16384)))
        self.assertEqual(int(out[0,0]),32768) # Reading old state would give0.
        # Wrong serial K partitions recompute prediction after the first writes.
        wrong=np.array([.5,.5,.25,.25]);self.assertFalse(np.array_equal(new[0,:,0]/32768,wrong))

    def test_near_one_decay_format_has_length_sensitive_loss(self):
        true=1-2.**-17
        d15,_=bridge_codes(np.array([true]),-15,0,1<<15);d31,_=bridge_codes(np.array([true]),-31,0,1<<31)
        self.assertEqual(int(d15[0]),1<<15);self.assertLess(int(d31[0]),1<<31)
        self.assertGreater(abs(1-true**8192),abs(1-true**32))
        initial=np.array([[[1<<24]]],dtype=np.int64)
        encoded={'q':np.full((256,1,1),32767),'k':np.zeros((256,1,1),dtype=np.int64),'v':np.zeros((256,1,1),dtype=np.int64),'beta':np.zeros((256,1),dtype=np.int64)}
        traces=[]
        for df,d in [(15,d15),(31,d31)]:
            e={**encoded,'decay':np.full((256,1),int(d[0]))}
            _,s,_=run_integer(e,initial,np.array([-24]),np.array([-10]),32,{'decay_fraction':df},0,32)
            traces.append(s)
        self.assertEqual(int(traces[0][-1,0,0,0]),1<<24)
        self.assertLess(int(traces[1][-1,0,0,0]),int(traces[1][32,0,0,0]))

    def test_commit_rejects_stale_foreign_epoch_position_and_mutation(self):
        lease=StateLease(np.ones((1,2,2),dtype=np.int64),{'sequence':'a','epoch':0,'unit':[-15]},128)
        for version,pos,contract in [(1,128,lease.contract),(0,129,lease.contract),(0,128,'foreign')]:
            with self.assertRaises(ValueError):lease.propose(lease.state,np.zeros((1,2)),version,pos,contract)
        p=lease.propose(lease.state+1,np.zeros((1,2)),0,128,lease.contract)
        bad=copy.deepcopy(p);bad['new'][0,0,0]+=1
        with self.assertRaises(ValueError):lease.commit(bad)
        bad=copy.deepcopy(p);bad['out'][0,0]+=1
        with self.assertRaises(ValueError):lease.commit(bad)
        lease.commit(p)
        with self.assertRaises(ValueError):lease.commit(p)

    def test_chunks_preserve_exact_state_and_version(self):
        rng=np.random.default_rng(901)
        encoded={'q':rng.integers(-3000,3001,(17,2,4)), 'k':rng.integers(-3000,3001,(17,2,4)),
            'v':rng.integers(-100,101,(17,2,3)),'beta':np.full((17,2),16384),'decay':np.full((17,2),1<<31)}
        initial=np.ones((2,4,3),dtype=np.int64);su=np.array([-14,-14]);vu=np.array([-10,-10]);d={'decay_fraction':31,'epoch':0}
        a,s,m=run_integer(encoded,initial,su,vu,16,d,128,32)
        b,t,n=run_integer(encoded,initial,su,vu,16,d,128,8)
        self.assertTrue(np.array_equal(a,b));self.assertTrue(np.array_equal(s,t));self.assertEqual(m,n)

    def test_width_guards_and_inventory_are_explicit(self):
        p=format_bounds(128,32,-28,-10,31)
        self.assertGreaterEqual(p['signed_bits']['prediction_dot'],54)
        with self.assertRaises(OverflowError):format_bounds(128,32,-60,0,31)
        c=cost(2,128,128,32,32,31)
        self.assertEqual(c['stored_state_bytes'],131072)
        self.assertGreater(c['alternative_state_schedules']['recompute_decay']['minimum_old_new_payload_for_atomic_rollback_bytes'],32768)

    def test_calibration_evaluation_saved_contract_and_refuse_overwrite(self):
        task=Path('D:/Projects/Codex/issue66-scale-state-20261024/state');task.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='state-test-',dir=task) as td:
            root=Path(td);rng=np.random.default_rng(26666);arrays={}
            for name in ('calibration','evaluation'):
                p={k:rng.normal(0,.1,(1,4,2,4)).astype(np.float32) for k in ('query','key','value')}
                p['initial_state']=rng.normal(0,.01,(1,2,4,4)).astype(np.float32)
                p['g']=np.full((1,4,2),-.01,dtype=np.float32);p['beta']=np.full((1,4,2),.5,dtype=np.float32)
                out,states,final,_=float_reference(p)
                p['output']=out[None].astype(np.float32);p['final_state']=final[None].astype(np.float32)
                for k,v in p.items():arrays[name+'.'+k]=v
                arrays[name+'.state_boundaries']=states[:,None].astype(np.float32)
            save_npz(root/'state-raw.npz',arrays)
            save(root/'manifest.json',{'status':'PASS','state':{'use_qk_l2norm':True,'checks':[{'case':n,'start_position':128} for n in ('calibration','evaluation')]},
                'artifacts':{'state-raw.npz':{'bytes':(root/'state-raw.npz').stat().st_size,'sha256':sha(root/'state-raw.npz')}}})
            execute(root,root/'results')
            m=json.loads((root/'results/manifest.json').read_text());self.assertEqual(m['status'],'PASS');self.assertEqual(m['integer_conditions'],8)
            r=json.loads((root/'results/state-results.json').read_text());self.assertEqual(sum(x['role']=='independent evaluation' for x in r),4)
            with np.load(root/'results/evaluation.S32.D31.npz',allow_pickle=False) as z:
                self.assertEqual(z['decay'].dtype,np.uint32);self.assertEqual(z['state_trace'].dtype,np.int32);self.assertEqual(z['state_trace'].shape,(5,2,4,4))
            with self.assertRaises(ValueError):execute(root,root/'results')
            execute(root,root/'limit256',steps=256)
            long_records=json.loads((root/'limit256/state-results.json').read_text())
            self.assertTrue(all(x['requested_step_limit']==256 and x['integer_steps']==4 for x in long_records))
            conv=root/'conv';conv.mkdir();carrays={}
            for variant,factor in [('conv8',.99),('conv16',1.001)]:
                for name in ('calibration','evaluation'):
                    for field in ('query','key','value'):carrays[variant+'.'+name+'.'+field]=arrays[name+'.'+field]*factor
            save_npz(conv/'conv-output.npz',carrays)
            save(conv/'manifest.json',{'status':'PASS','capture_manifest_sha256':sha(root/'manifest.json'),
                'artifacts':{'conv-output.npz':{'bytes':(conv/'conv-output.npz').stat().st_size,'sha256':sha(conv/'conv-output.npz')}}})
            execute(root,root/'coupled',conv=conv,only_coupled=True)
            records=json.loads((root/'coupled/state-results.json').read_text());self.assertEqual(len(records),2)
            for row in records:
                with np.load(root/'coupled'/row['artifact']['name'],allow_pickle=False) as z,np.load(root/'results/evaluation.S32.D31.npz',allow_pickle=False) as original:
                    self.assertTrue(np.array_equal(z['state_units'],original['state_units']))
                    self.assertTrue(np.array_equal(z['value_units'],original['value_units']))
                    self.assertIn('FP64_coupled_input_output_reference',z.files)
                self.assertEqual(row['format']['decay_fraction'],31)
                self.assertIn(row['format']['input_variant'],('conv8','conv16'))


if __name__=='__main__':unittest.main()
