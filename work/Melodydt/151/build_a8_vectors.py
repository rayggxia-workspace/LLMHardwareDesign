"""Freeze A8 mathematical JSON and literal SV include; Python3.7/UTF8LF."""
import argparse
import hashlib
import json
from pathlib import Path
from a8_integer_reference import a8,validate_native_exp,QK_FACTOR


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def definitions():
    pattern=lambda seed:[[((t*37+d*19+seed)%191)-95 for d in range(8)] for t in range(8)]
    eye=[[127 if t==d else 0 for d in range(8)] for t in range(8)]
    return [
      ('nonconstant_asymmetric',[16,-32,48,-64,80,-96,112,-128],pattern(11),pattern(53)),
      ('equal_scores_distinct_values',[91,-77,63,-49,35,-21,7,-3],[[31,-27,23,-19,15,-11,7,-3] for t in range(8)],pattern(79)),
      ('zero_query_nonzero_values',[0]*8,pattern(97),pattern(139)),
      ('last_key_newmax_extreme',[127]*8,[[-128]*8 for t in range(7)]+[[127]*8],pattern(17)),
      ('alternating_signed_extreme',[-128,127,-128,127,-128,127,-128,127],[[(-128 if (t+d)%2==0 else 127) for d in range(8)] for t in range(8)],[[(-128 if (c*3+t)%5<2 else 127) for t in range(8)] for c in range(8)]),
      ('sparse_identity_layout',[-128,127,-1,0,1,-64,64,2],eye,[[((c+1)*(t+3)*11)%255-128 for t in range(8)] for c in range(8)]),
      ('negative_query_mixed_keys',[-127,-113,-97,-83,-61,-43,-29,-11],pattern(47),pattern(121)),
      ('constant_value_channels',[127,-128,127,-128,127,-128,127,-128],pattern(3),[[[-128,-97,-31,-1,0,1,63,127][c]]*8 for c in range(8)])]


def sv_include(vectors):
    lines=['// Independent generated A8 literals. Include inside an SV TB module.','// Q/K/V S8Fin7; score S16Fin10; EXP U16; prob S16Q14; final S16Fin10.','localparam integer A8_VECTOR_COUNT={};'.format(len(vectors))]
    records=[('a8_input_word',128,[(v['index']*16+i,w) for v in vectors for i,w in enumerate(v['expected']['ingress_words_hex'])],'input integer vector_no,word_index;','vector_no*16+word_index'),('a8_stage_word',128,[(v['index']*1024+int(k),w) for v in vectors for k,w in v['expected']['S_words_hex'].items()],'input integer vector_no,address;','vector_no*1024+address'),('a8_qk_carrier',128,[(v['index']*2+i,w) for v in vectors for i,w in enumerate(v['expected']['M_QK_op5_carriers_hex'])],'input integer vector_no,half_index;','vector_no*2+half_index'),('a8_pv_carrier',128,[(v['index']*2+i,w) for v in vectors for i,w in enumerate(v['expected']['M_PV_op5_carriers_hex'])],'input integer vector_no,half_index;','vector_no*2+half_index')]
    for name,bits,items,args,index in records:
        lines+=['function automatic [127:0] '+name+';',args,'begin case('+index+')']
        lines+=[' {}:{}=128\'h{};'.format(i,name,w) for i,w in items]
        lines+=[' default:'+name+"=128'hbad;",'endcase end','endfunction']
    lines+=['function automatic a8_expected_saturated;input integer vector_no;begin case(vector_no)']
    lines+=[' {}:a8_expected_saturated=1\'b{};'.format(v['index'],int(v['expected']['done_saturated'])) for v in vectors]
    lines+=[' default:a8_expected_saturated=1\'bx;endcase end endfunction']
    lines+=['function automatic [8*100-1:0] a8_vector_name;input integer vector_no;begin case(vector_no)']
    lines+=[' {}:a8_vector_name="{}";'.format(v['index'],v['id']) for v in vectors]
    lines+=[' default:a8_vector_name="invalid";endcase end endfunction']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    ep=a.root/'project/rtl/block_v2/block_v2_n_exp.svh';mp=a.root/'project/rtl/block_v2/block_v2_m.sv';np=a.root/'project/rtl/block_v2/block_v2_n.sv'
    table_check=validate_native_exp(ep.read_text(encoding='utf-8'));vectors=[]
    for i,(name,q,k,v) in enumerate(definitions()):
        r=a8(q,k,v)
        for field in ['ingress_words','M_QK_op5_carriers','M_PV_op5_carriers']:r[field+'_hex']=['%032x'%w for w in r.pop(field)]
        r['S_words_hex']={str(k):'%032x'%w for k,w in r.pop('S_words').items()}
        vectors.append({'index':i,'id':name,'Q':q,'K_token_dimension':k,'V_channel_token':v,'expected':r})
    data={'schema_version':1,'research_parent':'1d722477564e14f7dc93e39ce8e28b8e2d150cb0','native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba','status':'FROZEN_MATH_EXPECTATIONS_NOT_RTL_EXECUTION_OR_FULL_ATTENTION','oracle':{'file':'a8_integer_reference.py','sha256':sha(Path(__file__).with_name('a8_integer_reference.py')),'no_DUT_results_used':True},'native_sources':{'M':{'path':'project/rtl/block_v2/block_v2_m.sv','sha256':sha(mp)},'N':{'path':'project/rtl/block_v2/block_v2_n.sv','sha256':sha(np)},'EXP':{'path':'project/rtl/block_v2/block_v2_n_exp.svh','sha256':sha(ep),'math_validation':table_check}},'contract':{'shape':'one query, eight keys/tokens, head dimension8, output channels8','QKV':'signedS8Fin7','K_layout':'K[token][dimension], M B n-major token*8+dimension','V_layout':'V[channel][token], M B n-major channel*8+token','QK':'dot rawFin14, multiply signedS16 factor11585(Q15), leftshift0; op5 widthS16/RNE19 -> Fin10','QK_M_commands':{'CLEAR_opcode':6,'factor':QK_FACTOR,'readout_data':0x113,'EXEC_data':0x9884},'N':'Softmax8 exact U16 EXPcode -> factor floor(2^44/sumEXP), RNE30 -> nonnegativeS16Q14','PV':'M A16 probabilitiesQ14 x B8 VFin7; rawFin21, factor1 left0, op5S16 RNE11 -> Fin10','PV_M_commands':{'CLEAR_opcode':6,'factor':1,'readout_data':0x10b,'EXEC_data':0x9885},'ingress':'12x128b, effectiveQ8+K64+V64=136B; Qpadding56B actually zero','S_layout':{'448..451':'Q8+actualzero padding','452..455':'K token/dimension','456..459':'V channel/token','460':'score8S16Fin10','461':'EXP8U16','464':'prob8S16Q14, M A base four-word aligned','465..467':'actualzero A padding','468':'final8S16Fin10'},'normal_counts':{'S_requests_ACKs':23,'S_write':19,'S_read':4,'M_commands_responses':10,'loader_accept_done':2,'N_services':1,'N_commands_responses':6,'T_words':1},'saturation':'OR observed M QK/N/M PV sat, independent from protocol error; current legal bounded S8 vectors do not reach S16 clip','scope':'QK/Softmax/PV compute slice only; no QKV projection, Norm, RoPE, mask, KV cache, output projection/residual, multihead or full-model quality'},'vectors':vectors}
    save(a.directory/'a8-contract-vectors.json',data);(a.directory/'a8_expected_vectors.svh').write_bytes(sv_include(vectors).encode('utf-8'))
    print('PASS independent math EXP1025 equals native; froze{} A8 vectors; no RTL execution'.format(len(vectors)))
    for v in vectors:print(v['index'],v['id'],'score',v['expected']['scores'],'prob',v['expected']['softmax']['prob'],'out',v['expected']['S_words_hex']['468'])


if __name__=='__main__':main()
