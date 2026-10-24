"""Independent Issue64 integer-attention receiver; no producer imports.

Checks captured integer-path arithmetic and diagnostics, not model quality,
target implementation, cycle performance, RTL or PPA.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tempfile
import time
import traceback

import numpy as np

I32_MIN, I32_MAX = -(1 << 31), (1 << 31) - 1
I64_MIN, I64_MAX = -(1 << 63), (1 << 63) - 1
U64_MAX = (1 << 64) - 1
SAMPLES = ('qwen25.prefix128.l0.kv16.lut128', 'gemma.prefix4096.l0.kv16.lut128')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def bytes_equal(first, second):
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open('rb') as f, second.open('rb') as g:
        while True:
            a, b = f.read(8 << 20), g.read(8 << 20)
            if a != b:
                return False
            if not a:
                return True


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def equal(got, wanted, label):
    if not np.array_equal(got, wanted):
        where = np.argwhere(np.asarray(got) != np.asarray(wanted))
        first = tuple(where[0]) if len(where) else None
        detail = '' if first is None else ': first=' + str(first) + ', got=' + str(got[first]) + ', wanted=' + str(wanted[first])
        raise AssertionError(label + detail)


def check_float(got, wanted, label):
    if not (np.isfinite(got) and np.isfinite(wanted)) or abs(float(got) - float(wanted)) > 1e-12:
        raise AssertionError(label + ': got=' + repr(got) + ', wanted=' + repr(wanted))


def div_even_u64(numerator, denominator):
    """Exact unsigned quotient/remainder RNE; avoids doubled-remainder overflow."""
    n, d = np.asarray(numerator), np.asarray(denominator)
    if n.dtype != np.dtype('uint64') or d.dtype != np.dtype('uint64'):
        raise TypeError('U64 divider requires explicit uint64 operands')
    if np.any(d == 0):
        raise ZeroDivisionError('zero normalization sum')
    q, r = np.divmod(n, d)
    complement = d - r
    up = (r > complement) | ((r == complement) & ((q & np.uint64(1)) != 0))
    if np.any(up & (q == np.uint64(U64_MAX))):
        raise OverflowError('RNE quotient exceeds U64')
    return q + up.astype(np.uint64)


def decimal_lut(grid):
    if grid not in (128, 256):
        raise ValueError('unsupported frozen grid')
    with localcontext() as ctx:
        ctx.prec = 50
        return np.asarray([int(((-Decimal(i) / Decimal(grid)).exp() * Decimal(1 << 30)).to_integral_value(rounding=ROUND_HALF_EVEN))
                           for i in range(16 * grid + 1)], dtype='<u4')


def scores_from_dot(dot, qexp, kexp, multiplier):
    """All-value vectorized integer oracle plus separate Fraction samples."""
    if not 0 < int(multiplier) < 1 << 32:
        raise ValueError('score multiplier outside U32')
    qexp = np.asarray(qexp)
    if qexp.shape != dot.shape[:-1]:
        raise ValueError('query exponent shape')
    result = np.empty(dot.shape, dtype=np.int64)
    witnesses = 0
    for h, row in np.ndindex(dot.shape[:-1]):
        values = dot[h, row].astype(np.int64)
        minimum, maximum = int(values.min()) * int(multiplier), int(values.max()) * int(multiplier)
        if minimum < I64_MIN or maximum > I64_MAX:
            raise OverflowError('independent S64 score product')
        product = values * np.int64(multiplier)
        shift = 18 - int(qexp[h, row]) - int(kexp)
        if not -63 <= shift <= 63:
            raise ValueError('score shift outside declared domain')
        if shift > 0:
            positive = np.abs(product).astype(np.uint64)
            denom = np.asarray(np.uint64(1) << np.uint64(shift), dtype=np.uint64)
            quotient = div_even_u64(positive, denom).astype(np.int64)
            converted = np.where(product < 0, -quotient, quotient)
        elif shift == 0:
            converted = product
        else:
            if minimum << -shift < I32_MIN or maximum << -shift > I32_MAX:
                raise OverflowError('left score shift outside S32')
            converted = product * np.int64(1 << -shift) if shift > -63 else np.zeros(product.shape, dtype=np.int64)
        if int(converted.min()) < I32_MIN or int(converted.max()) > I32_MAX:
            raise OverflowError('independent S32Q12 score')
        result[h, row] = converted
        # First/middle/last/max signed dot; max-score sample is added by caller.
        selected = {0, len(values)//2, len(values)-1, int(np.argmax(values))}
        for j in selected:
            value = Fraction(int(values[j]) * int(multiplier)) * Fraction(2) ** (-shift)
            if round(value) != int(converted[j]):
                raise AssertionError('independent Fraction score witness')
            witnesses += 1
    return result, witnesses


def normalize_from_scores(scores, mask, grid, lut):
    """Rebuild LUT addresses/exponents/sums/P15 directly from scores and mask."""
    scores, mask = np.asarray(scores), np.asarray(mask)
    if scores.dtype != np.dtype('int32') or mask.dtype != np.dtype('bool'):
        raise TypeError('S32Q12 and boolean mask required')
    if scores.ndim != 3 or mask.shape != scores.shape[1:] or np.any(mask.sum(-1) == 0):
        raise ValueError('legal nonempty masked attention rows required')
    if lut.dtype != np.dtype('uint32') or lut.shape != (16 * grid + 1,):
        raise ValueError('LUT domain/type')
    top = np.where(mask[None], scores, I32_MIN).max(-1)
    distance = top[:, :, None].astype(np.int64) - scores.astype(np.int64)
    eligible = mask[None] & (distance <= 65536)
    # Distances of masked elements may be negative; they never address a used ROM entry.
    distance = np.maximum(distance, 0)
    width = 4096 // grid
    address, rem = np.divmod(distance, width)
    address = address + ((rem > width-rem) | ((rem == width-rem) & ((address & 1) != 0)))
    address = np.clip(address, 0, 16*grid)
    exponents = np.where(eligible, lut[address], 0).astype(np.uint32)
    if scores.shape[-1] * (1 << 30) > U64_MAX:
        raise OverflowError('exp sum format bound')
    sums = exponents.sum(-1, dtype=np.uint64)
    if np.any(sums < 1 << 30):
        raise AssertionError('every valid query retains maximum exp')
    p = np.minimum(div_even_u64(exponents.astype(np.uint64) * np.uint64(32768), sums[:, :, None]), 32767).astype(np.int16)
    active = mask.sum(-1, dtype=np.int64)
    if int(active.max()) * 32767 > (1 << 32)-1:
        raise OverflowError('U32 probability counter format bound')
    budget = 32769 + (active+1)//2
    psum = p.sum(-1, dtype=np.uint64)
    if np.any(psum > budget[None]) or np.any(p[:, ~mask]):
        raise AssertionError('P-sum/masking invariant')
    statistics = {'maximum_exp_sum_U64': int(sums.max()), 'maximum_P_sum_U32': int(psum.max()),
                  'maximum_P_sum_budget': int(budget.max()), 'masked_nonzero_count': 0,
                  'truncated_active_exp_count': int(np.count_nonzero(mask[None] & ~eligible)),
                  'LUT_reads': int(np.count_nonzero(eligible)), 'U64_sum_terms': int(exponents.size),
                  'U64_divisions_RNE': int(exponents.size), 'U32_Psum_add_terms': int(p.size),
                  'P15_saturation_at32768_count': int(np.count_nonzero((exponents.astype(np.uint64)*np.uint64(32768))//sums[:, :, None] >= 32768))}
    return p, exponents, sums, budget, statistics


def metric(value, reference):
    difference = np.asarray(value, dtype=np.float64) - np.asarray(reference, dtype=np.float64)
    return {'relative_rmse': float(np.linalg.norm(difference) / max(float(np.linalg.norm(np.asarray(reference, dtype=np.float64))), 1e-30)),
            'max_abs': float(np.max(np.abs(difference)))}


def verify_case(path, record, lut, totals):
    with np.load(path, allow_pickle=False) as z:
        a = {key: z[key] for key in z.files}
    q, qe, k, v = (a[key] for key in ('Q8', 'Qe', 'K', 'V'))
    for key,dtype in [('scoreQ12','int32'),('mask','bool'),('expQ30','uint32'),('exp_sum_U64','uint64'),('Psum_budget','int64')]:
        if a[key].dtype != np.dtype(dtype):raise TypeError('stored '+key+' dtype')
    if q.dtype != np.dtype('int8') or qe.dtype != np.dtype('int8') or a['QK32'].dtype != np.dtype('int32'):
        raise TypeError('Q/Qe/QK dtype')
    want_dtype = np.dtype('int8' if record['KV_bits']==8 else 'int16')
    if k.dtype != want_dtype or v.dtype != want_dtype or a['P15'].dtype != np.dtype('int16') or a['PV32'].dtype != np.dtype('int32'):
        raise TypeError('KV/P/PV dtype')
    if record['KV_bits'] not in (8,16) or np.any(np.abs(q.astype(np.int64))>127):
        raise ValueError('Q8 symmetric code domain')
    maximum = (1 << (record['KV_bits']-1))-1
    if np.any(np.abs(k.astype(np.int64))>maximum) or np.any(np.abs(v.astype(np.int64))>maximum):
        raise ValueError('KV symmetric code domain')
    positions = np.asarray(record['positions'], dtype=np.int64)
    equal(a['positions'], positions, 'saved query positions')
    if q.shape != (record['GQA_Q_heads'],len(positions),record['head_dim']) or k.shape != (record['keys'],record['head_dim']) or v.shape != k.shape:
        raise ValueError('complete GQA case dimensions')
    if np.any(positions<0) or np.any(positions>=len(k)) or np.any(np.diff(positions)<=0):
        raise ValueError('query position bounds/order')
    mask = np.arange(len(k))[None,:] <= positions[:,None]
    if record['window']:
        mask &= np.arange(len(k))[None,:] > positions[:,None]-int(record['window'])
    equal(a['mask'],mask,'actual causal/local mask')
    dot = q.astype(np.int64) @ k.astype(np.int64).T
    if int(dot.min())<I32_MIN or int(dot.max())>I32_MAX:
        raise OverflowError('QK outside S32')
    equal(a['QK32'],dot,'complete QK I64 oracle')
    totals['QK_I64_values'] += int(dot.size)
    scaling = float.fromhex(record['score_scale']['source_float_hex'])
    multiplier = int(record['score_scale']['multiplier'])
    if multiplier != round(Fraction.from_float(scaling)*(1 << 30)):
        raise AssertionError('offline score multiplier')
    score, witnesses = scores_from_dot(dot,qe,int(record['K_exponent']),multiplier)
    equal(a['scoreQ12'],score,'complete integer score conversion')
    totals['score_integer_values'] += int(score.size)
    totals['score_Fraction_witnesses'] += witnesses
    # Explicit max among legal keys, even where a masked future dot is larger.
    for h,row in np.ndindex(dot.shape[:-1]):
        j=int(np.argmax(np.where(mask[row],dot[h,row],I64_MIN)))
        wanted=round(Fraction(int(dot[h,row,j])*multiplier)*Fraction(2)**(int(qe[h,row])+int(record['K_exponent'])-18))
        if wanted != int(a['scoreQ12'][h,row,j]):
            raise AssertionError('Fraction score legal-max witness')
        totals['score_Fraction_witnesses']+=1
    p,exp,sums,budget,stats = normalize_from_scores(a['scoreQ12'],mask,int(record['LUT_grid']),lut)
    equal(a['expQ30'],exp,'scores/mask/Decimal-validated LUT exponent reconstruction')
    equal(a['exp_sum_U64'],sums,'independent U64 exp sum')
    equal(a['Psum_budget'],budget,'active-length normalized probability budget')
    # This second divider uses stored exp/sum directly as a separate receipt boundary.
    from_stored=np.minimum(div_even_u64(a['expQ30'].astype(np.uint64)*np.uint64(32768),a['exp_sum_U64'][:,:,None]),32767).astype(np.int16)
    equal(a['P15'],from_stored,'all stored exponent/sum -> P15 quotient/remainder RNE')
    equal(a['P15'],p,'all reconstructed exponent/sum -> P15')
    totals['exp_and_P15_values'] += int(p.size)
    for name,value in stats.items():
        if record['operations']['softmax'][name] != value:
            raise AssertionError('reported softmax statistic '+name)
    pv=p.astype(np.int64) @ v.astype(np.int64)
    if int(pv.min())<I32_MIN or int(pv.max())>I32_MAX:
        raise OverflowError('PV32 range')
    equal(a['PV32'],pv,'complete PV I64 oracle')
    totals['PV_I64_values'] += int(pv.size)
    exact=dot.astype(np.float64)*np.exp2(qe.astype(np.float64)+int(record['K_exponent']))[:,:,None]*scaling
    exact_masked=np.where(mask[None],exact,-np.inf)
    prob=np.exp(exact_masked-exact_masked.max(-1,keepdims=True));prob/=prob.sum(-1,keepdims=True)
    fp_p=np.clip(np.rint(prob*32768),0,32767).astype(np.int16)
    equal(a['P15_FP64_softmax_reference'],fp_p,'independent FP64 same-coded-input P15 diagnostic')
    fp_pv=(fp_p.astype(np.int64)@v.astype(np.int64)).astype(np.float64)*2.**(int(record['V_exponent'])-15)
    if not np.allclose(a['PV_FP64_softmax_reference'],fp_pv,rtol=0,atol=1e-12):
        raise AssertionError('saved FP64 same-KV output diagnostic')
    converted=pv.astype(np.float64)*2.**(int(record['V_exponent'])-15)
    diagnostics={'integer_output_vs_native':metric(converted,a['native_reference']),
       'FP64_same_encoded_KV_P15_output_vs_native':metric(fp_pv,a['native_reference']),
       'integer_output_vs_FP64_same_encoded_KV_P15':metric(converted,fp_pv)}
    for name,result in diagnostics.items():
        for field,value in result.items():check_float(record[name][field],value,name+'.'+field)
    mismatch=int(np.count_nonzero(p!=fp_p))
    if mismatch != record['P15_code_mismatches_vs_FP64_softmax']:
        raise AssertionError('FP64 softmax probability mismatch count')
    score_error=np.abs(a['scoreQ12'].astype(np.float64)*2.**-12-exact)
    check_float(record['score_q12_vs_exact_score_max_abs'],float(np.max(score_error[np.broadcast_to(mask,score_error.shape)])),'score numerical diagnostic')
    totals['diagnostic_metrics']+=7
    if record['exploratory_local_RMSE_screen_passed'] != (diagnostics['integer_output_vs_native']['relative_rmse']<=.05 and record['K_clips']==0 and record['V_clips']==0):
        raise AssertionError('reported local screen')
    if record['full_model_quality_accepted'] or record['hardware_supported']:
        raise ValueError('scope overclaim')
    bad=p.copy();idx=(0,0,0);bad[idx]=int(bad[idx])+1 if int(bad[idx])<32767 else int(bad[idx])-1
    try:equal(bad,from_stored,'intentional in-memory P-code mutation')
    except AssertionError:negative=True
    else:raise AssertionError('P-code mutation was not rejected')
    return {'id':record['id'],'status':'PASS','QK_values':int(dot.size),'P15_values':int(p.size),'PV_values':int(pv.size),
            'Fraction_score_witnesses':witnesses+int(np.prod(dot.shape[:-1])),'maximum_Psum':int(p.sum(-1,dtype=np.uint64).max()),
            'maximum_Psum_budget':int(budget.max()),'native_and_FP64_diagnostics':diagnostics,
            'in_memory_P_code_mutation_rejected':negative,
            'negative_scope':'in-memory code-only mutation, not a rehashed file or full-model adversarial experiment'}


def verify_artifacts(root,manifest):
    checked={};base=root.resolve()
    for name,description in manifest['artifacts'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(base):raise ValueError('artifact escaped result directory')
        if not path.is_file() or path.stat().st_size!=description['bytes'] or sha(path)!=description['sha256']:
            raise ValueError('artifact SHA/size mismatch '+name)
        checked[name]={'bytes':path.stat().st_size,'sha256':description['sha256']}
    return checked


def receive(root,out,code_root):
    if out.exists():raise ValueError('refuse existing receiver output directory')
    out.mkdir(parents=True);started=time.monotonic()
    receipt={'status':'RUNNING','receiver_source_sha256':sha(Path(__file__)),'scope':__doc__,
      'environment':{'python':platform.python_version(),'numpy':np.__version__},
      'root':str(root),'code_root':str(code_root),'input_rounds':{},'Decimal50_LUTs':{},'cases':[],
      'counts':{'QK_I64_values':0,'score_integer_values':0,'score_Fraction_witnesses':0,'exp_and_P15_values':0,'PV_I64_values':0,'diagnostic_metrics':0},
      'upstream_scope':'Input capture SHA bindings are recorded, not a reproof of original FP32 capture, KV calibration, full model, or hardware.'}
    try:
        rounds={};records={}
        for name in ('attention01','attention02'):
            folder=root/name;m=read_json(folder/'manifest.json')
            if m['status']!='PASS' or m['conditions']!=56 or m['conditions_passed_integer_execution']!=56 or m['conditions_failed_integer_execution']!=0:
                raise ValueError('incomplete/failed producer round '+name)
            if m['full_model_quality_accepted'] or m['hardware_implemented']:
                raise ValueError('producer scope overclaim')
            if set(m['source']['files'])!={'attention.py','server_models/bounds.py'}:
                raise ValueError('unexpected producer source file set')
            for key,value in m['source']['files'].items():
                path=code_root/'block_decisions/attention.py' if key=='attention.py' else code_root/key
                if not path.is_file() or sha(path)!=value:raise ValueError('producer source SHA '+key)
            manifest_path=folder/'manifest.json'
            receipt['input_rounds'][name]={'manifest_sha256':sha(manifest_path),'source':m['source'],
                'input_captures':m['input_captures'],'artifacts':verify_artifacts(folder,m)}
            rounds[name]=m;records[name]=read_json(folder/'attention.json')
            if len(records[name])!=56 or len({r['id'] for r in records[name]})!=56 or any(r['status']!='PASS' for r in records[name]):
                raise ValueError('actual attention condition set '+name)
            if any(r['model'] not in ('gemma','qwen25','qwen35') or not r['id'].startswith(r['model']+'.') for r in records[name]):
                raise ValueError('unexpected/reserved model record')
            if len([n for n in m['artifacts'] if n.endswith('.npz')])!=56:
                raise ValueError('actual NPZ condition count '+name)
            wanted={r['id']+'.npz' for r in records[name]}|{'attention.json','exp-grid128.u32le.bin','exp-grid256.u32le.bin'}
            if set(m['artifacts'])!=wanted:raise ValueError('artifact set does not match indexed records')
        first=dict(rounds['attention01']);second=dict(rounds['attention02'])
        first.pop('seconds',None);second.pop('seconds',None)
        if first!=second:raise AssertionError('producer manifests differ beyond seconds')
        if set(first['artifacts'])!=set(second['artifacts']):raise AssertionError('round artifact sets')
        for name in first['artifacts']:
            if not bytes_equal(root/'attention01'/name,root/'attention02'/name):raise AssertionError('round file differs '+name)
        receipt['two_rounds_all_artifacts_byte_identical']=True
        receipt['two_rounds_manifest_equal_except_seconds']=True
        binding=root/'phase2/binding.json'
        if first['source'].get('binding_supplied') and not binding.is_file():raise ValueError('bound producer binding is absent')
        if binding.is_file():
            b=read_json(binding)
            if b.get('commit')!=first['source']['commit']:raise AssertionError('producer binding commit')
            if first['source'].get('binding_sha256')!=sha(binding):raise AssertionError('producer binding SHA')
            receipt['producer_binding_sha256']=sha(binding)
        tables={}
        for grid in (128,256):
            path=root/'attention01'/('exp-grid'+str(grid)+'.u32le.bin');table=np.fromfile(path,dtype='<u4')
            expected=decimal_lut(grid);bad=np.flatnonzero(table!=expected) if table.shape==expected.shape else np.arange(max(len(table),len(expected)))
            receipt['Decimal50_LUTs'][str(grid)]={'entries':len(table),'sha256':sha(path),'mismatches':int(len(bad))}
            if len(bad):
                differences=[{'index':int(j),'producer':int(table[j]) if j<len(table) else None,'Decimal50':int(expected[j]) if j<len(expected) else None} for j in bad]
                save(out/('LUT-'+str(grid)+'-compiler-failure.json'),differences)
                raise AssertionError('Decimal50 LUT compiler mismatch retained; producer not changed')
            tables[grid]=table
        # Complete second-round byte identity proves the identical arithmetic input stream;
        # execute the independent arithmetic oracle once rather than duplicate costly I64 dots.
        for record in records['attention01']:
            receipt['cases'].append(verify_case(root/'attention01'/(record['id']+'.npz'),record,tables[int(record['LUT_grid'])],receipt['counts']))
        sample_dir=out/'samples';sample_dir.mkdir()
        for name in [s+'.npz' for s in SAMPLES]+['exp-grid128.u32le.bin','exp-grid256.u32le.bin']:
            shutil.copyfile(root/'attention01'/name,sample_dir/name)
        receipt['samples']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(sample_dir.iterdir())}
        receipt['status']='PASS'
        receipt['arithmetic_replayed_round']='attention01; attention02 complete artifact byte identity verified'
    except Exception as exc:
        receipt.update(status='FAIL',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
    receipt['seconds']=time.monotonic()-started
    save(out/'audit.json',receipt)
    print(json.dumps({'status':receipt['status'],'cases':len(receipt['cases']),'counts':receipt['counts'],'seconds':receipt['seconds']}),flush=True)
    if receipt['status']!='PASS':raise SystemExit(1)


def self_test():
    n=np.array([1,3,5,7,U64_MAX-1,U64_MAX],dtype=np.uint64)
    d=np.array([2,2,2,2,U64_MAX,U64_MAX],dtype=np.uint64)
    equal(div_even_u64(n,d),np.array([round(Fraction(int(x),int(y))) for x,y in zip(n,d)],dtype=np.uint64),'synthetic U64 ties/max')
    dot=np.array([[[-7,-5,-3,-1,0,1,3,5,7]]],dtype=np.int64)
    for e in (-12,-1,0,1):
        qe=np.array([[e]],dtype=np.int8);got,_=scores_from_dot(dot,qe,-1,1<<17)
        wanted=np.array([round(Fraction(int(x)*(1<<17))*Fraction(2)**(e-19)) for x in dot.flat]).reshape(dot.shape)
        equal(got,wanted,'synthetic independent score Fraction')
    got,_=scores_from_dot(dot,np.array([[25]],dtype=np.int8),0,1)
    equal(got,dot*128,'synthetic left shift')
    for grid in (128,256):
        table=decimal_lut(grid)
        if len(table)!=16*grid+1 or table[0]!=(1<<30) or table[-1]!=121:raise AssertionError('Decimal LUT endpoints')
        score=np.array([[[0,-16,-48,-65536,-65537,I32_MAX]]],dtype=np.int32)
        mask=np.array([[True,True,True,True,True,False]])
        p,ex,sums,budget,stats=normalize_from_scores(score,mask,grid,table)
        if int(ex[0,0,3])!=121 or ex[0,0,4]!=0 or ex[0,0,5]!=0:raise AssertionError('LUT truncation/mask')
        wanted=np.array([min(32767,round(Fraction(int(x)*32768,int(sums[0,0])))) for x in ex.flat],dtype=np.int16).reshape(ex.shape)
        equal(p,wanted,'synthetic full Fraction P15')
        if stats['maximum_P_sum_U32']>int(budget[0]):raise AssertionError('Psum budget')
    # Exercise the exact saved-array contract and all reported diagnostic fields.
    rng=np.random.default_rng(264)
    q=rng.integers(-12,13,(2,3,4),dtype=np.int16).astype(np.int8)
    k=rng.integers(-32,33,(7,4),dtype=np.int16);v=rng.integers(-80,81,(7,4),dtype=np.int16)
    qe=np.full((2,3),-4,dtype=np.int8);ke,ve=-3,-6;scaling=.25;multiplier=1<<28
    pos=np.array([1,3,6],dtype=np.int64);mask=(np.arange(7)[None]<=pos[:,None])&(np.arange(7)[None]>pos[:,None]-3)
    dot=q.astype(np.int64)@k.astype(np.int64).T
    score,_=scores_from_dot(dot,qe,ke,multiplier);score=score.astype(np.int32)
    p,ex,sums,budget,stats=normalize_from_scores(score,mask,128,decimal_lut(128))
    pv=p.astype(np.int64)@v.astype(np.int64)
    exact=dot.astype(np.float64)*np.exp2(qe.astype(np.float64)+ke)[:,:,None]*scaling
    masked=np.where(mask[None],exact,-np.inf);prob=np.exp(masked-masked.max(-1,keepdims=True));prob/=prob.sum(-1,keepdims=True)
    fp_p=np.clip(np.rint(prob*32768),0,32767).astype(np.int16)
    fp_out=(fp_p.astype(np.int64)@v.astype(np.int64)).astype(np.float64)*2.**(ve-15)
    converted=pv.astype(np.float64)*2.**(ve-15)
    record={'id':'synthetic.l0.kv16.lut128','KV_bits':16,'LUT_grid':128,'GQA_Q_heads':2,'head_dim':4,'keys':7,'positions':pos.tolist(),'window':3,
      'K_exponent':ke,'V_exponent':ve,'K_clips':0,'V_clips':0,
      'score_scale':{'multiplier':multiplier,'source_float_hex':scaling.hex()},'operations':{'softmax':stats},
      'integer_output_vs_native':metric(converted,fp_out),'FP64_same_encoded_KV_P15_output_vs_native':metric(fp_out,fp_out),
      'integer_output_vs_FP64_same_encoded_KV_P15':metric(converted,fp_out),
      'P15_code_mismatches_vs_FP64_softmax':int(np.count_nonzero(p!=fp_p)),
      'score_q12_vs_exact_score_max_abs':float(np.max(np.abs(score.astype(np.float64)*2.**-12-exact)[np.broadcast_to(mask,score.shape)])),
      'exploratory_local_RMSE_screen_passed':metric(converted,fp_out)['relative_rmse']<=.05,'full_model_quality_accepted':False,'hardware_supported':False}
    arrays={'Q8':q,'Qe':qe,'K':k,'V':v,'QK32':dot.astype(np.int32),'scoreQ12':score,'mask':mask,'positions':pos,
      'expQ30':ex,'exp_sum_U64':sums,'P15':p,'P15_FP64_softmax_reference':fp_p,'Psum_budget':budget,
      'PV32':pv.astype(np.int32),'native_reference':fp_out,'PV_FP64_softmax_reference':fp_out}
    counts={'QK_I64_values':0,'score_integer_values':0,'score_Fraction_witnesses':0,'exp_and_P15_values':0,'PV_I64_values':0,'diagnostic_metrics':0}
    with tempfile.TemporaryDirectory(prefix='receiver-synthetic-',dir=Path(__file__).resolve().parent) as td:
        path=Path(td)/'case.npz';np.savez_compressed(path,**arrays)
        verify_case(path,record,decimal_lut(128),counts)
    print(json.dumps({'status':'PASS','scope':'local synthetic integer divider, score, mask/LUT/truncation/Psum; no actual model receiver run'}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--code-root',type=Path,help='default ROOT/phase2/project/experiments')
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    if a.self_test:self_test();return
    if a.root is None or a.out is None:p.error('--root and --out are required for receiver execution')
    receive(a.root,a.out,a.code_root or a.root/'phase2/project/experiments')


if __name__=='__main__':main()
