"""Meaningful integer rounding, LUT-version, vector and packing checks only."""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from w3_integer_reference import rne,clip,pack,unpack,ffn8,e_vector,g_vector,validate_native_table


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--receipt',type=Path);a=ap.parse_args()
    p=a.directory/'w3-contract-vectors.json';d=json.loads(p.read_text(encoding='utf-8'));assertions=0
    for value in range(-2049,2050):
        for shift in range(11):
            assert rne(value,shift)==round(Fraction(value,1<<shift));assertions+=1
    for value in [-(1<<63),(1<<63)-1,-65537,-65535,65535,65537]:
        for shift in range(64):
            assert rne(value,shift)==round(Fraction(value,1<<shift));assertions+=1
    table=a.root/'project/rtl/block_v2/block_v2_g_tables.svh';lut=validate_native_table(table.read_text(encoding='utf-8'));assert sha(table)==d['table_provenance']['table_sha256'];assertions+=2565
    assert e_vector(8,1,[3,-3],[0]*8,[0]*8,2)['output']==[1,-2]
    assert e_vector(10,1,[3,-3],[0]*8,[0]*8,2)['output']==[2,-2]
    assert e_vector(13,1,[3,-3,65537,-65537],[0]*8,[0]*8,4)['output']==[2,-2,32767,-32768]
    assert e_vector(12,31,[-129,-128,127,128],[0]*8,[0]*8,4)['output']==[-128,-128,127,127]
    assert g_vector(1,False,[32767]*8,[0]*8,8)['output']==[16384]*8
    assert g_vector(1,True,[32767]*8,[1024]*8,8)['output']==[1024]*8
    assert g_vector(3,False,[0]*8,[0]*8,1)['output']==[710]+[0]*7
    assertions+=7
    for v in d['vectors']:
        expected=ffn8(v['x'],v['Wgate'],v['Wup'],v['Wdown'])
        assert ['%032x'%w for w in expected['ingress_words']]==v['expected']['ingress_words_hex']
        assert {str(k):'%032x'%w for k,w in expected['S_words'].items()}==v['expected']['S_words_hex']
        assert expected['done_saturated']==v['expected']['done_saturated']
        assert not expected['stage_saturated']['gate_M'] and not expected['stage_saturated']['up_M']
        assert len(expected['ingress_words'])==16 and all(expected['S_words'][x]==0 for x in [469,470,471])
        assert unpack(expected['S_words'][466],16,8)==v['x']
        assert expected['ingress_words'][0]>>64==0 and expected['ingress_words'][1:4]==[0,0,0]
        assertions+=7
    assert d['vectors'][2]['expected']['S_words_hex']['473']=='7fff'*8
    assert d['vectors'][3]['expected']['S_words_hex']['473']=='8000'*8
    assertions+=2
    for p in a.directory.iterdir():
        if p.is_file() and p.suffix in ['.py','.json','.md','.sv']:
            raw=p.read_bytes();raw.decode('utf-8');assert b'\r' not in raw and raw.endswith(b'\n');assertions+=1
    result={'status':'PASS_PYTHON_INTEGER_ORACLE_AND_SOURCE_TABLE_CHECKS_ONLY','utc_time':datetime.utcnow().isoformat()+'Z','parent':d['input_parent'],'native_source':d['native_source'],'python':sys.version,'assertions':assertions,'LUT':lut,'contract_sha256':sha(a.directory/'w3-contract-vectors.json'),'reference_sha256':sha(a.directory/'w3_integer_reference.py'),'checker_sha256':sha(Path(__file__)),'table_sha256':sha(table),'new_RTL_execution_by_oracle_agent':False,'scope':'small explicit Fin FFN8 arithmetic and finite adapter expected vectors; not full model quality or PPA'}
    if a.receipt:a.receipt.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS {} integer/reference/table/UTF8LF assertions; LUT2564 nodes; no RTL execution'.format(assertions))


if __name__=='__main__':main()
