"""Float sensitivity diagnosis from saved integer codes; no hardware timing claim."""
import argparse
import json
from pathlib import Path
import numpy as np


def rel(x,y):return float(np.sqrt(np.mean((x-y)**2))/max(np.sqrt(np.mean(y*y)),1e-30))


def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path)
    p.add_argument('--linear',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    data=np.load(a.capture/'gqa-group.npz',allow_pickle=False);codes=np.load(a.linear/'integers.npz',allow_pickle=False)
    result=[]
    for row in json.loads((a.linear/'linear.json').read_text()):
        name=row['name'];layer,text,phase,mode=name.split('.');prefix=name+'.'
        sl=slice(0,32) if phase=='prefill' else slice(32,40)
        x=data[text+'.'+layer+'.A'][sl].astype(np.float64);w=data['weight.'+layer].astype(np.float64)
        y=data[text+'.'+layer+'.Y'][sl].astype(np.float64)
        ea=codes[prefix+'A_exponents'].astype(np.float64);ew=codes[prefix+'W_exponents'].astype(np.float64)
        qa=codes[prefix+'A_i8'].astype(np.float64);qw=codes[prefix+'W_i8'].astype(np.float64)
        xd=qa*np.exp2(ea)[:,None];wd=qw*np.exp2(ew)[:,None]
        before=codes[prefix+'acc_i32'].astype(np.float64)*np.exp2(ea[:,None]+ew[None,:])
        final=codes[prefix+'out_i8'].astype(np.float64)*np.exp2(codes[prefix+'Y_exponents'].astype(np.float64))
        result.append({'name':name,'weight_only_relative_rmse':rel(x@wd.T,y),'activation_only_relative_rmse':rel(xd@w.T,y),
            'integer_acc_dequant_before_RQ_relative_rmse':rel(before,y),'final_RQ_relative_rmse':rel(final,y),
            'A_zero_fraction':float(np.mean(qa==0)),'A_exponent_min':float(ea.min()),'A_exponent_max':float(ea.max())})
    record={'diagnostics':result,'scope':'dequantized float sensitivity only; terms are not additive causal contributions or hardware costs'}
    a.out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([r for r in result if r['name'].startswith('down_proj')]))


if __name__=='__main__':main()
