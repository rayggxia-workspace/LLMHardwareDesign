"""Generate additive physical costs with explicit footprint/leaf-area separation."""
import argparse
import json
from pathlib import Path
import re
from quality import evaluate

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('selection',type=Path)
a=p.parse_args()
selection=json.loads(a.selection.read_text())
data=json.loads((HERE/'results/latest.json').read_text())['attempts']
rows={}
for kind,name in selection.items():
    row=data.get(name,{})
    if not row.get('metrics',{}).get('6_report.json'):
        raise SystemExit('Incomplete extracted result: '+name)
    q=evaluate(row)
    if not q['passed']: raise SystemExit('Strict budget failed: '+name)
    if kind.startswith('top_'):
        assert row.get('full-hierarchy-quality.json',{}).get('passed'), 'Full extracted hierarchy did not qualify: '+name
        assert row.get('strict-pg.json',{}).get('passed') and row.get('final-pg/strict-pg.json',{}).get('passed'), 'Native PG did not qualify: '+name
        assert all(v['passed'] for v in row['resource-qualification.json'].values()), 'Architecture inventory differs'
    else:
        assert row.get('layer-reservation.json',{}).get('passed'), 'M10 reservation not qualified: '+name
    rows[kind]=dict(attempt=name,quality=q,record=row)
assert set(rows)=={'act','mxu','merged','top_split','top_merged'}
costs={}
for kind,blocks in [('split',['act','mxu']),('merged',['merged'])]:
    top=rows['top_'+kind]
    final=top['record']['metrics']['6_report.json']
    meta=top['record']['experiment.json']
    leaf=sum(rows[b]['quality']['area_um2'] for b in blocks)
    parent_cells=final['finish__design__instance__area__stdcell']
    footprint=sum(meta['views'][b]['size'][0]*meta['views'][b]['size'][1] for b in blocks)
    log=top['record'].get('full-hierarchy-sta.log','')
    max_ws=re.search(r'worst slack max\s+(-?[\d.]+)',log)
    min_ws=re.search(r'worst slack min\s+(-?[\d.]+)',log)
    assert max_ws and min_ws, 'Missing actual hierarchical STA'
    costs[kind]=dict(
        implemented_leaf_area_um2=leaf+parent_cells,
        private_leaf_area_um2=leaf,parent_stdcell_area_um2=parent_cells,
        hard_macro_footprint_um2=footprint,
        occupied_footprint_plus_parent_cells_um2=footprint+parent_cells,
        common_die_area_um2=top['quality']['die_area_um2'],
        private_signal_wire_um=sum(rows[b]['quality']['signal_wire_um'] for b in blocks),
        parent_signal_wire_um=top['quality']['signal_wire_um'],
        total_signal_wire_um=sum(rows[b]['quality']['signal_wire_um'] for b in blocks)+top['quality']['signal_wire_um'],
        private_signal_vias=sum(rows[b]['quality']['signal_vias'] for b in blocks),
        parent_signal_vias=top['quality']['signal_vias'],
        total_signal_vias=sum(rows[b]['quality']['signal_vias'] for b in blocks)+top['quality']['signal_vias'],
        complete_setup_ws_ns=float(max_ws[1]),complete_hold_ws_ns=float(min_ws[1]),
        parent_macro_only_setup_ws_ns=top['quality']['setup_ns'])
assert costs['split']['common_die_area_um2']==costs['merged']['common_die_area_um2']
assert rows['top_split']['record']['external_pin_contract']==rows['top_merged']['record']['external_pin_contract']
split_pins=rows['top_split']['record']['actual_signal_pin_geometry']
merged_pins=rows['top_merged']['record']['actual_signal_pin_geometry']
assert split_pins['all_contract_names_present'] and merged_pins['all_contract_names_present']
assert split_pins['canonical_sha256']==merged_pins['canonical_sha256'], 'Actual pin geometry differs'
output=dict(selection=selection,costs=costs,
    split_change_vs_merged_percent={k:100*(costs['split'][k]/costs['merged'][k]-1) for k in
        ['implemented_leaf_area_um2','occupied_footprint_plus_parent_cells_um2','total_signal_wire_um','total_signal_vias']},
    scope='H1 same compute/storage/state resources; physical buffer and CTS costs included. Footprint is not added to its own leaf-cell area. Signal route excludes special PG, which requires separate geometry audit. Complete STA never sums separate-block slack values.')
(HERE/'results/comparison.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
