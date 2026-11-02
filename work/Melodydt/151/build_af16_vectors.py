"""Freeze AF16 math expectations; output directory never selects dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
from af16_integer_reference import compose, REFERENCE_DEPENDENCIES


NORMAL_COUNTS = {'input':40,'A_input':27,'F_input':34,'S':181,'S_write':131,
 'S_read':50,'M':72,'N_native':28,'E_services':10,'G_services':2,'G_pairs':8,
 'loader':12,'wide_reads':26,'A_beats':18,'B_beats':14,
 'child_T_take':4,'child_T_release':3,'host_output':2}


def serial(value):
    if isinstance(value,dict):
        return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,list):return [serial(v) for v in value]
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    args=p.parse_args();args.directory.mkdir(parents=True,exist_ok=True)
    source=args.root/'work/Melodydt/151/a16-contract-vectors.json'
    original=json.loads(source.read_text(encoding='utf-8'))
    pattern=lambda s:[[((c*17+k*11+s)%41)-20 for k in range(8)] for c in range(8)]
    gammas=[[1536,512,-1024,0,2048,-512,1024,3072],
            [1536,512,-1024,0,2048,-512,1024,3072],[0]*8,
            [-1024,2048,512,-512,0,3072,-3072,1024],
            [32767,-32768,0,1,-1,1024,-1024,17],[32767]*8,
            [-32768]*8,[1024,0,-2048,3072,-512,512,1536,-1024],
            [1701,-2103,19,0,1024,-32768,32767,711],
            [-1711,2201,-13,512,0,1024,-2048,32767]]
    vectors=[]
    for i, av in enumerate(original['vectors']):
        if i in (5,6):
            weights=[[[127 if i==5 else (-128 if (c+k)%2 else 127) for k in range(8)] for c in range(8)] for _ in range(3)]
        else:
            wi=0 if i==1 else i  # causal pair differs only in the future X row
            weights=[pattern(3+wi*7),pattern(11+wi*5),pattern(29+wi*3)]
        a_input={k:av[k] for k in ['X','gamma','Wq','Wk','Wv','Wo','coeff']}
        result=compose(args.root,a_input,gammas[i],*weights)
        vectors.append({'index':i,'id':av['id'],'A_input':a_input,'F_gamma':gammas[i],
          'F_gate_weights':weights[0],'F_up_weights':weights[1],'F_down_weights':weights[2],
          'expected':serial(result)})
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    dependencies=REFERENCE_DEPENDENCIES+['work/Melodydt/151/a16-contract-vectors.json']
    d={'schema_version':1,'status':'INDEPENDENT_COMPOSED_INTEGER_EXPECTATIONS_NOT_RTL_EXECUTION',
       'research_parent':'cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6',
       'native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba',
       'reference_sha256':sha(Path(__file__).with_name('af16_integer_reference.py')),
       'reference_dependencies':[{'path':s,'sha256':sha(args.root/s)} for s in dependencies],
       'normal_counts':NORMAL_COUNTS,'vectors':vectors,
       'scope':'H8,two causal tokens,one head,I8;bit-exact A16 hidden to F16 per row;not full model quality/physical/network qualification'}
    (args.directory/'af16-contract-vectors.json').write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS_AF16_MATH_VECTORS count='+str(len(vectors)))
    for v in vectors:print(v['index'],v['id'],['%032x'%w for w in v['expected']['final_words']],v['expected']['done_saturated'])


if __name__=='__main__':main()
