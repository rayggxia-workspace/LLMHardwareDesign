"""Prove all-input R temporary arithmetic, then actual-initial-state regression.

The proof extracts both actual RTL value cases and functions, not a handwritten
alternate formula. All phase encodings, S65 products, S64 dots and S32 operands
are free SAT inputs. Full sign-extended value and overflow decisions must match.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
from run_rtl import ROOT,COMPILER,sha
from retain_r import adapt


def arithmetic(old,new):
    def extract(text,suffix):
        functions=re.findall(r' function automatic[\s\S]*? endfunction',text)
        assert len(functions)==2
        functions='\n'.join(functions)
        case=re.search(r'   case\(phase\)\n(    DEC_MUL,DEC_WRITE,ERR_WRITE:[\s\S]*?)   endcase',text)
        assert case
        value='always @* begin case(phase)\n'+case.group(1)+'endcase end\n'
        for name in ('value','product','dot','x','error_value','product_state_base','output_value'):
            value=value.replace(name+'[l]',name)
        for name in ('rne','fits32','value'):
            functions=re.sub(r'\b'+name+r'\b',name+suffix,functions)
            value=re.sub(r'\b'+name+r'\b',name+suffix,value)
        return functions+'\n'+value
    constants=re.search(r' localparam IDLE=[\s\S]*?;',old).group(0)
    assert constants==re.search(r' localparam IDLE=[\s\S]*?;',new).group(0)
    return '''module r_temp_proof(input [4:0] phase,input signed [64:0] product,
input signed [63:0] dot,input signed [31:0] x,error_value,product_state_base,output_value,
output ok);
reg signed [127:0] value_old;
reg signed [51:0] value_new;
'''+constants+'\n'+extract(old,'_old')+extract(new,'_new')+'''
assign ok=(value_old=={{76{value_new[51]}},value_new})
 && (fits32_old(value_old)==fits32_new(value_new));
endmodule
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    assert len(os.sched_getaffinity(0))==16
    rtl=ROOT/'project/rtl/block_library_v1/block_v1_r.sv'
    baseline=ROOT/'work/YUZE-LU/143/r-temp-before.sv'
    bench=ROOT/'project/experiments/block_v1/test_recurrent_macro.cpp'
    report=dict(passed=False,model='r',runs=[],source_sha256={str(f.relative_to(ROOT)):sha(f) for f in (rtl,baseline,bench,Path(__file__).resolve())},
        started_unix=time.time(),physical_qualified=False)
    def run(command,log,success=True):
        with (out/log).open('w') as stream:
            result=subprocess.run(list(map(str,command)),cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        assert (result.returncode==0)==success,(log,result.returncode)
        return result.returncode
    try:
        # Only the pure temporary functions/declarations/value cases may change.
        old=baseline.read_text();new=rtl.read_text()
        assert 'reg signed [31:0] bank0[0:2047],bank1[0:2047];' in new
        assert old[:old.index(' function automatic')]==new[:new.index(' // Local temporaries')]
        assert old[old.index(' integer i;'):]==new[new.index(' integer i;'):]
        proof=arithmetic(old,new);(out/'proof.sv').write_text(proof)
        controls={}
        for name,source,expected in [('positive',proof,True),
            ('flipped-value',proof.replace('assign ok=(value_old==','assign ok=((value_old ^ 128\'d1)=='),False),
            ('flipped-overflow',proof.replace('fits32_old(value_old)==','fits32_old(value_old)!='),False)]:
            assert source!=proof or name=='positive'
            sv=out/(name+'.sv');sv.write_text(source)
            ys=out/(name+'.ys');ys.write_text('read_verilog -sv '+str(sv)+'\nprep -top r_temp_proof\nflatten\nopt\nsat -verify -prove ok 1 -show-inputs\n')
            code=run(['yosys','-s',ys],name+'.log',expected)
            text=(out/(name+'.log')).read_text()
            if expected:assert 'SAT proof finished - no model found: SUCCESS!' in text
            else:assert 'proof did fail' in text
            controls[name]=dict(returncode=code,log_sha256=sha(out/(name+'.log')))
        report['all_input_arithmetic']=dict(passed=True,controls=controls,proof_sha256=sha(out/'proof.sv'),
            state_and_sequential_control_byte_identical=True,
            scope='Every value case, all 32 phase encodings, full signed value and fits32; free S65/S64/S32 inputs')
        generated=out/'test-r.cpp';generated.write_text(adapt(bench.read_text()))
        run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','block_v1_r',
            '--Mdir',out/'obj','--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O1',rtl,generated],'build.log')
        for mode,seed in ((1,143),(2,143),(2,144)):
            log=f'result-{mode}-{seed}.json'
            run([out/'obj/Vblock_v1_r',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
            result=json.loads((out/log).read_text());assert result['passed']
            report['runs'].append(dict(mode=mode,seed=seed,result=result,sha256=sha(out/log)))
        report['passed']=True
    finally:
        report['finished_unix']=time.time()
        (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
