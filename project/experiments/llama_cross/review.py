"""Compact data replay: independent INT64/Fraction oracle and saved trace audit.

The kit intentionally omits fullK float linear sources; it cannot recheck their
float-to-code calibration. Full local audit_linear.py does, with source hashes.
"""
import argparse
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from common import ROOT,HERE,save
from audit import compile_decimal
from oracle import attention
from service_model import audit_schedule


def main():
    p=argparse.ArgumentParser();p.add_argument('kit',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    maps=json.loads((a.kit/'array-map.json').read_text());arrays={}
    for label,items in maps.items():
        arrays[label]={}
        for name,target in items.items():
            raw=(a.kit/target).read_bytes()
            assert Path(target).stem==hashlib.sha256(raw).hexdigest()
            arrays[label][name]=np.load(io.BytesIO(raw),allow_pickle=False)
    lin=arrays['linear'];values=0;acc_values=0
    for r in json.loads((a.kit/'linear01/linear.json').read_text()):
        prefix=r['name']+'.';qa,qw,acc,y=[lin[prefix+k] for k in ['A_i8','W_i8','acc_i32','out_i8']]
        expected=qa.astype(np.int64)@qw.astype(np.int64).T
        assert np.array_equal(acc,expected);acc_values+=acc.size
        shifts=30-(lin[prefix+'A_exponents'][:,None].astype(np.int16)+lin[prefix+'W_exponents'][None,:].astype(np.int16)
                   -lin[prefix+'Y_exponents'][None,:].astype(np.int16))
        assert np.array_equal(shifts,lin[prefix+'r_u8'])
        for idx in np.ndindex(y.shape):
            assert int(y[idx])==max(-128,min(127,round(Fraction(int(expected[idx])*(1<<30),2**int(shifts[idx])))))
            values+=1
    table=json.loads((HERE.parent/'integer_precision/tables.json').read_text())['exp_u32_f24']
    payload=arrays['attention'];gqa=0
    cfg=json.loads((HERE/'experiment.json').read_text())
    for par in json.loads((a.kit/'attention01/frozen-calibration.json').read_text()):
        for name in cfg['evaluation_texts']:
            prefix=par['profile']+'.'+name+'.'
            qa,ki,vi,qe=[payload[prefix+k] for k in ['Q_i8','K_i8','V_i8','Q_exponents']]
            assert qa.shape==(4,40,64) and ki.shape==vi.shape==(40,64)
            allowed=(np.arange(40)[None,:]<=np.arange(40)[:,None]).tolist()
            for h in range(4):
                params=[]
                for t,e in enumerate(qe[h]):
                    m,r=compile_decimal(e,par['K_exponent'],64)
                    assert (m,r)==(int(payload[prefix+'score_M_u32'][h,t]),int(payload[prefix+'score_r_u8'][h,t]))
                    params.append([(m,r)]*5)
                expected=attention(qa[h].tolist(),ki.tolist(),vi.tolist(),[par['V_exponent']]*5,params,8,15,allowed,table)
                for t,row in enumerate(expected):
                    for field,key in [('qk_i32','qk_i32'),('scores_i16_f8','scores_i16'),('probabilities','probabilities_i16'),('output_i16_f12','output_i16_f12')]:
                        assert np.array_equal(row[field],payload[prefix+key][h,t]);gqa+=len(row[field])
    witness_nodes=0;witnesses=0
    for path in sorted((a.kit/'service01').glob('witness-*.json.gz')):
        d=json.loads(gzip.decompress(path.read_bytes()))
        graph=SimpleNamespace(**{k:d[k] for k in ['nodes','packets','leases','sizes']})
        scheduled=d['schedule'];scheduled['trace']={int(k):v for k,v in scheduled['trace'].items()}
        result=audit_schedule(graph,scheduled);witness_nodes+=result['nodes'];witnesses+=1
    result={'status':'PASS','INT64_fullK_values':acc_values,'Fraction_linear_RQ_values':values,
        'independent_GQA_values':gqa,'witnesses':witnesses,'witness_nodes':witness_nodes,
        'scope':'all encoded integer arrays and eight saved service witnesses; full float linear calibration and full model/RTL/PPA are not independently reproduced from this compact kit'}
    save(a.out,result);print(json.dumps(result))


if __name__=='__main__':main()
