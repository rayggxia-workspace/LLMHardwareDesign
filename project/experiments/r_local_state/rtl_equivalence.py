"""Full RTL-to-cell sequential equivalence, with no excluded outputs or states."""
from pathlib import Path
import argparse,subprocess,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,required=True);p.add_argument('--mapped',type=Path,required=True);p.add_argument('--lower-only',action='store_true');a=p.parse_args()
R=Path.cwd();O=R/'rtl-equivalence';O.mkdir(exist_ok=False);S=R/'project/rtl/r_local_state';L=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(O/'ff_generic.v').write_text("module \\$_DFF_P_ (input C,D,output Q); \\$dff #(.WIDTH(1),.CLK_POLARITY(1'b1)) _TECHMAP_REPLACE_ (.CLK(C),.D(D),.Q(Q)); endmodule\n")
script='read_liberty -ignore_miss_func -ignore_miss_dir '+str(L)+'\n'
script+='read_verilog -sv '+str(S/'r_state_store.sv')+' '+str(S/'r_stream_local.sv')+'\nchparam -set WORDS '+str(a.capacity)+' r_stream_local\nhierarchy -check -top r_stream_local\nproc\nflatten\nopt\nmemory_map\nopt\ndffunmap\ntechmap -map ff_generic.v\nwrite_json gold-lowered.json\nrename r_stream_local gold\ndesign -stash gold\n'
script+='read_liberty -ignore_miss_func -ignore_miss_dir '+str(L)+'\nread_verilog '+str(a.mapped)+'\nhierarchy -check -top r_stream_local\nproc\nflatten\nopt\ndffunmap\ntechmap -map ff_generic.v\nwrite_json gate-lowered.json\nrename r_stream_local gate\ndesign -stash gate\n'
script+='design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple -seq 2\nequiv_induct -seq 4\nequiv_status -assert\n'
if a.lower_only:script=script[:script.index('design -copy-from gold')]
(O/'complete.ys').write_text(script)
with(O/'complete.log').open('w')as f:r=subprocess.run(['yosys','-s','complete.ys'],cwd=O,stdout=f,stderr=subprocess.STDOUT)
if a.lower_only:raise SystemExit(r.returncode)
t=(O/'complete.log').read_text();passed=r.returncode==0 and 'Equivalence successfully proven!'in t
(O/'receipt.json').write_text(json.dumps({'passed':passed,'exit':r.returncode,'capacity':a.capacity,'inputs':{str(f):sha(f)for f in [S/'r_state_store.sv',S/'r_stream_local.sv',a.mapped,L]},'log_sha256':sha(O/'complete.log'),'no_excluded_outputs':True,'no_assumed_internal_invariants':True,'scope':'Full Yosys equiv_status -assert, sequential RTL to actual cell netlist; physical final LEC and numeric regression remain separate.'},indent=2)+'\n');assert passed
