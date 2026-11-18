"""Check native pin annotation on a completed trace prefix, excluded from energy rollup."""
from pathlib import Path
from hashlib import sha256
import json,re,subprocess
from map_vcd_pins import map_pins

work=Path.cwd()
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
results=[]
for model in ('qwen35-fast','falcon-wide-fast'):
    design=work.parent/model
    source=design/'power-full/raw.vcd'
    dst=work/model
    dst.mkdir(exist_ok=False)
    wave=dst/'prefix.vcd'
    cutoff=100000
    with source.open() as inp,wave.open('w') as out:
        for line in inp:
            if line.startswith('#') and int(line[1:])>cutoff:
                out.write('#'+str(cutoff)+'\n');break
            out.write(line)
        else:raise AssertionError('trace has not passed preflight cutoff')
    h=sha256(wave.read_bytes()).hexdigest()
    pins=map_pins(wave,design/'pin-map/sta_graph.json',dst/'pins.vcd',h)
    assert pins.get('uses_original_vcd'),'full trace must natively include connected pins'
    tcl=dst/'probe.tcl'
    tcl.write_text('\n'.join([
        'read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}',
        'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
        'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
        'read_verilog {'+str(design/'sta-view/mapped_sta.v')+'}',
        'link_design block_v1_r',
        'create_clock -name core -period 5 [get_ports clk]',
        'set_input_transition 0.05 [all_inputs]',
        'read_vcd -scope '+pins['scope']+' {'+str(wave)+'}',
        'report_activity_annotation','report_power -digits 9'])+'\n')
    log=dst/'probe.log'
    with log.open('w') as f:subprocess.run(['openroad','-no_init','-threads','3','-exit',str(tcl)],stdout=f,stderr=subprocess.STDOUT,check=True)
    text=log.read_text()
    counts=re.findall(r'Annotated (\d+) pin activities\.',text)
    assert len(counts)==1 and int(counts[0])==pins['connected_pin_declarations'],text[-2000:]
    result=dict(model=model,passed=True,annotated=int(counts[0]),wave_sha256=h,
                log_sha256=sha256(log.read_bytes()).hexdigest(),pins=pins,
                use='Reader/coverage preflight only; excluded from calibration and model energy.')
    results.append(result)
    (work/'receipt.json').write_text(json.dumps(results,indent=2)+'\n')
    print('FULL_PIN_PREFLIGHT_PASS',model,counts[0],flush=True)
