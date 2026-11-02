from pathlib import Path
import hashlib,json,subprocess,sys,copy,importlib.util
sys.path.insert(0,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/physical-004/source/project/experiments/block_v1')
from native_formal import inspect
from structural_view import compare
spec=importlib.util.spec_from_file_location('formal_banks',str(Path.cwd()/'formal_banks.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
TOOL=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,log):
 with Path(log).open('w') as f:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(log,r.returncode)
definition='(* blackbox *) module s_sram_256x128_freepdk45(input clk0,csb0,web0,input [7:0] addr0,input [127:0] din0,output [127:0] dout0); endmodule\n'
result=dict(passed=False,qualified=False,cases={},inputs={str(p):sha(p) for p in [LIB,TOOL,Path.cwd()/'formal_banks.py']})
for case in ('gold','positive','address','clock','response'):
 text=definition+'module block_feed_s_macro_sram(input clk,csb,web,input [7:0] addr,input [127:0] din,output [127:0] dout,output q);\n'
 text+='wire [127:0] r0,r1,r2,r3; wire bit0;\n'
 if case=='address':text+='INV_X1 changed(.A(addr[0]),.ZN(bit0));\n'
 elif case!='gold':text+='BUF_X2 same(.A(addr[0]),.Z(bit0));\n'
 for i in range(4):
  clock='web' if case=='clock' and i==0 else 'clk'
  address='{addr[7:1],bit0}' if i==0 and case!='gold' else 'addr'
  text+=f's_sram_256x128_freepdk45 b{i}(.clk0({clock}),.csb0(csb),.web0(web),.addr0({address}),.din0(din),.dout0(r{i}));\n'
 text+='assign dout='+('r1' if case=='response' else 'r0')+'; DFF_X1 ff(.CK(clk),.D(r0[0]),.Q(q)); endmodule\n'
 Path(case+'.v').write_text(text)
 ys=f'read_liberty -lib {LIB}\nread_verilog {case}.v\nhierarchy -check -top block_feed_s_macro_sram\nwrite_json {case}.json\n'
 Path(case+'.ys').write_text(ys);run(['yosys','-s',case+'.ys'],case+'-parse.log')
 data=json.loads(Path(case+'.json').read_text());boundaries=module.cut(data)
 Path(case+'-cut.json').write_text(json.dumps(data)+'\n')
 ys=f'read_json {case}-cut.json\nwrite_verilog -noexpr -noattr -norename {case}-cut.v\ndesign -reset\nread_liberty -lib {LIB}\nread_verilog {case}-cut.v\nhierarchy -check -top block_feed_s_macro_sram\nwrite_json {case}-readback.json\n'
 Path(case+'-emit.ys').write_text(ys);run(['yosys','-s',case+'-emit.ys'],case+'-emit.log')
 proof=compare(data,json.loads(Path(case+'-readback.json').read_text()))
 result['cases'][case]=dict(bank_boundaries=boundaries,structural_readback=proof)
 if case=='gold':continue
 config=f'format: verilog\ninput_paths:\n  - {Path.cwd()/"gold-cut.v"}\n  - {Path.cwd()/(case+"-cut.v")}\nliberty_files:\n - {LIB}\nlog_file: {Path.cwd()/(case+"-kepler.log")}\n'
 Path(case+'.yml').write_text(config)
 with Path(case+'-command.log').open('w') as f:r=subprocess.run([str(TOOL),'--config',case+'.yml'],stdout=f,stderr=subprocess.STDOUT)
 text=Path(case+'-kepler.log').read_text();report=inspect(text)
 if case=='positive':assert r.returncode==0 and report['passed'],report
 else:assert not report['passed'] and ('Found difference' in text or 'SAT solver finished: SAT' in text)
 result['cases'][case].update(formal=report,returncode=r.returncode)
result.update(passed=True,scope='Synthetic actual-Yosys/Kepler SRAM-boundary fixture only: exact structural roundtrip, positive buffering and real address/clock/response faults. Not actual S physical/formal qualification.')
Path('receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:dict(passed=v.get('formal',{}).get('passed'),returncode=v.get('returncode')) for k,v in result['cases'].items()},indent=2))
