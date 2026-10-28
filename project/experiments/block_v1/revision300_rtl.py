"""Fresh RTL checks/mapping for the review revision, with explicit source binds."""
import json
from pathlib import Path

COMPILER='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'


def sources(root,kind):
    folder=root/'project/rtl/block_library_v1'
    top='transaction6k'if kind=='t'else'block_v1_s16k'if kind=='s'else'block_v1_'+kind
    rtl=[root/'project/rtl/block_v1/transaction6k.sv']if kind=='t'else[folder/(top+'.sv')]
    if kind=='v':rtl+=[folder/(top+'_function.sv'),folder/(top+'_group.sv')]
    bench=root/'project/experiments/block_v1'/('test_transaction.cpp'if kind=='t'else'test_'+dict(m='matrix',v='vector',r='recurrent',s='store')[kind]+'_macro.cpp')
    return top,rtl,bench


def test(root,out,cpus,run,kind):
    from io_slots import file_sha
    assert cpus==16 and kind in ('s','t','m','v','r')
    top,rtl,bench=sources(root,kind)
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--x-initial','unique','--x-assign','unique',
         '--top-module',top,'-I'+str(rtl[0].parent),'-Mdir',str(out/'obj'),'-CFLAGS','-std=c++17 -O2']+rtl+[bench],'build.log')
    runs={}
    for name,initial,seed in [('all-ones',1,121),('random-121',2,121),('random-122',2,122)]:
        run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],name+'.json')
        report=json.loads((out/(name+'.json')).read_text());assert report['passed']
        runs[name]=dict(initial=initial,seed=seed,result=report)
    assert all(d['result']==runs['all-ones']['result']for d in runs.values())
    bound=rtl+([rtl[0].parent/'block_v1_v_tables.svh']if kind=='v'else[])
    result=dict(passed=True,top=top,rtl_sha256={str(p.relative_to(root)):file_sha(p)for p in bound},
                bench_sha256=file_sha(bench),initial_runs=runs,final_netlist_verified=False,
                physical_implementation_completed=False,scope='Independent revised-RTL numerical/transaction tests; not final-netlist or physical acceptance')
    (out/'revision300-rtl-test.json').write_text(json.dumps(result,indent=2)+'\n')


def mapping(root,out,cpus,run,kind):
    from io_slots import file_sha
    assert cpus==16
    top,rtl,bench=sources(root,kind)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    script='read_liberty -lib '+str(lib)+'\nread_verilog -sv -I'+str(rtl[0].parent)+' '+' '.join(map(str,rtl))+'\n'
    script+='hierarchy -check -top '+top+'\nsynth -top '+top+' -noabc\n'
    script+='dfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\ncheck -assert\n'
    script+='flatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty '+str(lib)+'\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (out/'map.ys').write_text(script);run(['yosys','-s',out/'map.ys'],'map.log')
    module=json.loads((out/'mapped.json').read_text())['modules'][top];cells={}
    for c in module['cells'].values():
        assert not c['type'].startswith('$'),c['type']
        cells[c['type']]=cells.get(c['type'],0)+1
    bound=rtl+([rtl[0].parent/'block_v1_v_tables.svh']if kind=='v'else[])
    result=dict(passed=True,top=top,rtl_sha256={str(p.relative_to(root)):file_sha(p)for p in bound},
                liberty_sha256=file_sha(lib),mapped_sha256=file_sha(out/'mapped.v'),cells=cells,cell_count=sum(cells.values()),
                ports={k:dict(direction=v['direction'],bits=len(v['bits']))for k,v in module['ports'].items()},
                physical_implementation_completed=False,functional_equivalence_qualified=False)
    (out/'revision300-rtl-map.json').write_text(json.dumps(result,indent=2)+'\n')
