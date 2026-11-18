"""Gate replay and matched active/quiet windows for isolated 8-lane state services."""
from pathlib import Path
from hashlib import sha256
import json,re,subprocess,shutil,sys,os
from concurrent.futures import ThreadPoolExecutor
from map_vcd_pins import map_pins

work=Path.cwd()
design=work.parent
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
cells=Path('/public/home/yuzelu/project-circuit/issue250-p-final-native-diode-gate-GlrL0V/cells.v')
verilator=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def run(args,log):
    with Path(log).open('w') as f:
        subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
receipt=json.loads((design/'synth-receipt.json').read_bytes())
assert receipt['liberty_sha256']==digest(lib)
assert receipt['netlist_sha256']==digest(design/'mapped.v')
sta_view=json.loads((design/'sta-view/sta-view.json').read_bytes())
sta_netlist=design/'sta-view/mapped_sta.v'
assert sta_view['original_netlist_sha256']==receipt['netlist_sha256']
assert sta_view['sta_netlist_sha256']==digest(sta_netlist)
count=sum(1 for _ in (work/'commands.txt').open())
segments=json.loads((work/'segments.json').read_bytes())
(work/'ends.txt').write_text('\n'.join(str(x['end_command']) for x in segments)+'\n')
signature={str(p):digest(p) for p in [design/'mapped.v',cells,work/'commands.txt',
                                    work/'segments.json',work/'calibrate_tb.sv']}
checkpoint=work/'gate-replay-receipt.json'
resume=json.loads(checkpoint.read_text()) if checkpoint.exists() else None
if resume:
    assert resume['inputs']==signature and resume['vcd_sha256']==digest(work/'raw.vcd')
    assert resume['log_sha256']==digest(work/'replay.log')
else:
    prebuilt=work/'prebuilt-receipt.json'
    if prebuilt.exists():
        built=json.loads(prebuilt.read_text())
        assert built['inputs']==signature
        assert built['binary_sha256']==digest(work/'obj_dir/Vcalibrate_tb')
        assert built['build_input_sha256']==digest(work/'low-build-input.json')
    else:
        run([verilator,'--binary','--timing','--trace','--trace-depth','2','--assert',
             '--trace-underscore','-Wno-fatal','-j','12','--output-groups','0','--top-module','calibrate_tb',design/'mapped.v',cells,
             'calibrate_tb.sv'],'build.log')
    run([work/'obj_dir/Vcalibrate_tb',f'+count={count}'],'replay.log')
text=(work/'replay.log').read_text()
assert 'GATE_REPLAY_PASS' in text
windows=re.findall(r'WINDOW (\d+) (\d+) (\d+) (\d+)',text)
assert len(windows)==12
if not resume:
    checkpoint.write_text(json.dumps(dict(inputs=signature,vcd_sha256=digest(work/'raw.vcd'),
                                         log_sha256=digest(work/'replay.log')),indent=2)+'\n')

def split_windows(source):
    # Read the potentially large gate trace once, preserving boundary values.
    spans=[]
    for ident,a,b,c in windows:
        ident,a,b,c=map(int,(ident,a,b,c))
        assert c-b==b-a and b>a
        spans.extend([(a,b,work/f'window-{ident}-active.vcd'),
                      (b,c,work/f'window-{ident}-idle.vcd')])
    assert all(x[1]==y[0] for x,y in zip(spans,spans[1:]))
    values={};header=[];index=0;out=None;timestamp=0
    with source.open() as f:
        for line in f:
            header.append(line)
            if '$enddefinitions' in line:break
        for line in f:
            first,last,dst=spans[index]
            if line.startswith('#'):
                timestamp=int(line[1:])
                if timestamp>last:
                    assert out is not None
                    out.write('#'+str(last-first)+'\n');out.close();out=None
                    index+=1
                    if index==len(spans):break
                    first,last,dst=spans[index]
                    assert timestamp<=last
                if timestamp>first:
                    if out is None:
                        out=dst.open('w');out.writelines(header);out.write('#0\n')
                        out.writelines(values.values())
                    out.write('#'+str(timestamp-first)+'\n')
            elif line and line[0] in '01xz':
                values[line.strip()[1:]]=line
                if out is not None:out.write(line)
            elif line and line[0] in 'bBrR':
                values[line.split()[1]]=line
                if out is not None:out.write(line)
    if out is not None:
        assert timestamp>=spans[index][1]
        out.write('#'+str(spans[index][1]-spans[index][0])+'\n');out.close();index+=1
    assert index==len(spans)

stack=[];dut_scope=None;internal_nets=0
with (work/'raw.vcd').open() as f:
    for line in f:
        fields=line.split()
        if not fields:continue
        if fields[0]=='$scope':
            stack.append(fields[2])
            if stack[-1]=='dut':dut_scope='/'.join(stack)
        elif fields[0]=='$upscope':stack.pop()
        elif fields[0]=='$var' and stack and stack[-1]=='dut' and re.fullmatch(r'_\d+_',fields[4]):internal_nets+=1
        elif fields[0]=='$enddefinitions':break
assert dut_scope and internal_nets>100000,(dut_scope,internal_nets)
graph_receipt=json.loads((design/'pin-map/graph-receipt.json').read_text())
assert graph_receipt['source_verilog_sha256']==sta_view['sta_netlist_sha256']
assert graph_receipt['graph_sha256']==digest(design/'pin-map/sta_graph.json')
pin_mapping=map_pins(work/'raw.vcd',design/'pin-map/sta_graph.json',work/'pins.vcd',
                     json.loads(checkpoint.read_text())['vcd_sha256'])
assert pin_mapping['scope']==dut_scope
expected_pins=graph_receipt['connected_cell_pins']+graph_receipt['top_port_bits']
assert pin_mapping['connected_pin_declarations']==expected_pins
split_windows(work/('raw.vcd' if pin_mapping.get('uses_original_vcd') else 'pins.vcd'))

def measure_window(task):
        ident,name=task
        prefix=work/f'window-{ident}-{name}'
        wave=prefix.with_suffix('.vcd')
        assert wave.exists()
        script=prefix.with_suffix('.tcl')
        script.write_text('\n'.join([
            'read_liberty {'+str(lib)+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
            'read_verilog {'+str(sta_netlist)+'}',
            'link_design block_v1_r',
            'create_clock -name core -period 5 [get_ports clk]',
            'set_input_transition 0.05 [all_inputs]',
            'read_vcd -scope '+dut_scope+' {'+str(wave)+'}',
            'report_activity_annotation','report_power -digits 9'])+'\n')
        log=prefix.with_suffix('.log')
        run(['openroad','-no_init','-threads','3','-exit',script],log)
        txt=log.read_text()
        vals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',txt)
        ann=re.findall(r'Annotated (\d+) pin activities\.',txt)
        assert len(vals)==1 and len(ann)==1 and int(ann[0])==expected_pins,txt[-3000:]
        assert not re.search(r'(?m)^(Error:|\[ERROR)',txt)
        power=dict(zip(['internal','switching','leakage','total'],map(float,vals[0])))
        power['annotated']=int(ann[0])
        print('POWER_WINDOW_PASS',ident,name,flush=True)
        return task,power

tasks=[(int(w[0]),name) for w in windows for name in ('active','idle')]
with ThreadPoolExecutor(max_workers=4) as executor:
    measured=dict(executor.map(measure_window,tasks))
results=[]
for ident,a,b,c in windows:
    ident,a,b,c=map(int,(ident,a,b,c))
    assert c-b==b-a and b>a
    powers={name:measured[(ident,name)] for name in ('active','idle')}
    delta=(powers['active']['total']-powers['idle']['total'])*(b-a)/1000
    assert delta>0
    results.append(dict(segment=segments[ident],window_ps=b-a,power_w=powers,increment_nj=delta))
    print('STATE_ENERGY',ident,delta,flush=True)
result=dict(clock_mhz=200,wire_parasitics_loaded=False,activity='mapped gate-level VCD',
            vcd_scope=dut_scope,traced_internal_nets=internal_nets,
            sta_view=sta_view,driver_sha256=digest(Path(__file__)),
            pin_mapping=pin_mapping,pin_graph=graph_receipt,
            source=receipt,inputs_sha256={p.name:digest(p) for p in [cells,lib,work/'commands.txt',work/'calibrate_tb.sv']},
            windows=results,gate_replay_pass=True)
result['tools']={'python':sys.version}
if (work/'prebuilt-receipt.json').exists():
    result['prebuilt']=json.loads((work/'prebuilt-receipt.json').read_text())
for name,path,arg in [('verilator',verilator,'--version'),('yosys',Path(shutil.which('yosys')),'-V'),
                      ('openroad',Path(shutil.which('openroad')),'-version')]:
    result['tools'][name]=dict(path=str(path),resolved_executable_sha256=digest(path.resolve()),
        version=subprocess.check_output([str(path),arg],text=True).strip())
(work/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
print('RECURRENT_CALIBRATION_PASS',flush=True)
