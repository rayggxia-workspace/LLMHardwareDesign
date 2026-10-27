"""Full native library GDS/DRC of the sealed accepted C8 edit.

Run independently of the pending final LEC/RCX. This only qualifies geometry
of the exact edit; final source identity and all other receiver gates remain.
"""
import json
from pathlib import Path
import shutil
from io_slots import file_sha,slot
from native_drc import summarize


DECK_SHA='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'


def verify(root,out,cpus,run,policy):
    assert cpus==4 and policy in ('A','C');base=out.parents[2]
    source=base/'block-v1-20261027-165/tasks'/('native-c8-probe-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] is True
    path=source/'native-c8-probe.json';assert file_sha(path)==receipt['outputs'][path.name]
    probe=json.loads(path.read_text());assert probe['passed'] is True and probe['policy']==policy and all(v is True for v in probe['checks'].values())
    helpers=['native_c8_probe.py','native_c8_legalize.py','native_c8_geometry.py','native_escape_audit.py','native_c8_gds.rb','native_upper_index.py']
    for name in helpers:
        relative='project/experiments/block_v1/'+name;assert file_sha(root/relative)==receipt['inputs'][relative]
    original=Path(probe['source']);bound=json.loads((original/'receipt.json').read_text());assert bound['passed'] is True
    assert file_sha(original/'receipt.json')==probe['source_receipt_sha256']
    prep=base/'block-v1-20261027-123/tasks/native-prepare'
    pr=json.loads((prep/'receipt.json').read_text());assert pr['passed'] is True
    blueprint=prep/('shared109-'+policy)/'config.mk';assert file_sha(blueprint)==pr['outputs'][str(blueprint.relative_to(prep))]
    from native_run import checked_fresh_config
    config=checked_fresh_config(original,bound,blueprint)
    inputs={str(p):file_sha(p)for p in [source/'receipt.json',path,original/'receipt.json',prep/'receipt.json',blueprint,config]}
    with slot(base):
        for name in ['after.def','edited.odb','after.v']:
            inputs[str(source/name)]=file_sha(source/name);assert inputs[str(source/name)]==receipt['outputs'][name]
    assert inputs[str(source/'after.def')]==probe['edited_def_sha256']
    assert inputs[str(source/'edited.odb')]==probe['edited_odb_sha256']
    relative=Path('results/nangate45')/('bv1_shared109_'+policy)/'base'
    folder=out/'gds-flow'/relative;folder.mkdir(parents=True)
    for category in ['logs','reports','objects']:
        (out/'gds-flow'/category/'nangate45'/('bv1_shared109_'+policy)/'base').mkdir(parents=True)
    with slot(base):shutil.copyfile(source/'after.def',folder/'6_final.def')
    assert file_sha(folder/'6_final.def')==inputs[str(source/'after.def')]
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(config),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=4','do-gds'],'independent-gds.log')
    gds=folder/'6_final.gds';assert gds.is_file() and gds.stat().st_size>0
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');assert file_sha(deck)==DECK_SHA==probe['native_full_deck_sha256']
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'native-drc.lyrdb'),'-r',str(deck)],'independent-drc.log')
    summary=summarize(out/'native-drc.lyrdb');(out/'native-drc-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with slot(base):unchanged=all(file_sha(Path(p))==digest for p,digest in inputs.items())
    checks=dict(sealed_accepted_edit=True,exact_full_def_input=file_sha(folder/'6_final.def')==probe['edited_def_sha256'],
        exact_full_native_deck=file_sha(deck)==DECK_SHA,independent_full_native_drc_zero=summary['total_items']==0,source_unchanged=unchanged)
    result=dict(schema='block-v1-native-c8-edit-full-drc/1',passed=all(checks.values()),checks=checks,policy=policy,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),source_probe_sha256=file_sha(path),inputs=inputs,
        accepted_edit_odb_sha256=probe['edited_odb_sha256'],accepted_edit_def_sha256=probe['edited_def_sha256'],
        full_native_deck_sha256=DECK_SHA,gds_sha256=file_sha(gds),report_sha256=file_sha(out/'native-drc.lyrdb'),
        summary=summary,exact_final_source_qualified=False,strict_lec_qualified=False,rc_sta_qualified=False,
        exact_final_function_qualified=False,qualified_hard_macro=False,
        scope='Full native library GDS and unchanged complete FreePDK45 deck on exact sealed165 edit DEF; pending167 final identity/RCX/LEC and complete physical/function/macro gates remain separate')
    (out/'native-c8-edit-full-drc.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Full accepted-edit GDS DRC failed; original source and complete report retained'
