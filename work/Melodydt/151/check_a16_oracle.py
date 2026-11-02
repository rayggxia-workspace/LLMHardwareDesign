"""Independent exact math and source-contract preparation checks, not RTL."""
import argparse,json,hashlib,re
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from a16_integer_reference import EXP,rne,clip,pack,root,validate_exp_table

def binary_sqrt(n):
    lo,hi=0,1<<((n.bit_length()+2)//2)
    while lo+1<hi:
        m=(lo+hi)//2
        if m*m<=n:lo=m
        else:hi=m
    return lo

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();checks=0
    def ck(v):
        nonlocal checks
        assert v
        checks+=1
    with localcontext() as c:
        c.prec=70
        for i,y in enumerate(EXP):ck(int(((Decimal(-16)+Decimal(i)/64).exp()*32768).to_integral_value(rounding=ROUND_HALF_EVEN))==y)
    for shift in [7,14,25,30]:
        for q in range(-16,17):
            for delta in [-1,0,1]:
                v=(q<<shift)+(1<<(shift-1))+delta;ck(rne(v,shift)==round(Fraction(v,1<<shift)))
    d=json.loads((a.directory/'a16-contract-vectors.json').read_text(encoding='utf-8'))
    for v in d['vectors']:
        e=v['expected'];history=e['S_write_history_hex'];ck(len(e['ingress_words_hex'])==27);ck(sum(len(x) for x in history.values())==73)
        ck(all(e['ingress_words_hex'][i]=='0'*32 for i in [1,2,3,5,6,7]));ck(all(len(history[str(i)])==2 for i in range(488,492)))
        for row in range(2):
            x=v['X'][row];g=v['gamma'];rad=(sum(t*t for t in x)<<16)//8+(1<<16);rt=binary_sqrt(rad);fac=(1<<38)//rt
            ck(rt==root(rad)==e['norm'][row]['root']);ck(e['norm'][row]['factor']==fac)
            norm=[clip(round(Fraction(xx*fac*gg,1<<30)))[0] for xx,gg in zip(x,g)];ck(e['norm'][row]['output']==norm)
            for p,w in enumerate([v['Wq'],v['Wk'],v['Wv']]):
                raw=[sum(norm[k]*col[k] for k in range(8)) for col in w];ck(raw==e['M_raw'][p][row]);ck([clip(round(Fraction(x,128)))[0] for x in raw]==e['M_outputs'][p][row])
            for plain,rotated in [('Q_plain','Q_rotated'),('K_plain','K_rotated')]:
                values=[]
                for pair in range(4):
                    xx,yy=e[plain][row][2*pair:2*pair+2];c,s=v['coeff'][row][2*pair:2*pair+2]
                    values.extend(clip(round(Fraction(t,16384)))[0] for t in [xx*c-yy*s,yy*c+xx*s])
                ck(values==e[rotated][row])
            scores=[clip(round(Fraction(sum(q*k for q,k in zip(e['Q_rotated'][row],col))*11585,1<<25)))[0] for col in e['K_columns']];ck(scores==e['scores'][row])
            probs=e['softmax'][row]['prob'];ck(probs[row+1:]==[0]*(7-row));ck(e['softmax'][row]['exp'][row+1:]==[0]*(7-row));ck(probs==[max(0,min(16384,round(Fraction(t*e['softmax'][row]['factor'],1<<30)))) for t in e['softmax'][row]['exp']])
            pv=[clip(round(Fraction(sum(pv*z for pv,z in zip(probs,col)),1<<14)))[0] for col in e['V_columns']];ck(pv==e['context'][row])
            wo=[clip(round(Fraction(sum(pv[k]*col[k] for k in range(8)),128)))[0] for col in v['Wo']];ck(wo==e['Wo'][row]);ck(e['final'][row]==[clip(xx+yy)[0] for xx,yy in zip(x,wo)])
        ck(e['softmax'][0]['prob']==[16384]+[0]*7)
        ck(e['K_columns'][:2]==e['K_rotated'] and e['K_columns'][2:]==[[0]*8]*6)
        ck(e['V_columns']==[[e['V'][0][c],e['V'][1][c]]+[0]*6 for c in range(8)])
        ck(e['done_saturated']==any(e['stage_saturated'].values()))
    ck(d['vectors'][0]['expected']['final'][0]==d['vectors'][1]['expected']['final'][0]);ck(d['vectors'][0]['expected']['final'][1]!=d['vectors'][1]['expected']['final'][1]);ck(d['vectors'][2]['expected']['final']==d['vectors'][2]['X'])
    ck(any(v['expected']['Q_plain']!=v['expected']['Q_rotated'] for v in d['vectors']))
    ck(any(v['expected']['done_saturated'] for v in d['vectors']) and any(not v['expected']['done_saturated'] for v in d['vectors']))
    ck(validate_exp_table((a.root/'project/rtl/block_v2/block_v2_n_exp.svh').read_text(encoding='utf-8'))['all_equal'])
    tb=(a.directory/'block_w4_a16_tb.sv').read_text(encoding='utf-8');ct=json.loads((a.directory/'a16-tb-contract.json').read_text(encoding='utf-8'))
    ck(len(ct['expected_case_ids'])==len(set(ct['expected_case_ids']))==30);ck(hashlib.sha256(tb.encode('utf-8')).hexdigest()==ct['tb_sha256']);ck('$display("PASS_W4_A16 cases=%0d",cases)' in tb)
    files={}
    for p in a.directory.iterdir():
        if p.is_file() and p.suffix in ['.py','.sv','.md','.json'] and p.name!='a16-oracle-checks.json':
            raw=p.read_bytes();raw.decode('utf-8');ck(b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'));files[p.name]=hashlib.sha256(raw).hexdigest()
    result={'status':'PASS_PYTHON_ONLY_NOT_SV_COMPILE_OR_RTL','assertions':checks,'vectors':10,'predeclared_cases':30,'files':files,'scope':'independentinteger/literalcontractpreparation;serverVerilatorstillrequired'}
    (a.directory/'a16-oracle-checks.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'));print('PASS{}Pythonassertions,10A16vectors/30CASE;notSVcompileorRTL'.format(checks))

if __name__=='__main__':main()
