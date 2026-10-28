"""Resume the failed V global route from sealed CTS; keep all real rules."""
import json
import re
import shutil


def implement(root,out,cpus,run):
    from io_slots import file_sha,slot
    assert cpus==16 and out.name=='revision300-route-v'
    policy=root/'project/experiments/block_v1/revision300-v-grt-resume.json'
    assert json.loads(policy.read_text())==dict(schema='revision300-v-grt-resume/1',
        source='block-v1-20261028-236/tasks/revision300-route-v',resume_from='4_cts.odb',
        upper_layer_adjustment=.20,same_native_geometry_rules=True,
        same_approved_timing_constraints=True,requires_fresh_final_acceptance=True)
    base=out.parents[2]
    source=base/'block-v1-20261028-236/tasks/revision300-route-v'
    receipt=json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is False and receipt['mode']==out.name
    report=source/'revision300-native-flow.json'
    assert file_sha(report)==receipt['outputs'][report.name]
    original=json.loads(report.read_text())
    assert original['stages']==['do-1_synth','do-floorplan','do-place','do-cts']
    grt=source/'flow/logs/nangate45/bv1_block_v1_v/base/5_1_grt.log'
    assert file_sha(grt)==receipt['outputs'][str(grt.relative_to(source))]
    text=grt.read_text()
    assert 'Global routing finished with congestion' in text
    assert 'Try reduce the layer adjustment from 25% to 20%' in text
    for name,digest in original['rtl_sha256'].items():assert file_sha(root/name)==digest
    sealed=('pins.json','pins.tcl','input.sdc','input.v','input-diodes.tcl','config.mk')
    for name in sealed:
        assert file_sha(source/name)==receipt['outputs'][name]
        shutil.copyfile(source/name,out/name)
    config=(out/'config.mk').read_text()
    assert not re.search(r'(?m)^.*export GRT_ADJUSTMENT\s*=',config)
    for name in ('pins.tcl','input.sdc','input.v','input-diodes.tcl'):
        assert config.count(str(source/name))==1
        config=config.replace(str(source/name),str(out/name))
    # This changes the global router's conservative capacity reservation only.
    # It does not change native track geometry, spacing, DRC or timing limits.
    hook=out/'grt-capacity.tcl'
    hook.write_text('source {'+str(out/'input-diodes.tcl')+'}\n'
        'set_global_routing_layer_adjustment metal4-metal10 0.20\n'
        'set f [open [file join $::env(RESULTS_DIR) bv1-grt-adjustment.tsv] w]\n'
        'puts $f "metal4-metal10\\t0.20"\nputs $f "native_rules\\tunchanged"\nclose $f\n')
    previous='export PRE_GLOBAL_ROUTE_TCL = '+str(out/'input-diodes.tcl')
    assert config.count(previous)==1
    config=config.replace(previous,'export PRE_GLOBAL_ROUTE_TCL = '+str(hook))
    (out/'config.mk').write_text(config)
    relative='flow/results/nangate45/bv1_block_v1_v/base'
    results=out/relative;results.mkdir(parents=True)
    copied={}
    with slot(base):
        for path in (source/relative).iterdir():
            if not path.is_file() or not re.match(r'^[1234]_',path.name):continue
            digest=file_sha(path);assert digest==receipt['outputs'][str(path.relative_to(source))]
            shutil.copyfile(path,results/path.name);copied[path.name]=digest
    assert {'4_cts.odb','4_cts.sdc','1_synth_lec.v'}<=set(copied)
    result=dict(original)
    result.update(passed=False,pipeline_completed=False,final_files={},qualified_hard_macro=False,
        source_cts_task=str(source),source_cts_receipt_sha256=file_sha(source/'receipt.json'),
        source_function_task=str(source.parent/'revision300-test-v'),
        inherited_cts_files_sha256=copied,failed_grt_log_sha256=file_sha(grt),
        resume_policy_sha256=file_sha(policy),
        executable_pre_global_route_hook_sha256=file_sha(hook),
        config_sha256=file_sha(out/'config.mk'),global_route_adjustment=.20,
        acceptance_policy='Unchanged native rules and approved300MHz SDC. Detailed routing and all new final gates remain mandatory; no congestion or DRC waiver.',
        scope='Same V RTL/footprint/placement/CTS; resume router with20percent conservative capacity adjustment explicitly suggested by failed native log. Fresh route/finish and all final acceptance required.')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    wanted=dict(original['actual_variables'],PRE_GLOBAL_ROUTE_TCL=str(hook))
    result['actual_variables']={}
    for name,expected in wanted.items():
        log='variable-'+name+'.log';run(command+['print-'+name],log)
        value=re.search(r'(?m)^'+name+r': (.+)$',(out/log).read_text()).group(1).strip()
        assert value==expected,(name,value,expected);result['actual_variables'][name]=value
    def save():(out/'revision300-native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for stage in ('do-route','do-finish'):
        run(command+[stage],stage+'.log');result['stages'].append(stage);save()
        assert (results/'bv1-grt-adjustment.tsv').read_text()=='metal4-metal10\t0.20\nnative_rules\tunchanged\n'
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert all(file_sha(source/relative/name)==digest for name,digest in copied.items())
    assert all(file_sha(source/name)==receipt['outputs'][name] for name in sealed)
    assert file_sha(source/'receipt.json')==result['source_cts_receipt_sha256']
    result.update(passed=True,pipeline_completed=True);save()
