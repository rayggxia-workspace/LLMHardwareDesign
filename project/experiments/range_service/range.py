"""Causal integer R range guard/rescale experiments; no whole-model acceptance.

Consumes Issue66 already encoded NPZs. A range retry cannot observe floating
references or future tokens. All trial state/units/epochs remain unpublished
until a successful complete-token state/output commit. Software copies are
evidence, never free hardware shadow SRAM.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import time

import numpy as np

OLD_PATH=Path(__file__).resolve().parents[1]/'scale_state'/'state.py'
_spec=importlib.util.spec_from_file_location('issue66_frozen_state',OLD_PATH)
old=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(old)
POLICIES=('static_sat','static_guard','guard_rescale')
MAX_RETRIES=8


def checked_input(s,q,k,v,d,b,su,vu,bits,df):
    s=np.asarray(s,dtype=np.int64);q=np.asarray(q,dtype=np.int64);k=np.asarray(k,dtype=np.int64)
    v=np.asarray(v,dtype=np.int64);d=np.asarray(d,dtype=np.int64);b=np.asarray(b,dtype=np.int64)
    h,dim,width=s.shape;lo,hi=old.state_bounds(bits)
    if q.shape!=(h,dim) or k.shape!=q.shape or v.shape!=(h,width) or d.shape!=(h,) or b.shape!=(h,):raise ValueError('recurrence shapes')
    if np.asarray(su).shape!=(h,) or np.asarray(vu).shape!=(h,):raise ValueError('unit head shape')
    if np.any(np.abs(q)>32767) or np.any(np.abs(k)>32767) or np.any(np.abs(v)>32767):raise ValueError('S16 symmetric operand')
    if df not in (15,31) or np.any((d<0)|(d>(1<<df))|(b<0)|(b>32768)):raise ValueError('gate code domain')
    if np.any((s<lo)|(s>hi)):raise ValueError('stored state domain')
    if np.any((np.asarray(su)<-128)|(np.asarray(su)>127)) or np.any((np.asarray(vu)<-128)|(np.asarray(vu)>127)):raise ValueError('I8 exponent')
    for a in range(h):old.format_bounds(dim,bits,su[a],vu[a],df)
    return s,q,k,v,d,b


def proposal(s,q,k,v,d,b,su,vu,bits,df,permit_saturation=False):
    """Same Issue66 stages, but range guard precedes new-state output work."""
    s,q,k,v,d,b=checked_input(s,q,k,v,d,b,su,vu,bits,df);h,dim,width=s.shape
    dp=old.checked_product(s,d[:,None,None],'decay');dec=old.rne(dp,df)
    pp=old.checked_product(dec,k[:,:,None],'prediction')
    if dim*max(abs(int(pp.min())),abs(int(pp.max())))>old.I64_MAX:raise OverflowError('prediction reduction')
    pd=pp.sum(axis=1,dtype=np.int64);pred=old.rne(pd,15)
    aligned=np.stack([old.rne(v[a],int(su[a])-int(vu[a])) for a in range(h)])
    residual=old.checked_add(aligned,-pred,'residual')
    bp=old.checked_product(residual,b[:,None],'beta');correction=old.rne(bp,15)
    op=old.checked_product(k[:,:,None],correction[:,None,:],'outer')
    proposed=old.checked_add(dec,old.rne(op,15),'state update');lo,hi=old.state_bounds(bits)
    counts=np.count_nonzero((proposed<lo)|(proposed>hi),axis=(1,2))
    stages={'decay_product':dp,'decayed_state':dec,'prediction_dot':pd,'prediction':pred,
            'aligned_value':aligned,'residual':residual,'beta_product':bp,'correction':correction,
            'outer_product':op,'state_sum':proposed}
    stats={'guard_count_by_head':counts.tolist(),'guard_count':int(counts.sum()),
           'proposed_state_sha256':old.digest_array(proposed),
           'output_work_performed':False}
    new=np.clip(proposed,lo,hi).astype(np.int64)
    out=None
    if not stats['guard_count'] or permit_saturation:
        yp=old.checked_product(new,q[:,:,None],'output')
        if dim*max(abs(int(yp.min())),abs(int(yp.max())))>old.I64_MAX:raise OverflowError('output reduction')
        yd=yp.sum(axis=1,dtype=np.int64);out=old.rne(yd,15);stages['output_dot']=yd
        stats['output_work_performed']=True
    stats['observed_absolute_max']={n:max(abs(int(a.min())),abs(int(a.max()))) for n,a in stages.items()}
    stats['observed_signed_bits']={n:old.bits_for(v) for n,v in stats['observed_absolute_max'].items()}
    return new,out,stats


def stamp(s,units,epoch,version,position,sequence):
    return {'state_sha256':old.digest_array(s),'units':np.asarray(units).astype(int).tolist(),
            'epoch':int(epoch),'version':int(version),'position':int(position),'sequence':str(sequence)}


def resume_contract(bits,df,value_units,policy):
    return {'state_bits':int(bits),'decay_fraction':int(df),'value_units':np.asarray(value_units).astype(int).tolist(),'policy':str(policy)}


def checkpoint(snapshot,contract):
    """Integrity witness, not authentication or a hardware checkpoint engine."""
    body={'snapshot':copy.deepcopy(snapshot),'contract':copy.deepcopy(contract)}
    return dict(body,checkpoint_sha256=old.stable_hash(body))


class RangeLease:
    """Atomic software witness. Every state/output/scale/epoch publication binds."""
    def __init__(self,state,units,position=0,sequence='synthetic',resume=None,contract=None):
        self.state=np.asarray(state,dtype=np.int64).copy();self.units=np.asarray(units,dtype=np.int16).copy()
        self.epoch=0;self.version=0;self.position=int(position);self.sequence=str(sequence)
        if resume is not None:
            if set(resume)!={'snapshot','contract','checkpoint_sha256'}:raise ValueError('checkpoint fields')
            body={k:resume[k] for k in ('snapshot','contract')}
            if old.stable_hash(body)!=resume['checkpoint_sha256']:raise ValueError('checkpoint integrity')
            if resume['contract']!=contract:raise ValueError('checkpoint format/value units/policy contract')
            s=resume['snapshot']
            if set(s)!=set(self.snapshot()) or type(s['epoch']) is not int or type(s['version']) is not int:raise ValueError('checkpoint snapshot fields')
            if not 0<=s['epoch']<(1<<32) or not 0<=s['version']<(1<<64):raise ValueError('checkpoint epoch/version domain')
            self.epoch=s['epoch'];self.version=s['version']
            if self.snapshot()!=s:raise ValueError('checkpoint state/units/position/sequence data mismatch')

    def snapshot(self):return stamp(self.state,self.units,self.epoch,self.version,self.position,self.sequence)

    def prepare(self,new,out,units,epoch,expected):
        if expected!=self.snapshot():raise ValueError('stale/foreign state/scale/epoch/position proposal')
        units=np.asarray(units,dtype=np.int16)
        if new.shape!=self.state.shape or out.shape!=(new.shape[0],new.shape[2]) or units.shape!=self.units.shape:raise ValueError('partial state/output proposal')
        if np.any((units<self.units)|(units>127)) or epoch<self.epoch or epoch>=1<<32:raise ValueError('invalid scale/epoch transition')
        if bool(np.any(units!=self.units))!=bool(epoch!=self.epoch):raise ValueError('scale/epoch change must coincide')
        p={'old':copy.deepcopy(expected),'new':np.asarray(new,dtype=np.int64).copy(),'output':np.asarray(out,dtype=np.int64).copy(),
                'units':units.copy(),'epoch':int(epoch),'new_sha256':old.digest_array(new),
                'output_sha256':old.digest_array(out),'units_sha256':old.digest_array(units)}
        p['seal']=old.stable_hash({k:v for k,v in p.items() if k not in ('new','output','units')})
        return p

    def commit(self,p):
        if p['old']!=self.snapshot():raise ValueError('stale/foreign/duplicate commit')
        if p['seal']!=old.stable_hash({k:v for k,v in p.items() if k not in ('new','output','units','seal')}):raise ValueError('mutated scale/epoch/descriptor')
        for key,digest in [('new','new_sha256'),('output','output_sha256'),('units','units_sha256')]:
            if old.digest_array(p[key])!=p[digest]:raise ValueError('mutated commit payload '+key)
        if p['new'].shape!=self.state.shape or p['output'].shape!=(self.state.shape[0],self.state.shape[2]):raise ValueError('partial commit')
        self.state=p['new'].copy();self.units=p['units'].copy();self.epoch=p['epoch'];self.version+=1;self.position+=1
        return {'old':p['old'],'new':self.snapshot(),'output_sha256':p['output_sha256'],'publication':'state/output/units/epoch one token commit'}


def run(encoded,initial,units,value_units,bits,df,policy,position=0,sequence='synthetic',resume=None):
    if policy not in POLICIES:raise ValueError('unknown range policy')
    lease=RangeLease(initial,units,position,sequence,resume,resume_contract(bits,df,value_units,policy))
    states=[lease.state.copy()];u=[lease.units.copy()];epochs=[lease.epoch]
    outputs=[];ou=[];tokens=[];events=[];maxima={};total_saturations=0;reject=None
    h,dim,width=initial.shape;cells=dim*width;payload_bytes=cells*(bits//8)
    for t in range(len(encoded['q'])):
        before=lease.snapshot();trial=lease.state.copy();tu=lease.units.copy();te=lease.epoch;attempts=[];result=None
        for n in range(MAX_RETRIES+1):
            a={'attempt':n,'trial_old_sha256':old.digest_array(trial),'units':tu.astype(int).tolist(),'epoch':te}
            try:
                new,y,stats=proposal(trial,encoded['q'][t],encoded['k'][t],encoded['v'][t],encoded['decay'][t],encoded['beta'][t],tu,value_units,bits,df,policy=='static_sat')
                a.update(stats)
                for key,value in stats['observed_absolute_max'].items():maxima[key]=max(maxima.get(key,0),value)
                bad=np.asarray(stats['guard_count_by_head'])>0
                if not bad.any() or policy=='static_sat':
                    a['outcome']='COMMIT';attempts.append(a)
                    p=lease.prepare(new,y,tu,te,before);commit=lease.commit(p)
                    result={'token':t,'before':before,'attempts':attempts,'commit':commit,'outcome':'COMMITTED'}
                    total_saturations+=stats['guard_count'] if policy=='static_sat' else 0
                    states.append(lease.state.copy());u.append(lease.units.copy());epochs.append(lease.epoch)
                    outputs.append(y);ou.append(tu.copy());break
                a['outcome']='ABORT_RANGE';attempts.append(a)
                reason='state range guard'
            except OverflowError as exc:
                a.update(outcome='ABORT_WIDTH',error=str(exc),guard_count=None,guard_count_by_head=None,output_work_performed=False)
                attempts.append(a);bad=np.ones(h,dtype=bool);reason='I64/shift guard'
            if policy!='guard_rescale' or n==MAX_RETRIES:
                reject={'token':t,'reason':reason,'attempt':n};break
            if np.any(tu[bad]>=127) or te+1>=1<<32:
                reject={'token':t,'reason':'exponent/epoch domain guard','attempt':n};break
            previous=trial.copy();trial[bad]=old.rne(trial[bad],1);tu[bad]+=1;te+=1
            event={'token':t,'after_attempt':n,'heads':np.flatnonzero(bad).tolist(),'trial_epoch':te,
                   'old_units':a['units'],'new_units':tu.astype(int).tolist(),
                   'old_trial_state_sha256':old.digest_array(previous),'recoded_trial_state_sha256':old.digest_array(trial),
                   'state_scan_elements':int(bad.sum())*cells,'RNE_elements':int(bad.sum())*cells,
                   'nonexact_halvings':int(np.count_nonzero(previous[bad]-trial[bad]*2)),
                   'state_read_bytes':int(bad.sum())*payload_bytes,'state_write_bytes':int(bad.sum())*payload_bytes,
                   'scale_descriptor_write_bytes':int(bad.sum()),'epoch_descriptor_write_bytes':4,
                   'published':False,'cause':'current token proposal range/I64 guard only'}
            events.append(event)
        if result is None:
            if lease.snapshot()!=before:raise AssertionError('aborted token mutated published state/units/epoch')
            tokens.append({'token':t,'before':before,'attempts':attempts,'outcome':'REJECTED','after':lease.snapshot()});break
        tokens.append(result)
    shape=initial.shape
    arrays={'state_trace':np.stack(states).astype(np.int16 if bits==16 else np.int32),
            'state_units_trace':np.stack(u).astype(np.int8),'epoch_trace':np.asarray(epochs,dtype=np.uint32),
            'output_codes':np.stack(outputs) if outputs else np.empty((0,shape[0],shape[2]),dtype=np.int64),
            'output_units':np.stack(ou).astype(np.int8) if ou else np.empty((0,shape[0]),dtype=np.int8)}
    attempts_total=sum(len(t['attempts']) for t in tokens)
    products={'decay':0,'prediction':0,'beta':0,'outer':0,'output':0}
    for token in tokens:
        for a in token['attempts']:
            # Width rejection may precede any product; preserve separate bound.
            if a['outcome']=='ABORT_WIDTH':continue
            for key in ('decay','prediction','outer'):products[key]+=h*cells
            products['beta']+=h*width
            if a['output_work_performed']:products['output']+=h*cells
    cost={'state_bytes':h*payload_bytes,'minimum_old_new_atomic_payload_bytes':2*h*payload_bytes,
          'software_trial_copy_not_free_hardware':True,'guard_scan_elements':sum(h*cells for t in tokens for a in t['attempts'] if a['outcome']!='ABORT_WIDTH'),
          'integer_products_executed':products,'width_rejected_attempts_cost_unqualified':sum(a['outcome']=='ABORT_WIDTH' for t in tokens for a in t['attempts']),
          'rescale_scan_elements':sum(e['state_scan_elements'] for e in events),
          'rescale_RNE_elements':sum(e['RNE_elements'] for e in events),
          'rescale_state_read_bytes':sum(e['state_read_bytes'] for e in events),
          'rescale_state_write_bytes':sum(e['state_write_bytes'] for e in events),
          'rescale_scale_epoch_write_bytes':sum(e['scale_descriptor_write_bytes']+e['epoch_descriptor_write_bytes'] for e in events),
          'commit_metadata_candidate_bytes_per_token':64+h+4,'attempts':attempts_total,
          'schedule_scope':'logical stage/product/event counts only; materialize/recompute and real ports/shadow supplied by service experiment; rejected width attempts unqualified'}
    return arrays,{'policy':policy,'requested_tokens':len(encoded['q']),'committed_tokens':len(outputs),
                   'status':'REJECTED_GUARD' if reject else 'EXECUTED','rejection':reject,
                   'saturations_published':total_saturations,'tokens':tokens,'rescale_events':events,
                   'observed_absolute_max':maxima,'observed_signed_bits':{k:old.bits_for(v) for k,v in maxima.items()},
                   'cost':cost,'final':lease.snapshot()}


def receive(root):
    root=Path(root).resolve();m=json.loads((root/'manifest.json').read_text());records=json.loads((root/'state-results.json').read_text())
    if m.get('status')!='PASS':raise ValueError('source execution not accepted')
    artifacts=m.get('artifacts',{})
    if 'state-results.json' not in artifacts:raise ValueError('source metrics not indexed')
    for name in ['state-results.json']+[r['artifact']['name'] for r in records]:
        p=(root/name).resolve();desc=artifacts.get(name)
        if not p.is_relative_to(root) or not p.is_file() or desc is None or old.sha(p)!=desc['sha256'] or p.stat().st_size!=desc['bytes']:raise ValueError('source artifact mismatch '+name)
    for r in records:
        if r['artifact']!=dict(name=r['artifact']['name'],**artifacts[r['artifact']['name']]):raise ValueError('source metric artifact descriptor mismatch')
    return m,records


def errors(arrays,z):
    count=len(arrays['output_codes']);samples=[]
    if not count:return samples
    y=arrays['output_codes'].astype(np.float64)*np.exp2(arrays['output_units'].astype(np.float64))[:,:,None]
    s=arrays['state_trace'].astype(np.float64)*np.exp2(arrays['state_units_trace'].astype(np.float64))[:,:,None,None]
    for n in sorted({1,min(8,count),min(32,count),count}):
        row={'steps':n,'output_vs_native':old.metric(y[:n],z['native_output'][:n]),'state_vs_FP64_replay':old.metric(s[n],z['FP64_state_reference'][n])}
        if 'native_state_reference' in z:row['state_vs_native_capture']=old.metric(s[n],z['native_state_reference'][n])
        samples.append(row)
    return samples


def execute(native,legacy,out,binding=None,suite='all'):
    native=Path(native).resolve();legacy=Path(legacy).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('refuse existing output')
    source={'range_sha256':old.sha(__file__),'state_sha256':old.sha(OLD_PATH)}
    if binding:
        binding=Path(binding);b=json.loads(binding.read_text())
        for field in ('range_sha256','state_sha256'):
            if b.get(field)!=source[field]:raise ValueError('source binding mismatch '+field)
        source.update(commit=b['commit'],binding_sha256=old.sha(binding))
    if suite not in ('all','native','legacy'):raise ValueError('suite')
    selected=[]
    for role,root in [('native',native),('legacy',legacy)]:
        if suite!='all' and role!=suite:continue
        m,records=receive(root)
        source[role]={'path':str(root),'manifest_sha256':old.sha(root/'manifest.json'),'records_sha256':old.sha(root/'state-results.json'),'provenance':m['source']}
        for row in records:
            accepted=(role=='native' and re.fullmatch(r'evaluation\.S(16|32)\.D(15|31)',row['id'])) or (role=='legacy' and re.fullmatch(r'layer(0|14|30)-end(2048|8192)\.S(16|32)\.D(15|31)',row['id']))
            if accepted:selected.append((role,root,row))
    counts={role:sum(r[0]==role for r in selected) for role in ('native','legacy')}
    expected={'native':4 if suite in ('all','native') else 0,'legacy':24 if suite in ('all','legacy') else 0}
    if counts!=expected:raise ValueError('frozen 4 native/24 full legacy source selection '+str(counts))
    out.mkdir(parents=True);start=time.monotonic();rows=[];failures=[]
    for role,root,row in selected:
        with np.load(root/row['artifact']['name'],allow_pickle=False) as z:
            encoded={k:z[k] for k in ('q','k','v','beta','decay')};initial=z['state_initial'].astype(np.int64)
            su=z['state_units'].astype(np.int16);vu=z['value_units'].astype(np.int16)
            steps=32 if role=='native' else 256
            if len(encoded['q'])!=steps:raise ValueError('source real contiguous step length')
            bits=int(row['format']['state_bits']);df=int(row['format']['decay_fraction'])
            position=int(row['execution']['final_position'])-steps
            for policy in POLICIES:
                label=role+'.'+row['id']+'.'+policy
                try:
                    a,stats=run(encoded,initial,su,vu,bits,df,policy,position,row['format']['sequence'])
                    baseline=False
                    if policy=='static_sat':
                        if not np.array_equal(a['state_trace'],z['state_trace']) or not np.array_equal(a['output_codes'],z['output_codes']):raise AssertionError('static_sat differs from original Issue66 trace')
                        if stats['saturations_published']!=row['execution']['saturations']:raise AssertionError('original saturation count mismatch')
                        baseline=True
                    samples=errors(a,z);filename=label+'.npz';tracefile=label+'.json'
                    old.save_npz(out/filename,a);old.save(out/tracefile,stats)
                    rows.append({'id':label,'role':role,'source_id':row['id'],'source_artifact':row['artifact'],
                                 'format':row['format'],'policy':policy,'protocol_version':'causal-range/1','max_rescale_retries':MAX_RETRIES,
                                 'original_initial_bridge_code_clips':row['initial_bridge_code_clips'],'original_operand_bridge_clips':row['operand_bridge_clips'],
                                 'original_saturations':row['execution']['saturations'],'original_scale_source':row['scale_source'],
                                 'original_conservative_format_proofs':row['conservative_format_proofs'],
                                 'original_role':row['role'],'original_position_source':row['position_source'],
                                 'requested_tokens':steps,'committed_tokens':stats['committed_tokens'],'status':stats['status'],'rejection':stats['rejection'],
                                 'saturations_published':stats['saturations_published'],'rescale_waves':len(stats['rescale_events']),
                                 'rescaled_head_events':sum(len(e['heads']) for e in stats['rescale_events']),
                                 'final':stats['final'],'observed_signed_bits':stats['observed_signed_bits'],'cost':stats['cost'],
                                 'static_original_bitexact':baseline,'error_by_length':samples,
                                 'artifact':{'name':filename,'bytes':(out/filename).stat().st_size,'sha256':old.sha(out/filename)},
                                 'transaction_trace':{'name':tracefile,'bytes':(out/tracefile).stat().st_size,'sha256':old.sha(out/tracefile)},
                                 'quality_accepted':False,'hardware_implemented':False})
                except (ValueError,OverflowError,AssertionError) as exc:
                    failures.append({'id':label,'type':type(exc).__name__,'error':str(exc)})
    old.save(out/'range-results.json',rows)
    old.save(out/'manifest.json',{'status':'FAIL' if failures else 'PASS','source':source,'schema':'issue68-range/1',
                                'suite':suite,'selection':counts,'conditions':len(rows),'failures':failures,'seconds':time.monotonic()-start,
                                'quality_accepted':False,'performance_eligible':False,'hardware_implemented':False,
                                'environment':{'python':platform.python_version(),'numpy':np.__version__,'host':platform.node(),'SLURM_JOB_ID':os.environ.get('SLURM_JOB_ID'),
                                               'OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS'),'MKL_NUM_THREADS':os.environ.get('MKL_NUM_THREADS'),'OPENBLAS_NUM_THREADS':os.environ.get('OPENBLAS_NUM_THREADS')},
                                'causality':'range decision uses current integer proposal only; initial codes and units reused, no future/native/error based scale fitting',
                                'floating_bridges':'unchanged Issue66 q/k/v/gate/initial compilers and FP64 reference for metrics only; not a complete integer model',
                                'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':old.sha(p)} for p in out.iterdir() if p.is_file()}})
    print(json.dumps({'status':'FAIL' if failures else 'PASS','conditions':len(rows),'failures':failures}),flush=True)
    if failures:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--legacy',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--binding',type=Path)
    p.add_argument('--suite',choices=('native','legacy','all'),default='all')
    a=p.parse_args();execute(a.native,a.legacy,a.out,a.binding,a.suite)


if __name__=='__main__':main()
