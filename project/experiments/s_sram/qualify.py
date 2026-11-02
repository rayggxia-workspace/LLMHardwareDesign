"""Join independently passed whole-S gates with exact source/artifact bindings.

Engineering acceptance only within the recorded TT schematic-bank model;
does not confer review/merge status or internal-bank PEX qualification.
"""
import argparse,hashlib,json
from pathlib import Path

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser()
for name in ['physical','audit','function','formal','out']:ap.add_argument('--'+name,type=Path,required=True)
a=ap.parse_args();assert not a.out.exists();records={};receipts={}
for name in ['physical','audit','function','formal']:
    path=getattr(a,name).resolve()/'receipt.json';d=json.loads(path.read_text());assert d['passed'],name
    for p,h in d.get('inputs',{}).items():assert sha(p)==h,(name,p)
    for c in d.get('commands',[]):
        assert c['returncode']==0 or (name=='formal' and c['log']=='negative-command.log')
        assert sha(path.parent/c['log'])==c['sha256']
    receipts[name]=dict(path=str(path),sha256=sha(path));records[name]=d
p,au,f,fo=[records[n]for n in ['physical','audit','function','formal']]
assert p['pipeline_completed'] and p['whole_gds_drc']['clean'] and p['whole_gds_drc']['items']==0
assert p['stream_geometry']['passed'] and sha(p['stream_geometry']['path'])==p['stream_geometry']['sha256']
stream=json.loads(Path(p['stream_geometry']['path']).read_text())
assert stream['passed'] and stream['all_used_standard_cell_masks_exact'] and stream['four_original_bank_masks_exact'] and stream['all_native_component_placements_exact']
for path,h in stream['inputs'].items():assert sha(path)==h
normalization=Path(p['bank_stream_normalization']['path'])
assert sha(normalization)==p['bank_stream_normalization']['sha256']
normalized=json.loads(normalization.read_text())
assert normalized['passed'] and normalized['all_cell_masks_labels_and_instances_exact']
assert sha(normalized['source'])==normalized['source_sha256']
assert sha(normalized['output'])==normalized['output_sha256']
well_path=Path(p['well_stream']['path']);assert sha(well_path)==p['well_stream']['sha256']
well=json.loads(well_path.read_text())
assert well['passed'] and well['all_global_physical_masks_identical'] and well['original_cell_names_instances_labels_and_nonroot_masks_unchanged'] and well['root_nonwell_geometry_unchanged']
assert sha(well['source'])==well['source_sha256']
assert sha(well['output'])==well['output_sha256']==p['final_files']['6_final.gds']['sha256']
assert sha(p['whole_gds_drc']['path'])==p['whole_gds_drc']['sha256']
assert au['checks'] and all(au['checks'].values())
assert f['physical_receipt_sha256']==receipts['physical']['sha256']
assert fo['inputs'][receipts['physical']['path']]==receipts['physical']['sha256']
assert au['inputs'][receipts['physical']['path']]==receipts['physical']['sha256']
assert len(fo['bank_boundaries'])==4 and fo['formal']['gate']['passed'] and not fo['formal']['negative']['passed']
assert len(f['results']['feeder'])==3 and all(row['passed']for row in f['results']['feeder'])
assert au['sram_clocks']['bank_period_checks']==au['sram_clocks']['bank_high_pulse_checks']==au['sram_clocks']['bank_low_pulse_checks']==4
assert p['budget']['clock_ns']==3.3333333333333335
files=p['final_files'];assert set(files)=={'6_final.'+x for x in ['v','sdc','def','odb','gds','spef']}
for name,v in files.items():
    assert sha(v['path'])==v['sha256']==f['final_file_sha256'][name]
    assert au['inputs'][v['path']]==v['sha256']
if 'landing_patches' in p:
    proof_path=Path(p['landing_patches']['path'])
    assert sha(proof_path)==p['landing_patches']['sha256']
    proof=json.loads(proof_path.read_text())
    assert proof['passed'] and proof['all_original_connected_metal_covered'] and proof['all_patches_clear_other_bank_m3_by_70nm']
    assert len(proof['patches'])==267 and proof['manufacturing_grid_um']==.005
    for path,h in proof['inputs'].items():assert sha(path)==h and p['inputs'][path]==h
    assert sha(proof['output'])==proof['output_sha256']
    access=proof['routing_lef'];assert sha(access['path'])==access['sha256']
    assert access['only_signal_m3_pin_geometry_changed'] and access['requires_all_1068_actual_top_level_patch_rectangles']
    native_access=p['landing_access_readback'];assert native_access['passed'] and native_access['pins']==267
    assert sha(native_access['path'])==native_access['sha256'] and sha(native_access['script_path'])==native_access['script_sha256']
    from landing_readback import inspect
    definition=Path(files['6_final.def']['path'])
    inventory=definition.parent/'sram-landing-patches.tsv'
    patch_readback=inspect(definition.read_text(),inventory.read_text())
    # An actual connection corruption must be rejected independently of
    # the geometry-generator assertions; retain the real positive result.
    rows=inventory.read_text().splitlines();fields=rows[0].split('\t');fields[2]='__WRONG_ACTUAL_LANDING_NET__'
    wrong='\n'.join(['\t'.join(fields),*rows[1:]])
    rejected=False
    try:inspect(definition.read_text(),wrong)
    except AssertionError:rejected=True
    assert rejected
    patch_readback.update(wrong_net_negative_rejected=True,inventory_path=str(inventory),
                          inventory_sha256=sha(inventory),def_sha256=sha(definition),
                          validator_sha256=sha(Path(__file__).with_name('landing_readback.py')))
else:raise AssertionError('Missing actual routed landing patch proof')
assert fo['inputs'][files['6_final.odb']['path']]==files['6_final.odb']['sha256']
assert stream['inputs'][files['6_final.odb']['path']]==files['6_final.odb']['sha256']
assert stream['inputs'][files['6_final.gds']['path']]==files['6_final.gds']['sha256']
assert stream['inputs'][files['6_final.def']['path']]==files['6_final.def']['sha256']
gen=[Path(path)for path in p['inputs']if path.endswith('/generation.json')];assert len(gen)==1
g=json.loads(gen[0].read_text());assert sha(gen[0])==p['inputs'][str(gen[0])]==f['generation_receipt_sha256']
assert g['macro_drc_items']==0 and g['macro_lvs_match'] and g['functional_emitted_model_same_sha']
for path,h in g['inputs'].items():assert sha(path)==h
for v in g['views'].values():assert sha(v['path'])==v['sha256']
assert normalized['source_sha256']==g['views']['gds']['sha256']
assert f['emitted_model_sha256']==g['views']['v']['sha256']
for path,h in f['source_sha256'].items():assert sha(path)==h
assert sha(p['image']['path'])==p['image']['sha256']
result=dict(passed=True,engineering_acceptance=True,review_acceptance=False,
    scope='Entire four-bank 16KiB SRAM S at the unchanged 300MHz boundary, within the stated bank timing-model limitations',
    receipts=receipts,final_files=files,image=p['image'],bank_views=g['views'],generation=dict(path=str(gen[0]),sha256=sha(gen[0])),
    checks=au['checks'],budget=p['budget'],timing=au['timing'],sram_clocks=au['sram_clocks'],
    final_function=f['results'],strict_formal=fo['formal'],landing_readback=patch_readback,
    limitations=['TT/1.1V/25C only','Bank transistor schematic characterization; internal bank wire PEX unimplemented','Upstream OpenRAM alter_lh_char_data copies HL to LH','Final functional simulation uses unchanged generated behavioral delays at a slower clock; 300MHz acceptance is separately extracted STA','Independent PR review and merge remain pending; no self-merge'],
    qualifier_sha256=sha(Path(__file__)))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS: all whole-S gates and six-file source bindings')
