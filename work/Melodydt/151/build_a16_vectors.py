"""Freeze pure mathematical A16 vectors, source table checked not consumed."""
import argparse,json,hashlib
from pathlib import Path
from a16_integer_reference import a16,coefficients,validate_exp_table

def definitions():
    pat=lambda s:[[((c*19+k*13+s)%31)-15 for k in range(8)] for c in range(8)]
    x0=[13,-259,777,-1023,1537,-2001,4095,-8191];x1=[101,-311,607,-997,1499,-1901,3089,-4093]
    ws=[pat(3),pat(11),pat(19),pat(27)];cs=[coefficients(0),coefficients(1)]
    defs=[('real_rope_causal_baseline',[x0,x1],[1024]*8,*ws,cs),('future_token_changed',[x0,[9001,-8003,7001,-6007,5003,-4001,3001,-2003]],[1024]*8,*ws,cs),('zero_gamma_exact_residual',[[1,-1,7,-7,15,-15,32767,-32768],[11,19,-27,35,-43,51,-59,67]],[0]*8,*ws,cs),('signed_nonunity_gamma',[x0,x1],[-2048,512,0,1536,-1024,3072,-3072,1024],*ws,cs),('zero_rows_variable_gamma',[[0]*8,[0]*8],[-32768,32767,0,1024,-1024,512,1536,-3072],*ws,cs),('positive_saturation',[[32767]*8,[32767,-32768]*4],[32767]*8,*([[[127]*8 for _ in range(8)]]*4),cs),('negative_saturation',[[-32768]*8,[-32768,32767]*4],[-32768]*8,*([[[(-128 if (c+k)%2 else 127) for k in range(8)] for c in range(8)]]*4),cs)]
    eye=[[127 if c==k else 0 for k in range(8)] for c in range(8)]
    defs.append(('quarter_turn_sparse_layout',[[-32768,32767,-1,0,1,-16381,16379,19],[71,-89,107,-131,157,-181,211,-239]],[1024,2048,-1024,0,512,-512,1536,3072],eye,pat(7),eye,pat(29),[[16384,0]*4,[0,16384]*4]))
    state=0x7ad139b5
    def next_value(bits):
        nonlocal state
        state=(1664525*state+1013904223)&0xffffffff;n=(state>>(32-bits))&((1<<bits)-1)
        return n-(1<<bits) if n&(1<<(bits-1)) else n
    for i in range(2):
        xx=[[next_value(16) for _ in range(8)] for _ in range(2)];gg=[next_value(16) for _ in range(8)];ww=[[[next_value(8) for _ in range(8)] for _ in range(8)] for _ in range(4)]
        defs.append(('seeded_random_'+str(i),xx,gg,*ww,cs))
    return defs

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    table=a.root/'project/rtl/block_v2/block_v2_n_exp.svh';validation=validate_exp_table(table.read_text(encoding='utf-8'));vectors=[]
    for i,(name,x,g,wq,wk,wv,wo,c) in enumerate(definitions()):
        r=a16(x,g,wq,wk,wv,wo,c);r['ingress_words_hex']=['%032x'%w for w in r.pop('ingress_words')];r['S_write_history_hex']={str(k):['%032x'%w for w in values] for k,values in r.pop('S_write_history').items()};r['S_final_hex']={str(k):'%032x'%w for k,w in r.pop('S_final').items()}
        vectors.append({'index':i,'id':name,'X':x,'gamma':g,'Wq':wq,'Wk':wk,'Wv':wv,'Wo':wo,'coeff':c,'expected':r})
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    d={'schema_version':1,'research_parent':'f665230a392cbcf2422594167e1f163d5e5d1c80','native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba','status':'INDEPENDENT_MATH_EXPECTATIONS_NOT_RTL_EXECUTION_OR_MODEL_QUALITY','reference_sha256':sha(Path(__file__).with_name('a16_integer_reference.py')),'EXP_table':{'sha256':sha(table),'validation':validation},'normal_counts':{'input':27,'S':103,'S_write':73,'S_read':30,'M':42,'loader':6,'wide_reads':14,'A_beats':12,'B_beats':8,'N_services':4,'N_native':20,'E_services':6,'T_words':2},'numeric_profile':'X/gammaS16Fin10;Wq/k/v/oS8Fin7;QKV/WoRNE7,adjacentpairRoPEQ14RNE14,QKfactor11585RNE25,causalprefixNcount1/2Q14,PV RNE14,originalX residualclipS16','scope':'H8,two tokens,head1, no bias/cache;not fullsamplemodel/layout/precision/physical qualification','vectors':vectors}
    (a.directory/'a16-contract-vectors.json').write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS independentmathEXP1025;frozen10A16vectors,noRTLrun')
    for v in vectors:print(v['index'],v['id'],'final',v['expected']['S_final_hex']['528'],v['expected']['S_final_hex']['529'],'sat',v['expected']['done_saturated'])

if __name__=='__main__':main()
