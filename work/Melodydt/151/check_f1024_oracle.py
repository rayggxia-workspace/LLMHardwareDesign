"""Independent exact full-size math/stream-contract checks, no RTL launch."""
import argparse,json,hashlib,re
from pathlib import Path
from fractions import Fraction
from f1024_integer_reference import f1024,prior,weight,request_fields,weight_beat


def binary_root(n):
    lo,hi=0,1<<((n.bit_length()+2)//2)
    while lo+1<hi:
        mid=(lo+hi)//2
        if mid*mid<=n:lo=mid
        else:hi=mid
    return lo


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--observed-weight-directory',type=Path);a=p.parse_args();d=a.directory
    data=json.loads((d/'f1024-contract-vectors.json').read_text(encoding='utf-8'))
    contract=json.loads((d/'f1024-tb-contract.json').read_text(encoding='utf-8'))
    tb_path=a.root/'project/tb/block_connection_w4/block_w4_f1024_tb.sv'
    tb=tb_path.read_text(encoding='utf-8');checks=0
    def ck(v):
        nonlocal checks
        checks+=1
        if not v:raise AssertionError('F1024 check '+str(checks))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for dep in data['reference_dependencies']:ck(sha(a.root/dep['path'])==dep['sha256'])
    ck(len(data['vectors'])==2);ck(len(data['selected_ungrouped_full_dot_checks'])==48)
    selected=[]
    for v in data['vectors']:
        e=v['expected'];r=f1024(a.root,v['X'],v['gamma'],v['seed']);ck(e==r)
        rad=(sum(x*x for x in v['X'])<<16)//1024+65536;rt=binary_root(rad)
        ck(rt==e['norm_root']);factor=(1<<38)//rt;ck(factor==e['norm_factor'])
        rounded=[round(Fraction(xx*gg*factor,1<<30)) for xx,gg in zip(v['X'],v['gamma'])]
        ck([max(-32768,min(32767,x)) for x in rounded]==e['norm'])
        for m,key,src in [(0,'gate_raw',e['norm']),(1,'up_raw',e['norm']),(2,'down_raw',e['mid'])]:
            for row in [x for x in data['selected_ungrouped_full_dot_checks'] if x['fixture']==v['id'] and x['matrix']==m]:
                direct=sum(value*(((13*row['n']+7*k+v['seed']+41*m)%251)-125) for k,value in enumerate(src))
                ck(direct==row['ungrouped_raw']==e[key][row['n']]);selected.append(row)
        ck(len(e['words']['norm'])==128);ck(len(e['words']['mid'])==384);ck(len(e['words']['output'])==128)
        ck(e['done_saturated']==any(e['stage_saturated'].values()))
    ck(data['vectors'][1]['expected']['final']==data['vectors'][1]['X'])
    ck(data['vectors'][1]['expected']['done_saturated']==False)
    seen=set();counts=[0,0,0]
    for seq in range(36864):
        m,g,c=request_fields(seq);ck((m,g,c) not in seen);seen.add((m,g,c));counts[m]+=1
        ck(0<=g<(128 if m==2 else 384));ck(0<=c<(96 if m==2 else 32))
    ck(counts==[12288]*3)
    for seed in [37,91]:
        for m,g,c in [(0,0,0),(0,383,31),(1,123,17),(2,127,95)]:
            for beat in range(16):
                word=weight_beat(m,g,c,beat,seed)
                for lane,value in enumerate(word):
                    n=g*8+2*(beat%4)+lane//8;k=c*32+8*(beat//4)+lane%8
                    ck(value==(weight(m,n,k,seed)&255))
    ck(len(contract['expected_case_ids'])==26 and len(set(contract['expected_case_ids']))==26)
    ck(re.findall(r'\d+:case_name="([A-Z0-9_]+)";',tb)==contract['expected_case_ids'])
    ck(sha(tb_path)==contract['tb_sha256'])
    ck('p_index<=p_index+1' in tb and 'p_active<=1' in tb)
    ck('PASS_W4_F1024 cases=%0d' in tb and 'if(cases!=26)' in tb)
    ck('accepted-ac0!=589824' in tb and 'execs-x0!=36864' in tb)
    ck('dump_bytes!=9437184' in tb and '"wb"' in tb)
    observed=[]
    if a.observed_weight_directory:
        for v in data['vectors']:
            path=a.observed_weight_directory/('weights-'+v['id']+'.bin')
            ck(path.stat().st_size==9437184);ck(sha(path)==v['canonical_weight_stream']['sha256'])
            observed.append({'fixture':v['id'],'bytes':path.stat().st_size,'sha256':sha(path),'matches_canonical':True})
    result={'status':'PASS_FULL_DIMENSION_PYTHON_AND_STATIC_CONTRACT_NOT_RTL_EXECUTION',
      'assertions':checks,'fixtures':2,'cases':26,'selected_ungrouped_full_dot_count':len(selected),
      'request_schedule_matrix_counts':counts,'request_schedule_no_missing_or_duplicate_chunks':True,
      'observed_weight_streams_checked':observed,'tb_sha256':contract['tb_sha256'],
      'scope':'mathematical/static checks,not simulation or trained model/physical quality'}
    (d/'f1024-oracle-checks.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print('PASS_F1024_ORACLE assertions='+str(checks)+';ungrouped48;noRTLrun')


if __name__=='__main__':main()
