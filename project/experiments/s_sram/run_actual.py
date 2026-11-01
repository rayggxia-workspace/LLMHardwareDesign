"""Run the existing protocol scoreboards with the actually emitted RAM model.

Retains OpenRAM's arbitrary DELAY=3ns/T_HOLD=1ns and advances simulation time
between evaluations. This is functional verification at a deliberately slower
clock, NOT 300MHz timing validation. The latter requires characterized STA.
Only the third-party model's logging parameter is changed, with both hashes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--generation',required=True,type=Path)
    ap.add_argument('--verilator',required=True)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--physical',type=Path,help='Completed independent S implementation; test actual final netlist instead of RTL')
    a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    assert os.environ.get('SLURM_JOB_ID')
    result=dict(passed=False,scope='Actual generated SRAM behavioral model, original default delay/hold; slower-clock functional test only, not physical timing or final routed-netlist qualification',commands=[],results={})
    def save():(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    def call(argv,name):
        argv=list(map(str,argv))
        with (out/name).open('w')as log:
            p=subprocess.run(argv,cwd=out,stdout=log,stderr=subprocess.STDOUT)
        result['commands'].append(dict(argv=argv,returncode=p.returncode,log=name,sha256=sha(out/name)));save()
        assert p.returncode==0,(name,p.returncode)
    try:
        g=json.loads((a.generation/'generation.json').read_text())
        assert g['status']=='views_generated_not_qualified'
        model=Path(g['views']['v']['path']);assert sha(model)==g['views']['v']['sha256']
        text,count=re.subn(r'parameter VERBOSE\s*=\s*1\s*;', 'parameter VERBOSE = 0 ;',model.read_text())
        assert count==1
        actual=out/model.name;actual.write_text(text)
        result.update(generation_receipt_sha256=sha(a.generation/'generation.json'),
                      emitted_model_sha256=sha(model),test_model_sha256=sha(actual),
                      only_model_override='VERBOSE=0; DELAY=3ns and T_HOLD=1ns unchanged',source_sha256={})
        physical_sources=None
        if a.physical:
            folder=a.physical.resolve();pr=json.loads((folder/'receipt.json').read_text())
            assert pr['pipeline_completed'] and pr['passed']
            assert pr['inputs'][str(a.generation.resolve()/'generation.json')]==sha(a.generation/'generation.json')
            paths={n:Path(v['path']) for n,v in pr['final_files'].items()}
            for n,p in paths.items():assert sha(p)==pr['final_files'][n]['sha256']
            syslib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
            source=out/'physical-functional.v'
            # Export all signal-bearing cells, including protection loads and
            # real SRAMs; only filler/tap-only geometry is absent from logic.
            script=f'read_liberty {syslib}\nread_liberty {g["views"]["lib"]["path"]}\nread_db {{{paths["6_final.odb"]}}}\n'
            script+='set remove {}\nforeach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0; foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}; if {!$signal} {lappend remove [$master getName]}}}\n'
            script+=f'write_verilog -remove_cells $remove {{{source}}}\n'
            (out/'export.tcl').write_text(script)
            call(['openroad','-no_init','-exit',out/'export.tcl'],'export.log')
            sysys=f'read_liberty -ignore_miss_func -ignore_miss_dir {syslib}\nwrite_verilog -noattr cells.v\n'
            (out/'cells.ys').write_text(sysys)
            call(['yosys','-s',out/'cells.ys'],'cells.log')
            physical_sources=[source,out/'cells.v',actual]
            result.update(physical_receipt_sha256=sha(folder/'receipt.json'),
                          final_file_sha256={n:sha(p) for n,p in paths.items()},
                          library_sha256=sha(syslib),
                          scope='Actual final ODB exported with every signal-bearing cell and real generated SRAM model; default behavioral delays at slow test clock. Characterized extracted timing is separate.')
        call([a.verilator,'--version'],'tool.txt')
        helper='''
static void evaluate(){
 d.eval();
 const uint64_t end=Verilated::time()+5000;
 while(d.eventsPending()&&d.nextTimeSlot()<=end){
  Verilated::timeInc(d.nextTimeSlot()-Verilated::time());d.eval();
 }
 Verilated::timeInc(end-Verilated::time());d.eval();
}
'''
        for mode in (('feeder',) if physical_sources else ('store','feeder')):
            top='block_feed_s16k_sram' if mode=='store' else 'block_feed_s_macro_sram'
            original=HERE/('test_'+mode+'.cpp')
            cpp=original.read_text().replace('d.eval();','evaluate();')
            assert cpp.count('#define d (*p)\n')==1
            cpp=cpp.replace('#define d (*p)\n','#define d (*p)\n'+helper)
            test=out/original.name;test.write_text(cpp)
            sources=[ROOT/'project/rtl/s_sram/block_feed_s16k_sram.sv',actual]
            if mode=='feeder':sources += [ROOT/'project/rtl/s_sram/block_feed_s_macro_sram.sv',ROOT/'project/rtl/block_feed_v1/block_feed_loader.sv']
            if physical_sources:sources=physical_sources
            for p in sources+[original,test]:result['source_sha256'][str(p)]=sha(p)
            flags=['--timing','--timescale-override','1ns/1ps','--top-module',top,*sources]
            # Retain generated-model diagnostics. This is not a strict lint
            # pass; the separately recorded strict wrapper lint is unchanged.
            call([a.verilator,'--cc','--exe','--build','-Wall','-Wno-fatal','-j','4',
                  '--x-initial','unique','--x-assign','unique','--Mdir',out/(mode+'-obj'),*flags,test],mode+'-build.log')
            rows=[]
            for init,seed in ((1,143),(2,143),(2,144)):
                log=mode+f'-{init}-{seed}.json'
                call([out/(mode+'-obj')/('V'+top),f'+verilator+rand+reset+{init}',f'+verilator+seed+{seed}'],log)
                row=json.loads((out/log).read_text());assert row['passed'];rows.append(row)
            result['results'][mode]=rows;save()
        result['passed']=True
    except Exception as e:
        result['failure']=repr(e)
        raise
    finally:save()

if __name__=='__main__':main()
