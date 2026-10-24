"""Qwen3.5 continuous integer-state candidates, not a complete integer model.

FP32 capture, L2 normalization/sqrt(D), sigmoid/softplus/exp and initial/scale
compilers are explicit offline bridges. Only the typed recurrence below is
integer. No intermediate state is reset from a captured native state.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time
import zipfile

import numpy as np

I64_MAX=(1<<63)-1
FRACTION=15


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(8<<20),b''):h.update(data)
    return h.hexdigest()


def digest_array(value):
    x=np.ascontiguousarray(value)
    return hashlib.sha256(str(x.dtype).encode()+str(x.shape).encode()+x.tobytes()).hexdigest()


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def save_npz(path,arrays):
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for name,value in sorted(arrays.items()):
            data=io.BytesIO();np.save(data,np.asarray(value),allow_pickle=False)
            member=zipfile.ZipInfo(name+'.npy',(2026,10,24,0,0,0));member.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(member,data.getvalue())


def bits_for(bound):
    return max(1,int(bound).bit_length()+1)


def rne(values,shift):
    """Exact signed integer RNE, with checked I64 before a left shift."""
    x=np.asarray(values,dtype=np.int64);shift=int(shift)
    if not -62<=shift<=62:raise ValueError('RNE shift outside frozen [-62,62]')
    if np.any(x==-(1<<63)):raise OverflowError('I64 minimum requires wider absolute value')
    if shift<=0:
        bound=max(abs(int(x.min())),abs(int(x.max())))
        if bound<<-shift>I64_MAX:raise OverflowError('I64 left-shift bound')
        return x*np.int64(1<<-shift)
    a=np.abs(x);q,r=np.divmod(a,np.int64(1<<shift))
    q=q+((r>(1<<(shift-1)))|((r==(1<<(shift-1)))&((q&1)!=0)))
    return np.where(x<0,-q,q)


def checked_product(a,b,label):
    a,b=np.asarray(a,dtype=np.int64),np.asarray(b,dtype=np.int64)
    ma=max(abs(int(a.min())),abs(int(a.max())))
    mb=max(abs(int(b.min())),abs(int(b.max())))
    if ma*mb>I64_MAX:raise OverflowError(label+' I64 product bound')
    return a*b


def checked_add(a,b,label):
    a,b=np.asarray(a,dtype=np.int64),np.asarray(b,dtype=np.int64)
    if max(abs(int(a.min())),abs(int(a.max())))+max(abs(int(b.min())),abs(int(b.max())))>I64_MAX:
        raise OverflowError(label+' I64 sum bound')
    return a+b


def bridge_codes(value,units,lo,hi):
    """Offline FP64 RNE compiler, not runtime floating point capability."""
    x=np.asarray(value,dtype=np.float64)
    rounded=np.rint(x*np.exp2(-np.asarray(units,dtype=np.float64)))
    if not np.isfinite(rounded).all():raise ValueError('nonfinite bridge')
    clips=int(np.count_nonzero((rounded<lo)|(rounded>hi)))
    return np.clip(rounded,lo,hi).astype(np.int64),clips


def head_units(value,bound,head_axis,headroom=2.,floor=-26):
    x=np.moveaxis(np.asarray(value,dtype=np.float64),head_axis,0)
    maxima=np.max(np.abs(x.reshape(len(x),-1)),axis=1)
    if not np.isfinite(maxima).all():raise ValueError('finite scale input required')
    result=np.array([max(floor,-20 if m==0 else int(math.ceil(math.log2(float(m)*headroom/bound)))) for m in maxima],dtype=np.int16)
    if np.any(result<-111) or np.any(result>127):raise OverflowError('state/value exponent outside frozen I8 domain after refinement')
    return result


def state_bounds(bits):
    if bits==16:return -32768,32767
    if bits==32:return -(1<<31),32767<<16
    raise ValueError('state candidate bits16/32 only')


def format_bounds(dim,sbits,sunit,vunit,decay_fraction=15):
    """Conservative format guard, independent of observed small products."""
    lo,hi=state_bounds(sbits);sb=max(abs(lo),abs(hi));shift=int(vunit)-int(sunit)
    value_bound=32767<<shift if shift>=0 else (32767+(1<<-shift)-1)//(1<<-shift)
    pred_product=dim*sb*32767;prediction=(pred_product+32767)//32768
    residual=value_bound+prediction
    bounds={'decay_product':sb*(1<<decay_fraction),'prediction_dot':pred_product,'prediction_state_unit':prediction,
      'aligned_value':value_bound,'residual':residual,'beta_product':residual*32768,
      'correction_state_unit':residual,'outer_product':residual*32767,
      'state_sum':sb+(residual*32767+32767)//32768,'output_dot':dim*sb*32767}
    if any(v>I64_MAX for v in bounds.values()):raise OverflowError('conservative recurrence requires wider than I64')
    return {'absolute_bounds':bounds,'signed_bits':{k:bits_for(v) for k,v in bounds.items()}}


def step(state,q,k,v,decay,beta,sunits,vunits,sbits,decay_fraction=15):
    """Sdec -> complete prediction -> correction -> new S -> new-S output."""
    state=np.asarray(state,dtype=np.int64);q=np.asarray(q,dtype=np.int64);k=np.asarray(k,dtype=np.int64)
    v=np.asarray(v,dtype=np.int64);decay=np.asarray(decay,dtype=np.int64);beta=np.asarray(beta,dtype=np.int64)
    h,dim,width=state.shape
    if q.shape!=(h,dim) or k.shape!=q.shape or v.shape!=(h,width) or decay.shape!=(h,) or beta.shape!=(h,):
        raise ValueError('recurrence shape')
    if np.any(np.abs(q)>32767) or np.any(np.abs(k)>32767) or np.any(np.abs(v)>32767):raise ValueError('S16 symmetric operand domain')
    if decay_fraction not in (15,31):raise ValueError('decay fraction15/31 only')
    if np.any((decay<0)|(decay>(1<<decay_fraction))|(beta<0)|(beta>32768)):raise ValueError('unsigned gate code domain including exact1')
    lo,hi=state_bounds(sbits)
    if np.any((state<lo)|(state>hi)):raise ValueError('stored state code domain')
    proofs=[format_bounds(dim,sbits,su,vu,decay_fraction) for su,vu in zip(sunits,vunits)]
    decay_product=checked_product(state,decay[:,None,None],'decay')
    dec=rne(decay_product,decay_fraction)
    pred_products=checked_product(dec,k[:,:,None],'prediction')
    if dim*max(abs(int(pred_products.min())),abs(int(pred_products.max())))>I64_MAX:raise OverflowError('prediction reduction')
    pred_dot=pred_products.sum(axis=1,dtype=np.int64);pred=rne(pred_dot,15)
    aligned=np.stack([rne(v[i],int(sunits[i])-int(vunits[i])) for i in range(h)])
    residual=checked_add(aligned,-pred,'residual')
    beta_product=checked_product(residual,beta[:,None],'beta')
    correction=rne(beta_product,15)
    outer_product=checked_product(k[:,:,None],correction[:,None,:],'outer')
    update=rne(outer_product,15);proposed=checked_add(dec,update,'state update')
    saturations=int(np.count_nonzero((proposed<lo)|(proposed>hi)))
    new=np.clip(proposed,lo,hi).astype(np.int64)
    out_products=checked_product(new,q[:,:,None],'output')
    if dim*max(abs(int(out_products.min())),abs(int(out_products.max())))>I64_MAX:raise OverflowError('output reduction')
    out_dot=out_products.sum(axis=1,dtype=np.int64);out=rne(out_dot,15)
    stage={'decay_product':decay_product,'decayed_state':dec,'prediction_dot':pred_dot,'prediction':pred,
       'aligned_value':aligned,'residual':residual,'beta_product':beta_product,'correction':correction,
       'outer_product':outer_product,'state_sum':proposed,'output_dot':out_dot}
    maxima={name:max(abs(int(x.min())),abs(int(x.max()))) for name,x in stage.items()}
    return new,out,{'saturations':saturations,'observed_absolute_max':maxima,'observed_signed_bits':{k:bits_for(v) for k,v in maxima.items()},'format_proofs':proofs}


class StateLease:
    """Software atomic version/epoch witness, not a hardware SHA engine."""
    def __init__(self,state,descriptor,position=0):
        self.state=np.asarray(state,dtype=np.int64).copy();self.descriptor=dict(descriptor)
        self.contract=stable_hash(descriptor);self.position=int(position);self.version=0

    def propose(self,new,out,expected_version,expected_position,contract):
        if expected_version!=self.version or expected_position!=self.position or contract!=self.contract:
            raise ValueError('state version/position/sequence/scale contract mismatch')
        return {'old_version':self.version,'old_position':self.position,'contract':contract,
          'old_state_sha256':digest_array(self.state),'new_state_sha256':digest_array(new),'output_sha256':digest_array(out),'new':np.asarray(new,dtype=np.int64).copy(),'out':np.asarray(out).copy()}

    def commit(self,proposal):
        if proposal['old_version']!=self.version or proposal['old_position']!=self.position or proposal['contract']!=self.contract or proposal['old_state_sha256']!=digest_array(self.state):
            raise ValueError('stale/foreign state commit')
        if proposal['new_state_sha256']!=digest_array(proposal['new']):raise ValueError('mutated proposed state')
        if proposal['output_sha256']!=digest_array(proposal['out']):raise ValueError('mutated proposed output')
        self.state=proposal['new'].copy();self.position+=1;self.version+=1
        return {'version':self.version,'position':self.position,'contract':self.contract,
          'old_state_sha256':proposal['old_state_sha256'],'state_sha256':digest_array(self.state),'output_sha256':proposal['output_sha256']}


def run_integer(encoded,initial,sunits,vunits,sbits,descriptor,start_position,chunk=32):
    lease=StateLease(initial,descriptor,start_position);outputs=[];states=[initial.copy()];commits=[];maxima={};saturations=0
    for begin in range(0,len(encoded['q']),chunk):
        for t in range(begin,min(begin+chunk,len(encoded['q']))):
            new,out,stats=step(lease.state,encoded['q'][t],encoded['k'][t],encoded['v'][t],encoded['decay'][t],encoded['beta'][t],sunits,vunits,sbits,descriptor['decay_fraction'])
            p=lease.propose(new,out,lease.version,lease.position,lease.contract);commits.append(lease.commit(p))
            outputs.append(out);states.append(new.copy());saturations+=stats['saturations']
            for name,value in stats['observed_absolute_max'].items():maxima[name]=max(maxima.get(name,0),value)
    return np.stack(outputs),np.stack(states),{'commits':commits,'saturations':saturations,'observed_absolute_max':maxima,'observed_signed_bits':{k:bits_for(v) for k,v in maxima.items()},'final_version':lease.version,'final_position':lease.position}


def normalized_inputs(payload):
    q,k,v=(np.asarray(payload[name],dtype=np.float64)[0] for name in ('query','key','value'))
    if q.ndim!=3 or q.shape!=k.shape or v.shape[:2]!=q.shape[:2]:raise ValueError('B1 time/head/dimension capture contract')
    q=q/np.sqrt(np.sum(q*q,axis=-1,keepdims=True)+1e-6)/math.sqrt(q.shape[-1])
    k=k/np.sqrt(np.sum(k*k,axis=-1,keepdims=True)+1e-6)
    g,b=(np.asarray(payload[name],dtype=np.float64)[0] for name in ('g','beta'))
    if np.any(g>0) or np.any((b<0)|(b>1)):raise ValueError('decay-log/beta semantic domain')
    return {'q':q,'k':k,'v':v,'decay':np.exp(g),'beta':b}


def float_reference(payload,keep=32):
    p=normalized_inputs(payload);state=np.asarray(payload['initial_state'],dtype=np.float64)[0].copy();outs=[];states=[state.copy()]
    for i in range(len(p['q'])):
        state=state*p['decay'][i,:,None,None]
        prediction=np.einsum('hkv,hk->hv',state,p['k'][i],optimize=False)
        correction=(p['v'][i]-prediction)*p['beta'][i,:,None]
        state=state+p['k'][i,:,:,None]*correction[:,None,:]
        outs.append(np.einsum('hkv,hk->hv',state,p['q'][i],optimize=False))
        if i<keep:states.append(state.copy())
    return np.stack(outs),np.stack(states),state,p


def metric(a,b):
    a,b=np.asarray(a,dtype=np.float64),np.asarray(b,dtype=np.float64)
    return {'relative_rmse':float(np.linalg.norm(a-b)/max(float(np.linalg.norm(b)),1e-30)),
      'max_abs':float(np.max(np.abs(a-b)))}


def cost(heads,dim,width,steps,sbits,decay_fraction=15):
    state_bytes=heads*dim*width*(sbits//8);cells=heads*dim*width
    digits=3 if sbits==16 else 5
    return {'stored_state_bytes':state_bytes,'software_I64_working_state_bytes':cells*8,
      'QK_S16_bytes_per_step':heads*dim*4,'V_S16_bytes_per_step':heads*width*2,'beta_decay_bytes_per_step':heads*(4 if decay_fraction==15 else 6),
      'state_exponent_I8_bytes':heads,'value_exponent_I8_bytes':heads,'commit_descriptor_candidate_bytes':64,
      'integer_stage_products_per_step':{'decay_state_bits_by_U16':cells,'prediction_state_bits_by_S16':cells,
        'correction_I64_by_U16':heads*width,'outer_S16_by_I64':cells,'output_state_bits_by_S16':cells},
      'S8_radix128_candidate_base_products_per_step':(cells*digits*((3 if decay_fraction==15 else 5)+6))+(heads*width*30)+(cells*30),
      'S8_cost_scope':'balanced digits: S16=3/S32=5/I64=10; unsigned U16Q15=3/U32Q31=5. Only a conservative decomposition count; wide shift/add/RNE/reduction/packing/ports/control additional. No native wide multiplier or measured S8 execution.',
      'alternative_state_schedules':{
        'materialize_decay':{'logical_state_read_write_bytes_per_step':state_bytes*4,'minimum_old_new_payload_for_atomic_rollback_bytes':state_bytes*2,'decay_products_per_step':cells},
        'recompute_decay':{'logical_state_read_write_bytes_per_step':state_bytes*3,'minimum_old_new_payload_for_atomic_rollback_bytes':state_bytes*2,'decay_products_per_step':cells*2}},
      'schedule_scope':'alternative lower-bound accounting, not summed; prediction requires all K before correction; output can fuse with new-state write. Transaction rollback needs shadow/checkpoint or an explicitly different failure policy. Not scheduled or hardware verified.',
      'V_tiles':[{ 'V_columns':n,'one_head_state_bytes':dim*n*(sbits//8),'old_new_state_payload_bytes':2*dim*n*(sbits//8),'prediction_correction_output_I64_bytes':n*8*3,'scope':'V tiling preserves complete K; gated norm must still reduce over full original V dimension'} for n in (16,32,64,width) if n<=width],
      'captured_steps':steps,'hardware_implemented':False}


def load_capture(root):
    manifest=json.loads((root/'manifest.json').read_text());name='windows.npz' if 'windows' in manifest else 'state-raw.npz'
    if manifest.get('status')!='PASS':raise ValueError('unaccepted capture')
    artifacts=manifest.get('artifacts',{})
    if name not in artifacts:raise ValueError('capture must index state NPZ SHA/bytes in artifacts')
    for filename,desc in [(name,artifacts[name])]:
        path=(root/filename).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path)!=desc['sha256'] or path.stat().st_size!=desc['bytes']:
            raise ValueError('capture artifact mismatch '+filename)
    if name=='state-raw.npz':
        if manifest.get('state',{}).get('use_qk_l2norm') is not True:raise ValueError('unknown native normalization contract')
        manifest['windows']={r['case']:{} for r in manifest['state']['checks']}
        if set(manifest['windows'])!={'calibration','evaluation'}:raise ValueError('new capture case split')
        manifest['calibration_windows']=['calibration']
        manifest['window_metadata']={r['case']:r for r in manifest['state']['checks']}
        manifest['_state_adapter']='new calibrated continuous32 capture; only state-raw.npz artifact verified by this branch'
    return manifest,np.load(root/name,allow_pickle=False),name


def execute(root,out,binding=None,conv=None,only_coupled=False):
    if out.exists():raise ValueError('refuse existing output directory')
    manifest,z,input_name=load_capture(root);out.mkdir(parents=True);start=time.monotonic();records=[];errors=[]
    source={'state_sha256':sha(Path(__file__)),'input_manifest_sha256':sha(root/'manifest.json'),'input_NPZ_sha256':sha(root/input_name),'input_NPZ_name':input_name,
      'input_provenance':{k:v for k,v in manifest.items() if k not in ('windows','artifacts')}}
    if binding:
        b=json.loads(binding.read_text())
        if b.get('state_sha256')!=source['state_sha256']:raise ValueError('state source binding mismatch')
        source.update(commit=b['commit'],binding_sha256=sha(binding))
    conv_data=None
    if only_coupled and conv is None:raise ValueError('only-coupled requires a conv result directory')
    if conv is not None:
        cm=json.loads((conv/'manifest.json').read_text());desc=cm.get('artifacts',{}).get('conv-output.npz')
        if cm.get('status')!='PASS' or desc is None:raise ValueError('unaccepted integer conv input')
        if cm.get('capture_manifest_sha256')!=source['input_manifest_sha256']:raise ValueError('conv source capture mismatch')
        if sha(conv/'conv-output.npz')!=desc['sha256'] or (conv/'conv-output.npz').stat().st_size!=desc['bytes']:
            raise ValueError('conv artifact hash/size')
        if not manifest.get('calibration_windows'):raise ValueError('coupled conv requires explicit independent calibration capture')
        conv_data=np.load(conv/'conv-output.npz',allow_pickle=False)
        source['conv_input']={'manifest_sha256':sha(conv/'manifest.json'),'NPZ_sha256':sha(conv/'conv-output.npz'),'capture_manifest_sha256':cm['capture_manifest_sha256']}
    for name,fieldmeta in manifest['windows'].items():
        try:
            p={field:z[name+'.'+field] for field in ('query','key','value','g','beta','initial_state','output','final_state')}
            if any(not np.isfinite(x).all() for x in p.values()):raise ValueError('nonfinite native data')
            if p['initial_state'].shape[0]!=1:raise ValueError('B1 initial state')
            native_out,reference_states,final,normalized=float_reference(p)
            oracle_out=metric(native_out,np.asarray(p['output'])[0]);oracle_state=metric(final,np.asarray(p['final_state'])[0])
            if oracle_out['relative_rmse']>=1e-4 or oracle_state['relative_rmse']>=1e-4:raise ValueError('native FP32/independent FP64 reference mismatch')
            length=min(32,len(native_out));h,dim,width=p['initial_state'].shape[1:]
            state_unit=head_units(p['initial_state'][0],32767,0)
            value_unit=np.full(h,-10,dtype=np.int16)
            scale_source='initial-state encoding/transition profile: 2x perhead max; floor=-26; not a lifetime calibrated static capability'
            calnames=manifest.get('calibration_windows',[])
            compiler_scan_elements=int(p['initial_state'].size)
            if calnames:
                cal_states=np.concatenate([np.stack([z[c+'.initial_state'][0],z[c+'.final_state'][0]]) for c in calnames],axis=0)
                cal_values=np.concatenate([z[c+'.value'][0] for c in calnames],axis=0)
                state_unit=head_units(cal_states,32767,1);value_unit=head_units(cal_values,32767,1,floor=-26)
                scale_source='declared external calibration windows only; 2x perhead maxima, fixed across evaluation; state floor=-26'
                compiler_scan_elements=int(cal_states.size+cal_values.size)
            endmatch=re.search(r'layer(\d+)-end(\d+)',name)
            inferred_start=int(endmatch.group(2))-len(native_out) if endmatch else 0
            meta=manifest.get('window_metadata',{}).get(name,{})
            if meta:inferred_start=int(meta['start_position'])
            native_states=None
            if name+'.state_boundaries' in z:
                native_states=z[name+'.state_boundaries'][:,0]
                if native_states.shape!=reference_states.shape or metric(native_states,reference_states)['relative_rmse']>=1e-4:
                    raise ValueError('native captured intermediate state/FP64 mismatch')
            profiles=[] if only_coupled else [(16,15,'native'),(16,31,'native'),(32,15,'native'),(32,31,'native')]
            if conv_data is not None and name not in calnames:profiles.extend([(32,31,'conv8'),(32,31,'conv16')])
            for bits,df,variant in profiles:
                inputs=normalized;coupled_y=coupled_s=None
                if variant!='native':
                    cp=dict(p)
                    for key in ('query','key','value'):
                        value=conv_data[variant+'.'+name+'.'+key]
                        if value.shape!=p[key].shape or not np.isfinite(value).all():raise ValueError('coupled QKV shape/finite contract')
                        cp[key]=value
                    coupled_y,coupled_s,_,inputs=float_reference(cp)
                encoded={};clip={}
                for key in ('q','k'):encoded[key],clip[key]=bridge_codes(inputs[key][:length],-15,-32767,32767)
                encoded['v'],clip['v']=bridge_codes(inputs['v'][:length],value_unit[None,:,None],-32767,32767)
                encoded['beta'],clip['beta']=bridge_codes(normalized['beta'][:length],-15,0,32768)
                encoded['decay'],clip['decay']=bridge_codes(normalized['decay'][:length],-df,0,1<<df)
                unit=state_unit-(16 if bits==32 else 0);lo,hi=state_bounds(bits)
                initial,init_clips=bridge_codes(p['initial_state'][0],unit[:,None,None],lo,hi)
                desc={'window':name,'sequence':stable_hash({'source':source['input_manifest_sha256'],'window':name}) if meta else 'unknown:'+name+': no cross-window commits','head_slots':list(range(h)),
                  'source_input_sha256':source['input_NPZ_sha256'],'format_epoch':0,'state_bits':bits,'state_unit':unit.tolist(),
                  'value_unit':value_unit.tolist(),'QK_unit':-15,'beta_unit':-15,'decay_fraction':df,
                  'input_variant':variant,
                  'stage_contract':'decay RNE at declared fraction; prediction/beta/outer/output RNE15; state-only final saturation'}
                y,s,stats=run_integer(encoded,initial,unit,value_unit,bits,desc,inferred_start,chunk=32)
                for chunk in (8,16):
                    cy,cs,cstats=run_integer(encoded,initial,unit,value_unit,bits,desc,inferred_start,chunk=chunk)
                    if not np.array_equal(y,cy) or not np.array_equal(s,cs) or stats['commits']!=cstats['commits']:
                        raise AssertionError('integer chunk/version continuity')
                samples=[]
                physical_y=y.astype(np.float64)*np.exp2(unit)[None,:,None]
                physical_s=s.astype(np.float64)*np.exp2(unit)[None,:,None,None]
                for n in sorted({1,min(8,length),length}):
                    row={'steps':n,'output_vs_native':metric(physical_y[:n],np.asarray(p['output'])[0,:n]),
                        'state_vs_FP64_replay':metric(physical_s[n],reference_states[n]),'state_reference_scope':'actual native captured boundaries and independent FP64 replay' if native_states is not None else 'FP64 replay checked at original captured full-window endpoint, not captured native state at this short prefix'}
                    if native_states is not None:row['state_vs_native_capture']=metric(physical_s[n],native_states[n])
                    if coupled_y is not None:
                        row['output_vs_FP64_same_coupled_input']=metric(physical_y[:n],coupled_y[:n])
                        row['state_vs_FP64_same_coupled_input']=metric(physical_s[n],coupled_s[n])
                        row['FP64_coupled_output_vs_native']=metric(coupled_y[:n],np.asarray(p['output'])[0,:n])
                    samples.append(row)
                label=name+('.'+variant if variant!='native' else '')+'.S'+str(bits)+'.D'+str(df);filename=label+'.npz'
                arrays={**{k:v.astype(np.int16 if k in ('q','k','v') else np.uint16 if k=='beta' or df==15 else np.uint32) for k,v in encoded.items()},'state_initial':initial.astype(np.int16 if bits==16 else np.int32),'state_trace':s.astype(np.int16 if bits==16 else np.int32),
                  'output_codes':y,'state_units':unit.astype(np.int8),'value_units':value_unit.astype(np.int8),
                  'native_output':np.asarray(p['output'])[0,:length],'FP64_state_reference':reference_states[:length+1]}
                if native_states is not None:arrays['native_state_reference']=native_states[:length+1]
                if coupled_y is not None:
                    arrays['FP64_coupled_input_output_reference']=coupled_y[:length]
                    arrays['FP64_coupled_input_state_reference']=coupled_s[:length+1]
                save_npz(out/filename,arrays)
                proofs=[format_bounds(dim,bits,su,vu,df) for su,vu in zip(unit,value_unit)]
                records.append({'id':label,'status':'PASS_INTEGER_EXECUTION','original_native_steps':len(native_out),'integer_steps':length,
                  'integer_scope':'one original contiguous window prefix only; no cross-window integer continuity claim','position_source':'actual captured positions; candidate epoch0 is a new encoding epoch' if meta else 'end minus original T inferred from original window ID; no independently captured runtime epoch' if endmatch else 'unknown: local window index only',
                  'format':desc,'scale_source':scale_source,'initial_state_scan_elements':int(p['initial_state'].size),
                  'offline_scale_compiler_scan_elements':compiler_scan_elements,
                  'role':'calibration' if name in calnames else 'independent evaluation' if calnames else 'previously observed legacy diagnostic',
                  'initial_bridge_code_clips':init_clips,'operand_bridge_clips':dict(clip),'native_FP64_oracle':{'output':oracle_out,'final_state':oracle_state},
                  'decay_near_one':{'original_full_window_steps':len(normalized['decay']),'source_less_than1_encoded_exact1_full_window':int(np.count_nonzero((normalized['decay']<1)&(np.rint(normalized['decay']*(1<<df))==(1<<df)))),'integer_prefix_source_less_than1_encoded_exact1':int(np.count_nonzero((normalized['decay'][:length]<1)&(encoded['decay']==(1<<df))))},
                  'error_by_length':samples,'execution':stats,'conservative_format_proofs':proofs,'cost':cost(h,dim,width,length,bits,df),
                  'chunk8_16_vs_whole_bitexact':True,'artifact':{'name':filename,'bytes':(out/filename).stat().st_size,'sha256':sha(out/filename)},
                  'quality_accepted':False,'hardware_implemented':False})
        except (ValueError,OverflowError,AssertionError) as exc:
            errors.append({'window':name,'status':'FAIL','error_type':type(exc).__name__,'error':str(exc)})
    save(out/'state-results.json',records)
    save(out/'manifest.json',{'status':'FAIL' if errors else 'PASS','source':source,'integer_conditions':len(records),'failures':errors,
      'seconds':time.monotonic()-start,'scope':__doc__,'floating_bridges':['captured FP32 conv/SiLU and QKV projections','offline FP64 L2norm/rsqrt/head scaling','source sigmoid/softplus/exp and U16Q15/U32Q31 gate compiler','initial state and static exponent compiler','FP64 numerical oracle only'],
      'conv_scope':'Native and optionally externally verified H8/W8 or H16/W8 integer conv outputs; SiLU and subsequent L2 normalization remain explicit floating bridges. Same native-calibration eS/eV reused for controlled coupled comparison. Conv implementation/cost is independently indexed, not duplicated in R cost.',
      'run_selection':'coupled-only evaluation2' if only_coupled else 'native calibration4/evaluation4 and optional coupled evaluation2',
      'artifacts':{f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file()}})
    print(json.dumps({'status':'FAIL' if errors else 'PASS','integer_conditions':len(records),'failures':len(errors)}),flush=True)
    if errors:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--binding',type=Path)
    p.add_argument('--conv',type=Path);p.add_argument('--only-coupled',action='store_true')
    a=p.parse_args();execute(a.root,a.out,a.binding,a.conv,a.only_coupled)


if __name__=='__main__':main()
