"""Small physical RC liveness regression for hierarchical SPEF read order.

Two real Nangate buffers and a known parent R/C network. Increasing only
parent C must change the real leaf driver's slack. Old order is a negative
control, rather than a second measurement of the production layout.
"""
import json
import os
from pathlib import Path
import re
import subprocess

from timing_run import PLATFORM


def main():
    out = Path(os.environ['TIMING_OUT']) / 'result'; out.mkdir()
    (out / 'toy.v').write_text('''module mt_a(input A, output Y); BUF_X4 u0(.A(A),.Z(Y)); endmodule
module mt_b(input A, output Y); BUF_X1 u0(.A(A),.Z(Y)); endmodule
module stitch_fixture(input x,output y); wire word; mt_a A(.A(x),.Y(word)); mt_b B(.A(word),.Y(y)); endmodule
''')
    header = '''*SPEF "IEEE 1481-1998"
*DESIGN "stitch_fixture"
*DATE "2026-11-08"
*VENDOR "timing validation"
*PROGRAM "explicit RC control"
*VERSION "1"
*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
'''
    native_a = header.replace('"stitch_fixture"', '"mt_a"') + '''*D_NET Y 0.001
*CONN
*P Y O
*I u0:Z O
*CAP
1 u0:Z 0.001
*RES
1 u0:Z Y 10
*END
'''
    native_b = header.replace('"stitch_fixture"', '"mt_b"') + '''*D_NET A 0.001
*CONN
*P A I
*I u0:A I
*CAP
1 u0:A 0.001
*RES
1 A u0:A 10
*END
'''
    (out / 'a.spef').write_text(native_a); (out / 'b.spef').write_text(native_b)
    result = {}
    for order in ('native_first', 'parent_first'):
        for ff in (10, 100):
            run = out / (order + '-' + str(ff)); run.mkdir()
            upper = header + f'''*D_NET word {ff / 1000:.6g}
*CONN
*I A:Y O
*I B:A I
*CAP
1 word:1 {ff / 1000:.6g}
*RES
1 A:Y word:1 5
2 word:1 B:A 5
*END
'''
            (run / 'upper.spef').write_text(upper)
            text = f'''read_lef {{{PLATFORM}/lef/NangateOpenCellLibrary.tech.lef}}
read_lef {{{PLATFORM}/lef/NangateOpenCellLibrary.macro.mod.lef}}
read_liberty {{{PLATFORM}/lib/NangateOpenCellLibrary_typical.lib}}
read_verilog {{{out.resolve()}/toy.v}}
link_design -hier stitch_fixture
create_clock -name core -period 3.3333
set_input_delay 0.1 -clock core [get_ports x]
set_input_transition 0.05 [get_ports x]
set_output_delay 0.1 -clock core [get_ports y]
set_load 2 [get_ports y]
'''
            top = f'read_spef {{{run.resolve()}/upper.spef}}\n'
            native = f'read_spef -path A {{{out.resolve()}/a.spef}}\nread_spef -path B {{{out.resolve()}/b.spef}}\n'
            text += native + top if order == 'native_first' else top + native
            text += 'puts "LEAF_SLACK [get_property [get_pins A/u0/Z] slack_max]"\nreport_parasitic_annotation\nexit\n'
            (run / 'run.tcl').write_text(text)
            with (run / 'openroad.log').open('xb') as f:
                subprocess.run(['openroad', '-no_init', '-exit', str(run.resolve() / 'run.tcl')], cwd=run,
                               stdout=f, stderr=subprocess.STDOUT, check=True)
            log = (run / 'openroad.log').read_text()
            assert 'not found' not in log
            value = float(re.search(r'LEAF_SLACK\s+([-\d.eE+]+)', log)[1])
            result[order + '/' + str(ff)] = value
    result['native_first_delta_ps'] = 1000 * (result['native_first/100'] - result['native_first/10'])
    result['parent_first_delta_ps'] = 1000 * (result['parent_first/100'] - result['parent_first/10'])
    result['passed'] = abs(result['native_first_delta_ps']) < .01 and result['parent_first_delta_ps'] < -1
    (out / 'stitch-control.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    assert result['passed']


if __name__ == '__main__': main()
