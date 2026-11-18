"""Prove signed-declaration compatibility view preserves all mapped connectivity."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
work=Path.cwd()
def digest(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
rows=[]
for model in ('qwen35-fast','falcon-wide-fast'):
    design=work.parent/model
    view=json.loads((design/'sta-view/sta-view.json').read_bytes())
    graph_info=json.loads((design/'pin-map/graph-receipt.json').read_bytes())
    assert digest(design/'mapped.v')==view['original_netlist_sha256']
    assert digest(design/'pin-map/sta_graph.json')==graph_info['graph_sha256']
    out=work/model;out.mkdir(exist_ok=False)
    (out/'read.ys').write_text('read_verilog '+str(design/'mapped.v')+'\nwrite_json original_graph.json\n')
    with (out/'read.log').open('w') as f:subprocess.run(['yosys','read.ys'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
    before=json.loads((out/'original_graph.json').read_bytes())['modules']['block_v1_r']
    after=json.loads((design/'pin-map/sta_graph.json').read_bytes())['modules']['block_v1_r']
    assert before['ports'].keys()==after['ports'].keys()
    for name,p in before['ports'].items():
        for key in ('bits','direction','offset','upto'):assert p.get(key)==after['ports'][name].get(key),(model,name,key)
    assert before['cells'].keys()==after['cells'].keys()
    for name,c in before['cells'].items():
        for key in ('type','parameters','connections'):assert c[key]==after['cells'][name][key],(model,name,key)
    assert before['netnames'].keys()==after['netnames'].keys()
    for name,n in before['netnames'].items():
        for key in ('bits','offset','upto'):assert n.get(key)==after['netnames'][name].get(key),(model,name,key)
    assert not any(c['type'].startswith('$') for c in before['cells'].values())
    rows.append(dict(model=model,passed=True,cell_count=len(before['cells']),net_count=len(before['netnames']),
        source_verilog_sha256=view['original_netlist_sha256'],sta_verilog_sha256=view['sta_netlist_sha256'],
        original_graph_sha256=digest(out/'original_graph.json'),sta_graph_sha256=graph_info['graph_sha256'],
        checked='Every cell type, parameter and connected bit; all port directions/bits/ranges and all named net bits/ranges. Signed metadata and source-location attributes alone are ignored. No behavioral cells remain.'))
    (work/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('SIGNED_GRAPH_EQUIVALENCE_PASS',model,len(before['cells']),flush=True)
    del before,after
