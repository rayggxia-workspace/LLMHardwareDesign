"""Audit actual STA-written boundary constraints, including capacitance units."""
import re


def audit(text,pins,budget):
    inputs={p['pin']for p in pins if p['direction']=='input'and p['pin']!='clk'}
    outputs={p['pin']for p in pins if p['direction']=='output'}
    assert 'set_false_path'not in text and 'set_multicycle_path'not in text
    assert 'set_case_analysis'not in text and 'set_disable_timing'not in text
    delays={('input','min'):{},('input','max'):{},('output','min'):{},('output','max'):{}}
    loads={};drivers={}
    for line in text.splitlines():
        if line.startswith(('set_input_delay ','set_output_delay ')):
            m=re.fullmatch(r'set_(input|output)_delay ([\d.]+) -clock \[get_clocks \{core\}\] -(min|max) -add_delay \[get_ports \{([^}]+)\}\]',line)
            assert m,('Unexpected delay grammar',line)
            kind,value,limit,pin=m.groups();assert pin not in delays[kind,limit]
            delays[kind,limit][pin]=float(value)
        if line.startswith('set_load '):
            m=re.fullmatch(r'set_load -pin_load ([\d.]+) \[get_ports \{([^}]+)\}\]',line)
            assert m,('Unexpected load grammar',line)
            value,pin=m.groups();assert pin not in loads;loads[pin]=float(value)
        if line.startswith('set_driving_cell '):
            m=re.fullmatch(r'set_driving_cell -lib_cell (\S+) -pin \{([^}]+)\} -input_transition_rise 0\.0000 -input_transition_fall 0\.0000 \[get_ports \{([^}]+)\}\]',line)
            assert m,('Unexpected driver grammar',line)
            cell,port,pin=m.groups();assert pin not in drivers;drivers[pin]=(cell,port)
    for (kind,limit),values in delays.items():
        assert set(values)==(inputs if kind=='input'else outputs),(kind,limit,'Incomplete port coverage')
        expected=budget[kind+'_delay_'+limit+'_ns']
        assert all(abs(value-expected)<1e-8 for value in values.values())
    assert set(loads)==outputs and all(abs(v-budget['output_load_pf']*1000)<1e-8 for v in loads.values())
    assert set(drivers)==inputs and set(drivers.values())=={(budget['input_driver']['cell'],budget['input_driver']['pin'])}
    def number(pattern):
        m=re.search(pattern,text,re.M);assert m,pattern;return float(m.group(1))
    assert abs(number(r'^create_clock -name core -period ([\d.]+) \[get_ports \{clk\}\]$')-budget['clock_ns'])<1e-8
    assert abs(number(r'^set_clock_transition ([\d.]+) \[get_clocks \{core\}\]$')-budget['clock_transition_ns'])<1e-8
    assert abs(number(r'^set_clock_uncertainty ([\d.]+) core$')-budget['uncertainty_ns'])<1e-8
    return dict(inputs_except_clock=len(inputs),outputs=len(outputs),all_delay_limits_covered=True,
                output_load_ff=budget['output_load_pf']*1000,all_input_drivers=True)
