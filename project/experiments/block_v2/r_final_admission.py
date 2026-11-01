"""Join actual final-R computations only after the native producer succeeds.

This never changes the historical fragmented report or the computation-only
route proof. Acceptance requires the separate, complete, unchanged-rule checks.
"""
import json
from pathlib import Path
from r_monolithic_drc import compare_grid_only


RELATIVE=Path('flow/results/nangate45/bv1_block_v1_r/base')


def diagnostic(folder,sha,mode):
    folder=folder.resolve()
    path=folder/'diagnostic.json';result=json.loads(path.read_text())
    assert result['mode']==mode and result['diagnostic_completed'] and result['source_bytes_unchanged']
    assert result['diagnostic_only'] and not result['qualified'] and not result['native_leaf_accepted']
    for name,row in result['outputs'].items():
        f=folder/name
        f.resolve().relative_to(folder)
        assert f.is_file()
        assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    for name,digest in result['inputs'].items():assert sha(Path(name))==digest
    for c in result['commands']:
        assert c['returncode']==0 and sha(folder/c['log'])==c['sha256']
    return result


def native(root,raw,computation,sha):
    """Reject pending/failed producer even if a diagnostic happened to pass."""
    assert computation is not None,'Actual final native computation is required'
    raw=raw.resolve();computation=computation.resolve()
    receipt=json.loads((raw/'receipt.json').read_text());assert receipt['passed']
    flow=json.loads((raw/'native-flow.json').read_text())
    assert flow['passed'] and flow['pipeline_completed'] and flow['top']=='block_v1_r'
    assert sha(raw/'native-flow.json')==receipt['outputs']['native-flow.json']
    for name,digest in flow['rtl_sha256'].items():assert sha(root/name)==digest
    x=diagnostic(computation,sha,'final-native')
    captured=x['final_source_inputs']
    assert captured['passed'] and not captured['qualified'] and not captured['native_leaf_accepted']
    assert Path(captured['raw_source']).resolve()==raw and captured['rtl_sha256']==flow['rtl_sha256']
    for name,row in captured['fixed_files'].items():
        assert Path(row['path'])==raw/name
        assert sha(raw/name)==row['sha256']==receipt['outputs'][name]
    assert x['native_drc_count']==0 and x['native_drc_zero']
    proof=json.loads((computation/'native-complete-proof.json').read_text())
    assert proof==x['complete_native_proof'] and proof['passed']
    for key in ('original_source_unchanged','complete_native_rule_check','one_complete_native_worker','no_marker_or_rule_exclusions'):
        assert proof[key]
    assert proof['complete_die_box_dbu']==[0,0,6000000,6000000]
    assert proof['diagnostic_only'] and not proof['qualified'] and not proof['native_leaf_accepted']
    assert proof['source_odb_sha256']==captured['fixed_files'][str(RELATIVE/'6_final.odb')]['sha256']
    assert proof['controls']['passed'] and proof['controls']['real_foreign_spacing_and_same_net_notch_detected']
    assert proof['controls']['exact_fragmented_reproduction']
    from r_complete_native_check import control_evidence
    evidence,control=control_evidence(root,sha)
    assert proof['controls']['source_index_sha256']==sha(evidence/'index.json')
    assert proof['controls']['technology_sha256']==control['technology_sha256']
    for label in ('fragmented','complete','spacing-negative'):
        assert (computation/('control-'+label+'-drc.rpt')).read_bytes()==(evidence/(label+'-drc.rpt')).read_bytes()
    assert not (computation/'native-whole-drc.rpt').read_bytes()
    assert proof['native_report_sha256']==sha(computation/'native-whole-drc.rpt')
    assert proof['fragmented_report_sha256']==sha(computation/'native-fragmented-drc.rpt')
    assert proof['fragmented_diagnostic_count']==822
    assert (computation/'native-fragmented-drc.rpt').read_text().count('violation type:')==822
    assert sha(computation/'before.def')==sha(computation/'after.def')
    assert sha(computation/'complete-grid-before.def')==sha(computation/'complete-grid-after.def')
    assert compare_grid_only(computation/'before.def',computation/'complete-grid-before.def')==proof['geometry_proof']
    assert [c['log'] for c in x['commands']]==[
        'control-fragmented.log','control-complete.log','control-spacing-negative.log','native-fragmented.log','native-complete.log']
    return dict(passed=True,raw_source=str(raw),producer_receipt_sha256=sha(raw/'receipt.json'),
                computation=str(computation),diagnostic_sha256=sha(computation/'diagnostic.json'),
                complete_native_proof_sha256=sha(computation/'native-complete-proof.json'),
                actual_final_odb_sha256=proof['source_odb_sha256'],native_drc_count=0,
                retained_fragmented_diagnostic_count=822,qualified_hard_macro=False)


def gds(root,raw,computation,sha):
    """Only reuse138 after the recorded actual139/142 binary identity proof."""
    from native_drc import summarize
    assert computation is not None and computation.name=='138'
    x=diagnostic(computation,sha,'gds')
    assert x['full_deck_zero'] and x['full_deck']['total_items']==0
    assert summarize(computation/'full-deck.lyrdb')==x['full_deck']
    assert [c['log'] for c in x['commands']]==['gds.log','full-deck.log']
    proof_dir=root/'work/YUZE-LU/143/r-input-hold/launch-142'
    idx=json.loads((proof_dir/'index.json').read_text())
    for name,digest in idx['files'].items():assert sha(proof_dir/name)==digest
    identity=json.loads((proof_dir/'gds-identity.json').read_text())
    assert identity['passed'] and not identity['qualified'] and not identity['native_leaf_accepted']
    for key in ('only_gds_timestamp_payloads_differ','old_candidate_and_actual_final_def_bytes_identical','config_only_output_directory_prefix_differs'):
        assert identity[key]
    assert identity['source_gds']['path']==x['gds']['path']
    assert sha(Path(x['gds']['path']))==x['gds']['sha256']==identity['source_gds']['sha256']
    assert sha(Path(identity['final_generated_gds']['path']))==identity['final_generated_gds']['sha256']
    assert Path(x['gds']['path']).stat().st_size==x['gds']['bytes']==identity['bytes']
    definition=computation/'gds-flow/results/nangate45/bv1_block_v1_r/base/6_final.def'
    assert sha(definition)==sha(raw/RELATIVE/'6_final.def')==identity['actual_final_def_sha256']
    old_configs=[Path(p) for p in x['inputs'] if p.endswith('/pnr/r/config.mk')]
    assert len(old_configs)==1
    old=old_configs[0]
    assert sha(old)==identity['source_config_sha256']
    assert sha(raw/'config.mk')==identity['final_config_sha256']
    assert old.read_text().replace(str(old.parent),str(raw))==(raw/'config.mk').read_text()
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    assert x['inputs'][str(deck)]==sha(deck)
    return dict(passed=True,diagnostic_sha256=sha(computation/'diagnostic.json'),
                input_identity_sha256=sha(proof_dir/'gds-identity.json'),full_deck=x['full_deck'],
                deck_sha256=sha(deck),gds=x['gds'],exact_final_def_sha256=sha(definition),
                qualified_hard_macro=False)
