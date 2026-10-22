"""Generate additive physical costs with explicit footprint/leaf-area separation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from quality import evaluate, require_sealed_input, require_toolchain

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('selection',type=Path)
a=p.parse_args()
definition=json.loads(a.selection.read_text())
selection=definition['implementations']
snapshot=json.loads((HERE/'results/latest.json').read_text())
data=snapshot['attempts']
stitch_proof=data[definition['stitch_proof']]
assert stitch_proof.get('exit_code')=='0' and stitch_proof.get('stitch-validation.json',{}).get('passed'), 'Unvalidated hierarchical boundary RC stitching'
assert stitch_proof['spec'].get('stitch_selftest')=='two_child', 'Final split comparison requires a source-to-receiver cross-child RC fixture'
inventory=data[definition['inventory_proof']]
assert inventory.get('exit_code')=='0' and Path(inventory['spec']['inventory_proof_source']).name==definition['functional_proof']
assert all(inventory.get('logical-resource-inventory.json',{}).get(k,{}).get('equal') for k in ['act','mxu','merged']), 'Logic/state/SRAM resources changed'
stock=inventory['logical-resource-inventory.json']
assert Counter(stock['act']['physical'])+Counter(stock['mxu']['physical'])==Counter(stock['merged']['physical']), 'Split/merged non-support resource stock differs'
evidence_keys=['functional_proof','parent_functional_proof','stitch_proof','inventory_proof','annotation_proof']
if definition.get('wire_audit_proof'):
    evidence_keys.append('wire_audit_proof')
    wire_proof=data[definition['wire_audit_proof']]
    assert wire_proof.get('exit_code')=='0', 'Complete final ODB wire audit did not finish'
    for kind,name in selection.items():
        source=data[name]
        receipt=wire_proof.get('wire-audit-sources.json',{}).get(kind,{})
        assert receipt.get('passed') and all(receipt.get('checks',{}).values()), 'Final ODB wirelength crosscheck failed: '+kind
        assert Path(receipt['source']).name==name, 'Final ODB wire audit belongs to another implementation'
        assert Path(wire_proof['spec']['wire_audit_sources'][kind]).name==name
        assert receipt['source_manifest_sha256']==source['output_manifest_sha256']
        relative=source['experiment.json']['result_relative']
        require_sealed_input(wire_proof,source,relative+'/6_final.odb')
        require_sealed_input(wire_proof,source,relative.replace('/results/','/logs/')+'/5_2_route.json')
        assert receipt['native_drt_wire_um']==source['metrics']['5_2_route.json']['detailedroute__route__wirelength']
        if source['spec'].get('extracted_preserve_unchanged_routes'):
            require_sealed_input(wire_proof,source,'route-reuse.json')
else:
    assert not any(data[name]['spec'].get('extracted_preserve_unchanged_routes') for name in selection.values()), 'Route reuse requires an independent complete final ODB cost audit'
annotation=data[definition['annotation_proof']]
assert annotation.get('exit_code')=='0', 'Native annotation audit did not complete'
for kind in ['top_split','top_merged']:
    receipt=annotation.get('annotation-validation.json',{}).get(kind,{})
    assert receipt.get('passed') and all(receipt.get('checks',{}).values()), 'Unresolved or connected unannotated driver: '+kind
    assert Path(receipt['source']).name==selection[kind], 'Annotation audit belongs to another parent'
    assert Path(annotation['spec']['annotation_sources'][kind]).name==selection[kind]
for name in list(selection.values())+[definition[k] for k in evidence_keys]:
    row=data[name]
    integrity=row.get('collected_file_integrity',{})
    assert integrity and all(integrity.values()), 'Collected evidence differs from sealed output manifest: '+name
    assert '|COMPLETED|' in row.get('scheduler',''), 'Wait for sealed scheduler terminal state: '+name
    assert row['scheduler'].split('|')[4]=='UNLIMITED' and 'TimeLimit=UNLIMITED' in row.get('allocation.txt',''), 'Execution limit differs from the authorized unlimited experiment: '+name
    require_toolchain(row)
    terminal=json.loads((HERE/'results'/(name+'-terminal.json')).read_text())
    assert terminal['output_manifest_sha256']==row['output_manifest_sha256'], 'Source manifest changed since its first terminal receipt: '+name
shared_inputs={}
for name in list(selection.values())+[definition[k] for k in evidence_keys]:
    for path,digest in data[name].get('input-sha256.json',{}).items():
        assert path not in shared_inputs or shared_inputs[path]==digest, 'Shared model/input changed between implementations or proofs: '+path
        shared_inputs[path]=digest
proof=data[definition['functional_proof']]
assert proof.get('exit_code')=='0'
for name in ['act','mxu','merged']:
    assert proof['structural-equivalence.json'][name]['passed'], 'Missing logical cone certificate'
    assert Path(proof['spec']['structural_sources'][name]).name==selection[name], 'Proof belongs to another block'
    source=data[selection[name]]
    require_sealed_input(proof,source,'mapped.v')
    require_sealed_input(proof,source,source['experiment.json']['result_relative']+'/6_final.v')
    for stage in ['mapped','physical']:
        require_sealed_input(inventory,proof,'equivalence-'+name+'/'+stage+'.json')
parent_proof=data[definition['parent_functional_proof']]
assert parent_proof.get('exit_code')=='0'
for name in ['top_split','top_merged']:
    assert parent_proof['structural-equivalence.json'][name]['passed'], 'Parent wiring function changed'
    assert Path(parent_proof['spec']['structural_sources'][name]).name==selection[name]
    source=data[selection[name]]
    require_sealed_input(parent_proof,source,'top.v')
    require_sealed_input(parent_proof,source,source['experiment.json']['result_relative']+'/6_final.v')
    for relative in [source['experiment.json']['result_relative']+'/6_final.'+ext for ext in ['v','spef']]+['boundary.sdc']:
        require_sealed_input(source,source,relative)
        require_sealed_input(annotation,source,relative)
    for child in (['act','mxu'] if name=='top_split' else ['merged']):
        block=data[selection[child]]
        for ext in ['v','spef']:
            relative=block['experiment.json']['result_relative']+'/6_final.'+ext
            require_sealed_input(source,block,relative)
            require_sealed_input(annotation,block,relative)
rows={}
for kind,name in selection.items():
    row=data.get(name,{})
    if not row.get('metrics',{}).get('6_report.json'):
        raise SystemExit('Incomplete extracted result: '+name)
    q=evaluate(row)
    if not q['passed']: raise SystemExit('Strict budget failed: '+name)
    route=row['route_layer_report']
    assert row['collected_file_integrity'].get(route['path']), 'Layer costs lack a sealed native route log: '+name
    assert route['total_um']==q['signal_wire_um'] and route['vias']==q['signal_vias'], 'Native route table and metrics differ: '+name
    assert abs(sum(row['route_layer_wire_um'].values())-route['total_um'])<=len(row['route_layer_wire_um']), 'Rounded layer lengths do not sum to the native total: '+name
    if kind.startswith('top_'):
        assert row.get('full-hierarchy-quality.json',{}).get('passed'), 'Full extracted hierarchy did not qualify: '+name
        assert row.get('strict-pg.json',{}).get('passed') and row.get('final-pg/strict-pg.json',{}).get('passed'), 'Native PG did not qualify: '+name
        assert all(v['passed'] for v in row['resource-qualification.json'].values()), 'Architecture inventory differs'
        assert row['pg_access'] and all(v['remaining_guard_intersections']==0 for v in row['pg_access'].values()), 'PG landing geometry failed'
    else:
        assert row.get('layer-reservation.json',{}).get('passed'), 'M10 reservation not qualified: '+name
    rows[kind]=dict(attempt=name,quality=q,record=row)
assert set(rows)=={'act','mxu','merged','top_split','top_merged'}
costs={}
for kind,blocks in [('split',['act','mxu']),('merged',['merged'])]:
    top=rows['top_'+kind]
    final=top['record']['metrics']['6_report.json']
    meta=top['record']['experiment.json']
    assert all(Path(meta['views'][b]['source']).name==selection[b] for b in blocks), 'Parent uses another block implementation'
    leaf=sum(rows[b]['quality']['area_um2'] for b in blocks)
    parent_cells=final['finish__design__instance__area__stdcell']
    footprint=sum(meta['views'][b]['size'][0]*meta['views'][b]['size'][1] for b in blocks)
    log=top['record'].get('full-hierarchy-sta.log','')
    max_ws=re.search(r'worst slack max\s+(-?[\d.]+)',log)
    min_ws=re.search(r'worst slack min\s+(-?[\d.]+)',log)
    assert max_ws and min_ws, 'Missing actual hierarchical STA'
    component_rows=[rows[b]['record']['metrics']['6_report.json'] for b in blocks]+[final]
    classes={c:{quantity:sum(r.get('finish__design__instance__'+quantity+'__class:'+c,0) for r in component_rows)
                for quantity in ['count','area']} for c in
                ['buffer','clock_buffer','clock_inverter','timing_repair_buffer','inverter','tie_cell','tap_cell','diode']
                if any('finish__design__instance__count__class:'+c in r for r in component_rows)}
    layer_wire=top['record']['route_layer_wire_um']
    private_layer_wire=dict(sum((Counter(rows[b]['record']['route_layer_wire_um']) for b in blocks),Counter()))
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
        parent_macro_only_setup_ws_ns=top['quality']['setup_ns'],
        physical_cell_classification=classes,parent_signal_wire_by_layer_um=layer_wire,
        physical_cell_classification_scope='Native support-cell metric categories. The buffer category includes tool-classified CTS/other buffers; absent clock-only categories do not imply zero physical clock buffers. Total cell area includes every non-filler support cell.',
        private_signal_wire_by_layer_um=private_layer_wire,
        total_signal_wire_by_layer_um=dict(Counter(private_layer_wire)+Counter(layer_wire)),
        parent_signal_wire_below_m10_percent=100*sum(v for k,v in layer_wire.items() if k!='metal10')/sum(layer_wire.values()))
assert costs['split']['common_die_area_um2']==costs['merged']['common_die_area_um2']
assert {rows[k]['record']['boundary_constraint_contract_sha256'] for k in rows}=={
    'b08d83cc225c1753aee3027d6c97e296bc25d4cf9d5cdd7ffd0b4efc6694f044'
}, 'Clock/IO contract differs from the frozen 2.5 ns / 0.5 ns / BUF_X4 / 5 fF definition'
assert rows['top_split']['record']['external_pin_contract']==rows['top_merged']['record']['external_pin_contract']
split_pins=rows['top_split']['record']['actual_signal_pin_geometry']
merged_pins=rows['top_merged']['record']['actual_signal_pin_geometry']
assert split_pins['all_contract_names_present'] and merged_pins['all_contract_names_present']
for kind,pins in [('top_split',split_pins),('top_merged',merged_pins)]:
    assert pins['rows']==1662, 'Expected one actual physical box for each of 1662 external bits'
    stage=rows[kind]['record']['pin-placement-quality.json']
    assert stage['passed'] and pins['canonical_sha256']==stage['canonical_sha256'], 'Routing moved common external pins'
assert split_pins['canonical_sha256']==merged_pins['canonical_sha256'], 'Actual pin geometry differs'
inputs=dict(observed_utc=snapshot['observed_utc'],attempts={n:data[n] for n in list(selection.values())+[definition[k] for k in evidence_keys]})
input_path=HERE/'results/comparison-inputs.json'
input_path.write_text(json.dumps(inputs,indent=2)+'\n')
output=dict(selection=selection,functional_proof=definition['functional_proof'],parent_functional_proof=definition['parent_functional_proof'],
    stitch_proof=definition['stitch_proof'],inventory_proof=definition['inventory_proof'],annotation_proof=definition['annotation_proof'],
    input_snapshot_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),costs=costs,
    toolchain_sha256=require_toolchain(rows['act']['record']),
    split_change_vs_merged_percent={k:100*(costs['split'][k]/costs['merged'][k]-1) for k in
        ['implemented_leaf_area_um2','occupied_footprint_plus_parent_cells_um2','total_signal_wire_um','total_signal_vias']},
    scope='H1 same compute/storage/state resources; physical buffer and CTS costs included. Footprint is not added to its own leaf-cell area. Signal route excludes special PG, which requires separate geometry audit. Complete STA never sums separate-block slack values.')
if definition.get('wire_audit_proof'):
    output['wire_audit_proof']=definition['wire_audit_proof']
(HERE/'results/comparison.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
