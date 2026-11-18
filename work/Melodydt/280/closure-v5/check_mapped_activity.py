"""Check SV logic, aliases, bus rejection, and paired-window initialization."""
from pathlib import Path
import tempfile

from dma_state_power import mapped_wave

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    raw = root / 'raw.vcd'
    raw.write_text('''$timescale 1ps $end
$scope module tb $end
$var logic 1 a outer $end
$scope module dut $end
$var logic 1 c clk $end
$var logic 8 r state [7:0] $end
$var logic 4 b packed [3:0] $end
$upscope $end
$upscope $end
$enddefinitions $end
#0
0a
0c
b00000001 r
b0000 b
#3
1c
b00000011 r
#6
0c
1a
#9
1c
''')
    known = {'clk': 1, 'state': 8, 'packed': 1, 'port': 1}
    row = mapped_wave(raw, root/'paired.vcd', known, 'tb/dut', 3, 9,
                      boundary={'port':'tb/outer'}, time_divisor=1)
    assert row['retained_names'] == ['clk', 'port', 'state']
    assert row['bits'] == 10 and row['window_ps'] == 6
    assert row['excluded_width_mismatches'] == {'packed':[4,1]}
    assert '#6' in (root/'paired.vcd').read_text()
    row = mapped_wave(raw, root/'retimed.vcd', known, 'tb/dut', 0, 9,
                      boundary={'port':'tb/outer'})
    assert row['window_ps'] == 3
    try:
        mapped_wave(raw, root/'invalid.vcd', known, 'tb/dut', 0, 9,
                    boundary={'packed':'tb/dut/packed'})
    except ValueError as error:
        assert 'boundary width mismatch' in str(error)
    else:
        raise AssertionError('mismatched boundary incorrectly accepted')
print('MAPPED_ACTIVITY_MATCHING_PASS')
