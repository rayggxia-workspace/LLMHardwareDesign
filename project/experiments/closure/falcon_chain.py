"""Issue72 Falcon integer branch compiler/runtime; execute real data on server."""
import argparse, hashlib, json, math, platform, time
from pathlib import Path
import numpy as np
import falcon_int as fi

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def put(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def load_bound(directory):
    d=Path(directory);m=json.loads((d/'manifest.json').read_text())
    for a in m['artifacts']:
        p=d/a['path'];assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'],p
    return d,m
def seal(out,binding,schema,status='EXECUTED'):
    put(out/'manifest.json',{'schema':schema,'status':status,'source':binding,'producer_sha256':sha(__file__),'integer_source_sha256':sha(fi.__file__),'artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()]})
def binding(args):
    b=json.loads(Path(args.binding).read_text());assert b['falcon_chain_sha256']==sha(__file__) and b['falcon_int_sha256']==sha(fi.__file__);return b

def fp_encode(x,frac,dtype=np.int32):
    q=np.rint(np.asarray(x,np.float64)*(2.**frac))
    limit=np.iinfo(dtype)
    if not np.all(np.isfinite(q)) or q.min(initial=0)<limit.min or q.max(initial=0)>limit.max:raise OverflowError('offline fixed format boundary')
    return q.astype(dtype)
def weight_compile(w):
    w=np.asarray(w,np.float64);scale=np.max(np.abs(w),axis=1)/127
    scale=np.where(scale==0,1.,scale);codes=np.rint(w/scale[:,None]).clip(-127,127).astype(np.int8)
    mant,exp=np.frexp(scale);m=np.rint(mant*(1<<31)).astype(np.int64)
    carry=m==(1<<31);m[carry]>>=1;exp[carry]+=1
    return codes,m.astype(np.int32),exp.astype(np.int16),scale

def native_calibration(projected,cap,cfg):
    p=np.asarray(projected,np.float64);heads=int(cfg['mamba_n_heads']);dim=int(cfg['mamba_d_head']);n=int(cfg['mamba_d_state']);inner=heads*dim
    gate=p[:,:inner];v=p[:,inner:2*inner+2*n];rawdt=p[:,2*inner+2*n:]
    w=np.asarray(cap['weight.conv_weight'],np.float64).reshape(inner+2*n,4);bias=np.asarray(cap.get('weight.conv_bias',np.zeros(inner+2*n)),np.float64)
    history=np.zeros((inner+2*n,4));conv=[]
    for row in v:
        history[:,:-1]=history[:,1:];history[:,-1]=row;z=(history*w).sum(axis=1)+bias
        conv.append(z*np.exp(-np.logaddexp(0,-z)))
    conv=np.asarray(conv);x=conv[:,:inner].reshape(-1,heads,dim);b=conv[:,inner:inner+n];c=conv[:,inner+n:]
    limits=list(map(float,cfg['time_step_limit']));dt=np.clip(np.logaddexp(0,rawdt+cap['weight.dt_bias']),*limits);alpha=np.exp(-np.exp(cap['weight.A_log'])*dt)
    state=np.zeros((heads,dim,n));maxima=np.zeros(heads)
    for t in range(x.shape[0]):
        state=alpha[t,:,None,None]*state+dt[t,:,None,None]*x[t,:,:,None]*b[t,None,None,:]
        maxima=np.maximum(maxima,np.max(np.abs(state),axis=(1,2)))
    return maxima

def compile_model(args):
    started=time.time();out=Path(args.out);out.mkdir(parents=True,exist_ok=False);bd=binding(args);src,man=load_bound(args.capture)
    cfg=json.loads((src/'config.json').read_text());cap=dict(np.load(src/'capture.npz',allow_pickle=False))
    heads=int(cfg['mamba_n_heads']);dim=int(cfg['mamba_d_head']);n=int(cfg['mamba_d_state']);inner=heads*dim
    assert heads==32 and dim==128 and n==256 and not cfg['mamba_norm_before_gate'] and cfg['mamba_n_groups']==1
    data={};refs={}
    for split in ('calibration','evaluation'):
        for suffix in ('input','attention','projected'):
            data[split+'.'+suffix+'_q12']=fp_encode(cap[split+'.'+suffix],12)
        for suffix in ('input','norm','projected','raw_scan','scan_normed','mamba','pre_ff_input','next_norm_reference'):
            refs[split+'.'+suffix]=cap[split+'.'+suffix]
        data[split+'.tokens']=cap[split+'.tokens'].astype(np.int64)
    const={}
    for short,key,frac in (('input_gamma_q20','input_gamma',20),('next_gamma_q20','next_gamma',20),('gated_gamma_q20','gated_norm_gamma',20),('conv_weight_q20','conv_weight',20),('dt_bias_q12','dt_bias',12),('skip_q20','D',20),('mup_q20','mup_vector',20)):
        const[short]=fp_encode(cap['weight.'+key],frac).reshape(-1) if short!='conv_weight_q20' else fp_encode(cap['weight.'+key],frac).reshape(inner+2*n,4)
    const['conv_bias_q12']=fp_encode(cap.get('weight.conv_bias',np.zeros(inner+2*n)),12)
    constants_receipt={}
    for which in ('in','out'):
        q,m,e,s=weight_compile(cap['weight.'+which+'_weight']);const[which+'_weight_w8']=q;const[which+'_scale_q31']=m;const[which+'_scale_exp']=e
        const[which+'_bias_q12']=fp_encode(cap.get('weight.'+which+'_bias',np.zeros(q.shape[0])),12)
        constants_receipt[which]={'weight_shape':list(q.shape),'scale_granularity':'one per output row','floating_scale_min':float(s.min()),'floating_scale_max':float(s.max()),'compiled_q31_mantissa_exp':True}
    grid=np.arange(-8192,8193,dtype=np.float64)/256
    const['silu_lut_q12']=fp_encode(grid*np.exp(-np.logaddexp(0,-grid)),12)
    dt=np.clip(np.logaddexp(0,grid),*list(map(float,cfg['time_step_limit'])))
    const['dt_lut_q20']=np.repeat(fp_encode(dt,20)[None,:],heads,axis=0)
    a=np.exp(cap['weight.A_log'].astype(np.float64))
    const['alpha_lut_q31']=fp_encode(np.exp(-a[:,None]*dt[None,:]),31,np.uint32)
    maxima=native_calibration(cap['calibration.projected'],cap,cfg)
    for bits in (16,32):
        exps=np.ceil(np.log2(np.maximum(maxima,2.**-100)/((1<<(bits-1))-1))).astype(np.int16)
        if exps.min()<-127 or exps.max()>127:raise ValueError('calibration state exponent out of contract')
        const['state_s%d_exponents'%bits]=exps
    for key in ('ssm_in_multiplier','ssm_out_multiplier','attention_out_multiplier'):const[key+'_q20']=fp_encode(np.array(cfg[key]),20)
    np.savez_compressed(out/'inputs.npz',**data);np.savez_compressed(out/'constants.npz',**const);np.savez_compressed(out/'reference.npz',**refs)
    spec={'schema':'falcon-integer-closure-v1','source_capture_manifest_sha256':sha(src/'manifest.json'),'source_capture_npz_sha256':sha(src/'capture.npz'),'heads':heads,'head_dim':dim,'state_size':n,'inner':inner,'hidden':int(cfg['hidden_size']),'epsilon_q24':int(round(float(cfg['rms_norm_eps'])*(1<<24))),'data_format':{'storage':'I32','fraction':12},'gamma_mup_skip_format':{'storage':'I32','fraction':20},'dt_format':{'storage':'I32','fraction':20},'alpha_format':{'storage':'U32','fraction':31},'state_format':'S16 or S32 with one I16 power2 exponent/head,calibration16 only','state_calibration_tokens':16,'nonlinear_lut':{'domain_q12':[-(32<<12),32<<12],'step_q12':16,'entries':16385,'index':'RNE shift4 after clipped domain offset','silu_outside':'negative zero,positive identity','dt_outside':'clip; count, no claim original dt outside domain is preserved','rom_payload_bytes':sum(v.nbytes for k,v in const.items() if 'lut' in k)},'injection_contract':'dt20*B12_RNE12_to_dtB20_then_x12_RNE(32+state_exp)','linear_contract':'W8 per-output arbitrary scale represented Q31/I16 exponent; integer dynamic row A8 via minimal RNE rightshift, no float max/127; full K INT32 guard','norm_contract':'complete group sumsq U128; floor variance/N + epsilon_q24; denominator=isqrt(variance<<40); RNE signed division (x_q12*gamma_q20<<12)/denominator; output I32Q12','arithmetic_contract':'I64 checked conservative guards for products/sums, I128 guarded norm. Python div/isqrt are software definitions with restoring iteration costs, not free hardware SFU. Radix128 lowdigits0..127/highest signed8 use digits=1 for width<=8 else 1+ceil((width-8)/7); S8 products plus explicit wide shift-add with signed highest digit. U128 restoring divide uses128 iterations and isqrt64, no free SFU.','external_cut':'layer0 true residual/input and native A output encoded once to I32Q12; A/MLP not integer-closed here. boundary to full true pre_ff_layernorm output only.','state_guard':{'maximum_retries':8,'minimum_exponent':-127,'maximum_exponent':127,'epoch_bits':32,'token_atomic_publish':True},'weight_compilation':constants_receipt,'calibration_state_maxima':maxima.tolist(),'runtime_no_float':True}
    put(out/'spec.json',spec)
    put(out/'compiler.json',{'status':'COMPILED_NOT_EXECUTED','calibration_source':'Issue70 calibration16 only; no eval state/max/error in exponent selection','offline_fp_allowed':'native calibration maxima, static BF16 weight/scales/constants and LUT generation only; evaluation FP used solely fixed-format external cut encoding and post-run references','constant_arrays':[{'name':k,'dtype':str(v.dtype),'shape':list(v.shape),'bytes':v.nbytes,'array_sha256':fi.array_sha(v)} for k,v in const.items()],'elapsed_seconds':time.time()-started})
    seal(out,bd,'falcon-integer-compiler-v1');print(json.dumps({'out':str(out),'manifest_sha256':sha(out/'manifest.json')}))

def metric(a,r):
    a=np.asarray(a,np.float64);r=np.asarray(r,np.float64);d=a-r
    return {'relative_l2':float(np.linalg.norm(d.ravel())/max(np.linalg.norm(r.ravel()),1e-30)),'max_abs':float(np.max(np.abs(d),initial=0))}

def run_model(args):
    started=time.time();out=Path(args.out);out.mkdir(parents=True,exist_ok=False);bd=binding(args);src,man=load_bound(args.compiled)
    spec=json.loads((src/'spec.json').read_text());const=dict(np.load(src/'constants.npz',allow_pickle=False));inp=dict(np.load(src/'inputs.npz',allow_pickle=False));ops=fi.Ops();trace={};split=args.split
    for k,v in const.items():fi.require_int(v)
    x=inp[split+'.input_q12'];attention=inp[split+'.attention_q12'];trace['input_q12']=x;trace['external_attention_q12']=attention
    if args.mode=='full':
        norm=fi.rmsnorm(x,const['input_gamma_q20'],spec['epsilon_q24'],ops);trace['input_norm_q12']=norm
        scaled=fi.cast_i32(fi.mul_q(norm,const['ssm_in_multiplier_q20'],20,ops));trace['mamba_input_q12']=scaled
        projected,a8,delta,acc=fi.linear(scaled,const['in_weight_w8'],const['in_scale_q31'],const['in_scale_exp'],ops)
        projected=fi.cast_i32(fi.checked_add(projected,const['in_bias_q12'],ops));trace.update({'in_a8':a8,'in_a8_delta':delta,'in_acc32':acc,'in_linear_q12':projected})
        projected=fi.cast_i32(fi.mul_q(projected,const['mup_q20'],20,ops))
    else:projected=inp[split+'.projected_q12'];trace['external_native_projected_q12']=projected
    trace['projected_q12']=projected;coeff=fi.coefficients(projected,const,spec,ops)
    for k,v in coeff.items():
        if k!='counts':trace[k]=v
    initial_units=const['state_s%d_exponents'%args.bits]
    scan=fi.scan(coeff,initial_units,const['skip_q20'],args.bits,args.policy,ops,chunk=args.chunk)
    count=scan['committed'];trace.update({'state_initial':scan['initial_state'],'state_final':scan['final_state'],'state_units_trace':scan['units_trace'],'scan_q12':scan['output_q12']})
    if count:
        gated=fi.cast_i32(fi.mul_q(trace['scan_q12'],fi.silu(coeff['gate_q12'][:count],const['silu_lut_q12'],ops,coeff['counts']),12,ops));trace['gated_q12']=gated
        normed=fi.rmsnorm(gated,const['gated_gamma_q20'],spec['epsilon_q24'],ops);trace['gated_norm_q12']=normed
        y,a8,delta,acc=fi.linear(normed,const['out_weight_w8'],const['out_scale_q31'],const['out_scale_exp'],ops)
        y=fi.cast_i32(fi.checked_add(y,const['out_bias_q12'],ops));trace.update({'out_a8':a8,'out_a8_delta':delta,'out_acc32':acc,'out_linear_q12':y})
        mamba=fi.cast_i32(fi.mul_q(y,const['ssm_out_multiplier_q20'],20,ops));attn=fi.cast_i32(fi.mul_q(attention[:count],const['attention_out_multiplier_q20'],20,ops));trace['mamba_scaled_q12']=mamba;trace['attention_scaled_q12']=attn
        join=fi.cast_i32(fi.checked_add(fi.checked_add(x[:count],mamba,ops),attn,ops));trace['join_q12']=join
        trace['next_norm_q12']=fi.rmsnorm(join,const['next_gamma_q20'],spec['epsilon_q24'],ops)
    np.savez_compressed(out/'runtime.npz',**trace)
    put(out/'transactions.json',{'schema':'falcon-causal-transactions-v1','contract':scan['contract'],'state_sha256':scan['state_sha256'],'tokens':scan['transactions'],'rescale_events':scan['rescale_events'],'checkpoints':scan['checkpoints']})
    # Float reference becomes visible only after complete integer execution.
    refs=np.load(src/'reference.npz',allow_pickle=False);errors={}
    mapping={'input_norm_q12':'norm','projected_q12':'projected','scan_q12':'raw_scan','gated_norm_q12':'scan_normed','out_linear_q12':'mamba','join_q12':'pre_ff_input','next_norm_q12':'next_norm_reference'}
    for k,v in mapping.items():
        if k in trace:errors[k]=metric(trace[k].astype(np.float64)/(1<<12),refs[split+'.'+v][:trace[k].shape[0]])
    report={'schema':'falcon-integer-closure-v1','status':'EXECUTED_COMPLETE' if count==x.shape[0] else 'EXECUTED_REJECTED_PREFIX','mode':args.mode,'state_bits':args.bits,'policy':args.policy,'split':split,'input_tokens':x.shape[0],'committed_tokens':count,'published_state_saturations':scan['saturations'],'rejection':scan['rejection'],'rescale_events':len(scan['rescale_events']),'final_epoch':scan['epoch'],'integer_chain':'external I32Q12 hidden -> full integer RMSNorm -> complete W8A8 in_proj -> integer MuP/RQ -> complete depthwise conv/SiLU -> integer dt/alpha LUT -> all32heads integer Mamba2 -> full4096 gate-before-RMSNorm -> complete W8A8 out_proj -> external A + residual + R -> fullH2560 nextnorm' if args.mode=='full' else 'external native projected I32Q12 cut -> complete integer conv/nonlinear/all32head R/full consumers; in_proj bypass diagnostic','nonlinear_counts':coeff['counts'],'reference_errors':errors,'ops':ops.values,'actual_payload':{'runtime_npz_bytes':(out/'runtime.npz').stat().st_size,'constant_payload_bytes':sum(v.nbytes for v in const.values()),'lut_rom_payload_bytes':spec['nonlinear_lut']['rom_payload_bytes'],'initial_state_bytes':trace['state_initial'].nbytes,'state_units_bytes':initial_units.nbytes},'limitations':['Integer software reference, no real INT8 speed/RTL/PPA/model application quality acceptance.','Input/residual and native attention externally encoded; MLP and attention not integer-closed.','Local errors only; static_sat is diagnostic and saturation is retained.','Dynamic scales use only current integer rows/state guards; no future/native-state eval scale selection.'],'environment':{'python':platform.python_version(),'numpy':np.__version__},'elapsed_seconds':time.time()-started,'compiled_manifest_sha256':sha(src/'manifest.json')}
    put(out/'report.json',report);seal(out,bd,'falcon-integer-closure-run-v1');print(json.dumps({'out':str(out),'committed':count,'saturations':scan['saturations'],'rescale_events':len(scan['rescale_events']),'manifest_sha256':sha(out/'manifest.json')}))

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('compile');p.add_argument('--capture',required=True)
    p2=sub.add_parser('run');p2.add_argument('--compiled',required=True);p2.add_argument('--mode',choices=('state','full'),required=True);p2.add_argument('--bits',type=int,choices=(16,32),required=True);p2.add_argument('--policy',choices=('static_sat','static_guard','guard_rescale'),required=True);p2.add_argument('--split',choices=('calibration','evaluation'),default='evaluation');p2.add_argument('--chunk',type=int,choices=(0,8,16),default=8)
    for p in (p,p2):
        p.add_argument('--out',required=True);p.add_argument('--binding',required=True)
    a=ap.parse_args();compile_model(a) if a.command=='compile' else run_model(a)
if __name__=='__main__':main()
