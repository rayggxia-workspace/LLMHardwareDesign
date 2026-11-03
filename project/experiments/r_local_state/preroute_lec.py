"""Formal complete state-boundary check of exact RTL synthesis before/after ABC."""
from pathlib import Path
import argparse,subprocess,hashlib,json,re
from lec_receive import inspect,fixture
p=argparse.ArgumentParser();p.add_argument('--mapped',type=Path,required=True);a=p.parse_args()
R=Path.cwd();O=R/'preroute-lec';O.mkdir(exist_ok=False);L=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');B=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rec={'passed':False,'mapped':str(a.mapped),'scope':'Complete pre-ABC to actual ABC cell-netlist formal state-boundary equivalence. Trusted Yosys RTL synthesis lowering is reproduced with exact source binding; independent RTL and cell numeric tests remain required.'}
def run(args,log):
 with(O/log).open('w')as f:subprocess.run(list(map(str,args)),cwd=O,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
 bound=json.loads((a.mapped/'receipt.json').read_text());assert bound['passed']
 for path,h in bound['source_sha256'].items():assert sha(R/path)==h
 (O/'mux_native.v').write_text("module \\$_MUX_ (input A,B,S,output Y); MUX2_X1 _TECHMAP_REPLACE_ (.A(A),.B(B),.S(S),.Z(Y)); endmodule\n"+"\n".join('module \\'+generic+' (input A'+(',B'if binary else'')+',output Y); '+native+' _TECHMAP_REPLACE_ ('+ports+'); endmodule'for generic,native,ports,binary in [('$_AND_','AND2_X1','.A1(A),.A2(B),.ZN(Y)',True),('$_OR_','OR2_X1','.A1(A),.A2(B),.ZN(Y)',True),('$_XOR_','XOR2_X1','.A(A),.B(B),.Z(Y)',True),('$_XNOR_','XNOR2_X1','.A(A),.B(B),.ZN(Y)',True),('$_NAND_','NAND2_X1','.A1(A),.A2(B),.ZN(Y)',True),('$_NOR_','NOR2_X1','.A1(A),.A2(B),.ZN(Y)',True),('$_NOT_','INV_X1','.A(A),.ZN(Y)',False)])+'\n')
 recipe=(a.mapped/'map.ys').read_text();assert recipe.count('\nabc -liberty')==1
 script=recipe.split('\nabc -liberty')[0]+'\ntechmap -map '+str(O/'mux_native.v')+'\nwrite_verilog -norename -noattr '+str(O/'gold.v')+'\ndesign -reset\nread_json '+str(a.mapped/'mapped.json')+'\nwrite_verilog -norename -noattr '+str(O/'gate.v')+'\n'
 (O/'prepare.ys').write_text(script);run(['yosys','-s','prepare.ys'],'prepare.log')
 for name in ['gold.v','gate.v']:
  f=O/name;f.write_text(re.sub(r'\bwire signed\b','wire',f.read_text()))
 (O/'controls').mkdir();fixture(R,O/'controls',run)
 cfg='format: verilog\ninput_paths:\n  - '+str(O/'gold.v')+'\n  - '+str(O/'gate.v')+'\nliberty_files:\n - '+str(L)+'\nlog_file: '+str(O/'kepler.log')+'\n';(O/'config.yml').write_text(cfg)
 run([B,'--config','config.yml'],'command.log');proof=inspect((O/'kepler.log').read_text());rec['proof']=proof;rec['passed']=proof['passed']
 rec['inputs']={str(f):sha(f)for f in [a.mapped/'mapped.json',a.mapped/'map.ys',L,B,O/'gold.v',O/'gate.v',O/'config.yml',O/'kepler.log']};rec['source_sha256']=bound['source_sha256'];rec['controls_sha256']=sha(O/'controls/native-formal-control.json')
except Exception as e:rec['error']=repr(e)
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));assert rec['passed']
