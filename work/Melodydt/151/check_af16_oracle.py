"""Meaningful mathematical/source/contract checks; never runs RTL."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from af16_integer_reference import compose,load_reference


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args();d=a.directory
    data=json.loads((d/'af16-contract-vectors.json').read_text(encoding='utf-8'))
    contract=json.loads((d/'af16-tb-contract.json').read_text(encoding='utf-8'))
    tb=(d/'block_w4_af16_tb.sv').read_text(encoding='utf-8');checks=0
    def check(value):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError('AF16 oracle check '+str(checks))
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    for dep in data['reference_dependencies']:check(sha(a.root/dep['path'])==dep['sha256'])
    aa=load_reference(a.root,'a16_integer_reference.py');ff=load_reference(a.root,'f16_integer_reference.py')
    exp=aa.validate_exp_table((a.root/'project/rtl/block_v2/block_v2_n_exp.svh').read_text(encoding='utf-8'))
    act=ff.validate_native_table((a.root/'project/rtl/block_v2/block_v2_g_tables.svh').read_text(encoding='utf-8'))
    check(exp['all_equal']);check(act['equal_all_nodes'])
    check(len(data['vectors'])==10)
    for v in data['vectors']:
        original=v['expected'];r=compose(a.root,v['A_input'],v['F_gamma'],v['F_gate_weights'],v['F_up_weights'],v['F_down_weights'])
        normalized=json.loads(json.dumps(r));check(normalized==original)
        check(len(r['ingress_words'])==40);check(len(r['parameter_words'])==13)
        check(r['ingress_words'][27:]==r['parameter_words'])
        check(sum(len(ws) for ws in r['A']['S_write_history'].values())==73)
        for row in range(2):
            check(r['F'][row]['ingress_words'][0]==r['A_hidden_words'][row])
            check(r['F'][row]['ingress_words'][1:4]==[0,0,0])
            check(r['F'][row]['ingress_words'][4:]==r['parameter_words'])
            check(sum(len(ws) for ws in r['F_S_write_history'][row].values())==29)
            check(r['F'][row]['residual']==r['A']['final'][row])
            check(r['final_words'][row]==ff.pack(r['F'][row]['final'],16))
        check(r['done_saturated']==(r['A']['done_saturated'] or any(f['done_saturated'] for f in r['F'])))
    v=data['vectors'];check(v[0]['expected']['final_words'][0]==v[1]['expected']['final_words'][0])
    check(v[0]['expected']['final_words'][1]!=v[1]['expected']['final_words'][1])
    check(v[2]['expected']['final_words']==v[2]['expected']['A_hidden_words'])
    check(any(lane%8 for row in v[0]['expected']['A']['final'] for lane in row))
    check(v[0]['A_input']['gamma']!=v[0]['F_gamma'])
    check(any(vv['expected']['done_saturated'] for vv in v));check(any(not vv['expected']['done_saturated'] for vv in v))
    # Same signed ties-to-even convention in the two previously frozen oracles.
    for shift in [1,7,10,14,25]:
        for q in range(-9,10):
            for rem in [-1,0,1]:
                x=q*(1<<shift)+(1<<(shift-1))+rem
                check(aa.rne(x,shift)==ff.rne(x,shift))
    check(len(contract['expected_case_ids'])==33);check(len(set(contract['expected_case_ids']))==33)
    names=re.findall(r'\d+:case_name="([A-Z0-9_]+)";',tb)
    check(names==contract['expected_case_ids']);check(sha(d/'block_w4_af16_tb.sv')==contract['tb_sha256'])
    check('PASS_W4_AF16 cases=%0d' in tb);check('if(cases!=33)' in tb)
    check(contract['normal_counts']==data['normal_counts'])
    result={'schema_version':1,'status':'PASS_INDEPENDENT_PYTHON_MATH_AND_STATIC_CONTRACT_NOT_RTL',
      'assertions':checks,'vectors':10,'cases':33,'EXP_table_validation':exp,'activation_table_validation':act,
      'TB_sha256':contract['tb_sha256'],'vectors_sha256':sha(d/'af16-contract-vectors.json'),
      'reference_dependencies':data['reference_dependencies'],'executed_RTL':False,
      'limits':'composed fixed integer profiles;not full model numerical accuracy or physical acceptance'}
    (d/'af16-oracle-checks.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS_AF16_ORACLE assertions='+str(checks)+' vectors=10 cases=33;noRTLrun')


if __name__=='__main__':main()
