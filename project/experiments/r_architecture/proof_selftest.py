"""Prove positive control and require rejection of a deliberately wrong bank."""
from pathlib import Path
import json
from strict_state import run,cut,prove

def selftest(out):
 out.mkdir();paths={};sources={}
 for kind in ['gold','same','wrong']:
  f=out/kind;f.mkdir();expr='sel ? bank1[row] : bank0[row]'if kind=='same'else'sel ? bank0[row] : bank1[row]'if kind=='wrong'else'row ? a1 : a0'
  src=f/'tiny.sv';src.write_text('module block_v1_r(input clk,reset,sel,row,input [7:0] data,output [7:0] y); reg [7:0] bank0[0:1],bank1[0:1];wire [7:0] a0=sel?bank1[0]:bank0[0],a1=sel?bank1[1]:bank0[1];assign y='+expr+';always @(posedge clk)begin if(reset)begin bank0[0]<=0;bank0[1]<=0;bank1[0]<=0;bank1[1]<=0;end else begin bank0[row]<=data;bank1[row]<=~data;end end endmodule\n')
  run('read_verilog -sv tiny.sv\nproc\nopt\nmemory_collect\nmemory_map\nopt -fast\ndffunmap\nopt_clean -purge\nwrite_json lowered.json\n',f,'lower');paths[kind]=f/'lowered.json';sources[kind]=src
 positive=prove('positive',{'A0':paths['gold'],'positive':paths['same']},out,rtl_source=sources['same']);negative=prove('negative',{'A0':paths['gold'],'negative':paths['wrong']},out,rtl_source=sources['wrong']);assert positive['passed']and not negative['passed'];assert(out/'negative-proof/counterexample.vcd').exists()
 (out/'SELFTEST.json').write_text(json.dumps(dict(positive=positive,negative=negative,deliberate_wrong_bank_rejected=True),indent=2)+'\n')
if __name__=='__main__':selftest(Path.cwd()/'selftest')
