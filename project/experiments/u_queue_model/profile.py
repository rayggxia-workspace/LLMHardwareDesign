"""Bind partial model calibration to verified native U-region evidence."""
import hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(c,m):
    if not c:raise ValueError(m)
def read_profile(root):
    root=Path(root);native=root/'native';receipt=native/'results/result.json'
    require(sha(receipt)=='4c006aa78b73a18bcdc90e7155c8995d2780ab38bfc6e3bd310c44d8ecd3c960','native evidence identity')
    r=json.loads(receipt.read_bytes());c=json.loads((native/'collection.json').read_bytes())
    for n,d in c['files'].items():require(sha(native/n)==d['sha256'],'received native file drift '+n)
    require(r['passed'] and r['functional_passed'] and r['default_exact_pairs']==27,'native functional gates')
    require(r['area']['status']=='passed' and sum(len(v['runs']) for v in r['tests'].values())==195,'native coverage/area gate')
    for n,d in r['source_sha256'].items():
        if n.startswith('project/rtl/'):require(sha(root/'source'/n)==d,'calibrated RTL drift '+n)
    tables={}
    for key in ['region0','region1']:
        table={}
        for run in r['tests'][key]['runs']:
            path=native/'results'/run['summary'];require(sha(path)==run['summary_sha256'],'region timing log drift')
            rows=[{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)} for s in path.read_text().splitlines() if s.startswith('REGION_TILE ')]
            require(rows==run['tiles'] and run['checks']['values']==24409,'timing log/numeric coverage')
            q=next(x for x in rows if x['elements']==64);value=q['cycles']+1
            if table:require(table[64]==value,'seed timing drift')
            table[64]=value
            m=run['measurements'];require(m['elements']==22016 and m['tiles']==344 and m['cycles']==q['cycles']*344,'whole shape accounting')
            require(m['writes']==5504 and m['reads']==(2752 if key=='region1' else 5504),'native traffic')
        tables[key]=table
    generation=r['generation'];audit=generation['trace_audit']
    require(all(v['eligible_pure_S16_E']==0 for v in audit.values()),'new graph requires new E mapping audit')
    return dict(result_sha256=sha(receipt),source_commit=r['source_commit'],tile64_cycles=tables['region1'][64],
        raw_tile64_cycles=tables['region1'][64]-1,retirement_cycles=1,trace_audit=audit,
        queue_E_gain_credited=0,scope='staged S16 Q5.10 NExp region only; old S32 graph fees retained',
        actual_model_values_verified=False,full_model_RTL_calibrated=False)
