"""Inspect actual complete intermediate wiring on a compute node; diagnostic only."""
from pathlib import Path
import hashlib,json
from router_conflict_snapshot import inspect,inputs


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert cfg['schema']=='control162-global-round-diagnostic-v1'
    paths={key:Path(cfg[key])for key in ('input','snapshot','log','graph')}
    for key,p in paths.items():assert sha(p)==cfg[key+'_sha256']
    graph=json.loads(paths['graph'].read_text());assert len(graph['instances'])==345 and 'macro_r'in graph['instances']
    header,nets,limits=inputs(paths['input']);assert len(nets)==11149 and header[:2]==[2345,2345]
    round_number=cfg['round'];assert round_number in(8,16,32,64)
    trace=[json.loads(l)for l in paths['log'].read_text().splitlines()if l.startswith('{')]
    expected=next(r for r in trace if r.get('round')==round_number-1 and 'conflict_nodes'in r)
    assert any(r.get('global_snapshot_round')==round_number and r.get('global_snapshot_nets')==len(nets)and r.get('diagnostic_only')is True for r in trace)
    diagnostic=inspect(paths['snapshot'],nets,*header[:2],limits)
    for key in ('conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity'):assert diagnostic[key]==expected[key]
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='actual-global-round-diagnostic-only',round=round_number,diagnostic=diagnostic,inputs={str(p):sha(p)for p in [config,Path(__file__),Path(__file__).with_name('router_conflict_snapshot.py'),*paths.values()]})
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
