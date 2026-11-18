"""Validate aliases, constants, unobserved nets, bus expansion, and pin values."""
import json
from pathlib import Path
import tempfile
from retained_pin_activity import map_retained

with tempfile.TemporaryDirectory() as directory:
    p=Path(directory)
    graph={'modules':{'example':dict(ports={'a':{'bits':[2,3]},'y':{'bits':[4]}},
        netnames={'a':{'bits':[2,3]},'y':{'bits':[4]},'state[0]':{'bits':[5,6]}},
        cells={'_10_':{'connections':{'A':[2],'B':['1'],'Z':[7]}},
               '_11_':{'connections':{'A':[5],'B':[7],'Z':[4]}}})}}
    (p/'graph.json').write_text(json.dumps(graph))
    (p/'raw.vcd').write_text('$timescale 1ps $end\n$scope module dut $end\n'
        '$var wire 2 a a [1:0] $end\n$var wire 1 y y $end\n'
        '$var wire 2 s state[0] [1:0] $end\n$upscope $end\n$enddefinitions $end\n'
        '#0\nb10 a\n0y\nb01 s\n#5\nb01 a\nb10 s\n#10\n1y\n#15\n')
    receipt=map_retained(p/'raw.vcd',p/'graph.json',p/'pins.vcd','example')
    assert receipt['expected_annotated_pins']==7 and receipt['total_connected_pins']==9
    assert receipt['pins_with_unobserved_activity']==2 and receipt['final_timestamp_ps']==15
    stack=[];pins={};values={};snapshots={};time=None
    for line in (p/'pins.vcd').read_text().splitlines():
        words=line.split()
        if words[0]=='$scope':stack.append(words[2])
        elif words[0]=='$upscope':stack.pop()
        elif words[0]=='$var':pins['/'.join(stack[1:]+[words[4]])]=words[3]
        elif line.startswith('#'):
            if time is not None:snapshots[time]={k:values[v] for k,v in pins.items()}
            time=int(line[1:])
        elif line[0] in '01':values[line[1:]]=int(line[0])
    snapshots[time]={k:values[v] for k,v in pins.items()}
    assert snapshots[0]=={'a[0]':0,'a[1]':1,'y':0,'_10_/A':0,'_10_/B':1,'_11_/A':1,'_11_/Z':0}
    assert snapshots[5]['a[0]']==snapshots[5]['_10_/A']==1
    assert snapshots[5]['_11_/A']==0
    assert snapshots[10]['y']==snapshots[10]['_11_/Z']==1
    assert snapshots[10]==snapshots[15]
print('RETAINED_PIN_ALIAS_PASS')
