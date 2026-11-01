"""Freeze explicit W3 integer contract and oracle vectors; Python3.7/UTF8/LF."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from w3_integer_reference import ffn8, validate_native_table, e_vector, g_vector


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args()
    table=a.root/'project/rtl/block_v2/block_v2_g_tables.svh';check=validate_native_table(table.read_text(encoding='utf-8'))
    pattern=lambda seed:[[((n*29+k*17+seed)%63)-31 for k in range(8)] for n in range(8)]
    definitions=[
     ('normal', [16,-32,48,-64,80,-96,112,-128],pattern(3),pattern(19),pattern(41)),
     ('zero',[0]*8,pattern(7),pattern(11),pattern(17)),
     ('positive_extreme',[127]*8,[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)]),
     ('negative_extreme',[-128]*8,[[-128]*8 for _ in range(8)],[[127]*8 for _ in range(8)],[[127]*8 for _ in range(8)]),
     ('mixed_weights',[-113,97,41,-59,11,-7,67,-83],pattern(29),pattern(47),pattern(59)),
     ('sparse_distinct',[-128,127,-1,0,1,-64,64,2],[[127 if n==k else 0 for k in range(8)] for n in range(8)],[[(-128 if n%2 else 127) if k==(n+3)%8 else 0 for k in range(8)] for n in range(8)],[[((n+1)*(k+3)%31)-15 for k in range(8)] for n in range(8)])]
    vectors=[]
    for index,(name,x,wg,wu,wd) in enumerate(definitions):
        result=ffn8(x,wg,wu,wd);result['ingress_words_hex']=['%032x'%w for w in result.pop('ingress_words')];result['S_words_hex']={str(k):'%032x'%v for k,v in result.pop('S_words').items()};vectors.append(dict(id=name,index=index,x=x,Wgate=wg,Wup=wu,Wdown=wd,expected=result,RTL_status='NOT_EXECUTED_BY_ORACLE_GENERATOR'))
    d={'schema_version':1,'issue':151,'PR':152,'input_parent':'99d6df2e094febe4ea8fc9896301adbbfdc803ed','native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba','status':'BOUNDED_W3_NUMERIC_PROFILE_NOT_FULL_MODEL_QUALIFICATION','contract':{'x_weights':'signedS8 Fin7; W all n-major8*n+k','gate_up':'M raw Fin14; RNE right4 then clipS16 Fin10; op5 data0x104','mid':'G fn0 gated1; math-derived LUT SiLU(gate), interpolationRNE5; multiply up RNE10 clipS16 Fin10','down':'A signedS16 Fin10/B signedS8 Fin7 rawFin17; RNE7 clipS16 Fin10; op5data0x107','residual':'x signextendedS16 Fin7; E7 left3 toFin10','final':'E0 clipS16(down+residual) Fin10','done_saturated':'OR gate/up M readout, G, down M readout and E responses; distinct from error','input':'16x128=256B; effective200B plus56B actualzero padding','stage_S':'448..463 ingress;464gate465up466x16 467residual468mid469..471zero472down473final','normal_counts':{'S_requests_ACKs':32,'S_write':26,'S_read':6,'M_commands_responses':15,'loader_accept_done':3,'T_words':1,'E_services':2,'G_services':1}},'table_provenance':{'formula_script_git_blob_reported_by_root':'b75c058284c95191a9b0449addf79f2a44b39de0','table_path':'project/rtl/block_v2/block_v2_g_tables.svh','table_sha256':sha(table),'table_validation':check,'rounding':'Python round nearest ties-even at LUT nodes; integer RNE ties-even for interpolation/products','oracle_uses_math_not_table_values':True},'python':sys.version,'oracle_script_sha256':sha(Path(__file__).with_name('w3_integer_reference.py')),'vectors':vectors,'scope':'explicit small-kernel Fin/ranges; product scale, full F with N, complete model quality and PPA not granted'}
    a.output_dir.mkdir(parents=True,exist_ok=True);(a.output_dir/'w3-contract-vectors.json').write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS math LUT2564 nodes equals fixed table; froze{} FFN8 vectors; no RTL run'.format(len(vectors)))
    for v in vectors:print(v['index'],v['id'],v['expected']['S_words_hex']['473'],'sat='+str(v['expected']['done_saturated']))


if __name__=='__main__':main()
