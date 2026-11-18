"""Synthesize and replay the explicit transcendental candidate, without SPEF."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from special_lut import generate,samples,FUNCTIONS
from control_gap_calibration import LIB,PLATFORM,power

def run(args,log,cwd):
    with log.open('w') as f:subprocess.run(list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
def digest(p):return sha256(p.read_bytes()).hexdigest()

def clip(raw,dest,lo,hi):
    stack=[];selected={};values={};started=False;now=0
    with raw.open() as src,dest.open('w') as out:
        out.write('$timescale 1ps $end\n$scope module dut $end\n')
        for line in src:
            p=line.split()
            if p[:1]==['$scope']:stack.append(p[2])
            elif p[:1]==['$upscope']:stack.pop()
            elif p[:1]==['$var'] and stack[-2:]==['tb','dut'] and p[4] in ('clk','reset','valid','ready','opcode','x','out_valid','out_ready','y','fault'):
                selected[p[3]]=int(p[2]);out.write('$var wire %s %s %s%s $end\n'%(p[2],p[3],p[4],(' [%d:0]'%(int(p[2])-1)) if int(p[2])>1 else ''))
            elif p[:1]==['$enddefinitions']:break
        out.write('$upscope $end\n$enddefinitions $end\n')
        for line in src:
            if line.startswith('#'):
                now=int(line[1:])
                if now>hi:break
                if now>=lo:
                    if not started:
                        if set(values)!=set(selected):raise ValueError('uninitialized boundary')
                        out.write('#0\n'+''.join('b%s %s\n'%(v,k) for k,v in values.items()));started=True
                    out.write('#%d\n'%(now-lo))
            else:
                p=line.split()
                if not p:continue
                if p[0][0] in 'bB' and len(p)==2:v,k=p[0][1:],p[1]
                elif p[0][0] in '01xz':v,k=p[0][0],p[0][1:]
                else:continue
                if k not in selected:continue
                if set(v)-{'0','1'}:raise ValueError('unknown boundary')
                values[k]=v
                if started:out.write('b%s %s\n'%(v,k))
        out.write('#%d\n'%(hi-lo))
    return sum(selected.values())

def main():
    bundle,out=map(Path,sys.argv[1:]);out.mkdir();generate(out);samples(bundle/'samples',out)
    lines=(out/'commands.txt').read_text().splitlines()
    for op in range(4):(out/('commands-%d.txt'%op)).write_text('\n'.join(x for x in lines if x.startswith(str(op)+' '))+'\n')
    tb='''`timescale 1ps/1ps
module tb;
logic clk=0,reset=1,valid=0,ready,out_valid,out_ready=1,fault;
logic [1:0] opcode=0;logic signed [39:0] x=0,y;
special_lut_q24 dut(.*);
always #1667 clk=~clk;
integer f,n,op,count,cycles,timeout;logic [39:0] xv,expected;
string command_file;time first,last;
initial begin
 if(!$value$plusargs("file=%s",command_file)) $fatal(1,"file");
 $dumpfile("raw.vcd");$dumpvars(0,tb);
 repeat(4) @(negedge clk);reset=0;repeat(4) @(negedge clk);
 f=$fopen(command_file,"r");if(f==0)$fatal(1,"open");
 first=$time;count=0;
 while(!$feof(f)) begin
   n=$fscanf(f,"%d %h %h\\n",op,xv,expected);
   if(n!=3) $fatal(1,"command parse");
   if(!ready) $fatal(1,"not ready");
   opcode=2'(op);x=xv;valid=1;@(negedge clk);valid=0;
   timeout=0;
   while(!out_valid)begin @(negedge clk);timeout++;if(timeout>10)$fatal(1,"timeout");end
   if(fault||y!==expected)$fatal(1,"numeric op=%0d x=%h actual=%h expected=%h",op,xv,y,expected);
   @(negedge clk);count++;
 end
 last=$time;cycles=int'((last-first)/3334);
 $display("WINDOW %0t %0t %0d %0d",first,last,cycles,count);
 repeat(cycles) @(negedge clk);
 $display("END %0t",$time);$display("SPECIAL_RTL_PASS");#1;$finish;
end
endmodule
'''
    (out/'tb.sv').write_text(tb)
    ys='\n'.join(['read_verilog -sv special_lut_q24.sv','synth -top special_lut_q24 -flatten -noabc -noshare',
        'dfflibmap -liberty '+str(LIB),'abc -liberty '+str(LIB),'clean','read_liberty -lib '+str(LIB),
        'check -assert','stat -liberty '+str(LIB),'write_verilog -noexpr -noattr mapped.v','write_json mapped.json'])+'\n'
    (out/'synth.ys').write_text(ys)
    verilator=bundle.parent.parent.parent/'opt/verilator-5.042/bin/verilator'
    run([verilator,'--binary','--timing','--trace','--trace-depth','2','--assert','-Wno-fatal','-j','12','--top-module','tb',
         '--Mdir',out/'obj',out/'special_lut_q24.sv',out/'tb.sv'],out/'build.log',out)
    observations={}
    for op in range(4):
        run([out/'obj/Vtb','+file=commands-%d.txt'%op],out/('replay-%d.log'%op),out)
        log=(out/('replay-%d.log'%op)).read_text()
        if 'SPECIAL_RTL_PASS' not in log:raise ValueError('RTL replay failed')
        lo,hi,cycles,count=map(int,re.search(r'WINDOW (\d+) (\d+) (\d+) (\d+)',log).groups())
        end=int(re.search(r'END (\d+)',log)[1]);assert end-hi==hi-lo==cycles*3334
        for name,a,b in (('active',lo,hi),('idle',hi,end)):clip(out/'raw.vcd',out/('%d-%s.vcd'%(op,name)),a,b)
        observations[FUNCTIONS[op]]=dict(opcode=op,calls=count,cycles=cycles,window_ps=hi-lo,
            replay_sha256=digest(out/('replay-%d.log'%op)))
    print('SPECIAL_ALL_RTL_REPLAYS_PASS',flush=True)
    run(['yosys','-l',out/'synth.log',out/'synth.ys'],out/'synth-stdout.log',out)
    design=json.loads((out/'mapped.json').read_text())['modules']['special_lut_q24']
    if any(c['type'].startswith('$') for c in design['cells'].values()):raise ValueError('unmapped cell')
    # OpenSTA's structural Verilog reader rejects signed declarations. There
    # are no expressions left in this mapped netlist: cell/pin connectivity
    # is unchanged by removing this source-language type annotation.
    mapped=(out/'mapped.v').read_text()
    normalized=re.sub(r'(?m)^(  (?:input|output|wire)) signed ',r'\1 ',mapped)
    (out/'mapped-sta.v').write_text(normalized)
    required=sum(len(p['bits']) for p in design['ports'].values())
    for kind,row in observations.items():
        powers={}
        for name in ('active','idle'):
            wave=out/('%d-%s.vcd'%(row['opcode'],name));target=out/(kind+'-'+name)
            tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(out/'mapped-sta.v')+'}','link_design special_lut_q24',
                'create_clock -name core -period 3.334 [get_ports clk]','set_input_transition 0.05 [all_inputs]',
                'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9'])+'\n'
            powers[name]=power(tcl,target,required)
        row['power']=powers;row['incremental_nj_per_call']=(powers['active']['power_w']['total']-powers['idle']['power_w']['total'])*row['window_ps']/1000/row['calls']
        print('SPECIAL_POWER_PASS',kind,flush=True)
    result=dict(scope='explicit Q24 transcendental candidate only; paired RTL boundary propagation through mapped cells',
        clock_period_ps=3334,wire_parasitics_loaded=False,timing_signoff=False,rtl_replay_all_commands_passed=True,
        primitives=observations,cell_count=len(design['cells']),netlist_sha256=digest(out/'mapped.v'),
        sta_netlist_sha256=digest(out/'mapped-sta.v'),sta_normalization='remove signed from structural input/output/wire declarations only',
        inputs={str(p):digest(p) for p in [Path(__file__),bundle/'special_lut.py',out/'special_lut_q24.sv',out/'special-lut.hex',LIB]},
        numerical_diagnostics=json.loads((out/'numeric-diagnostics.json').read_text()),
        limitations=['No global LUT switching statistics or full model RTL acceptance',
        'Multiply/divide/normalization, FP32 conversion and complete provider wrapper remain separate',
        'Sampled operation sequences include explicit edge tests; bounds are not statistical confidence intervals'])
    (out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SPECIAL_LUT_CALIBRATION_PASS',flush=True)
if __name__=='__main__':main()
