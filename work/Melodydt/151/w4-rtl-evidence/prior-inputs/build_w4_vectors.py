"""Freeze W4 N/F8 integer expectations. No RTL execution or DUT output input."""
import argparse
import hashlib
import json
from pathlib import Path
from w4_integer_reference import n_group,f8,validate_exp_table,validate_native_table,pack


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):path.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def hexwords(d):
    for key in list(d):
        if key.endswith('_words'):d[key+'_hex']=['%032x'%v for v in d.pop(key)]
    return d


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    ep=a.root/'project/rtl/block_v2/block_v2_n_exp.svh';gp=a.root/'project/rtl/block_v2/block_v2_g_tables.svh'
    definitions=[
      ('rms8_mixed',1,[16,-32,48,-64,80,-96,112,-128],[1024]*8,1),
      ('rms8_zero',1,[0]*8,[1024]*8,1),
      ('rms8_extreme_gamma_sat',1,[-32768,32767,-32768,32767,-1,1,0,7],[32767,-32768,32767,-32768,1024,-1024,0,3072],1),
      ('rms1_tail',1,[-32768],[-32768],1),
      ('rms257_tail',1,[((i*997)%65536)-32768 for i in range(257)],[1024 if i%2 else -2048 for i in range(257)],17),
      ('l2_8_signed_gamma',2,[-127,63,-31,15,-7,3,-1,0],[1024,-1024,2048,-2048,32767,-32768,0,1],1),
      ('l2_257_tail',2,[((i*173)%8192)-4096 for i in range(257)],[1024]*257,9),
      ('softmax257_last_newmax',0,[-4096+(i*29)%3072 for i in range(256)]+[3072],None,0),
      ('softmax8_equal_unsigned32768',0,[-123]*8,None,0),
      ('softmax9_cutoff_and_round',0,[-32768,-16385,-16384,-16383,-17,-16,-8,-1,0],None,0),
      ('softmax1',0,[32767],None,0)]
    nv=[]
    for i,(name,mode,x,g,eps) in enumerate(definitions):
        r=n_group(mode,x,g,eps);n=len(r['raw_words'])
        nv.append({'index':i,'id':name,'mode':mode,'count':len(x),'epsilon':eps,'x':x,'gamma':g,'words':n,'normal_counts':{'S_reads':3*n,'S_writes':n if mode else 2*n,'S_ACKs':4*n if mode else 5*n,'N_commands':2+2*n if mode else 3+3*n},'expected':hexwords(r)})
    old=json.loads((a.root/'project/tests/block_connection_w3/w3-contract-vectors.json').read_text(encoding='utf-8')) if (a.root/'project/tests/block_connection_w3/w3-contract-vectors.json').exists() else None
    if old is None:
        old=json.loads((a.directory.parents[2]/'w3-99d6df2/drafts/oracle/w3-contract-vectors.json').read_text(encoding='utf-8'))
    fv=[]
    for v in old['vectors']:
        r=f8(v['x'],v['Wgate'],v['Wup'],v['Wdown'])
        r['S_words'][474]=pack(r['normalized_x'],16);r['S_words'][475]=pack([1024]*8,16)
        r['S_words_hex']={str(k):'%032x'%w for k,w in r.pop('S_words').items()}
        r['ingress_words_hex']=['%032x'%w for w in r.pop('ingress_words')]
        r['norm']=hexwords(r['norm']);r['narrow_word_hex']='%032x'%r.pop('narrow_word')
        fv.append(dict(index=v['index'],id=v['id'],x=v['x'],Wgate=v['Wgate'],Wup=v['Wup'],Wdown=v['Wdown'],expected=r))
    provenance={'parent':'0101cc7e1e6d5718455fb45b61c7428439efc09a','native':'707878621b2add4ed218b8c43df2e95c9a56e2ba','oracle_sha256':sha(a.directory/'w4_integer_reference.py'),'EXP':{'path':'project/rtl/block_v2/block_v2_n_exp.svh','sha256':sha(ep),'validation':validate_exp_table(ep.read_text(encoding='utf-8'))},'G':{'sha256':sha(gp),'validation':validate_native_table(gp.read_text(encoding='utf-8'))}}
    save(a.directory/'w4-n-vectors.json',{'schema_version':1,'status':'FROZEN_MATH_EXPECTATIONS_NOT_RTL_EXECUTION','provenance':provenance,'vectors':nv})
    save(a.directory/'w4-f8-vectors.json',{'schema_version':1,'status':'BOUNDED_PRENORM_F8_NOT_FULL_F_OR_MODEL_QUALITY','provenance':provenance,'normal_counts':{'S_requests_ACKs':39,'S_write':29,'S_read':10,'N_service':1,'N_native_commands_responses':4,'M_commands_responses':15,'loader_accept_done':3,'E_services':2,'G_services':1,'T_words':1},'vectors':fv})
    print('PASS independent mathEXP1025/G2564 source nodes; froze {} N / {} F8 vectors, no RTL run'.format(len(nv),len(fv)))
    for v in fv:print(v['index'],v['id'],'norm',v['expected']['normalized_x'],'A8',v['expected']['projection_x'],'final',v['expected']['S_words_hex']['473'],'sat',v['expected']['done_saturated'])


if __name__=='__main__':main()
