"""Freeze F16 explicit integer profile without DUT-derived expectations."""
import argparse
import hashlib
import json
from pathlib import Path
from f16_integer_reference import f16,validate_exp_table,validate_native_table


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def definitions():
    pat=lambda s:[[((n*29+k*17+s)%63)-31 for k in range(8)] for n in range(8)]
    defs=[('s16_nonmultiple8',[13,-259,777,-1023,1537,-2001,4095,-8191],[1024]*8,pat(3),pat(19),pat(41)),
      ('zero_x_variable_gamma',[0]*8,[-2048,0,512,1024,3072,-1024,32767,-32768],pat(7),pat(11),pat(17)),
      ('positive_extreme_saturation',[32767]*8,[32767]*8,[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)]),
      ('negative_extreme_saturation',[-32768]*8,[-32768]*8,[[-128]*8 for _ in range(8)],[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)]),
      ('signed_nonunity_gamma',[-1137,973,419,-599,113,-71,677,-839],[-2048,512,0,1536,-1024,3072,-3072,1024],pat(29),pat(47),pat(59)),
      ('zero_gamma_preserves_full_s16_x',[1,-1,7,-7,15,-15,32767,-32768],[0]*8,pat(23),pat(31),pat(37)),
      ('sparse_layout',[-32768,32767,-1,0,1,-16381,16379,19],[1024,2048,-1024,0,512,-512,1536,3072],[[127 if n==k else 0 for k in range(8)] for n in range(8)],[[(-128 if n%2 else 127) if k==(n+3)%8 else 0 for k in range(8)] for n in range(8)],pat(13))]
    state=0x13579bdf
    def next_code(bits):
        nonlocal state
        state=(1664525*state+1013904223)&0xffffffff
        raw=(state>>(32-bits))&((1<<bits)-1)
        return raw-(1<<bits) if raw&(1<<(bits-1)) else raw
    for i in range(2):
        x=[next_code(16) for _ in range(8)];gamma=[next_code(16) for _ in range(8)]
        weights=[[[next_code(8) for _ in range(8)] for _ in range(8)] for _ in range(3)]
        defs.append(('seeded_random_'+str(i),x,gamma,*weights))
    defs.append(('zero_gamma_non8_residual',[11,19,-27,35,-43,51,-59,67],[0]*8,pat(43),pat(51),pat(61)))
    return defs


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    table=a.root/'project/rtl/block_v2/block_v2_g_tables.svh';exp=a.root/'project/rtl/block_v2/block_v2_n_exp.svh'
    gcheck=validate_native_table(table.read_text(encoding='utf-8'));ncheck=validate_exp_table(exp.read_text(encoding='utf-8'))
    vectors=[]
    for i,(name,x,gamma,wg,wu,wd) in enumerate(definitions()):
        r=f16(x,gamma,wg,wu,wd);r['ingress_words_hex']=['%032x'%w for w in r.pop('ingress_words')];r['S_words_hex']={str(k):'%032x'%v for k,v in r.pop('S_words').items()};r['normalized_input_word_hex']='%032x'%r.pop('normalized_input_word')
        for field in ['raw_words','gamma_words','output_words']:r['norm'][field+'_hex']=['%032x'%w for w in r['norm'].pop(field)]
        vectors.append({'index':i,'id':name,'x':x,'gamma':gamma,'Wgate':wg,'Wup':wu,'Wdown':wd,'expected':r})
    d={'schema_version':1,'status':'FROZEN_INDEPENDENT_INTEGER_EXPECTATIONS_NOT_RTL_OR_MODEL_QUALITY','research_parent':'febc042','native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba','oracle_sha256':sha(Path(__file__).with_name('f16_integer_reference.py')),'table_provenance':{'G':{'sha256':sha(table),'validation':gcheck},'EXP':{'sha256':sha(exp),'validation':ncheck}},'contract':{'X_gamma':'signedS16Fin10,all8lanes; gamma inputvariable; epsilon1rawsquarecodeunit','weights':'three8x8signedS8Fin7 matrices,n-major','Norm':'nativeRMS exactfloor division/isqrt/factor,RNE30 clipS16Fin10; no narrowing toS8','gate_up_down':'M A16Fin10*B8Fin7 rawFin17;factor1/left0,op5S16RNE7Fin10 allthree','G':'SiLU gatefn0,gated1,multiplyup,RNE10clipS16Fin10','residual':'originalX Fin10 preserved at466/467,identityE7shift0;E0 clipS16(down+originalX)','input':'17x128:0X,1..3actualzero,4..15weights,16gamma->S475','layout':'448..451normAcontainer;452..463weights;464gate465up466originalX467residual468mid469..471padding472down473final474norm475gamma','normal_counts':{'S_requests_ACKs':39,'S_write':29,'S_read':10,'M_commands_responses':15,'loader_accept_done':3,'N_service':1,'N_commands_responses':4,'E_services_native':2,'G_services':1,'G_pairs_accepted_retired':4,'T_words':1},'scope':'boundedH8/I8 explicitprofile,not fullF/allmodels/L4/MEM/productphysicalacceptance'},'vectors':vectors}
    (a.directory/'f16-contract-vectors.json').write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS mathG2564/EXP1025 nodes match source;frozen{}F16vectors;noRTLrun'.format(len(vectors)))
    for v in vectors:print(v['index'],v['id'],v['expected']['S_words_hex']['473'],'sat',v['expected']['done_saturated'])


if __name__=='__main__':main()
