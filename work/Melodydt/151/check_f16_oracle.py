"""Independent exact arithmetic and frozen F16 vector checks; no RTL run."""
import argparse
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path
from f16_integer_reference import rne,clip,pack,floor_sqrt,validate_exp_table,validate_native_table,f16


def binary_root(n):
    lo,hi=0,1<<((n.bit_length()+2)//2)
    while lo+1<hi:
        mid=(lo+hi)//2
        if mid*mid<=n:lo=mid
        else:hi=mid
    return lo


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args();checks=0
    def ck(value):
        nonlocal checks
        assert value
        checks+=1
    for shift in (7,10,30):
        for q in range(-33,34):
            for delta in (-1,0,1):
                value=(q<<shift)+(1<<(shift-1))+delta;ck(rne(value,shift)==round(Fraction(value,1<<shift)))
    for n in list(range(1025))+[(1<<k)+delta for k in range(1,64) for delta in (-1,0,1)]:ck(floor_sqrt(n)==binary_root(n))
    d=json.loads((a.directory/'f16-contract-vectors.json').read_text(encoding='utf-8'))
    for v in d['vectors']:
        x,g=v['x'],v['gamma'];e=v['expected'];r=f16(x,g,v['Wgate'],v['Wup'],v['Wdown']);q=sum(t*t for t in x)
        rad=(q<<16)//8+(1<<16);root=binary_root(rad);factor=(1<<38)//root
        norm=[clip(round(Fraction(xx*factor*gg,1<<30)))[0] for xx,gg in zip(x,g)]
        ck(e['norm']['root']==root and e['norm']['factor']==factor);ck(e['normalized_x']==norm)
        for name,w in [('gate',v['Wgate']),('up',v['Wup'])]:
            raw=[sum(norm[k]*col[k] for k in range(8)) for col in w];ck(raw==e['raw_'+name]);ck([clip(round(Fraction(t,128)))[0] for t in raw]==e[name])
        raw=[sum(e['mid'][k]*col[k] for k in range(8)) for col in v['Wdown']];ck(raw==e['raw_down']);ck([clip(round(Fraction(t,128)))[0] for t in raw]==e['down'])
        ck(e['residual']==x);ck(e['final']==[clip(down+xx)[0] for down,xx in zip(e['down'],x)])
        ck(e['done_saturated']==any(e['stage_saturated'].values()))
        ck(len(e['ingress_words_hex'])==17 and e['ingress_words_hex'][1:4]==['0'*32]*3)
        ck(e['ingress_words_hex'][0]=='%032x'%pack(x,16));ck(e['ingress_words_hex'][16]=='%032x'%pack(g,16))
        ck(e['S_words_hex']['466']==e['S_words_hex']['467']==e['ingress_words_hex'][0]);ck(e['S_words_hex']['475']==e['ingress_words_hex'][16])
        ck('%032x'%pack(r['final'],16)==e['S_words_hex']['473'])
        if not any(g):ck(e['final']==x and e['normalized_x']==[0]*8 and not e['done_saturated'])
    ck(any(any(t%8 for t in v['x']) for v in d['vectors']));ck(any(v['expected']['done_saturated'] for v in d['vectors']));ck(any(not v['expected']['done_saturated'] for v in d['vectors']))
    exp=a.root/'project/rtl/block_v2/block_v2_n_exp.svh';gt=a.root/'project/rtl/block_v2/block_v2_g_tables.svh'
    tables={'EXP':validate_exp_table(exp.read_text(encoding='utf-8')),'G':validate_native_table(gt.read_text(encoding='utf-8'))};ck(True)
    contract=json.loads((a.directory/'f16-tb-contract.json').read_text(encoding='utf-8'));tb=(a.directory/'block_w4_f16_tb.sv').read_text(encoding='utf-8')
    literal_markers=re.findall(r'mark\("([^"]+)"\)',tb);ck(literal_markers==contract['expected_case_ids']);ck(len(literal_markers)==len(set(literal_markers))==30)
    ck('$display("PASS_W4_F16 cases=%0d",cases)' in tb)
    ck(hashlib.sha256(tb.encode('utf-8')).hexdigest()==contract['tb_sha256'])
    files={}
    for p in sorted(a.directory.iterdir()):
        if p.is_file() and p.suffix in ('.py','.sv','.json','.md') and p.name!='f16-oracle-checks.json':
            raw=p.read_bytes();raw.decode('utf-8');ck(b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'));files[p.name]=hashlib.sha256(raw).hexdigest()
    receipt={'status':'PASS_PYTHON_ONLY_NOT_RTL_SIMULATION','assertions':checks,'vectors':10,'cases_predeclared':30,'tables':tables,'files':files,'scope':'F16 explicit H8I8 numeric/profile and testsource preparation;rootserverRTL stillrequired'}
    (a.directory/'f16-oracle-checks.json').write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS{}Pythonassertions,F16vectors10,CASEcontract30;noRTLrun'.format(checks))


if __name__=='__main__':main()
