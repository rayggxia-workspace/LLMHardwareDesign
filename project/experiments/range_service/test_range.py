"""Small independent Fraction arithmetic and transactional range boundaries."""
import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

_spec=importlib.util.spec_from_file_location('range_candidate',Path(__file__).with_name('range.py'))
r=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(r)


def fraction_proposal(state,q,k,v,d,b,su,vu,bits,df):
    h,dim,width=state.shape;lo,hi=r.old.state_bounds(bits);p=np.empty(state.shape,dtype=np.int64)
    for a in range(h):
        dec=[[round(Fraction(int(state[a,i,j])*int(d[a]),1<<df)) for j in range(width)] for i in range(dim)]
        pred=[round(Fraction(sum(dec[i][j]*int(k[a,i]) for i in range(dim)),32768)) for j in range(width)]
        delta=[round(Fraction((round(Fraction(int(v[a,j]))*Fraction(2)**(int(vu[a])-int(su[a])))-pred[j])*int(b[a]),32768)) for j in range(width)]
        for i in range(dim):
            for j in range(width):p[a,i,j]=dec[i][j]+round(Fraction(int(k[a,i])*delta[j],32768))
    counts=np.count_nonzero((p<lo)|(p>hi),axis=(1,2));new=np.clip(p,lo,hi)
    y=np.empty((h,width),dtype=np.int64)
    for a in range(h):
        for j in range(width):y[a,j]=round(Fraction(sum(int(new[a,i,j])*int(q[a,i]) for i in range(dim)),32768))
    return p,new,y,counts


def operands(t=1,h=1,dim=1,width=1,vu=0):
    encoded={'q':np.full((t,h,dim),32767,dtype=np.int16),'k':np.full((t,h,dim),32767,dtype=np.int16),
             'v':np.full((t,h,width),32767,dtype=np.int16),'beta':np.full((t,h),32768,dtype=np.uint16),
             'decay':np.full((t,h),32768,dtype=np.uint16)}
    return encoded,np.zeros((h,dim,width),dtype=np.int64),np.zeros(h,dtype=np.int16),np.full(h,vu,dtype=np.int16)


class CausalRange(unittest.TestCase):
    def test_rne_ties_double_rounding_is_sequential(self):
        for n in [-17,-7,-5,-3,-1,0,1,3,5,7,17]:
            for s in [0,1,2,15,31,62]:self.assertEqual(int(r.old.rne(np.array([n]),s)[0]),round(Fraction(n,1<<s)))
        x=np.array([5]);seq=x
        for _ in range(3):seq=r.old.rne(seq,1)
        self.assertEqual(int(seq[0]),0);self.assertEqual(int(r.old.rne(x,3)[0]),1)

    def test_fraction_all_cells_stages_four_formats(self):
        rng=np.random.default_rng(6801)
        for bits in (16,32):
            for df in (15,31):
                s=rng.integers(-100,101,(2,4,3));q=rng.integers(-30000,30001,(2,4));k=rng.integers(-30000,30001,(2,4));v=rng.integers(-10000,10001,(2,3))
                d=np.array([(1<<df)-3,1<<df]);b=np.array([17001,32768]);su=np.array([-14,-15])-(16 if bits==32 else 0);vu=np.array([-12,-13])
                p,new,y,c=fraction_proposal(s,q,k,v,d,b,su,vu,bits,df)
                got,out,stats=r.proposal(s,q,k,v,d,b,su,vu,bits,df,True)
                np.testing.assert_array_equal(got,new);np.testing.assert_array_equal(out,y)
                self.assertEqual(stats['guard_count_by_head'],c.tolist());self.assertEqual(stats['proposed_state_sha256'],r.old.digest_array(p))

    def test_static_sat_exact_original_but_guard_aborts_before_output(self):
        e,s,su,vu=operands(vu=2)
        sat,ss=r.run(e,s,su,vu,16,15,'static_sat')
        y,states,orig=r.old.run_integer(e,s,su,vu,16,{'decay_fraction':15},0)
        np.testing.assert_array_equal(sat['state_trace'],states);np.testing.assert_array_equal(sat['output_codes'],y)
        self.assertEqual(ss['saturations_published'],orig['saturations']);self.assertGreater(ss['saturations_published'],0)
        guarded,gs=r.run(e,s,su,vu,16,15,'static_guard')
        self.assertEqual(gs['status'],'REJECTED_GUARD');self.assertEqual(gs['committed_tokens'],0)
        self.assertFalse(gs['tokens'][0]['attempts'][0]['output_work_performed'])
        np.testing.assert_array_equal(guarded['state_trace'][0],s);self.assertEqual(gs['tokens'][0]['before'],gs['tokens'][0]['after'])

    def test_two_retries_commit_new_scale_epoch_and_output_together(self):
        e,s,su,vu=operands(vu=2);a,m=r.run(e,s,su,vu,16,15,'guard_rescale')
        self.assertEqual(m['committed_tokens'],1);self.assertEqual(len(m['rescale_events']),2)
        np.testing.assert_array_equal(a['state_units_trace'],[[0],[2]]);self.assertEqual(a['epoch_trace'].tolist(),[0,2])
        self.assertEqual(m['tokens'][0]['commit']['new']['version'],1)
        trial=s.copy();unit=su.copy()
        for _ in range(2):trial=r.old.rne(trial,1);unit+=1
        _,wanted,out,c=fraction_proposal(trial,e['q'][0],e['k'][0],e['v'][0],e['decay'][0],e['beta'][0],unit,vu,16,15)
        np.testing.assert_array_equal(a['state_trace'][1],wanted);np.testing.assert_array_equal(a['output_codes'][0],out);self.assertEqual(int(c.sum()),0)

    def test_only_bad_head_reencoded_epoch_once_per_wave(self):
        e,s,su,vu=operands(h=2,vu=2);e['v'][:,1]=0
        a,m=r.run(e,s,su,vu,16,15,'guard_rescale')
        self.assertEqual([x['heads'] for x in m['rescale_events']],[[0],[0]])
        self.assertEqual(a['state_units_trace'][-1].tolist(),[2,0]);self.assertEqual(a['epoch_trace'][-1],2)
        self.assertEqual(m['cost']['rescale_RNE_elements'],2)

    def test_sequential_trial_recode_hashes_not_native_or_single_shift(self):
        e,s,su,vu=operands(width=2,vu=3);e['v'][0,0,1]=0;s[0,0,1]=5
        a,m=r.run(e,s,su,vu,16,15,'guard_rescale');self.assertEqual(len(m['rescale_events']),3)
        trial=s.copy()
        for event in m['rescale_events']:
            self.assertEqual(event['old_trial_state_sha256'],r.old.digest_array(trial))
            trial=r.old.rne(trial,1);self.assertEqual(event['recoded_trial_state_sha256'],r.old.digest_array(trial))
        self.assertEqual(trial[0,0,1],0);self.assertEqual(r.old.rne(s,3)[0,0,1],1)

    def test_max_retries_reject_preserves_published_units_epoch_position(self):
        e,s,su,vu=operands(vu=20);a,m=r.run(e,s,su,vu,16,15,'guard_rescale',position=8192,sequence='actual-window')
        self.assertEqual(len(m['tokens'][0]['attempts']),9);self.assertEqual(len(m['rescale_events']),8)
        self.assertEqual(m['committed_tokens'],0);self.assertEqual(m['final']['position'],8192);self.assertEqual(m['final']['epoch'],0)
        self.assertEqual(m['final']['units'],[0]);np.testing.assert_array_equal(a['state_trace'][0],s)

    def test_exponent_domain_reject_and_checked_wide_guard(self):
        e,s,su,vu=operands(vu=127);su[:]=127
        # A unit delta of2 would exceed I8 before any rescale can publish.
        e['v'][:]=32767;s[:]=32767;e['k'][:]=16384
        a,m=r.run(e,s,su,vu,16,15,'guard_rescale')
        self.assertEqual(m['committed_tokens'],0);self.assertIn('domain',m['rejection']['reason']);self.assertEqual(m['final']['epoch'],0)
        e,s,su,vu=operands(vu=0);su[:]=-100
        a,m=r.run(e,s,su,vu,16,15,'guard_rescale')
        self.assertEqual(m['committed_tokens'],0);self.assertTrue(all(x['outcome']=='ABORT_WIDTH' for x in m['tokens'][0]['attempts']))

    def test_transaction_rejects_epoch_units_state_output_foreign_partial(self):
        lease=r.RangeLease(np.ones((1,2,2),dtype=np.int64),np.array([-15]),128,'a');snap=lease.snapshot()
        p=lease.prepare(lease.state+1,np.zeros((1,2),dtype=np.int64),lease.units,0,snap)
        for field in ('new','output','units','epoch'):
            bad=copy.deepcopy(p)
            if field=='epoch':bad[field]+=1
            else:bad[field].flat[0]+=1
            with self.assertRaises(ValueError):lease.commit(bad)
        foreign=copy.deepcopy(snap);foreign['sequence']='b'
        with self.assertRaises(ValueError):lease.prepare(lease.state,np.zeros((1,2)),lease.units,0,foreign)
        with self.assertRaises(ValueError):lease.prepare(lease.state[:,:,:1],np.zeros((1,1)),lease.units,0,snap)
        lease.commit(p)
        with self.assertRaises(ValueError):lease.commit(p)

    def test_endpoint_sign_full_K_and_new_state_output(self):
        lo16,hi16=r.old.state_bounds(16);lo32,hi32=r.old.state_bounds(32)
        self.assertEqual(lo16,lo32/65536);self.assertEqual(hi16,hi32/65536)
        # Complete K sum gives1 while independently rounded halves give0.
        s=np.ones((1,2,1),dtype=np.int64);q=np.full((1,2),16384);k=q.copy();v=np.zeros((1,1),dtype=np.int64)
        new,out,m=r.proposal(s,q,k,v,np.array([32768]),np.array([32768]),np.array([0]),np.array([0]),16,15)
        self.assertEqual(int(out[0,0]),1);np.testing.assert_array_equal(new,s)

    def test_manifest_hash_receiver_and_no_output_overwrite(self):
        temp=Path('D:/Projects/Codex/range-service-20261024-1238/range');temp.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp,prefix='boundary-') as td:
            p=Path(td);r.old.save_npz(p/'x.npz',{'state_initial':np.zeros((1,1,1))})
            desc={'name':'x.npz','bytes':(p/'x.npz').stat().st_size,'sha256':r.old.sha(p/'x.npz')}
            r.old.save(p/'state-results.json',[{'artifact':desc}]);artifacts={'x.npz':{k:desc[k] for k in ('bytes','sha256')},'state-results.json':{'bytes':(p/'state-results.json').stat().st_size,'sha256':r.old.sha(p/'state-results.json')}}
            r.old.save(p/'manifest.json',{'status':'PASS','artifacts':artifacts});self.assertEqual(len(r.receive(p)[1]),1)
            with (p/'x.npz').open('ab') as f:f.write(b'bad')
            with self.assertRaises(ValueError):r.receive(p)
            with self.assertRaises(ValueError):r.execute(p,p,p)

    def test_checkpoint_resume_preserves_nonzero_epoch_version_and_format(self):
        e,s,su,vu=operands(t=17,width=2,vu=3);e['v'][:,:,1]=0;s[0,0,1]=5
        full,stats=r.run(e,s,su,vu,16,15,'guard_rescale',128,'resume-sequence')
        cut=8;first={k:v[:cut] for k,v in e.items()};second={k:v[cut:] for k,v in e.items()}
        a,m=r.run(first,s,su,vu,16,15,'guard_rescale',128,'resume-sequence')
        cp=r.checkpoint(m['final'],r.resume_contract(16,15,vu,'guard_rescale'))
        b,n=r.run(second,a['state_trace'][-1],a['state_units_trace'][-1],vu,16,15,'guard_rescale',136,'resume-sequence',cp)
        self.assertGreater(int(a['epoch_trace'][-1]),0);self.assertEqual(n['final'],stats['final'])
        for key in ('state_trace','state_units_trace','epoch_trace'):
            np.testing.assert_array_equal(np.concatenate([a[key],b[key][1:]]),full[key])
        for key in ('output_codes','output_units'):np.testing.assert_array_equal(np.concatenate([a[key],b[key]]),full[key])
        for field in ('epoch','units','position'):
            bad=copy.deepcopy(cp)
            if field=='units':bad['snapshot'][field][0]+=1
            else:bad['snapshot'][field]+=1
            with self.assertRaises(ValueError):r.run(second,a['state_trace'][-1],a['state_units_trace'][-1],vu,16,15,'guard_rescale',136,'resume-sequence',bad)
        # A valid checksum cannot excuse changed payload/position/sequence/format.
        for changed in ('position','sequence','state','units','value_units','bits','policy'):
            state=a['state_trace'][-1].copy();units=a['state_units_trace'][-1].copy();vunits=vu.copy();position=136;sequence='resume-sequence';bits=16;policy='guard_rescale'
            if changed=='position':position+=1
            if changed=='sequence':sequence='foreign'
            if changed=='state':state.flat[0]+=1
            if changed=='units':units[0]+=1
            if changed=='value_units':vunits[0]+=1
            if changed=='bits':bits=32
            if changed=='policy':policy='static_sat'
            with self.assertRaises(ValueError):r.run(second,state,units,vunits,bits,15,policy,position,sequence,cp)

    def test_chunk_checker_compares_actual_rescale_and_all_commits(self):
        cs=importlib.util.spec_from_file_location('chunk_test',Path(__file__).with_name('chunk_check.py'))
        checker=importlib.util.module_from_spec(cs);cs.loader.exec_module(checker)
        e,s,su,vu=operands(t=17,width=2,vu=3);e['decay']=np.full((17,1),1<<31,dtype=np.uint32);e['v'][:,:,1]=0;s[0,0,1]=5
        full,trace=r.run(e,s,su,vu,16,31,'guard_rescale',128,'synthetic')
        for boundaries in ([8,16],[16],[1]):
            report=checker.compare_chunks(e,s,su,vu,16,31,128,'synthetic',full,trace,boundaries)
            self.assertTrue(report['complete_bitexact']);self.assertTrue(report['transaction_events_bitexact'])
        negatives=checker.negative_checks(e,s,su,vu,16,31,128,'synthetic',full)
        self.assertEqual(len(negatives),6);self.assertTrue(all(x['rejected'] for x in negatives))


if __name__=='__main__':unittest.main()
