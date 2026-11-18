"""Tool-format preflight only; the deliberately incomplete trace is not calibration."""
from pathlib import Path
import re, subprocess, json
work=Path.cwd()
design=work.parent
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
script=work/'probe.tcl'
script.write_text('\n'.join([
    'read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
    'read_verilog {'+str(work/'mapped_sta.v')+'}',
    'link_design block_v1_r', 'create_clock -name core -period 5 [get_ports clk]',
    'set_input_transition 0.05 [all_inputs]',
    'read_vcd -scope calibrate_tb/dut {'+str(design/'power-clang/window-0-active.vcd')+'}',
    'report_activity_annotation','report_power -digits 9'])+'\n')
with (work/'probe.log').open('w') as f:
    subprocess.run(['openroad','-no_init','-threads','3','-exit',str(script)],stdout=f,stderr=subprocess.STDOUT,check=True)
text=(work/'probe.log').read_text()
annotations=re.findall(r'Annotated (\d+) pin activities\.',text)
totals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',text)
assert len(annotations)==len(totals)==1,text[-2000:]
(work/'probe-receipt.json').write_text(json.dumps(dict(purpose='Tool API and report format only. Incomplete internal activity: NOT an energy calibration.',
    parsed_annotation_count=int(annotations[0]),power_total_fields=len(totals[0])),indent=2)+'\n')
print('POWER_READER_FORMAT_PASS',flush=True)
