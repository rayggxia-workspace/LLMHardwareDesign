"""Independent scalar accounting review; writes only beside this D-drive file."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger
import run as runner


def equal(actual, expected, label):
    if actual != expected:
        raise AssertionError((label, actual, expected))


def ffn_expected(t, h, f, tt, ft, b, schedule):
    nt, nf = (t + tt - 1)//tt, (f + ft - 1)//ft
    x, z, w = t*h, t*f, nt*h*f
    result = {
        'external_read': (x+3*w)*b, 'external_write': x*b,
        'matrix_read': ((1+3*nf)*x+3*w+3*z)*b,
        'matrix_write': ((2+nf)*x+3*w+3*z)*b,
        'vector_read': 4*z*b, 'vector_write': 4*z*b,
        'matrix_to_vector': 2*z*b, 'vector_to_matrix': z*b,
        'macs': 3*t*h*f,
    }
    u, v = min(t, tt), min(f, ft)
    if schedule == 'materialized':
        peaks = {'matrix': (u*h+2*u*f+h*v)*b, 'vector': 2*u*f*b}
        total = max(u*h+2*u*f+h*v, 3*u*f)*b
    else:
        peaks = {'matrix': (2*u*h+2*u*v+h*v)*b, 'vector': 2*u*v*b}
        total = (2*u*h+max(2*u*v+h*v, 3*u*v))*b
    return result, peaks, total


def attention_expected(q,k,nh,nk,d,qt,kt,b,schedule):
    nq, nkt = (q+qt-1)//qt, (k+kt-1)//kt
    a, s, c, r = nh*q*d, nh*q*k, nq*nk*k*d, nh*q
    result = {'external_read': (a+2*c)*b, 'external_write': a*b,
              'vector_to_matrix': s*b, 'macs': 2*s*d}
    if schedule == 'materialized':
        result.update(matrix_read=((2*nkt+1)*a+2*c+2*s)*b,
                      matrix_write=((nkt+2)*a+2*c+2*s)*b,
                      vector_read=(4*s+2*r)*b,
                      vector_write=(3*s+2*r)*b,
                      matrix_to_vector=s*b)
    else:
        result.update(matrix_read=(2*nkt*a+2*c+2*s)*b,
                      matrix_write=((nkt+1)*a+2*c+2*s)*b,
                      vector_read=(4*s+(2*nkt+2)*a+(3*nkt+1)*r)*b,
                      vector_write=(2*s+(2*nkt+2)*a+(3*nkt+2)*r)*b,
                      matrix_to_vector=(s+nkt*a)*b)
    return result


def derived_config_checks():
    entries=json.loads((HERE/'model-cases.json').read_text(encoding='utf-8'))['cases']
    results=[]
    for m in entries:
        path=HERE/m['input_file']; raw=path.read_bytes()
        equal(hashlib.sha256(raw).hexdigest(),m['input_sha256'],m['id']+' input sha')
        if path.suffix=='.json':
            cfg=json.loads(raw); cfg=cfg.get('text_config',cfg)
            exp={'hidden':cfg['hidden_size']}
            field='moe_intermediate_size' if 'one routed expert' in m['ffn_scope'] else 'intermediate_size'
            exp['intermediate']=cfg[field]
            if 'query_heads' in m:
                exp.update(query_heads=cfg['num_attention_heads'],kv_heads=cfg['num_key_value_heads'],
                           head_dim=cfg.get('head_dim',cfg['hidden_size']//cfg['num_attention_heads']))
        else:
            text=raw.decode().split('def arch_args_3b')[0]
            get=lambda key: float(re.search(r'"'+key+r'":\s*([0-9.]+)',text).group(1))
            h=int(get('dim')); multiple=int(get('multiple_of'))
            f=int(int(2*(4*h)/3)*get('ffn_dim_multiplier'))
            exp=dict(hidden=h,intermediate=((f+multiple-1)//multiple)*multiple,
                     query_heads=int(get('n_heads')),kv_heads=int(get('n_kv_heads')),
                     head_dim=h//int(get('n_heads')))
        for key,value in exp.items(): equal(m[key],value,m['id']+' '+key)
        results.append({'model':m['id'],'checked_fields':exp,'pass':True})
    # Current production startup binds input bytes but does not derive dimensions.
    m=dict(entries[0]);m['hidden']+=1
    accepted=hashlib.sha256((HERE/m['input_file']).read_bytes()).hexdigest()==m['input_sha256']
    return results, {'label':'wrong derived hidden with untouched input sha',
                     'wrong_hidden':m['hidden'],'source_sha_check_still_passes':accepted,
                     'auditor_field_check_rejects':m['hidden']!=results[0]['checked_fields']['hidden']}


def main():
    rng=random.Random(20261022)
    scalar_checks=peak_checks=event_replays=0
    for _ in range(80):
        t,h,f,tt,ft=[rng.randint(1,n) for n in [31,37,43,17,19]]
        for schedule in ['materialized','streaming']:
            got=ledger.ffn_workload(t,h,f,tt,ft,schedule,4)
            expected,peaks,total=ffn_expected(t,h,f,tt,ft,4,schedule)
            for key,value in expected.items():
                equal(got['counts'][key],value,'FFN '+key);scalar_checks+=1
            equal(got['peak_bank_bytes'],peaks,'FFN bank peaks');peak_checks+=2
            equal(got['peak_total_bytes'],total,'FFN simultaneous peak');peak_checks+=1
            runner.audit_events(got['events'],got);event_replays+=1
    for _ in range(80):
        k=rng.randint(1,37);q=rng.randint(1,k)
        nk=rng.randint(1,4);nh=nk*rng.randint(1,4)
        d,qt,kt=[rng.randint(1,n) for n in [17,13,19]]
        for schedule in ['materialized','streaming']:
            got=ledger.attention(q,k,nh,nk,d,qt,kt,schedule,4)
            expected=attention_expected(q,k,nh,nk,d,qt,kt,4,schedule)
            for key,value in expected.items():
                equal(got['counts'][key],value,'attention '+key);scalar_checks+=1
            runner.audit_events(got['events'],got);event_replays+=1
    fields,negative=derived_config_checks()
    result={'status':'PASS','seed':20261022,'schedule_cases':320,
            'independent_scalar_comparisons':scalar_checks,'independent_ffn_peak_comparisons':peak_checks,
            'production_event_replays':event_replays,'model_config_checks':fields,
            'derived_dimension_negative_control':negative,
            'source_snapshot':'snapshot.json','scope':'Analytical accounting; no timing, weights or physical implementation',
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out=HERE/'audit-math-results.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','schedule_cases','independent_scalar_comparisons','independent_ffn_peak_comparisons','production_event_replays','derived_dimension_negative_control']}))


if __name__=='__main__':main()
