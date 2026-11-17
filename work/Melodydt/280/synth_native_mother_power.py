"""Synthesize the actual nine-target mother core; estimate power without wire RC.

No PM array, packet transport, LC, placement, CTS, routing, or SPEF is included.
Boundary VCD propagation is a provisional reference, not internal gate replay.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


root, out = map(Path, sys.argv[1:])
rtl = root / 'm-product/wide-38792112/source/project/rtl/mother_control_native'
platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
lib = platform / 'lib/NangateOpenCellLibrary_typical.lib'
def digest(p):
    h = sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()
source = rtl / 'mc_native_controller.sv'
text = source.read_text()
anchor = 'parameter integer unsigned STALL_LIMIT=1024'
if text.count(anchor) != 1:
    raise ValueError('native mother parameter declaration changed')
wrapper = (rtl / 'mother_control_native64.sv').read_text()
if '.STALL_LIMIT(4096),.SERVICE_STALL_LIMIT(SERVICE_STALL_LIMIT)' not in wrapper:
    raise ValueError('actual mother instantiation changed')
text = text.replace(anchor, 'parameter integer unsigned STALL_LIMIT=4096')
# Slang rejects this forward net reference. Split its declaration and driver;
# preserve the exact combinational expression and every sequential assignment.
forward = '  wire return_fire=return_accept && return_validated;'
driver = '  wire return_validated='
if text.count(forward) != 1 or text.count(driver) != 1:
    raise ValueError('native mother forward declaration changed')
text = text.replace(forward, '  wire return_validated;\n'+forward).replace(driver, '  assign return_validated=')
(out / source.name).write_text(text)
inputs = {str(p):digest(p) for p in [source, rtl/'mother_control_native64.sv',
    rtl/'mc_native_ports.svh', rtl/'native_instruction_fetch.svh', lib]}
ys = '\n'.join([
    'read_slang --top mc_native_controller -I{} {}'.format(rtl, out/source.name),
    'synth -top mc_native_controller -flatten -noabc -noshare',
    'dfflibmap -liberty {}'.format(lib),
    'abc -liberty {}'.format(lib),
    'clean', 'check', 'stat -liberty {}'.format(lib),
    'write_verilog -noattr -noexpr {}'.format(out/'mapped.v'),
    'write_json {}'.format(out/'mapped.json')])+'\n'
(out/'synth.ys').write_text(ys)
subprocess.run(['yosys','-l',str(out/'synth.log'),str(out/'synth.ys')],check=True)
design = json.loads((out/'mapped.json').read_bytes())['modules']['mc_native_controller']
if any(cell['type'].startswith('$') for cell in design['cells'].values()):
    raise ValueError('unmapped cell remains')
ports = []
for name, pin in design['ports'].items():
    width = len(pin['bits'])
    ports.append('{} {}{};'.format(pin['direction'], '[{}:0] '.format(width-1) if width>1 else '', name))
(out/'boundary.v').write_text('\n'.join(ports)+'\n')
helper = root/'writer-power/frozen/extract_c639_m_ports.py'
helper_text = helper.read_text()
if helper_text.count('selected["clk"]') != 1:
    raise ValueError('boundary extractor changed')
(out/'extract_clk_i.py').write_text(helper_text.replace('selected["clk"]', 'selected["clk_i"]'))
sys.path.insert(0,str(out))
from extract_clk_i import extract
activity_path=root/'control-activity/activity-38796363/control-activity.json'
activity=json.loads(activity_path.read_bytes())
inputs[str(activity_path)]=digest(activity_path)
inputs[str(helper)]=digest(helper)

def measure(item):
    name, spec = item
    p=out/name;p.mkdir()
    fst=Path(spec['source'])
    if digest(fst)!=spec['fst_sha256']:
        raise ValueError('C639 source activity changed')
    raw=p/'raw.vcd'
    subprocess.run([str(root/'writer-power/frozen/fst_scope_vcd'),str(fst),str(raw),
                    activity['scopes']['mother_core']],check=True)
    with raw.open() as stream:
        times=[int(line[1:]) for line in stream if line.startswith('#')]
    wave=p/'ports-300.vcd'
    extract(out/'boundary.v',raw,wave,activity['scopes']['mother_core'],times[0],times[-1],300,
            expected_port_bits=None)
    tcl='\n'.join([
        'read_liberty {'+str(lib)+'}',
        'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
        'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
        'read_verilog {'+str(out/'mapped.v')+'}',
        'link_design mc_native_controller',
        'create_clock -name core -period 3.333333333333 [get_ports clk_i]',
        'set_input_transition 0.05 [all_inputs]',
        'read_vcd -scope dut {'+str(wave)+'}',
        'report_activity_annotation','report_power -digits 9'])+'\n'
    (p/'power.tcl').write_text(tcl)
    with (p/'power.log').open('w') as f:
        subprocess.run(['openroad','-no_init','-threads','3','-exit',str(p/'power.tcl')],
                       stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(p/'power.log').read_text()
    power=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',log)
    annotated=re.findall(r'Annotated (\d+) pin activities\.',log)
    if len(power)!=1 or len(annotated)!=1 or re.search(r'(?m)^(Error:|\[ERROR)',log):
        raise ValueError('invalid power output')
    if int(annotated[0]) < sum(len(pin['bits']) for pin in design['ports'].values()):
        raise ValueError('incomplete boundary annotation')
    return name, {'power_w':dict(zip(('internal','switching','leakage','total'),map(float,power[0]))),
        'annotated':int(annotated[0]),'wave_sha256':digest(wave),'source_fst_sha256':digest(fst),
        'power_log_sha256':digest(p/'power.log'),'window_ps':(times[-1]-times[0])*100/300}

with ThreadPoolExecutor(max_workers=4) as pool:
    rows=dict(pool.map(measure,sorted(activity['windows'].items())))
result={'top':'mc_native_controller','targets':9,'STALL_LIMIT':4096,'SERVICE_STALL_LIMIT':4096,
    'source_sha256':inputs,'mapped_netlist_sha256':digest(out/'mapped.v'),
    'wire_parasitics_loaded':False,'clock_mhz':300,'cell_count':len(design['cells']),
    'activity':'C639 boundary VCD propagated through mapped cells; internal gate replay not performed',
    'scope':'mother core only, excluding PM, transport and local controllers',
    'timing_signoff':False,'windows':rows}
(out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
print('NATIVE_MOTHER_NO_WIRE_POWER_PASS')
