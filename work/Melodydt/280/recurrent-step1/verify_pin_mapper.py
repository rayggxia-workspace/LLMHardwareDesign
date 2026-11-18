"""Check actual scalar/vector aliases, shared IDs, constants and timestamp preservation."""
from pathlib import Path
import json
from map_vcd_pins import map_pins,digest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
work=ROOT/('tmp/recurrent-step1/pin-mapper-check-'+digest(HERE/'map_vcd_pins.py')[:12])
work.mkdir(exist_ok=True,parents=True)
graph={'modules':{'block_v1_r':dict(
    ports={'a':{'bits':[2,3]},'y':{'bits':[4]}},
    netnames={'a':{'bits':[2,3]},'_1_':{'bits':[4]},'_2_':{'bits':[5]}},
    cells={'_10_':{'connections':{'A1':[2],'A2':['1'],'ZN':[4]}},
           '_11_':{'connections':{'A':[3],'ZN':[5]}}})}}
(work/'graph.json').write_text(json.dumps(graph))
raw=work/'raw.vcd'
raw.write_text('$timescale 1ps $end\n$scope module tb $end\n$scope module dut $end\n'
    '$var wire 2 s a [1:0] $end\n$var wire 1 c _1_ $end\n$var wire 1 e _2_ $end\n'
    '$upscope $end\n$upscope $end\n$enddefinitions $end\n'
    '#0\nb10 s\n0c\n0e\n#5\nb01 s\n#10\n1c\n1e\n#15\n')
output=work/'pins.vcd'
receipt=map_pins(raw,work/'graph.json',output,digest(raw))
assert receipt['connected_pin_declarations']==8 and receipt['final_timestamp_ps']==15
stack=[];pins={};values={};snapshots={};time=None
for line in output.read_text().splitlines():
    parts=line.split()
    if not parts:continue
    if parts[0]=='$scope':stack.append(parts[2])
    elif parts[0]=='$upscope':stack.pop()
    elif parts[0]=='$var':pins['/'.join(stack[2:]+[parts[4]])]=parts[3]
    elif line.startswith('#'):
        if time is not None:snapshots[time]={p:values[c] for p,c in pins.items()}
        time=int(line[1:])
    elif line[0] in '01':values[line[1:]]=int(line[0])
snapshots[time]={p:values[c] for p,c in pins.items()}
expected={'a[0]':0,'a[1]':1,'y':0,'_10_/A1':0,'_10_/A2':1,'_10_/ZN':0,'_11_/A':1,'_11_/ZN':0}
assert snapshots[0]==expected
expected.update({'a[0]':1,'a[1]':0,'_10_/A1':1,'_11_/A':0})
assert snapshots[5]==expected
expected.update({'y':1,'_10_/ZN':1,'_11_/ZN':1})
assert snapshots[10]==snapshots[15]==expected
assert map_pins(raw,work/'graph.json',output,digest(raw))==receipt
try:map_pins(raw,work/'graph.json',output,'wrong-hash')
except AssertionError:pass
else:raise AssertionError('stale input accepted')
native=work/'native.vcd'
native.write_text('$timescale 1ps $end\n$scope module tb $end\n$scope module dut $end\n'
    '$var wire 2 s a [1:0] $end\n$var wire 1 c y $end\n'
    '$scope module _10_ $end\n$var wire 1 p A1 $end\n$var wire 1 k A2 $end\n$var wire 1 c ZN $end\n$upscope $end\n'
    '$scope module _11_ $end\n$var wire 1 q A $end\n$var wire 1 e ZN $end\n$upscope $end\n'
    '$upscope $end\n$upscope $end\n$enddefinitions $end\n'
    '#0\nb10 s\n0c\n0e\n0p\n1k\n1q\n#5\nb01 s\n1p\n0q\n#10\n1c\n1e\n#15\n')
native_check=map_pins(native,work/'graph.json',work/'native-pins.vcd',digest(native))
assert native_check['uses_original_vcd'] and native_check['connected_pin_declarations']==8
assert not (work/'native-pins.vcd').exists()
(work/'missing-initial.vcd').write_text(native.read_text().replace('1k\n',''))
try:map_pins(work/'missing-initial.vcd',work/'graph.json',work/'missing-pins.vcd',digest(work/'missing-initial.vcd'))
except AssertionError:pass
else:raise AssertionError('missing initial value accepted')
(HERE/'pin-mapper-check.json').write_text(json.dumps(dict(passed=True,checked_pins=8,
    checked_timestamps=4,scalar_vector_constant_and_shared_aliases_pass=True,
    native_pin_path_pass=True,missing_initial_rejected=True,
    stale_input_rejected=True,mapper_sha256=digest(HERE/'map_vcd_pins.py')),indent=2)+'\n')
print('PIN_MAPPER_CHECK_PASS')
