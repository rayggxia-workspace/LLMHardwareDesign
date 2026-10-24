import copy, math, unittest
from fractions import Fraction
import numpy as np
import falcon_int as f

class IntegerBoundary(unittest.TestCase):
    def test_signed_rne_ties(self):
        a=np.array([-7,-5,-3,-1,1,3,5,7],np.int64)
        self.assertEqual(f.rshift(a,1).tolist(),[-4,-2,-2,0,0,2,2,4])
        self.assertEqual([f.rdiv(x,2) for x in a],[-4,-2,-2,0,0,2,2,4])
    def test_integer_boundaries(self):
        with self.assertRaises(TypeError):f.require_int(np.array([1.]))
        with self.assertRaises(OverflowError):f.require_int(np.array([1<<63],np.uint64))
        with self.assertRaises(OverflowError):f.rshift(np.array([-(1<<63)],np.int64),1)
        with self.assertRaises(OverflowError):f.checked_mul(np.array([1<<40]),np.array([1<<30]))
        with self.assertRaises(OverflowError):f.cast_i32(np.array([1<<31]))
        with self.assertRaises(OverflowError):f.checked_mul(np.array([1<<31]),np.array([1]))
        self.assertEqual(int(f.checked_mul(np.array([1]),np.array([1<<31]),b_unsigned=True)[0]),1<<31)
        self.assertEqual(f.rshift(np.array([-7,7]),100).tolist(),[0,0])
    def test_full_k_linear_dynamic_integer_scales(self):
        x=np.array([[4096,-8192,12288],[0,0,0]],np.int32);w=np.array([[127,127,-127],[-127,0,127]],np.int8)
        y,a,d,acc=f.linear(x,w,np.array([1<<30,1<<30],np.int32),np.array([-6,-6],np.int16),f.Ops())
        self.assertEqual(d.tolist(),[7,0]);self.assertEqual(a[0].tolist(),[32,-64,96])
        self.assertEqual(acc[0].tolist(),[-16256,8128]);self.assertEqual(y[0].tolist(),[-16256,8128])
    def test_rmsnorm_complete_group_integer(self):
        x=np.array([[3<<12,4<<12]],np.int32);gamma=np.array([1<<20,1<<20],np.int32);ops=f.Ops()
        y=f.rmsnorm(x,gamma,0,ops)
        den=math.isqrt(((sum(int(a)*int(a) for a in x[0])//2)<<40))
        expected=[f.rdiv((int(a)*(1<<20))<<12,den) for a in x[0]]
        self.assertEqual(y.tolist(),[expected]);self.assertEqual(ops.values['isqrt_restoring_iterations'],64)
        with self.assertRaises(ValueError):f.rmsnorm(x,np.array([1<<20]),0,f.Ops())
    def test_lut_endpoint_policy(self):
        lut=np.arange(16385,dtype=np.int32);counts={};x=np.array([-(33<<12),-(32<<12),0,32<<12,33<<12],np.int32)
        actual=f.silu(x,lut,f.Ops(),counts)
        self.assertEqual(actual.tolist(),[0,0,8192,16384,33<<12]);self.assertEqual(counts['silu_positive_identity'],1)
    def test_lowering_not_free_unsigned_byte_digits(self):
        ops=f.Ops();ops.mul(2,32,32)
        self.assertEqual(ops.values['s8_signed_high_radix128_products'],50)
        self.assertEqual(ops.values['wide_digit_shift_add'],48)
        native=f.Ops();native.mul(1,8,8);self.assertEqual(native.values['s8_signed_high_radix128_products'],1)
    def make_coeff(self,t=3):
        return {'x_q12':np.full((t,2,2),50000<<12,np.int32),'b_q12':np.full((t,3),1<<12,np.int32),'c_q12':np.zeros((t,3),np.int32),'dt_q20':np.full((t,2),1<<20,np.int32),'alpha_q31':np.full((t,2),1<<31,np.uint32)}
    def test_static_guard_no_partial_publication(self):
        r=f.scan(self.make_coeff(),np.zeros(2,np.int16),np.zeros(2,np.int32),16,'static_guard',f.Ops())
        self.assertEqual(r['committed'],0);self.assertEqual(r['transactions'][0]['before'],r['transactions'][0]['after']);self.assertEqual(r['saturations'],0)
    def test_static_sat_retains_failure(self):
        r=f.scan(self.make_coeff(),np.zeros(2,np.int16),np.zeros(2,np.int32),16,'static_sat',f.Ops())
        self.assertEqual(r['committed'],3);self.assertEqual(r['saturations'],36);self.assertEqual(r['epoch'],0)
    def test_causal_rescale_whole_token_and_chunk(self):
        c=self.make_coeff(4);a=f.scan(c,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),chunk=1)
        b=f.scan(c,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),chunk=2)
        self.assertEqual(a['committed'],4);self.assertEqual(a['saturations'],0);self.assertTrue(a['rescale_events']);self.assertEqual(a['state_sha256'],b['state_sha256']);np.testing.assert_array_equal(a['units_trace'],b['units_trace'])
        prefix={k:v[:2].copy() for k,v in c.items()};r=f.scan(prefix,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops())
        self.assertEqual(a['state_sha256'][:3],r['state_sha256']);np.testing.assert_array_equal(a['units_trace'][:3],r['units_trace'])
    def test_retry_limit_rollback(self):
        r=f.scan(self.make_coeff(),np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),max_retry=0)
        self.assertEqual(r['committed'],0);self.assertEqual(r['rejection']['reason'],'retry_limit');self.assertEqual(r['epoch'],0)
    def test_readout_failure_atomic(self):
        c=self.make_coeff(1);c['x_q12'][:]=1<<12;c['c_q12'][:]=(1<<31)-1
        r=f.scan(c,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops())
        self.assertEqual(r['committed'],0);self.assertEqual(r['rejection']['reason'],'readout_wide_guard');self.assertEqual(r['transactions'][0]['before'],r['transactions'][0]['after'])
    def test_checkpoint_tampering_rejected(self):
        state=np.zeros((2,2,3),np.int16);units=np.zeros(2,np.int16);contract={'bits':16};desc=f.checkpoint(state,units,3,4,contract)
        f.validate_checkpoint(desc,state,units,3,4,contract)
        for k,v in [('epoch',2),('position',3),('version',9),('units',[1,0])]:
            bad=copy.deepcopy(desc);bad[k]=v
            with self.assertRaises(ValueError):f.validate_checkpoint(bad,state,units,3,4,contract)
        changed=state.copy();changed[0,0,0]=1
        with self.assertRaises(ValueError):f.validate_checkpoint(desc,changed,units,3,4,contract)
    def test_two_stage_injection_is_explicit(self):
        old=np.zeros((1,1,1),np.int64);u=np.array([0]);alpha=np.array([0]);dt=np.array([3]);x=np.array([[1<<31-1]]);b=np.array([1<<11])
        actual,stages=f.proposal(old,u,alpha,dt,x,b,f.Ops())
        dtb=f.rdiv(3*(1<<11),1<<12);expected=f.rdiv(dtb*int(x[0,0]),1<<32)
        self.assertEqual(int(actual[0,0,0]),expected);self.assertIn('dtb_q20_sha256',stages)
    def test_actual_state_resume_matches_unbroken(self):
        c=self.make_coeff(5);full=f.scan(c,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),chunk=0)
        first={k:v[:2] for k,v in c.items()};rest={k:v[2:] for k,v in c.items()}
        r1=f.scan(first,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),chunk=0)
        descriptor=r1['transactions'][-1]['after']
        resumed={'state':r1['final_state'],'units':r1['units_trace'][-1],'epoch':r1['epoch'],'position':2,'checkpoint':descriptor}
        r2=f.scan(rest,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),chunk=0,resume=resumed)
        self.assertEqual(full['state_sha256'],r1['state_sha256']+r2['state_sha256'][1:]);np.testing.assert_array_equal(full['final_state'],r2['final_state']);self.assertEqual(r2['final_position'],5)
        bad=dict(resumed);bad['position']=3
        with self.assertRaises(ValueError):f.scan(rest,np.zeros(2,np.int16),np.zeros(2,np.int32),16,'guard_rescale',f.Ops(),resume=bad)
    def test_complete_conv_history_continuous(self):
        spec={'inner':4,'heads':2,'state_size':3,'head_dim':2};channels=10
        const={'conv_weight_q20':np.full((channels,4),1<<18,np.int32),'conv_bias_q12':np.zeros(channels,np.int32),'silu_lut_q12':np.arange(16385,dtype=np.int32),'dt_bias_q12':np.zeros(2,np.int32),'dt_lut_q20':np.full((2,16385),1<<20,np.int32),'alpha_lut_q31':np.full((2,16385),1<<30,np.uint32)}
        p=np.arange(5*16,dtype=np.int32).reshape(5,16)*128
        full=f.coefficients(p,const,spec,f.Ops());a=f.coefficients(p[:2],const,spec,f.Ops());b=f.coefficients(p[2:],const,spec,f.Ops(),initial_history=a['conv_history_final_q12'])
        np.testing.assert_array_equal(full['conv_q12'],np.concatenate([a['conv_q12'],b['conv_q12']]));np.testing.assert_array_equal(full['conv_history_final_q12'],b['conv_history_final_q12'])
        reset=f.coefficients(p[2:],const,spec,f.Ops());self.assertFalse(np.array_equal(reset['conv_q12'],b['conv_q12']))
    def test_full_checkpoint_checks_state_and_conv_together(self):
        import falcon_resume as resume
        state=np.zeros((2,2,3),np.int16);units=np.zeros(2,np.int16);history=np.zeros((10,4),np.int32);contract={'bits':16,'heads':2,'dim':2,'n':3,'compiled_manifest_sha256':'fixture'}
        d=resume.complete_checkpoint(state,units,history,2,4,contract)
        restored=resume.restore(d,state,units,history,4,contract);self.assertEqual(restored[-1],2)
        negative=resume.corrupted_checkpoint_negatives(d,state,units,history,4,contract);self.assertEqual(len(negative),8);self.assertTrue(all(x['rejected'] for x in negative))
    def test_consumer_failure_keeps_conv_and_state_atomic_then_recovers(self):
        import falcon_resume as resume
        spec={'inner':4,'heads':2,'state_size':3,'head_dim':2};channels=10
        wc=np.zeros((channels,4),np.int32);wc[:,-1]=1<<20
        const={'conv_weight_q20':wc,'conv_bias_q12':np.zeros(channels,np.int32),'silu_lut_q12':np.arange(16385,dtype=np.int32),'dt_bias_q12':np.zeros(2,np.int32),'dt_lut_q20':np.full((2,16385),1<<20,np.int32),'alpha_lut_q31':np.full((2,16385),1<<30,np.uint32),'skip_q20':np.zeros(2,np.int32)}
        contract={'bits':16,'heads':2,'dim':2,'n':3,'compiled_manifest_sha256':'tiny','policy':'guard_rescale'}
        state=np.zeros((2,2,3),np.int16);units=np.zeros(2,np.int16);history=np.zeros((channels,4),np.int32)
        def project(x,c,s,o):
            p=np.full((1,16),(4<<12)+int(x[0,0]),np.int32);return p,{'projected_q12':p}
        def consumer_ok(*args):return {'next_norm_q12':np.array([[1,2]],np.int32)}
        def consumer_bad(*args):raise OverflowError('injected final nextnorm guard')
        first=resume.complete_token(state,units,history,0,0,np.array([[0,0]],np.int32),np.zeros((1,2),np.int32),const,spec,16,'guard_rescale',contract,project_fn=project,consumer_fn=consumer_ok)
        self.assertIsNone(first['rejection']);self.assertTrue(first['tx']['branch_published']);self.assertTrue(np.any(first['history']))
        args=(first['state'],first['units'],first['history'],first['epoch'],first['position'],np.array([[1,0]],np.int32),np.zeros((1,2),np.int32),const,spec,16,'guard_rescale',contract)
        saved=[a.copy() for a in args[:3]];failed=resume.complete_token(*args,project_fn=project,consumer_fn=consumer_bad)
        self.assertEqual(failed['rejection']['reason'],'consumer_guard');self.assertEqual(failed['tx']['after'],failed['tx']['before']);self.assertFalse(failed['tx']['branch_published'])
        self.assertTrue(failed['tx']['private_R_transactions'][0]['committed'])
        for original,old in zip(args[:3],saved):np.testing.assert_array_equal(original,old)
        recovered=resume.complete_token(*args,project_fn=project,consumer_fn=consumer_ok);baseline=resume.complete_token(*args,project_fn=project,consumer_fn=consumer_ok)
        for k in ('state','units','history'):np.testing.assert_array_equal(recovered[k],baseline[k])
        self.assertEqual(recovered['tx']['after'],baseline['tx']['after']);self.assertEqual(recovered['position'],2)
if __name__=='__main__':unittest.main()


