"""Replay a full-width conv4 candidate on every captured channel, then map it."""
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from control_gap_calibration import LIB,PLATFORM,power
from special_lut import rounded

def digest(p):return sha256(p.read_bytes()).hexdigest()
def run(args,log,cwd):
    with log.open('w') as f:subprocess.run(list(map(str,args)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
def packed(v):return '%032x'%sum((x&0xffffffff)<<(32*i) for i,x in enumerate(v))

def clip(raw,dest,ports,lo,hi):
    selected={};values={};stack=[];started=False;time=0;found=set()
    with raw.open() as src,dest.open('w') as out:
        out.write('$timescale 1ps $end\n$scope module dut $end\n')
        for line in src:
            p=line.split()
            if p[:1]==['$scope']:stack.append(p[2])
            elif p[:1]==['$upscope']:stack.pop()
            elif p[:1]==['$var'] and stack[-2:]==['tb','dut'] and p[4] in ports:
                width=len(ports[p[4]]['bits']);assert int(p[2])==width
                selected[p[3]]=width;found.add(p[4]);out.write('$var wire %s %s %s%s $end\n'%(p[2],p[3],p[4],(' [%d:0]'%(width-1)) if width>1 else ''))
            elif p[:1]==['$enddefinitions']:break
        assert found==set(ports)
        out.write('$upscope $end\n$enddefinitions $end\n')
        for line in src:
            if line.startswith('#'):
                time=int(line[1:])
                if time>hi:break
                if time>=lo:
                    if not started:
                        assert set(values)==set(selected)
                        out.write('#0\n'+''.join('b%s %s\n'%(v,k) for k,v in values.items()));started=True
                    out.write('#%d\n'%(time-lo))
            else:
                p=line.split()
                if not p:continue
                if p[0][0] in 'bB' and len(p)==2:v,k=p[0][1:],p[1]
                elif p[0][0] in '01xz':v,k=p[0][0],p[0][1:]
                else:continue
                if k not in selected:continue
                assert not set(v)-{'0','1'}
                values[k]=v
                if started:out.write('b%s %s\n'%(v,k))
        out.write('#%d\n'%(hi-lo))

def main():
    bundle,out=map(Path,sys.argv[1:]);out.mkdir();shutil.copy2(bundle/'conv4_q24.sv',out/'conv4_q24.sv')
    cases={}
    for path in sorted((bundle/'samples').glob('*.json')):
        commands=[];errors=[];channels=0
        for index,s in enumerate(json.loads(path.read_bytes()).get('samples',[])):
            if s['kind']!='conv4':continue
            a=s['inputs'];expected=s['outputs']['result'];assert len(expected)%8==0
            for first in range(0,len(expected),8):
                values=[round(x*65536) for row in a['window'][first:first+8] for x in row]
                weights=[round(x*(1<<24)) for row in a['taps'][first:first+8] for x in row]
                assert len(values)==len(weights)==32 and all(-(1<<31)<=x<(1<<31) for x in values+weights)
                results=[rounded(sum(values[4*i+j]*weights[4*i+j] for j in range(4)),24) for i in range(8)]
                assert all(-(1<<31)<=x<(1<<31) for x in results)
                for op,values_ in ((0,values),(1,weights)):
                    for j in range(8):commands.append('%d %d %s %032x'%(op,j,packed(values_[4*j:4*j+4]),0))
                commands.append('2 0 %032x %032x'%(0,0))
                for j in range(2):commands.append('3 %d %032x %s'%(j,0,packed(results[4*j:4*j+4])))
                errors.extend(abs(v-round(y*65536)) for v,y in zip(results,expected[first:first+8]));channels+=8
        if commands:
            name=path.stem;(out/(name+'.txt')).write_text('\n'.join(commands)+'\n')
            cases[name]=dict(channels=channels,commands=len(commands),max_abs_q16=max(errors),mismatches=sum(x!=0 for x in errors),
                capture_sha256=digest(path),quantization='S32/Q16 values and S32/Q24 coefficients; final RNE Q16',
                full_model_precision_accepted=False)
    tb='''`timescale 1ps/1ps
module tb;
logic clk=0,reset=1,cmd_valid=0,cmd_ready,rsp_valid,rsp_ready=1,rsp_error;
logic [1:0] cmd_op=0;logic [2:0] cmd_index=0;logic [127:0] cmd_data=0,rsp_data;
conv4_q24 dut(.*);always #1667 clk=~clk;
integer f,n,op,idx,count,requested,timeout,cycles;logic [127:0] data,expected;
string file;time first,last;
initial begin
 if(!$value$plusargs("file=%s",file)||!$value$plusargs("count=%d",requested))$fatal(1,"arguments");
 $dumpfile("raw.vcd");$dumpvars(0,tb);repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
 f=$fopen(file,"r");if(!f)$fatal(1,"open");first=$time;
 for(count=0;count<requested;count++)begin
  n=$fscanf(f,"%d %d %h %h\\n",op,idx,data,expected);if(n!=4)$fatal(1,"parse");
  if(!cmd_ready)$fatal(1,"ready");cmd_op=2'(op);cmd_index=3'(idx);cmd_data=data;cmd_valid=1;
  @(negedge clk);cmd_valid=0;timeout=0;
  while(!rsp_valid)begin @(negedge clk);timeout++;if(timeout>30)$fatal(1,"timeout");end
  if(rsp_error||rsp_data!==expected)$fatal(1,"numeric command=%0d got=%h expected=%h",count,rsp_data,expected);
  @(negedge clk);
 end
 last=$time;cycles=int'((last-first)/3334);$display("WINDOW %0t %0t %0d",first,last,cycles);
 repeat(cycles)@(negedge clk);$display("END %0t",$time);$display("CONV4_RTL_PASS");#1;$finish;
end
endmodule
'''
    (out/'tb.sv').write_text(tb)
    verilator=bundle.parent.parent.parent/'opt/verilator-5.042/bin/verilator'
    run([verilator,'--binary','--timing','--trace','--trace-depth','2','--assert','-Wno-fatal','-j','12','--top-module','tb',
        '--Mdir',out/'obj',out/'conv4_q24.sv',out/'tb.sv'],out/'build.log',out)
    # Replay before mapping: a numeric failure never starts power calibration.
    for name,row in cases.items():
        run([out/'obj/Vtb','+file='+name+'.txt','+count='+str(row['commands'])],out/(name+'-replay.log'),out)
        log=(out/(name+'-replay.log')).read_text();assert 'CONV4_RTL_PASS' in log
        lo,hi,cycles=map(int,re.search(r'WINDOW (\d+) (\d+) (\d+)',log).groups());end=int(re.search(r'END (\d+)',log)[1])
        assert end-hi==hi-lo==cycles*3334
        row.update(first=lo,last=hi,end=end,cycles=cycles,rtl_q_reference_equal=True)
        (out/'raw.vcd').rename(out/(name+'.vcd'))
        print('CONV4_RTL_PASS',name,row['max_abs_q16'],flush=True)
    ys='\n'.join(['read_verilog -sv conv4_q24.sv','synth -top conv4_q24 -flatten -noabc -noshare',
        'dfflibmap -liberty '+str(LIB),'abc -liberty '+str(LIB),'clean','read_liberty -lib '+str(LIB),'check -assert',
        'stat -liberty '+str(LIB),'write_verilog -noexpr -noattr mapped.v','write_json mapped.json'])+'\n'
    (out/'synth.ys').write_text(ys);run(['yosys','-l',out/'synth.log',out/'synth.ys'],out/'synth-stdout.log',out)
    design=json.loads((out/'mapped.json').read_text())['modules']['conv4_q24'];assert all(not c['type'].startswith('$') for c in design['cells'].values())
    mapped=(out/'mapped.v').read_text();(out/'mapped-sta.v').write_text(re.sub(r'(?m)^(  (?:input|output|wire)) signed ',r'\1 ',mapped))
    for name,row in cases.items():
        powers={};duration=row['last']-row['first']
        for kind,lo,hi in (('active',row['first'],row['last']),('idle',row['last'],row['end'])):
            wave=out/(name+'-'+kind+'.vcd');clip(out/(name+'.vcd'),wave,design['ports'],lo,hi)
            tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(out/'mapped-sta.v')+'}','link_design conv4_q24',
                'create_clock -name core -period 3.334 [get_ports clk]','set_input_transition 0.05 [all_inputs]',
                'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9'])+'\n'
            powers[kind]=power(tcl,out/(name+'-'+kind),sum(len(p['bits']) for p in design['ports'].values()))
        row['power']=powers;row['incremental_nj_per_channel']=(powers['active']['power_w']['total']-powers['idle']['power_w']['total'])*duration/1000/row['channels']
    result=dict(scope='matched fixed-point convolution candidate; sampled FP32 error is not model acceptance',cases=cases,
        clock_period_ps=3334,wire_parasitics_loaded=False,timing_signoff=False,cell_count=len(design['cells']),
        inputs={str(p):digest(p) for p in (Path(__file__),bundle/'conv4_q24.sv',LIB)},netlist_sha256=digest(out/'mapped.v'),
        activity='normal command RTL boundary activity propagated through mapped cells; no internal gate replay',
        state='all captured channels replayed independently; full recurrent history/controller integration remains separate')
    (out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n');print('CONV4_CALIBRATION_PASS',flush=True)
if __name__=='__main__':main()
