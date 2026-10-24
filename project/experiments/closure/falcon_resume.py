"""Issue72 full-branch continuous conv+R+consumer checkpoint qualification.
Run after frozen integer full-chain baseline; no FP reference is loaded here.
"""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import falcon_int as fi
import falcon_chain as fc

def complete_checkpoint(state,units,history,epoch,position,contract):
    d={'owner':'layer0.mamba.integer','state_sha256':fi.array_sha(state),'units_sha256':fi.array_sha(units),'conv_sha256':fi.array_sha(history),'units':list(map(int,units)),'epoch':int(epoch),'version':int(position),'position':int(position),'contract':contract}
    d['checksum']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest();return d

def restore(d,state,units,history,position,contract):
    state=np.asarray(state);units=np.asarray(units);history=np.asarray(history)
    if state.shape!=(contract['heads'],contract['dim'],contract['n']) or units.shape!=(contract['heads'],) or history.shape!=(contract['heads']*contract['dim']+2*contract['n'],4):raise ValueError('complete checkpoint shape')
    if np.any(units<-127) or np.any(units>127):raise ValueError('checkpoint unit range')
    if state.dtype!=np.dtype('int'+str(contract['bits'])) or units.dtype!=np.int16 or history.dtype!=np.int32:raise ValueError('checkpoint physical dtype')
    if d['position']!=position or d['version']!=position or d['epoch']<0 or d['epoch']>(1<<32)-1:raise ValueError('checkpoint sequence/version/epoch')
    if d!=complete_checkpoint(state,units,history,d['epoch'],position,contract):raise ValueError('complete state/conv/units checkpoint mismatch')
    return state.copy(),units.copy(),history.copy(),int(d['epoch'])

def corrupted_checkpoint_negatives(d,state,units,history,position,contract):
    results=[]
    for name in ('state','units','conv','owner','epoch','position','version','contract'):
        dd=json.loads(json.dumps(d));s=state.copy();u=units.copy();c=history.copy()
        if name=='state':s.flat[0]^=1
        elif name=='units':u.flat[0]+=1
        elif name=='conv':c.flat[0]^=1
        elif name=='owner':dd['owner']='wrong.owner'
        elif name=='epoch':dd['epoch']+=1
        elif name=='position':dd['position']+=1
        elif name=='version':dd['version']+=1
        else:dd['contract']['compiled_manifest_sha256']='bad'
        try:restore(dd,s,u,c,position,contract)
        except ValueError:results.append({'tamper':name,'rejected':True})
        else:raise AssertionError('tampered checkpoint accepted: '+name)
    return results

def project_row(x,const,spec,ops):
    trace={};norm=fi.rmsnorm(x,const['input_gamma_q20'],spec['epsilon_q24'],ops);trace['input_norm_q12']=norm
    scaled=fi.cast_i32(fi.mul_q(norm,const['ssm_in_multiplier_q20'],20,ops));trace['mamba_input_q12']=scaled
    p,a,d,acc=fi.linear(scaled,const['in_weight_w8'],const['in_scale_q31'],const['in_scale_exp'],ops)
    p=fi.cast_i32(fi.checked_add(p,const['in_bias_q12'],ops));trace.update({'in_a8':a,'in_a8_delta':d,'in_acc32':acc,'in_linear_q12':p})
    p=fi.cast_i32(fi.mul_q(p,const['mup_q20'],20,ops));trace['projected_q12']=p
    return p,trace

def consumers(raw,gate,x,attention,const,spec,ops,counts):
    trace={};gated=fi.cast_i32(fi.mul_q(raw,fi.silu(gate,const['silu_lut_q12'],ops,counts),12,ops));trace['gated_q12']=gated
    norm=fi.rmsnorm(gated,const['gated_gamma_q20'],spec['epsilon_q24'],ops);trace['gated_norm_q12']=norm
    y,a,d,acc=fi.linear(norm,const['out_weight_w8'],const['out_scale_q31'],const['out_scale_exp'],ops)
    y=fi.cast_i32(fi.checked_add(y,const['out_bias_q12'],ops));trace.update({'out_a8':a,'out_a8_delta':d,'out_acc32':acc,'out_linear_q12':y})
    mamba=fi.cast_i32(fi.mul_q(y,const['ssm_out_multiplier_q20'],20,ops));attn=fi.cast_i32(fi.mul_q(attention,const['attention_out_multiplier_q20'],20,ops));trace['mamba_scaled_q12']=mamba;trace['attention_scaled_q12']=attn
    joined=fi.cast_i32(fi.checked_add(fi.checked_add(x,mamba,ops),attn,ops));trace['join_q12']=joined;trace['next_norm_q12']=fi.rmsnorm(joined,const['next_gamma_q20'],spec['epsilon_q24'],ops)
    return trace

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('compiled','baseline','binding','out'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--schedule',choices=('full','chunk8','chunk16','prefill64decode1'),required=True)
    a=ap.parse_args();started=time.time();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    bd=fc.binding(a);assert bd['falcon_resume_sha256']==fc.sha(__file__)
    src,_=fc.load_bound(a.compiled);base,_=fc.load_bound(a.baseline);baseline=json.loads((base/'report.json').read_text())
    if baseline['mode']!='full' or baseline['status']!='EXECUTED_COMPLETE':raise ValueError('complete full-chain baseline required')
    if baseline['compiled_manifest_sha256']!=fc.sha(src/'manifest.json'):raise ValueError('compiled baseline binding mismatch')
    spec=json.loads((src/'spec.json').read_text());const=dict(np.load(src/'constants.npz',allow_pickle=False));inputs=dict(np.load(src/'inputs.npz',allow_pickle=False));bit=baseline['state_bits'];policy=baseline['policy'];split=baseline['split'];x=inputs[split+'.input_q12'];attention=inputs[split+'.attention_q12']
    if x.shape[0]!=72 or split!='evaluation':raise ValueError('frozen qualification uses original72 eval tokens')
    contract={'compiled_manifest_sha256':fc.sha(src/'manifest.json'),'bits':bit,'policy':policy,'mode':'full','sequence':'Issue70.cal16/eval72','heads':spec['heads'],'dim':spec['head_dim'],'n':spec['state_size']}
    state=np.zeros((spec['heads'],spec['head_dim'],spec['state_size']),dtype='int'+str(bit));units=const['state_s%d_exponents'%bit].copy();history=np.zeros((spec['inner']+2*spec['state_size'],4),np.int32);epoch=0;position=0
    arrays={'input_q12':x,'external_attention_q12':attention};pieces={};transactions=[];checkpoint_arrays={};checkpoints=[];states_sha=[fi.array_sha(state)];units_trace=[units.copy()];ops=fi.Ops();counts={};rejection=None;published_sat=0
    boundaries={72}
    if a.schedule=='chunk8':boundaries.update(range(8,73,8))
    if a.schedule=='chunk16':boundaries.update(range(16,73,16))
    if a.schedule=='prefill64decode1':boundaries.update(range(64,73))
    for ti in range(72):
        before=complete_checkpoint(state,units,history,epoch,position,contract);private_ops=fi.Ops()
        p,tr=project_row(x[ti:ti+1],const,spec,private_ops)
        # Full conv history is a private candidate. Nothing is published until
        # R state AND every consumer through nextnorm have succeeded.
        coeff=fi.coefficients(p,const,spec,private_ops,initial_history=history)
        for k,v in coeff['counts'].items():counts[k]=counts.get(k,0)+v
        r_contract={'bits':bit,'policy':policy,'heads':spec['heads'],'dim':spec['head_dim'],'n':spec['state_size'],'injection':'dt20*B12_RNE12_then_x12_RNE(32+state_exp)','maximum_retries':8}
        resume={'state':state,'units':units,'epoch':epoch,'position':position,'checkpoint':fi.checkpoint(state,units,epoch,position,r_contract)}
        scan=fi.scan(coeff,units,const['skip_q20'],bit,policy,private_ops,chunk=0,resume=resume)
        private_ops.add('continuous_conv_trial_read_bytes',history.nbytes);private_ops.add('continuous_conv_trial_write_bytes',history.nbytes)
        private_ops.add('resume_state_read_bytes',state.nbytes);private_ops.add('resume_state_write_bytes',state.nbytes)
        tx={'token':ti,'before':before,'private_R_scope':'R local commits are private until branch_published true below','private_R_transactions':scan['transactions'],'private_R_rescale_events':scan['rescale_events'],'branch_published':False}
        if scan['committed']!=1:
            rejection={'token':ti,'reason':'private_R_rejected','detail':scan['rejection']};tx['after']=before;transactions.append(tx);ops.merge(private_ops.values);break
        try:
            downstream=consumers(scan['output_q12'],coeff['gate_q12'],x[ti:ti+1],attention[ti:ti+1],const,spec,private_ops,counts)
        except (OverflowError,ValueError) as exc:
            rejection={'token':ti,'reason':'consumer_guard','detail':str(exc)};tx['after']=before;transactions.append(tx);ops.merge(private_ops.values);break
        state=scan['final_state'];units=scan['units_trace'][-1].astype(np.int16);history=coeff['conv_history_final_q12'];epoch=scan['epoch'];position+=1;published_sat+=scan['saturations']
        units_trace.append(units.copy());states_sha.append(fi.array_sha(state));tr.update(downstream);tr['scan_q12']=scan['output_q12']
        for k,v in coeff.items():
            if k not in ('counts','conv_history_final_q12'):tr[k]=v
        for k,v in tr.items():pieces.setdefault(k,[]).append(v)
        tx['branch_published']=True;tx['after']=complete_checkpoint(state,units,history,epoch,position,contract);transactions.append(tx);ops.merge(private_ops.values)
        ops.add('atomic_branch_descriptor_bytes',64+units.nbytes);ops.add('conv_publish_bytes',history.nbytes)
        if position in boundaries:
            desc=tx['after'];checkpoints.append(desc);checkpoint_arrays['at%d.state'%position]=state.copy();checkpoint_arrays['at%d.units'%position]=units.copy();checkpoint_arrays['at%d.conv'%position]=history.copy()
            state,units,history,epoch=restore(desc,state,units,history,position,contract)
            # Serialization SHA/copies are qualification observers, not claimed
            # mandatory product cycles. Persistent state inventory is mandatory.
            ops.add('observer_checkpoint_read_bytes',state.nbytes+units.nbytes+history.nbytes)
            ops.add('observer_checkpoint_write_bytes',state.nbytes+units.nbytes+history.nbytes)
    for k,vs in pieces.items():arrays[k]=np.concatenate(vs,axis=0)
    arrays.update({'state_initial':np.zeros_like(state),'state_final':state,'state_units_trace':np.asarray(units_trace,np.int16),'conv_history_final_q12':history})
    reference=np.load(base/'runtime.npz',allow_pickle=False);comparisons=[]
    for k,v in arrays.items():
        if k not in reference.files:comparisons.append({'array':k,'status':'MISSING_BASELINE'});continue
        b=reference[k]
        match=v.dtype==b.dtype and v.shape==b.shape and np.array_equal(v,b)
        comparisons.append({'array':k,'equal':bool(match),'runtime_sha256':fi.array_sha(v),'baseline_sha256':fi.array_sha(b)})
    old_transactions=json.loads((base/'transactions.json').read_text())
    state_hash_equal=states_sha==old_transactions['state_sha256'];complete=position==72
    exact=complete and state_hash_equal and all(c.get('equal',False) for c in comparisons)
    final=complete_checkpoint(state,units,history,epoch,position,contract);negative=corrupted_checkpoint_negatives(final,state,units,history,position,contract)
    np.savez_compressed(out/'runtime.npz',**arrays);np.savez_compressed(out/'checkpoints.npz',**checkpoint_arrays)
    fc.put(out/'transactions.json',{'schema':'falcon-complete-causal-transactions-v1','contract':contract,'tokens':transactions,'state_sha256':states_sha,'checkpoints':checkpoints,'negatives':negative})
    fc.put(out/'report.json',{'schema':'falcon-complete-continuity-v1','status':'PASS_INTEGER_CONTINUITY' if exact else 'FAIL_INTEGER_CONTINUITY','schedule':a.schedule,'state_bits':bit,'policy':policy,'committed':position,'final_epoch':epoch,'rescale_events':sum(len(t.get('private_R_rescale_events',[])) for t in transactions),'published_state_saturations':published_sat,'rejection':rejection,'state_hashes_equal_to_frozen_baseline':state_hash_equal,'integer_arrays':comparisons,'all_integer_arrays_equal':exact,'ops':ops.values,'nonlinear_counts':counts,'inventory':{'conv_history_bytes':history.nbytes,'conv_old_plus_private_trial_bytes':2*history.nbytes,'state_bytes':state.nbytes,'state_old_plus_private_trial_bytes':2*state.nbytes,'unit_bytes':units.nbytes},'baseline_manifest_sha256':fc.sha(base/'manifest.json'),'compiled_manifest_sha256':fc.sha(src/'manifest.json'),'elapsed_seconds':time.time()-started,'limits':['Integer software qualification only; no FP reference loaded, no native INT8 speed/PPA or model quality claim.','Full conv and R state plus units/epoch/version/position are published atomically only after full downstream consumers succeeded.','A/residual are externally encoded cuts, MLP outside closure.','Checkpoint SHA/serialization observer cost is reported separately from mandatory persistent state/backing inventory.']})
    fc.seal(out,bd,'falcon-complete-continuity-v1',status='EXECUTED');print(json.dumps({'out':str(out),'status':'PASS' if exact else 'FAIL','committed':position,'manifest_sha256':fc.sha(out/'manifest.json')}))
if __name__=='__main__':main()
