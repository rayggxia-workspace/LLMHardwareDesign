"""Independent arithmetic and provenance checks for the conditional model rollup."""
from pathlib import Path
from hashlib import sha256
import json, math,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
selected=sys.argv[1:]
assert len(selected)<=1 and all(x in ('qwen35','falcon-wide') for x in selected)
suffix='-'+selected[0] if selected else ''
data=json.loads((HERE/('candidate-rollup'+suffix+'.json')).read_bytes())
base=json.loads((HERE/'baseline-200mhz-v3.json').read_bytes())
for p,digest in data['input_sha256'].items():
    assert sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
def equal(x,y):
    assert math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-12),(x,y)
checks=[]
for model in data['models']:
    baseline=next(m for m in base['models'] if m['name']==model['name'])
    key='qwen35' if model['name']=='Qwen3.5-4B' else 'falcon-wide'
    raw=json.loads((HERE/(key+'-calibration.json')).read_bytes())
    graph_audit=next(row for row in json.loads((HERE/'signed-graph-audit.json').read_bytes()) if row['model']==key+'-fast')
    assert graph_audit['passed'] and graph_audit['cell_count']==raw['source']['cell_count']
    assert graph_audit['sta_verilog_sha256']==raw['sta_view']['sta_netlist_sha256']
    assert len(raw['windows'])==12 and raw['gate_replay_pass']
    for sample in raw['windows']:
        p=sample['power_w']
        for state in ('active','idle'):
            # OpenSTA prints component and total sums with small float-precision differences.
            # The observed reader preflight differs by 7.7e-9 W at 0.238 W.
            assert math.isclose(sum(p[state][c] for c in ('internal','switching','leakage')),
                                p[state]['total'],rel_tol=5e-7,abs_tol=1e-9)
            assert p[state]['annotated']==raw['pin_mapping']['connected_pin_declarations']
        equal((p['active']['total']-p['idle']['total'])*sample['window_ps']/1000,sample['increment_nj'])
    for phase,window in model['windows'].items():
        b=baseline['windows'][phase]
        # Fixed transaction totals from the frozen v3 operation audit, independent of the new rollup.
        expected_calls={'qwen35':{'prefill':12288,'decode':6144},'falcon-wide':{'prefill':16384,'decode':8192}}
        assert window['calls']==expected_calls[key][phase]
        assert window['one_r_active_time_s']<b['seconds']
        groups={}
        for sample in raw['windows']:
            s=sample['segment']
            if s['window']==phase:groups[s['group']]=groups.get(s['group'],0)+sample['increment_nj']
        assert len(groups)==2
        pair=sorted(groups.values())
        for i in (0,1):
            expected=pair[i]*1e-9*window['calls']+b['seconds']*window['shared_r_idle_w'][i]+window['retained_injection_proxy_j'][i]
            equal(expected,window['candidate_replacement_j'][i])
            for scope in ('on_chip','on_chip_plus_ddr'):
                e=b[scope]['window_j'][i]-window['original_proxy_j'][i]+expected
                result=window['candidate'][scope]
                equal(e,result['window_j'][i]);equal(e/b['seconds'],result['mean_w'][i])
                equal(1000*e/b['tokens'],result['mj_per_token'][i])
            equal(window['candidate']['on_chip_plus_ddr']['window_j'][i]-window['candidate']['on_chip']['window_j'][i],b['ddr_j'])
        old=window['baseline']['on_chip_plus_ddr']['mean_w']
        new=window['candidate']['on_chip_plus_ddr']['mean_w']
        checks.append(dict(model=model['name'],phase=phase,old_width_w=old[1]-old[0],
                           candidate_width_w=new[1]-new[0],width_reduction=1-(new[1]-new[0])/(old[1]-old[0]),
                           old_state_proxy_width_w=(window['original_proxy_j'][1]-window['original_proxy_j'][0])/window['window_s'],
                           old_state_proxy_width_fraction=(window['original_proxy_j'][1]-window['original_proxy_j'][0])/window['window_s']/(old[1]-old[0])))
(HERE/('rollup-check'+suffix+'.json')).write_text(json.dumps(dict(passed=True,checks=checks),indent=2)+'\n')
print('CANDIDATE_ROLLUP_PASS',len(checks),'model windows; paired energy, units, sources and DDR difference')
