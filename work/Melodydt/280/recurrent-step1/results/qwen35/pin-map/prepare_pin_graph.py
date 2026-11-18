"""Read the exact structural STA view and verify this OpenSTA build's VCD aliases."""
from pathlib import Path
from hashlib import sha256
import json,re,subprocess
work=Path.cwd();design=work.parent
source=design/'sta-view/mapped_sta.v'
def digest(path):
    h=sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
view=json.loads((design/'sta-view/sta-view.json').read_bytes())
assert digest(source)==view['sta_netlist_sha256']
(work/'read.ys').write_text('read_verilog '+str(source)+'\nwrite_json sta_graph.json\n')
with (work/'read.log').open('w') as f:
    subprocess.run(['yosys','read.ys'],stdout=f,stderr=subprocess.STDOUT,check=True)
graph=json.loads((work/'sta_graph.json').read_bytes())['modules']['block_v1_r']
assert len(graph['cells'])==view['cell_count']
cell_name,cell=next(iter(graph['cells'].items()))
ports=list(cell['connections'])[:2]
assert len(ports)==2 and all(len(cell['connections'][p])==1 for p in ports)
net=next(k for k,v in graph['netnames'].items() if re.fullmatch(r'_\d+_',k) and len(v['bits'])==1)
tail='$enddefinitions $end\n#0\n0z\n#2500\n1z\n#5000\n0z\n#10000\n'
(work/'net-probe.vcd').write_text('$timescale 1ps $end\n$scope module probe_net $end\n$var wire 1 z '+net+' $end\n$upscope $end\n'+tail)
(work/'pin-probe.vcd').write_text('$timescale 1ps $end\n$scope module probe_pin $end\n$scope module '+cell_name+' $end\n'+
    ''.join('$var wire 1 z '+p+' $end\n' for p in ports)+'$upscope $end\n$upscope $end\n'+tail)
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
(work/'probe.tcl').write_text('\n'.join([
    'read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
    'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
    'read_verilog {'+str(source)+'}','link_design block_v1_r',
    'create_clock -name core -period 5 [get_ports clk]',
    'read_vcd -scope probe_net {'+str(work/'net-probe.vcd')+'}',
    'read_vcd -scope probe_pin {'+str(work/'pin-probe.vcd')+'}'])+'\n')
with (work/'probe.log').open('w') as f:
    subprocess.run(['openroad','-no_init','-threads','3','-exit',str(work/'probe.tcl')],stdout=f,stderr=subprocess.STDOUT,check=True)
counts=[int(x) for x in re.findall(r'Annotated (\d+) pin activities\.',(work/'probe.log').read_text())]
assert len(counts)==2 and counts[1]==2,counts
connected=sum(len(v) for c in graph['cells'].values() for v in c['connections'].values())
top=sum(len(v['bits']) for v in graph['ports'].values())
(work/'graph-receipt.json').write_text(json.dumps(dict(source_verilog_sha256=digest(source),
    graph_sha256=digest(work/'sta_graph.json'),cell_count=len(graph['cells']),
    connected_cell_pins=connected,top_port_bits=top,
    probe_net_annotations=counts[0],probe_shared_id_pin_annotations=counts[1],
    probe_purpose='Parser mapping only; synthetic probe is excluded from energy results.'),indent=2)+'\n')
print('PIN_GRAPH_PASS',connected,top,counts,flush=True)
