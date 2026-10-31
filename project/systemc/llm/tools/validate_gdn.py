#!/usr/bin/env python3
import pathlib,json,sys,hashlib,numpy as np
p=pathlib.Path(sys.argv[1]);receipt=json.loads((p/'export_receipt.json').read_text());result={'scope':receipt['scope'],'comparisons':{},'hashes':{}}
for suffix in ('output','state'):
    actual=np.ldexp(np.fromfile(p/('systemc_'+suffix+'.bin'),dtype='<i4').astype(np.float64),receipt['state_exponent'])
    expected=np.fromfile(p/('reference_'+suffix+'.bin'),dtype='<f4').astype(np.float64)
    delta=np.linalg.norm(actual-expected)/(np.linalg.norm(expected)+1e-30)
    result['comparisons'][suffix]={'relative_l2':float(delta),'max_absolute':float(np.max(np.abs(actual-expected))),
                                  'cosine':float(np.dot(actual,expected)/(np.linalg.norm(actual)*np.linalg.norm(expected)+1e-30))}
for f in sorted(p.glob('*.bin')):result['hashes'][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
result['pass']=all(x['relative_l2']<0.03 for x in result['comparisons'].values())
(p/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if not result['pass']:sys.exit(1)
