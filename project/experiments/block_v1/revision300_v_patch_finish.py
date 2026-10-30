"""Fresh RCX/final outputs from the real zero-DRC V repair, no old gate transfer."""
import json
import shutil
from pathlib import Path


def implement(root,out,cpus,run):
    from io_slots import file_sha,slot
    from native_escape_finish import FLOW_HASHES
    from native_escape_audit import def_inventory
    assert cpus==16 and out.name=='revision300-route-v'
    policy=json.loads((root/'project/experiments/block_v1/revision300-v-patch-finish.json').read_text())
    assert policy==dict(schema='revision300-v-patch-finish/1',native='block-v1-20261031-629/tasks/revision300-route-v',patch='block-v1-20261031-763/tasks/revision300-v-zero31-compose',requires_fresh_final_acceptance=True)
    base=out.parents[2]
    native=base/'block-v1-20261031-629/tasks/revision300-route-v'
    nr=json.loads((native/'receipt.json').read_text());assert nr['passed']
    assert file_sha(native/'revision300-native-flow.json')==nr['outputs']['revision300-native-flow.json']
    old=json.loads((native/'revision300-native-flow.json').read_text())
    assert old['passed']and old['pipeline_completed']and old['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
    for name,h in old['rtl_sha256'].items():assert file_sha(root/name)==h
    patch=base/'block-v1-20261031-763/tasks/revision300-v-zero31-compose'
    pr=json.loads((patch/'receipt.json').read_text());assert pr['passed']and pr['mode']==patch.name
    proof=patch/'revision300-v-local-vias.json';assert file_sha(proof)==pr['outputs'][proof.name]
    p=json.loads(proof.read_text())
    assert p['passed']and not p['physical_qualified']and p['candidate_native_count']==p['added_markers']==0
    assert p['exact_normal_nets_headers_paths_rectangles']and p['original_inputs_unchanged']and p['normal_net_counts']==[562494,562494]
    for name in('local-candidate.odb','local-candidate.def','local-native-drc.rpt'):assert file_sha(patch/name)==pr['outputs'][name]
    assert not(patch/'local-native-drc.rpt').read_text().strip()
    # The repaired copy descends from this 630 package, which descends from629.
    # Its old physical/function/LEC qualifications are explicitly not inherited.
    previous=base/'block-v1-20261031-630/tasks/revision300-final-source-v'
    previous_receipt=json.loads((previous/'receipt.json').read_text());assert previous_receipt['passed']
    assert file_sha(previous/'revision300-final-source.json')==previous_receipt['outputs']['revision300-final-source.json']
    previous_flow=json.loads((previous/'revision300-final-source.json').read_text())
    assert previous_flow['source_native_receipt_sha256']==file_sha(native/'receipt.json')and previous_flow['rtl_sha256']==old['rtl_sha256']
    relative=Path('flow/results/nangate45/bv1_block_v1_v/base');results=out/relative;results.mkdir(parents=True)
    for category in('logs','reports','objects'):(out/'flow'/category/'nangate45/bv1_block_v1_v/base').mkdir(parents=True)
    copied={}
    def copy(source,target,digest):
        assert file_sha(source)==digest
        with slot(base):shutil.copyfile(source,target)
        assert file_sha(target)==digest;copied[str(target.relative_to(out))]=digest
    copy(patch/'local-candidate.odb',results/'6_1_fill.odb',pr['outputs']['local-candidate.odb'])
    raw_results=native/relative
    for name in('1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv'):
        copy(raw_results/name,results/name,nr['outputs'][str(relative/name)])
    copy(raw_results/'6_final.sdc',results/'6_1_fill.sdc',nr['outputs'][str(relative/'6_final.sdc')])
    for name in('pins.json','pins.tcl','input.sdc','input-diodes.tcl','config.mk'):
        copy(native/name,out/name,nr['outputs'][name])
    flow=Path('/OpenROAD-flow-scripts/flow');assert {n:file_sha(flow/n)for n in FLOW_HASHES}==FLOW_HASHES
    record=dict(old,passed=False,pipeline_completed=False,final_files={},stages=old['stages'][:-1],
                inherited_stages=old['stages'][:-1],fresh_finish_commands=[],
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                patch_receipt_sha256=file_sha(patch/'receipt.json'),patch_report_sha256=file_sha(proof),
                source_native_task=str(native),source_native_receipt_sha256=file_sha(native/'receipt.json'),
                source_final_package_receipt_sha256=file_sha(previous/'receipt.json'),
                accepted_edit_odb_sha256=pr['outputs']['local-candidate.odb'],actual_flow_scripts=FLOW_HASHES,
                exact_geometry_readback_required=True,requires_fresh_final_acceptance=True,
                scope='One current V, unchanged576 RTL and629 cells/placement/CTS, bounded pre-freeze metal/via repairs. Fresh ordinary final-report/RCX only; no reroute/fill/optimization. Original630 gates do not transfer. Every final independent gate and all-port evidence must rerun.')
    def save():(out/'revision300-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log');record['fresh_finish_commands'].append('do-6_report');save()
    body='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def final-readback.def\n'
    body+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def checked-readback.def\n'
    (out/'final-check.tcl').write_text(body);run(['openroad','-no_init','-exit',out/'final-check.tcl'],'final-check.log')
    assert def_inventory(patch/'local-candidate.def')==def_inventory(out/'final-readback.def'),'Fresh finish changed geometry, VIAS, placement or net records'
    assert file_sha(out/'final-readback.def')==file_sha(out/'checked-readback.def')
    assert not(out/'native-whole-drc.rpt').read_text().strip()
    for name,h in copied.items():assert file_sha(out/name)==h
    route_report=out/'flow/reports/nangate45/bv1_block_v1_v/base/5_route_drc.rpt'
    shutil.copyfile(out/'native-whole-drc.rpt',route_report)
    for suffix in('v','sdc','def','odb','spef'):
        f=results/('6_final.'+suffix);assert f.is_file()and f.stat().st_size>0
        record['final_files'][f.name]=dict(path=str(f),sha256=file_sha(f),bytes=f.stat().st_size)
    assert file_sha(patch/'receipt.json')==record['patch_receipt_sha256']
    assert all(file_sha(patch/n)==pr['outputs'][n]for n in('local-candidate.odb','local-candidate.def','local-native-drc.rpt'))
    record['stages'].append('do-finish')
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True,whole_native_drc_zero=True,exact_accepted_geometry_unchanged=True)
    save()
