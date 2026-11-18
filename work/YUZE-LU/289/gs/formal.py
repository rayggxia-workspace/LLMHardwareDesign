"""ECO equivalence against the already accepted exact leaf netlist.
S exposes every SRAM input/output boundary and verifies bank identity.
"""
import sys, json, subprocess, hashlib
from pathlib import Path
role, arg = sys.argv[1:]
c = Path(arg).resolve(); out=c/'formal'; out.mkdir()
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source')
sys.path.insert(0,str(root/'project/experiments/block_v1'))
from native_logic_projection import export, project
from native_formal import inspect
from structural_view import compare
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
repo=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign')
gold=repo/('issue-201-compact-ge/2ba89c0bd/release/g/6_final.v' if role=='G' else 'issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.v')
top='block_v2_g' if role=='G' else 'local_s_base'
def run(args, log):
    with (out/log).open('w') as f:
        subprocess.run(list(map(str,args)),cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
def yosys(name, script):
    p=out/(name+'.ys');p.write_text(script);run(['yosys','-s',p],name+'.log')
views=[]; identities=[]
for label, netlist in [('gold',gold),('gate',c/'candidate.v')]:
    if role=='G':
        v,proof=export(root,out,run,netlist,lib,top,label,constant_functions=True)
    else:
        sram=repo/'issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib'
        yosys(label+'-parse',f'read_liberty -lib {lib}\nread_liberty -lib {sram}\nread_verilog {netlist}\nhierarchy -check -top {top}\nwrite_json {label}.json\n')
        data,proof=project(json.loads((out/(label+'.json')).read_text()),lib.read_text())
        module=data['modules'][top]
        banks=sorted(n for n,x in module['cells'].items() if x['type']=='s_sram_256x128_freepdk45')
        assert len(banks)==4
        identities.append(banks)
        contract={'clk0':('input',1),'csb0':('input',1),'web0':('input',1),'addr0':('input',8),'din0':('input',128),'dout0':('output',128)}
        for i,n in enumerate(banks):
            bank=module['cells'].pop(n)
            assert not bank['parameters'] and set(bank['connections'])==set(contract)
            for pin,(direction,width) in contract.items():
                bits=bank['connections'][pin]
                assert len(bits)==width and bank['port_directions'][pin]==direction
                key=f'__sram_{i}_{pin}'
                assert key not in module['ports'] and key not in module['netnames']
                module['ports'][key]=dict(direction='input' if direction=='output' else 'output',bits=bits[:])
                module['netnames'][key]=dict(hide_name=0,bits=bits[:],attributes={})
        (out/(label+'-cut.json')).write_text(json.dumps(data))
        v=out/(label+'-cut.v')
        yosys(label+'-emit',f'read_json {label}-cut.json\nwrite_verilog -noattr -noexpr -norename {v}\ndesign -reset\nread_liberty -lib {lib}\nread_verilog {v}\nhierarchy -check -top {top}\nwrite_json {label}-readback.json\n')
        compare(data,json.loads((out/(label+'-readback.json')).read_text()))
    (out/(label+'-projection.json')).write_text(json.dumps(proof,indent=2))
    views.append(v)
if role=='S': assert identities[0]==identities[1]
log=out/'kepler.log'
cfg=out/'kepler.yml'
cfg.write_text(f'format: verilog\ninput_paths:\n  - {views[0]}\n  - {views[1]}\nliberty_files:\n  - {lib}\nlog_file: {log}\n')
run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',cfg],'formal-command.log')
proof=inspect(log.read_text());assert proof['passed'],proof
(out/'receipt.json').write_text(json.dumps(dict(passed=True,scope='Accepted final leaf to ECO all-boundary equivalence',proof=proof,banks=identities,hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [gold,c/'candidate.v',lib]}),indent=2))
