"""Reanalyse accepted zero-delay gate events at 3334 ps, without resynthesis.

No event value, ordering, netlist, voltage, temperature or input slew changes.
This is conditional pre-layout power calibration, not 300 MHz timing signoff.
"""
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
import json,re,subprocess,sys

def digest(p):
    h=sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def retime(source,dest,old_duration):
    """Exact half-cycle bijection: 2500 ps -> 1667 ps; reject other timing."""
    ih,oh,events=sha256(),sha256(),sha256();timestamps=0;previous=-1;header=bytearray();in_header=True
    with source.open('rb') as inp,dest.open('wb') as out:
        for line in inp:
            ih.update(line)
            if in_header:
                header.extend(line)
                if b'$enddefinitions' in line:in_header=False
            if line.startswith(b'#'):
                value=int(line[1:]);assert value%2500==0 and value>=previous,(source,value,previous)
                assert value<=old_duration
                previous=value;timestamps+=1
                line=b'#'+str(value//2500*1667).encode()+b'\n'
            else:events.update(line)
            out.write(line);oh.update(line)
    assert b'$timescale1ps$end' in re.sub(rb'\s+',b'',header)
    assert previous==old_duration and old_duration%5000==0 and timestamps>1
    # Independently reread the new artifact: values/declarations must be unchanged.
    reread=sha256();new_events=sha256();last=-1;nt=0
    with dest.open('rb') as f:
        for line in f:
            reread.update(line)
            if line.startswith(b'#'):
                value=int(line[1:]);assert value%1667==0 and value>=last
                last=value;nt+=1
            else:new_events.update(line)
    assert reread.hexdigest()==oh.hexdigest() and new_events.digest()==events.digest() and nt==timestamps
    return dict(source_sha256=ih.hexdigest(),target_sha256=oh.hexdigest(),non_timestamp_sha256=events.hexdigest(),
                timestamp_lines=timestamps,source_window_ps=old_duration,target_window_ps=last,
                exact_half_cycle_mapping=[2500,1667],event_sequence_preserved=True)

def main():
    work=Path.cwd();config=json.loads((work/'config.json').read_bytes())
    source=Path(config['source']);design=source.parent
    oldpath=source/'calibration.json';assert digest(oldpath)==config['calibration_sha256']
    old=json.loads(oldpath.read_bytes());assert old['gate_replay_pass'] and old['clock_mhz']==200 and not old['wire_parasitics_loaded']
    assert len(old['windows'])==12
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    netlist=design/'sta-view/mapped_sta.v'
    assert digest(lib)==old['source']['liberty_sha256']
    assert digest(design/'mapped.v')==old['source']['netlist_sha256']
    assert digest(netlist)==old['sta_view']['sta_netlist_sha256']
    gate=json.loads((source/'gate-replay-receipt.json').read_bytes())
    assert digest(source/'raw.vcd')==gate['vcd_sha256']
    assert digest(source/'replay.log')==gate['log_sha256']
    expected=old['pin_graph']['connected_cell_pins']+old['pin_graph']['top_port_bits']
    scope=old['vcd_scope'];assert old['pin_mapping']['connected_pin_declarations']==expected
    for name in ('commands.txt','segments.json'):
        assert digest(source/name)==next(v for k,v in gate['inputs'].items() if Path(k).name==name)
    print('SOURCE_HASH_AND_FULL_GATE_REPLAY_VERIFIED',flush=True)
    def measure(task):
        ident,name=task;sample=old['windows'][ident]
        assert sample['power_w'][name]['annotated']==expected
        prefix=work/f'window-{ident}-{name}';vcd=prefix.with_suffix('.vcd')
        transfer=retime(source/vcd.name,vcd,sample['window_ps'])
        script=prefix.with_suffix('.tcl')
        script.write_text('\n'.join([
            'read_liberty {'+str(lib)+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
            'read_verilog {'+str(netlist)+'}','link_design block_v1_r',
            'create_clock -name core -period 3.334 [get_ports clk]',
            'set_input_transition 0.05 [all_inputs]',
            'read_vcd -scope '+scope+' {'+str(vcd)+'}',
            'report_activity_annotation','report_power -digits 9'])+'\n')
        log=prefix.with_suffix('.log')
        with log.open('w') as f:subprocess.run(['openroad','-no_init','-threads','3','-exit',str(script)],stdout=f,stderr=subprocess.STDOUT,check=True)
        txt=log.read_text();values=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',txt)
        ann=re.findall(r'Annotated (\d+) pin activities\.',txt)
        assert len(values)==1 and len(ann)==1 and int(ann[0])==expected
        assert not re.search(r'(?m)^(Error:|\[ERROR)',txt)
        power=dict(zip(['internal','switching','leakage','total'],map(float,values[0])));power['annotated']=int(ann[0])
        result=dict(power_w=power,retiming=transfer,tcl_sha256=digest(script),log_sha256=digest(log))
        prefix.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
        print('POWER_300_PASS',ident,name,flush=True)
        return task,result
    tasks=[(i,n) for i in range(12) for n in ('active','idle')]
    with ThreadPoolExecutor(max_workers=4) as pool:results=dict(pool.map(measure,tasks))
    windows=[]
    for ident,s in enumerate(old['windows']):
        pair={n:results[ident,n] for n in ('active','idle')};duration=s['window_ps']//5000*3334
        assert all(v['retiming']['target_window_ps']==duration for v in pair.values())
        delta=(pair['active']['power_w']['total']-pair['idle']['power_w']['total'])*duration/1000
        assert delta>0
        windows.append(dict(segment=s['segment'],window_ps=duration,power_w={k:v['power_w'] for k,v in pair.items()},
            increment_nj=delta,retiming={k:v['retiming'] for k,v in pair.items()},
            old_increment_nj=s['increment_nj'],increment_change_percent=(delta/s['increment_nj']-1)*100))
    result=dict(clock_mhz=300,core_period_ps=3334,effective_clock_mhz=1e6/3334,wire_parasitics_loaded=False,
        activity='accepted zero-delay full-pin gate events, exact half-cycle retiming, new 3334ps OpenROAD power analysis',
        source_calibration_sha256=digest(oldpath),source_gate_receipt_sha256=digest(source/'gate-replay-receipt.json'),
        original_gate_vcd_sha256=gate['vcd_sha256'],source_commit=config['source_commit'],baseline_commit=config['baseline_commit'],
        driver_sha256=digest(Path(__file__)),config_sha256=digest(work/'config.json'),source=old['source'],sta_view=old['sta_view'],
        pin_graph=old['pin_graph'],pin_mapping=old['pin_mapping'],vcd_scope=scope,
        gate_function_from_accepted_replay=True,new_gate_simulation=False,new_synthesis=False,timing_signoff=False,
        expected_annotated_pins=expected,windows=windows,tools=dict(python=sys.version,openroad_version=subprocess.check_output(['openroad','-version'],text=True).strip(),liberty_sha256=digest(lib)))
    (work/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    print('RECURRENT_300_CALIBRATION_PASS',flush=True)

if __name__=='__main__':main()
