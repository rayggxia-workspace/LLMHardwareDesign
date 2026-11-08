"""Server-only lint, control-boundary synthesis, hierarchy and SDC binding checks."""
from pathlib import Path
import argparse, collections, json, re, shutil, subprocess, tempfile
import package as pkg

def run(args, log, cwd):
    with log.open('wb') as stream:
        subprocess.run(list(map(str,args)),stdout=stream,stderr=subprocess.STDOUT,cwd=cwd,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--verilator',required=True);p.add_argument('--yosys',required=True);p.add_argument('--openroad',required=True);a=p.parse_args()
    root=a.package.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    receipt=pkg.audit(root);m=json.loads((root/'profile.json').read_text());top=m['top'];kind=m['parameters']['KIND']
    inc=['-I'+str(root/x) for x in m['include_dirs']]
    base=[a.verilator,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module',top,f'-GKIND={kind}','-GPM_USE_SRAM=1',*inc]
    run([*base,'-f','full.f'],out/'full-lint.log',root)
    run([*base,'-f','boundaries.f','-f','control.f'],out/'control-lint.log',root)
    warnings=re.findall(r'%Warning-([A-Z0-9_]+)',(out/'control-lint.log').read_text())
    assert not set(warnings)&{'LATCH','MULTIDRIVEN','UNOPTFLAT','PINMISSING','WIDTHTRUNC'},set(warnings)
    def q(path):return json.dumps(str(path))
    script=out/'structural.ys'
    script.write_text((root/'synth.ys').read_text()+'write_json '+q(out/'control.json')+'\nwrite_verilog -noattr '+q(out/'control.v')+'\n')
    run([a.yosys,'-s',script],out/'synth.log',root)
    design=json.loads((out/'control.json').read_text());modules=design['modules']
    def count(module, leaf):
        d=modules[module]
        if module==leaf or d.get('attributes',{}).get('hdlname')==leaf:return 1
        return sum(count(c['type'],leaf) for c in d.get('cells',{}).values() if c['type'] in modules)
    counts={name:count(top,name) for name in m['hierarchy_expected']}
    assert counts==m['hierarchy_expected'],counts
    ports=modules[top]['ports'];totals={d:sum(len(p['bits']) for p in ports.values() if p['direction']==d) for d in ('input','output')}
    # Actual elaborated top ports, without a fabricated timing path. This harness
    # tests SDC syntax/object coverage only; it cannot produce meaningful slack.
    decl=[]
    for name,port in ports.items():
        width=len(port['bits']);decl.append(port['direction']+(' ['+str(width-1)+':0]' if width>1 else '')+' '+name+';')
    interface=out/'interface.v';interface.write_text('module '+top+'('+','.join(ports)+');\n'+'\n'.join(decl)+'\nendmodule\n')
    tcl=out/'sdc-check.tcl'
    tcl.write_text('read_lef '+q(root/'technology/lef/NangateOpenCellLibrary.tech.lef')+'\nread_lef '+q(root/'technology/lef/NangateOpenCellLibrary.macro.mod.lef')+'\nread_liberty '+q(root/'technology/lib/NangateOpenCellLibrary_typical.lib')+'\nread_verilog '+q(interface)+f'\nlink_design {top}\nsource '+q(root/'constraints.sdc')+'\nreport_units\n'+
        'if {[llength [get_clocks *]] != 1} {error "clock count"}\n'+
        f'if {{[llength [all_inputs]] != {totals["input"]}}} {{error "input count"}}\n'+
        f'if {{[llength [all_inputs -no_clocks]] != {totals["input"]-1}}} {{error "data input count"}}\n'+
        f'if {{[llength [all_outputs]] != {totals["output"]}}} {{error "output count"}}\n'+
        'if {[llength [get_ports rst_ni]] != 1} {error "reset port"}\n'+
        'write_sdc -digits 12 '+q(out/'resolved.sdc')+'\nputs "PASS SDC object binding"\nexit\n')
    run([a.openroad,'-exit',tcl],out/'sdc.log',root)
    text=(out/'sdc.log').read_text();assert 'PASS SDC object binding' in text
    assert not re.search(r'\[(ERROR|WARNING) (STA|ORD)-',text),text
    resolved=(out/'resolved.sdc').read_text()
    assert 'rst_ni' in resolved
    period=float(re.search(r'create_clock .*?-period ([0-9.eE+-]+)',resolved)[1])
    # OpenSTA serializes its internal float representation. 1e-6 ns = 1 fs;
    # this checks representation precision, not a changed implementation budget.
    assert abs(period-3.333333333)<1e-6,period
    # Require actual serialized max/min constraints for every bit, not just counts.
    names={d:[] for d in ('input','output')}
    for name,port in ports.items():
        if name=='clk_i':continue
        names[port['direction']]+=([name] if len(port['bits'])==1 else [f'{name}[{i}]' for i in range(len(port['bits']))])
    for direction,nameset in names.items():
        command='set_'+direction+'_delay'
        lines=[x for x in resolved.splitlines() if x.startswith(command)]
        assert lines,command
        for name in nameset:
            escaped=name.replace('[','\\[').replace(']','\\]')
            found=[x for x in lines if name in x or escaped in x]
            for flag,expected in (('-max',0.5),('-min',0.05)):
                selected=[x for x in found if flag in x]
                assert selected,(command,name,flag)
                assert all(abs(float(re.search(command+r'\s+([0-9.eE+-]+)',x)[1])-expected)<1e-6 for x in selected),(command,name,flag)
            if direction=='output':
                loads=[x for x in resolved.splitlines() if x.startswith('set_load ') and (name in x or escaped in x)]
                assert loads and all(abs(float(re.search(r'-pin_load\s+([0-9.eE+-]+)',x)[1])-5.0)<1e-6 for x in loads),name
    with tempfile.TemporaryDirectory(prefix='relocated package ',dir=out) as temp:
        moved=Path(temp)/'copy';shutil.copytree(root,moved);assert pkg.audit(moved)==pkg.audit(root)
        commands=(moved/'synth.ys').read_text().split('\nsynth -top ',1)[0]+'\ncheck -assert\n'
        relscript=out/'relocation.ys';relscript.write_text(commands)
        run([a.yosys,'-s',relscript],out/'relocation.log',moved)
    receipt.update(schema='control-synthesis-freeze-validation/1',top=top,parameters=m['parameters'],hierarchy=counts,ports=totals,relocated_package_hierarchy_checked=True,
        sdc={'input_bits':totals['input']-1,'output_bits':totals['output'],'period_ns':'3.333333333','serialized_period_ns':period,'readback_tolerance_ns':1e-6,'all_max_min_serialized':True,'all_output_loads_ff':5.0,'reset_exception':False,'scope':'SDC syntax and object binding on actual elaborated port declarations; no timing path or slack claimed.'},
        control_warnings=dict(collections.Counter(warnings)),full_warnings=dict(collections.Counter(re.findall(r'%Warning-([A-Z0-9_]+)',(out/'full-lint.log').read_text()))),
        artifacts_sha256={x.name:pkg.sha(x) for x in sorted(out.iterdir()) if x.is_file()},scope=m['scope'])
    pkg.dump(out/'report.json',receipt);print('PASS synthesis freeze',m['profile']['name'])

if __name__=='__main__':main()
