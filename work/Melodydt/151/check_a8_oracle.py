"""Meaningful independent arithmetic/vector checks; never launches RTL."""
import argparse
import hashlib
import json
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
from a8_integer_reference import a8,rne,pack,signed,clip_s16,EXP_MATH_TABLE,mathematical_exp,validate_native_exp,QK_FACTOR


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args();checks=0
    def ck(value):
        nonlocal checks
        assert value
        checks+=1
    with localcontext() as ctx:
        ctx.prec=80
        ck(int((Decimal(2)**15/Decimal(8).sqrt()).to_integral_value(rounding=ROUND_HALF_EVEN))==QK_FACTOR==11585)
        # Separate high-precision Decimal reconstruction from Python math.exp.
        for i,node in enumerate(EXP_MATH_TABLE):
            exact=((Decimal(-16)+Decimal(i)/64).exp()*32768).to_integral_value(rounding=ROUND_HALF_EVEN)
            ck(int(exact)==node)
    for v in range(-32768,32768):
        ck(rne(v,11)==round(Fraction(v,1<<11)))
        ck(rne(v,19)==round(Fraction(v,1<<19)))
    for shift in (11,19,30):
        for retained in (-3,-2,-1,0,1,2,3):
            for delta in (-1,0,1):
                value=(retained<<shift)+(1<<(shift-1))+delta
                ck(rne(value,shift)==round(Fraction(value,1<<shift)))
    for diff in range(-16385,1):
        if diff < -16384:expected=0
        elif diff==0:expected=32768
        else:
            ix,rem=divmod(diff+16384,16)
            expected=EXP_MATH_TABLE[ix]+round(Fraction((EXP_MATH_TABLE[ix+1]-EXP_MATH_TABLE[ix])*rem,16))
        ck(mathematical_exp(diff)==expected)
    d=json.loads((a.directory/'a8-contract-vectors.json').read_text(encoding='utf-8'))
    for vec in d['vectors']:
        q,k,v=vec['Q'],vec['K_token_dimension'],vec['V_channel_token'];e=vec['expected'];r=a8(q,k,v)
        ck(r['qk_raw']==[sum(x*y for x,y in zip(q,row)) for row in k])
        ck(e['scores']==[clip_s16(round(Fraction(raw*11585,1<<19)))[0] for raw in r['qk_raw']])
        ck(e['softmax']['exp']==[mathematical_exp(x-max(e['scores'])) for x in e['scores']])
        ck(e['softmax']['factor']==(1<<44)//sum(e['softmax']['exp']))
        ck(e['softmax']['prob']==[max(0,min(16384,round(Fraction(x*e['softmax']['factor'],1<<30)))) for x in e['softmax']['exp']])
        ck(e['pv_raw']==[sum(prob*value for prob,value in zip(e['softmax']['prob'],row)) for row in v])
        ck(e['output']==[clip_s16(round(Fraction(raw,1<<11)))[0] for raw in e['pv_raw']])
        ck(['%032x'%w for w in r['ingress_words']]==e['ingress_words_hex'])
        ck({str(k):'%032x'%w for k,w in r['S_words'].items()}==e['S_words_hex'])
        ck(not e['done_saturated'])
        ck(16380<=e['softmax']['prob_sum']<=16388)
        for h in range(2):
            for field,lanes in [('M_QK_op5_carriers_hex',e['scores']),('M_PV_op5_carriers_hex',e['output'])]:
                word=int(e[field][h],16)
                ck([signed(word>>(32*i),32) for i in range(4)]==lanes[4*h:4*h+4])
                ck(pack([signed(word>>(32*i),16) for i in range(4)],16)==pack(lanes[4*h:4*h+4],16))
    equal=d['vectors'][1]['expected'];zero=d['vectors'][2]['expected'];last=d['vectors'][3]['expected']
    ck(equal['softmax']['exp']==[32768]*8 and equal['softmax']['prob']==[2048]*8)
    ck(zero['scores']==[0]*8 and zero['softmax']['prob']==[2048]*8)
    ck(last['scores'][-1]>max(last['scores'][:-1]) and last['softmax']['prob'][-1]>15000)
    # Layout trap: the nonsymmetric V really distinguishes channel-major from
    # an erroneous transpose, with the same physical B512 format.
    sample=d['vectors'][0];correct=sample['expected']['output'];prob=sample['expected']['softmax']['prob'];v=sample['V_channel_token']
    wrong=[round(Fraction(sum(prob[t]*v[t][c] for t in range(8)),1<<11)) for c in range(8)]
    ck(wrong!=correct)
    table=a.root/'project/rtl/block_v2/block_v2_n_exp.svh';validation=validate_native_exp(table.read_text(encoding='utf-8'));ck(True)
    ck(hashlib.sha256(table.read_bytes()).hexdigest()==d['native_sources']['EXP']['sha256'])
    files={}
    for p in sorted(a.directory.iterdir()):
        if p.is_file() and p.suffix in ('.py','.json','.svh','.md') and p.name!='a8-oracle-checks.json':
            raw=p.read_bytes();raw.decode('utf-8');ck(b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'));files[p.name]=hashlib.sha256(raw).hexdigest()
    receipt={'status':'PASS_PYTHON_INTEGER_REFERENCE_ONLY_NOT_RTL_EXECUTION','assertions':checks,'vectors':len(d['vectors']),'math_EXP_nodes':1025,'table_validation':validation,'files':files,'scope':'bounded QK/Softmax/PV contract, no model numerical-quality or simulator/physical acceptance'}
    (a.directory/'a8-oracle-checks.json').write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS {} independent Python assertions,{} A8 vectors, EXP1025 Decimal/math/source equal; no RTL run'.format(checks,len(d['vectors'])))


if __name__=='__main__':main()
