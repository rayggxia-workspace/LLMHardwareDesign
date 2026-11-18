"""Measured arithmetic increments plus explicitly assumed operation-level scenarios.

No claim of numerical RTL equivalence or confidence bounds for floating services.
Frozen latency/DDR remain unchanged. Existing G32 and SRAM work are not added twice.
"""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from six_model_tlm_power import metrics

HERE=Path(__file__).resolve().parent
MODELS=('qwen3','llama','granite','phi','gemma','qwen35','falcon')
IDS={38828362:'llama',38828902:'granite',38828903:'phi',38828904:'gemma',38828905:'qwen35',38828906:'falcon',38828968:'qwen3',
     38830188:'llama',38830189:'granite',38830190:'phi',38830191:'gemma',38830192:'qwen35',38830193:'falcon',38838045:'qwen3'}
N_IDS={38828633:'llama',38828634:'llama',38828998:'granite',38828999:'granite',38829000:'phi',38829001:'phi',
       38829002:'gemma',38829003:'gemma',38829004:'qwen35',38829005:'qwen35',38829006:'falcon',38829007:'falcon',38829008:'qwen3',38829009:'qwen3'}
def load(p):return json.loads(p.read_bytes())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def bounds(xs):
    xs=list(xs)
    if not xs or min(xs)<0:raise ValueError('missing/negative calibration')
    return [min(xs),max(xs)]
def add(a,b):return [x+y for x,y in zip(a,b)]
def scale(a,n):return [x*n for x in a]
def model_of(path):
    names={name for job,name in IDS.items() if str(job) in path}
    if len(names)!=1:raise ValueError('unknown capture '+path)
    return names.pop()

def calibrations():
    values=defaultdict(list);idle=defaultdict(list);mul=[];sources={};chunks=defaultdict(list)
    for p in sorted((HERE/'arithmetic-calibration-results').glob('*-calibration.json')):
        d=load(p);sources[p.name]=digest(p)
        if d.get('wire_parasitics_loaded') or d.get('timing_signoff'):raise ValueError('wrong calibration scope')
        if p.name.startswith('power-'):
            for s in d['samples']:
                mul.append(s['incremental_nj']/(4*s['packets']))
                idle['e32'].append(s['power']['idle']['power_w']['total'])
            continue
        if p.name.startswith('n-'):
            model=N_IDS[int(p.name.split('-')[1])]
            for s in d['samples']:
                values[(model,'n',s['signature'])].append(s['incremental_nj'])
                idle['n'].append(s['power']['idle']['power_w']['total'])
            continue
        kind=d['kind']
        if kind=='apply':continue
        for s in d['samples']:
            model=model_of(s['capture']);idle[kind].append(s['components']['dut']['power']['idle']['power_w']['total'])
            if kind=='apply_chunked':chunks[(model,s['capture'],s['sample_index'],s['signature'])].append(s)
            else:values[(model,kind,s['signature'])].append(s['incremental_nj'])
    for (model,capture,index,sig),parts in chunks.items():
        parts.sort(key=lambda s:s['shape']['chunk_offset_words']);offset=0;total=0
        for s in parts:
            if s['shape']['chunk_offset_words']!=offset:raise ValueError('missing/overlapping chunk')
            offset+=s['shape']['words'];total+=s['incremental_nj']
        if offset!=parts[0]['shape']['original_words']:raise ValueError('incomplete RMS vector')
        values[(model,'apply_chunked',sig)].append(total)
    if not chunks:raise ValueError('full-vector chunk calibration required')
    return {k:bounds(v) for k,v in values.items()},{k:bounds(v) for k,v in idle.items()},bounds(mul),sources

def operations(kind,sh,inputs):
    """Scalar arithmetic counts for the frozen service, not its timing model."""
    n=sh.get('elements',0)
    if kind in ('scale','scaled_silu'):return n,0,0,0
    if kind=='silu':return 0,0,0,0 # Already in v2 G32 term.
    if kind=='expert_sum':return n,n,0,0
    if kind=='gelu':return 7*n,2*n,n,0 # x^3, polynomial, half/gate/up, one tanh.
    if kind=='sigmoid':return n,n,n,n
    if kind=='conv4':return 4*sh['channels'],3*sh['channels'],0,0
    if kind in ('gdn_state','mamba_state'):
        c,d=sh['count'],sh['depth']
        return (4*c*d+c,3*c*d-c,0,0) if kind=='gdn_state' else (3*c*d+2*c,2*c*d,0,0)
    if kind=='router':
        e,k=sh['experts'],sh['top']
        # Insertion top-k upper work estimate: e*k scalar compare/select equivalents.
        return 0,e*k+2*k,k,k
    if kind=='recurrent_factors':
        n=inputs['a_log'][0]
        # a scaling, softplus, exp(a_log), exp(-exp(a_log)*delta), optional sigmoid.
        return 2*n,2*n,5*n if sh['gdn'] else 4*n,n if sh['gdn'] else 0
    if kind=='recurrent_norm_gate':
        n=inputs['value'][0]
        # SiLU gate and value multiply; GDN also squares/mean/rsqrt/gamma.
        return (5*n,2*n,n,n+32) if sh['gdn'] else (2*n,n,n,n)
    raise ValueError('unaccounted operator '+kind)

def integrate(model,values,idle,mul,sources):
    baseline=HERE/(model+'_tlm_power_v2_no_wire.json');b=load(baseline)
    countfile=HERE/'arithmetic-model-counts'/(model+'.json');counts=load(countfile)
    coef=load(HERE/'no-wire-results/coefficients.json');plus=coef['u_add_nj_per_word']/4
    result=dict(model=b['model'],scope='Conditional arithmetic-completed estimate; not complete physical-chip power',
                target_clock_mhz=300,sram_bits=512,wire_parasitics_loaded=False,rtl_special_numeric_accepted=False,
                estimator_sha256=digest(Path(__file__)),
                metrics_module_sha256=digest(HERE/'six_model_tlm_power.py'),
                reference_coefficients_sha256=digest(HERE/'no-wire-results/coefficients.json'),
                baseline_sha256=digest(baseline),counts_sha256=digest(countfile),calibration_sha256=sources,windows={},
                assumptions=[
                 'Existing v2 terms, DDR and frozen token times are preserved. SiLU/G32 and original SRAM transactions are already counted.',
                 'RMS uses N + scan + chunked apply; apply contains E32. RoPE contains its E32. Neither adds standalone E32 again.',
                 'Native activity ranges are sampled endpoints, not statistical confidence intervals.',
                 'Unbound arithmetic uses E32 S32 product and U ADD2 scalar energy as proxies; floating arithmetic transfer multiplier is an assumed 0.5x to 2x sensitivity.',
                 'Each EXP/tanh/softplus proxy assumes 4 to 12 multiply-plus-add stages; reciprocal/rsqrt assumes 4 to 16 such stages. These are cost scenarios, not verified approximations or error guarantees.',
                 'Router compare/select uses an ADD2 energy proxy and e*k work count; sorting implementation is not synthesized.',
                 'Additional arithmetic idle sensitivity: zero with ideal gating to 4 E32 + 4 RMS N + 4 scan + 4 apply wrappers + 1 RoPE wrapper + 1 softmax module, each counted once. This is a conditional common footprint, not a frozen deployment.',
                 'Large-vector staging sensitivity: zero additional copies to two 128-bit reads plus two writes per RMS word. Existing TLM SRAM work is not re-added.',
                 'FP32/RTL equivalence, overflow, revised timing and model accuracy are unverified for proxies. Energy scenarios do not fix the E32 9/18-cycle schedule discrepancy.'],
                not_included=[x for x in b['not_included'] if not ('RMS/normalization' in x)]+[
                 'Physical placement/routing, actual global clock/interconnect implementation and unmatched control/PHY remain outside the existing coverage.',
                 'Special arithmetic now has operation-level sensitivity estimates, not matched RTL energy or numerical acceptance.'])
    for window,old in b['windows'].items():
        phase=counts['phases']['prefill' if window=='prefill' else 'decode'];terms={};audit=[];stage=0
        def append(key,value):terms[key]=add(terms.get(key,[0.,0.]),value)
        for sig,n in phase['rms_counts'].items():
            if sig.split(':')[0]!=window:continue
            for kind in ('n','scan','apply_chunked'):
                append('rms_'+kind,scale(values[(model,kind,sig)],n))
            words=int(sig.split(':words')[1].split(':')[0])
            if words>512:stage+=2*words*n*(coef['sram_access_nj']['read128']+coef['sram_access_nj']['write128'])
        for sig,n in phase['operator_counts'].items():
            if sig.split(':')[0]!=window:continue
            spec=phase['operator_shapes'][sig];kind=spec['kind']
            if kind in ('softmax','rope','rope_native'):
                append('measured_'+('rope' if kind.startswith('rope') else kind),scale(values[(model,'rope' if kind.startswith('rope') else kind,sig)],n));continue
            m,a,t,r=operations(kind,spec['shape'],spec['input_shapes'])
            low=.5*((m+4*t+4*r)*mul[0]+(a+4*t+4*r)*plus)
            high=2*((m+12*t+16*r)*mul[1]+(a+12*t+16*r)*plus)
            append('proxy_'+kind,[low*n,high*n]);audit.append(dict(signature=sig,calls=n,multiply=m,add_compare=a,transcendental=t,reciprocal_sqrt=r))
        residency=sum(idle[k][1]*n for k,n in [('e32',4),('n',4),('scan',4),('apply_chunked',4),('rope',1),('softmax',1)])*old['elapsed_ps']/1000
        terms['arithmetic_idle_sensitivity']=[0.,residency];terms['chunk_staging_sensitivity']=[0.,stage]
        delta=[sum(v[i] for v in terms.values()) for i in (0,1)]
        chip=add(old['covered_on_chip_subtotal']['energy_nj_per_window'],delta)
        total=add(old['covered_subtotal']['energy_nj_per_window'],delta)
        ps,tokens=old['elapsed_ps'],old['tokens']
        result['windows'][window]=dict(elapsed_ps=ps,tokens=tokens,tokens_per_second=old['tokens_per_second'],
            previous_on_chip=old['covered_on_chip_subtotal'],previous_on_chip_plus_ddr=old['covered_subtotal'],
            arithmetic_components={k:metrics(v,ps,tokens) for k,v in terms.items()},
            arithmetic_increment=metrics(delta,ps,tokens),estimated_on_chip=metrics(chip,ps,tokens),
            estimated_on_chip_plus_ddr=metrics(total,ps,tokens),ddr=old['components']['ddr_devices'],operation_audit=audit)
        result['windows'][window]['read_dma_sensitivity']={}
        for label,s in old.get('read_dma_dynamic_sensitivity',{}).items():
            proxy=s['read_dma_active_proxy']['energy_nj_per_window']
            result['windows'][window]['read_dma_sensitivity'][label]=dict(
                read_dma_active_proxy=s['read_dma_active_proxy'],
                estimated_on_chip=metrics(add(chip,proxy),ps,tokens),
                estimated_on_chip_plus_ddr=metrics(add(total,proxy),ps,tokens))
    return result

if __name__=='__main__':
    values,idle,mul,sources=calibrations()
    for model in sys.argv[1:] or MODELS:
        result=integrate(model,values,idle,mul,sources)
        (HERE/(model+'_tlm_power_v3_arithmetic.json')).write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())
        print('ARITHMETIC_ESTIMATE_PASS',model,result['windows']['decode']['estimated_on_chip_plus_ddr']['energy_mj_per_token'])
