"""Fresh RCX/final outputs from the real zero-DRC R repair, no old gate transfer."""
import json
import shutil
import re
from pathlib import Path


def implement(root,out,cpus,run):
    from io_slots import file_sha,slot
    from native_escape_finish import FLOW_HASHES
    from native_escape_audit import def_inventory
    assert cpus==16 and out.name=='revision300-route-r'
    policy=json.loads((root/'project/experiments/block_v1/revision300-r-patch-finish.json').read_text())
    assert set(policy)=={'schema','native','patch','patch_receipt_sha256','requires_fresh_final_acceptance'}
    assert policy['schema']=='revision300-r-patch-finish/1' and policy['requires_fresh_final_acceptance'] is True
    assert policy['native']=='block-v1-20261101-827/tasks/revision300-route-r'
    assert policy['patch']=='block-v1-20261101-919/tasks/revision300-r-gap-compose'
    base=out.parents[2];native=base/policy['native'];patch=base/policy['patch']
    nr=json.loads((native/'receipt.json').read_text());assert nr['passed'] and nr['mode']==native.name
    assert file_sha(native/'revision300-native-flow.json')==nr['outputs']['revision300-native-flow.json']
    old=json.loads((native/'revision300-native-flow.json').read_text())
    assert old['passed'] and old['pipeline_completed'] and old['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
    for name,h in old['rtl_sha256'].items():assert file_sha(root/name)==h
    assert file_sha(patch/'receipt.json')==policy['patch_receipt_sha256']
    pr=json.loads((patch/'receipt.json').read_text());assert pr['passed'] and pr['mode']==patch.name
    proof=patch/'revision300-r-remaining.json';assert file_sha(proof)==pr['outputs'][proof.name]
    p=json.loads(proof.read_text())
    assert p['passed'] and p['combined'] and not p['physical_qualified'] and p['candidate_native_count']==0
    assert p['added_markers']==0 and p['removed_markers']==5 and p['original_native_count']==5
    assert p['normal_net_counts']==[1013372,1013372] and p['exact_normal_net_header_path_rect_and_nonnet_delta'] and p['original_inputs_unchanged']
    assert p['source_receipt_sha256']=='b622d31e751b0aa3c41205439aeb4b3b44c888feec037981e10cefc28999a52c'
    prior=base/'block-v1-20261101-903/tasks/revision300-r-current-compose'
    assert file_sha(prior/'receipt.json')==p['source_receipt_sha256']
    prior_receipt=json.loads((prior/'receipt.json').read_text());assert prior_receipt['passed']
    for name,h in p['source_files_sha256'].items():assert file_sha(prior/name)==h==prior_receipt['outputs'][name]
    for name in('remaining-candidate.odb','remaining-candidate.def','remaining-native-drc.rpt'):assert file_sha(patch/name)==pr['outputs'][name]
    assert not(patch/'remaining-native-drc.rpt').read_text().strip()
    previous=base/'block-v1-20261101-828/tasks/revision300-final-source-r'
    assert file_sha(previous/'receipt.json')=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    previous_receipt=json.loads((previous/'receipt.json').read_text());assert previous_receipt['passed']
    assert file_sha(previous/'revision300-final-source.json')==previous_receipt['outputs']['revision300-final-source.json']
    previous_flow=json.loads((previous/'revision300-final-source.json').read_text())
    assert previous_flow['rtl_sha256']==old['rtl_sha256'] and previous_flow['source_native_receipt_sha256']==file_sha(native/'receipt.json')
    relative=Path('flow/results/nangate45/bv1_block_v1_r/base');results=out/relative;results.mkdir(parents=True)
    for category in('logs','reports','objects'):(out/'flow'/category/'nangate45/bv1_block_v1_r/base').mkdir(parents=True)
    copied={}
    def copy(source,target,digest):
        assert file_sha(source)==digest
        with slot(base):shutil.copyfile(source,target)
        assert file_sha(target)==digest;copied[str(target.relative_to(out))]=digest
    copy(patch/'remaining-candidate.odb',results/'6_1_fill.odb',pr['outputs']['remaining-candidate.odb'])
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
                accepted_edit_odb_sha256=pr['outputs']['remaining-candidate.odb'],actual_flow_scripts=FLOW_HASHES,
                exact_geometry_readback_required=True,requires_fresh_final_acceptance=True,
                scope='One current R, unchanged827 RTL/cells/placement/CTS; actual919 copied repair. Fresh ordinary final-report/RCX only; no reroute/fill/optimization. All ancestral physical/function/LEC/GDS/interface gates do not transfer and must rerun.')
    def save():(out/'revision300-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log');record['fresh_finish_commands'].append('do-6_report');save()
    body='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def final-readback.def\n'
    body+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def checked-readback.def\n'
    (out/'final-check.tcl').write_text(body);run(['openroad','-no_init','-exit',out/'final-check.tcl'],'final-check.log')
    assert def_inventory(patch/'remaining-candidate.def')==def_inventory(out/'final-readback.def'),'Fresh finish changed geometry, VIAS, placement or net records'
    assert file_sha(out/'final-readback.def')==file_sha(out/'checked-readback.def')
    assert not(out/'native-whole-drc.rpt').read_text().strip()
    for name,h in copied.items():assert file_sha(out/name)==h
    route_report=out/'flow/reports/nangate45/bv1_block_v1_r/base/5_route_drc.rpt'
    shutil.copyfile(out/'native-whole-drc.rpt',route_report)
    for suffix in('v','sdc','def','odb','spef'):
        f=results/('6_final.'+suffix);assert f.is_file()and f.stat().st_size>0
        record['final_files'][f.name]=dict(path=str(f),sha256=file_sha(f),bytes=f.stat().st_size)
    assert file_sha(patch/'receipt.json')==record['patch_receipt_sha256']
    assert all(file_sha(patch/n)==pr['outputs'][n]for n in('remaining-candidate.odb','remaining-candidate.def','remaining-native-drc.rpt'))
    record['stages'].append('do-finish')
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True,whole_native_drc_zero=True,exact_accepted_geometry_unchanged=True)
    save()
