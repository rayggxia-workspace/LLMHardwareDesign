"""Independent exact-arithmetic, frozen-vector and text integrity checks."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from w4_integer_reference import floor_sqrt,rne,clip,n_group,f8,pack,validate_exp_table,validate_native_table


def binary_sqrt(n):
    lo,hi=0,1 << ((n.bit_length()+2)//2)
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
    for i in range(-32768,32768):
        ck(rne(i,3)==round(Fraction(i,8)))
        q,s=clip(rne(i,3),8);ck(q==max(-128,min(127,round(Fraction(i,8)))))
        ck(s==(not(-128<=round(Fraction(i,8))<=127)))
    for i in list(range(4097))+[(1<<b)+delta for b in range(1,64) for delta in (-1,0,1) if (1<<b)+delta>=0]:
        ck(floor_sqrt(i)==binary_sqrt(i))
    for i in [-(1<<62),-(1<<40)-1,-(1<<30)-536870912,-536870912,-1,0,1,536870912,(1<<30)+536870912,(1<<62)-1]:
        ck(rne(i,30)==round(Fraction(i,1<<30)))
    ns=json.loads((a.directory/'w4-n-vectors.json').read_text(encoding='utf-8'))
    fs=json.loads((a.directory/'w4-f8-vectors.json').read_text(encoding='utf-8'))
    for v in ns['vectors']:
        n=n_group(v['mode'],v['x'],v['gamma'],v['epsilon']);e=v['expected']
        for key in ['output','factor','saturated','sumsq']:ck(n[key]==e[key])
        ck(['%032x'%w for w in n['output_words']]==e['output_words_hex'])
        ck(n['sumsq']==sum(x*x for x in v['x']))
        if v['mode']==0:
            ck(n['exp_sum']==sum(n['exp']))
            ck(n['factor']==(1<<44)//n['exp_sum'])
            ck(max(n['exp'])==32768)
        else:
            ck(n['root']*n['root']<=n['radicand']<(n['root']+1)*(n['root']+1))
            ck(n['factor']==(1<<38)//n['root'])
            ck(n['output']==[max(-32768,min(32767,round(Fraction(x*n['factor']*g,1<<30)))) for x,g in zip(v['x'],v['gamma'])])
        if v['count']%8:ck(int(e['output_words_hex'][-1],16)>>(16*(v['count']%8))==0)
    for v in fs['vectors']:
        r=f8(v['x'],v['Wgate'],v['Wup'],v['Wdown']);e=v['expected']
        ck(r['projection_x']==e['projection_x']);ck(r['normalized_x']==e['normalized_x'])
        ck(r['residual']==[8*x for x in v['x']])
        for name,weights in [('gate',v['Wgate']),('up',v['Wup'])]:
            raw=[sum(e['projection_x'][k]*col[k] for k in range(8)) for col in weights]
            ck(raw==e['raw_'+name]);ck([clip(round(Fraction(x,16)))[0] for x in raw]==e[name])
        ck(r['final']==e['final']);ck(r['done_saturated']==e['done_saturated'])
        ck('%032x'%pack(r['final'],16)==e['S_words_hex']['473'])
        ck('%032x'%pack(v['x'],16)==e['S_words_hex']['466'])
        ck('%032x'%pack([1024]*8,16)==e['S_words_hex']['475'])
    table_checks={}
    for name,file,fn in [('EXP','block_v2_n_exp.svh',validate_exp_table),('G','block_v2_g_tables.svh',validate_native_table)]:
        path=a.root/'project/rtl/block_v2'/file;table_checks[name]=fn(path.read_text(encoding='utf-8'));ck(True)
        ck(hashlib.sha256(path.read_bytes()).hexdigest()==ns['provenance'][name]['sha256'])
    files={}
    for path in sorted(a.directory.iterdir()):
        if path.is_file() and path.suffix in ('.py','.sv','.json','.md') and path.name!='w4-oracle-checks.json':
            data=path.read_bytes();data.decode('utf-8');ck(b'\r' not in data);ck(not data.startswith(b'\xef\xbb\xbf'));files[path.name]=hashlib.sha256(data).hexdigest()
    receipt={'status':'PASS_PYTHON_ONLY_NOT_RTL_EXECUTION','assertions':checks,'N_vectors':len(ns['vectors']),'F8_vectors':len(fs['vectors']),'LUT_source_validation':table_checks,'files':files,'scope':'finite integer contract, not full model numeric quality or RTL handshake acceptance'}
    (a.directory/'w4-oracle-checks.json').write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS {} Python assertions; N{} F8{}, UTF8/LF; no RTL run'.format(checks,len(ns['vectors']),len(fs['vectors'])))


if __name__=='__main__':main()
