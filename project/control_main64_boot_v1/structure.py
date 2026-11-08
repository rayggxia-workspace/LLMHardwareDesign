"""R8.2 structural check with explicit native-data and SRAM boundaries."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from contract import HERE,ROOT,PAIRS


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--pair',type=int,choices=range(9),required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);k0,k1=PAIRS[a.pair]
    raw=json.loads((a.stage/'sources.json').read_text());sources=[Path(s) for s in raw['sources']]
    def call(cmd,name):
        with (out/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
    vl='/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator'
    include=['-I'+s for s in raw['include_dirs']]
    call([vl,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module','main64_boot_top',f'-GKIND0={k0}',f'-GKIND1={k1}',*include,raw['waiver'],*sources],'full-lint.log')
    native={'pu_p_group','pu_u_group','block_cfj_cf','block_cfj_j'}
    stubs=[]
    for name in sorted(native):
        source=next(s for s in sources if s.name==name+'.sv')
        target=out/(name+'.v');target.write_text(source.read_text().split(');',1)[0]+');\nendmodule\n');stubs.append(target)
    bank=next(s for s in sources if s.name=='s_sram_256x128_freepdk45.v')
    bankstub=out/'bank.v';bankstub.write_text(bank.read_text().split('  reg [DATA_WIDTH-1:0]    mem',1)[0]+'endmodule\n');stubs.append(bankstub)
    # Keep only the controllers, services, transport, host glue and actual PM
    # wrappers. Do not read a behavioral bank in the synthesis source set.
    control=[s for s in sources if s.is_relative_to(HERE) or 'generated' in s.parts or
             s.parent.name=='mother_control_v1' or s.name in ('two_local_link.sv','control_boot_manager.sv','native_result_fifo.sv','block_feed_s16k_sram.sv','pu_u_direct_pair.sv')]
    call([vl,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module','main64_boot_top',f'-GKIND0={k0}',f'-GKIND1={k1}',*include,*stubs,*control],'control-lint.log')
    warnings=re.findall(r'%Warning-([A-Z0-9_]+)',(out/'control-lint.log').read_text())
    forbidden=set(warnings)&{'LATCH','MULTIDRIVEN','UNOPTFLAT','PINMISSING','WIDTHTRUNC'}
    assert not forbidden,forbidden
    quote=lambda s:json.dumps(str(s))
    script='read_verilog -sv -lib '+' '.join(map(quote,stubs))+'\n'
    script+='read_verilog -sv '+' '.join(include)+' '+' '.join(map(quote,control))+'\n'
    script+=f'chparam -set KIND0 {k0} -set KIND1 {k1} main64_boot_top\nhierarchy -check -top main64_boot_top\nsynth -top main64_boot_top -noabc\ncheck -assert\nwrite_json '+quote(out/'control.json')+'\n'
    (out/'synth.ys').write_text(script);call(['/usr/local/bin/yosys','-s',out/'synth.ys'],'synth.log')
    design=json.loads((out/'control.json').read_text());modules=design['modules']
    def count(name,predicate):
        hdl=modules.get(name,{}).get('attributes',{}).get('hdlname',name)
        if predicate(name,hdl):return 1
        return sum(count(c['type'],predicate) for c in modules.get(name,{}).get('cells',{}).values() if c['type'] in modules)
    nbank=count('main64_boot_top',lambda n,h:h=='s_sram_256x128_freepdk45')
    npm=count('main64_boot_top',lambda n,h:h=='control_pm')
    nmc=count('main64_boot_top',lambda n,h:h=='mc_min_controller')
    nlc=count('main64_boot_top',lambda n,h:h.startswith('r82_') and h.endswith(('pu_native_lc','lc_min_controller')))
    assert (nmc,nlc,npm,nbank)==(1,2,3,12),(nmc,nlc,npm,nbank)
    record=dict(schema='main64-boot-structure/1',passed=True,pair=[k0,k1],mother=nmc,locals=nlc,pm=npm,program_banks=nbank,
        native_boundaries='actual main group interfaces; data internals excluded from control synthesis',
        forbidden_control_warnings=[],warnings={x:warnings.count(x) for x in sorted(set(warnings))},
        source_sha256={str(s):sha(s) for s in control},physical_or_mapped_timing=False)
    record['artifacts_sha256']={s.name:sha(s) for s in out.iterdir() if s.is_file()}
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS R8.2 structure',a.pair,'1MC 2LC 3PM 12banks')


if __name__=='__main__':main()
