"""Check exact VCD resampling and reject non-clock-grid events."""
import importlib.util,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('calibrate_300',Path(__file__).with_name('calibrate_300.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    d=Path(td);s=d/'source.vcd';o=d/'out.vcd'
    header=b'$timescale 1ps $end\n$scope module dut $end\n$var wire 1 ! clk $end\n$upscope $end\n$enddefinitions $end\n'
    s.write_bytes(header+b'#0\n0!\n#2500\n1!\n#5000\n0!\n#7500\n1!\n#10000\n0!\n')
    r=m.retime(s,o,10000);assert r['target_window_ps']==6668 and r['event_sequence_preserved']
    assert b'#1667\n1!\n#3334' in o.read_bytes()
    s.write_bytes(header+b'#0\n0!\n#2499\n1!\n#10000\n')
    try:m.retime(s,o,10000)
    except AssertionError:pass
    else:raise AssertionError('off-grid event must reject')
print('PASS exact clock-grid retiming, values and rejection checks')
