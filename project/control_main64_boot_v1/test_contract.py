"""Boundary checks on the R8.1 contract and deterministic glue generation."""
import json,tempfile
from pathlib import Path
from contract import contract,native_sources,host_allowed,topology,HERE
from generate import endpoint,control_top,host_front,boot_top


def main():
    cases=[]
    def ok(name,condition):assert condition,name;cases.append(name)
    d=contract();ok('contract-file-matches',json.loads((HERE/'contract.json').read_text())==d)
    ok('U-E-three-source',native_sources(0,0,3))
    for name,args in [('U-N-three-source',(0,1,3)),('F-E-three-source',(1,0,3)),('C-R-two-source',(2,2,2)),
                      ('unknown-lane',(0,2,0)),('negative-arity',(0,0,-1)),('boolean-arity',(0,0,True)),('unknown-kind',(5,0,1))]:
        try:native_sources(*args)
        except ValueError:cases.append('reject:'+name)
        else:raise AssertionError(name)
    ok('U-no-host-read',not host_allowed(0,11))
    ok('J-no-ordinary-S-IO',not host_allowed(4,11) and not host_allowed(4,12))
    for k in range(5):
        ok(f'no-seed-after-deploy-{k}',not host_allowed(k,12,True))
        ok(f'fragment-type-{k}',host_allowed(k,14)==(k==4))
        ok(f'topology-{k}',topology(k)==0x01938000+17*k)
    for pair in d['pairs']:
        a,b=pair['kinds'];ok('cohort-topology:'+pair['name'],pair['topology']==topology(a,b))
    ok('fixed-64-bit-and-clock',d['instruction_bits']==64 and d['clock_period_ns']=='3.333333333')
    ok('two-target-three-PM',d['mother_targets']==2 and d['pm_banks_each']*3==12)
    for name,fn in [('main64_endpoint',endpoint),('main64_control_top',control_top),('main64_host_front',host_front),('main64_boot_top',boot_top)]:
        ok('generated-current:'+name,(HERE/(name+'.sv')).read_text()==fn())
    ok('mother-wrapper-used','mother_control_64 #' in control_top())
    ok('no-extra-mother-PM','for(genvar k=1;k<3;' in control_top())
    ok('no-old-endpoint','native_control_endpoint #' not in control_top())
    ok('no-fixture-PM','network_pm' not in control_top()+endpoint()+boot_top())
    print('PASS R8.1 software',len(cases))
    return {'passed':len(cases),'total':len(cases),'cases':cases}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();r=main()
    if a.out:a.out.write_text(json.dumps(r,indent=2)+'\n')
