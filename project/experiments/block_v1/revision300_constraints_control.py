"""Actual native SDC serialization fixture; no leaf qualification."""
import json
import re
from pathlib import Path


def serialization(text):
    result={}
    for line in text.splitlines():
        tokens=line.split();key=None;index=1
        if line.startswith('create_clock '):key='clock_ns';index=4
        elif line.startswith('set_clock_transition '):key='clock_transition_ns'
        elif line.startswith('set_clock_uncertainty '):key='uncertainty_ns'
        elif line.startswith(('set_input_delay ','set_output_delay ')):
            key=('input'if line.startswith('set_input_delay ')else'output')+'_delay_'+('min'if' -min 'in line else'max')+'_ns'
        elif line.startswith('set_load '):key='output_load_ff';index=2
        if key:
            value=tokens[index]
            if key in result:assert result[key]==value
            result[key]=value
    assert set(result)=={'clock_ns','clock_transition_ns','uncertainty_ns','input_delay_min_ns','input_delay_max_ns','output_delay_min_ns','output_delay_max_ns','output_load_ff'}
    return result


def control(root,out,cpus,run):
    from constraints import generate
    from io_slots import file_sha
    from revision300_constraint_readback import audit
    assert cpus==16
    budget=json.loads((root/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    fixture=out/'fixture.v'
    fixture.write_text('module revision300_boundary_fixture(input clk,input d,output q); DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n')
    pins=[dict(pin='clk',direction='input'),dict(pin='d',direction='input'),dict(pin='q',direction='output')]
    variants={'positive':dict(budget),'old-rounded-period':dict(budget,clock_ns=3.3333),
              'wrong-cap':dict(budget,output_load_pf=.002),'wrong-delay':dict(budget,input_delay_max_ns=.8001)}
    reports={};reference=None
    for name,selected in variants.items():
        sdc=re.sub(r'create_clock -name core -period [^ ]+',
                   'create_clock -name core -period %.12g'%selected['clock_ns'],generate(selected))
        (out/(name+'-input.sdc')).write_text(sdc)
        script='read_liberty {'+str(lib)+'}\nread_verilog {'+str(fixture)+'}\nlink_design revision300_boundary_fixture\n'
        script+='read_sdc {'+str(out/(name+'-input.sdc'))+'}\nwrite_sdc -no_timestamp -digits 12 {'+str(out/(name+'-readback.sdc'))+'}\n'
        (out/(name+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/(name+'.tcl')],name+'.log')
        actual=(out/(name+'-readback.sdc')).read_text()
        if name=='positive':
            reference=serialization(actual)
            reports[name]=dict(passed=True,audit=audit(actual,pins,budget,reference))
        else:
            rejected=False
            try:audit(actual,pins,budget,reference)
            except AssertionError:rejected=True
            assert rejected,name
            reports[name]=dict(rejected=True)
    result=dict(passed=True,budget=budget,serialization=reference,cases=reports,
                library_sha256=file_sha(lib),qualified_hard_macro=False,
                scope='Native approved-budget 12-decimal SDC reference and three actual independently reparsed bad-budget controls; no STA slack adjustment or leaf acceptance')
    (out/'revision300-constraints-control.json').write_text(json.dumps(result,indent=2)+'\n')


def reference(root,out,budget):
    from io_slots import file_sha
    source=out.parent/'revision300-constraints-control'
    r=json.loads((source/'receipt.json').read_text());assert r['passed']is True and r['mode']==source.name
    p=source/'revision300-constraints-control.json'
    assert file_sha(p)==r['outputs'][p.name]
    report=json.loads(p.read_text());assert report['passed']is True and report['budget']==budget
    for name in ['revision300_constraint_readback.py','revision300_constraints_control.py']:
        relative='project/experiments/block_v1/'+name
        assert file_sha(root/relative)==r['inputs'][relative]
    assert all(file_sha(Path(path))==digest for path,digest in r['tool_hashes'].items())
    assert file_sha(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'))==report['library_sha256']
    return report['serialization'],file_sha(source/'receipt.json')
