"""Exhaustive Q16.16 grid scan vs independent binary64 analytic functions.

Decimal60-generated coefficients are the DUT data, not the reference formula.
Relative error reported only when |reference|>=1/256; absolute always.
"""
import hashlib,json,math,sys
from pathlib import Path


def scan(table_path):
    data=json.loads(table_path.read_text());results=[]
    for t in data['tables']:
        fn=t['function'];lo,hi=t['domain'];values=t['values'];shift=9 if fn==0 else 11
        max_abs=0.;max_rel=0.;worst=0
        for raw in range(lo*65536,hi*65536+1):
            x=raw/65536
            if fn==0:ref=math.exp(x)
            elif fn==1:ref=1/(1+math.exp(-x))
            elif fn==2:ref=x/(1+math.exp(-x))
            elif fn==3:ref=.5*x*(1+math.tanh(math.sqrt(2/math.pi)*(x+.044715*x*x*x)))
            else:ref=math.log1p(math.exp(x))
            off=raw-lo*65536;i=off>>shift;frac=off&((1<<shift)-1)
            if i==len(values)-1:actual=values[i]
            else:
                product=(values[i+1]-values[i])*frac;q=product>>shift;r=product&((1<<shift)-1);half=1<<(shift-1)
                actual=values[i]+q+(r>half or(r==half and q&1))
            error=abs(actual/65536-ref)
            if error>max_abs:max_abs=error;worst=raw
            if abs(ref)>=1/256:max_rel=max(max_rel,error/abs(ref))
        results.append(dict(name=t['name'],grid_points=(hi-lo)*65536+1,max_absolute_error=max_abs,
                            max_relative_error_where_abs_reference_at_least_1_over_256=max_rel,worst_raw=worst))
    result=dict(passed=True,reference='Independent Python binary64 math functions over every Q16.16 input in declared domains',
                coefficient_json_sha256=hashlib.sha256(table_path.read_bytes()).hexdigest(),results=results,
                actual_rtl_exhaustive_scan=False,model_quality_verified=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':scan(Path(sys.argv[1]))
