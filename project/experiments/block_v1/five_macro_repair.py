"""Repair a measured M hold violation within the same unfrozen implementation."""
import json
from pathlib import Path
import shutil


def matrix_hold(root,out,cpus,run):
    from five_macro_receive import source
    from io_slots import file_sha,slot
    assert cpus==16
    original,r,old,results=source(out,'m')
    failed=out.parents[2]/'block-v1-20261027-191/tasks/five-macro-physical-m'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed'] is False
    p=failed/'five-macro-physical.json';assert file_sha(p)==fr['outputs'][p.name]
    failure=json.loads(p.read_text());assert failure['passed'] is False
    assert failure['source_receipt_sha256']==file_sha(original/'receipt.json')
    timing=failure['timing']['timed_endpoints']
    assert timing['minimum_hold_ns']<0 and timing['native_summary']['hold_checks']>0
    assert all(v for k,v in failure['checks'].items() if k!='all_real_timed_endpoints')
    assert all(v for k,v in timing['checks'].items() if k not in ('all_hold_nonnegative','native_hold_count_zero'))
    rtl='project/rtl/block_library_v1/block_v1_m.sv'
    assert file_sha(root/rtl)==r['inputs'][rtl]
    nickname='bv1_block_v1_m'
    target=out/'flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    copied={}
    with slot(out.parents[2]):
        for name in ('1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','4_cts.odb','4_cts.sdc'):
            source_path=results/name;digest=file_sha(source_path)
            assert digest==r['outputs'][str(source_path.relative_to(original))]
            dest=target/name;shutil.copyfile(source_path,dest);dest.chmod(0o444);copied[name]=digest
        for name in ('pins.json','pins.tcl','input-diodes.tcl'):
            assert file_sha(original/name)==r['outputs'][name]
            shutil.copyfile(original/name,out/name)
    # New pre-freeze repair target, same physical implementation, RTL,
    # footprint, pin geometry, CTS source and actual electrical limits.
    # The .020 target is a repair knob; it is NOT a relaxed acceptance limit.
    config=(original/'config.mk').read_text()+'\nexport HOLD_SLACK_MARGIN = 0.020\n'
    (out/'config.mk').write_text(config)
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),
             'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['print-HOLD_SLACK_MARGIN'],'hold-variable.log')
    assert 'HOLD_SLACK_MARGIN: 0.020' in (out/'hold-variable.log').read_text()
    record=dict(old)
    record.update(passed=False,pipeline_completed=False,stages=[],final_files={},
                  config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                  repair_of=str(original),repair_source_receipt_sha256=file_sha(original/'receipt.json'),
                  measured_failure_sha256=file_sha(p),measured_failure_receipt_sha256=file_sha(failed/'receipt.json'),
                  measured_hold_ns=timing['minimum_hold_ns'],sealed_cts_inputs=copied,
                  repair_target_hold_ns=.020,implementation_count=1,
                  scope='Repair actual negative hold in same unfrozen M leaf, same RTL/die/pins/CTS; new route/RCX/final artifacts require every independent gate again')
    record['actual_variables']=dict(old['actual_variables'],HOLD_SLACK_MARGIN='0.020')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for stage in ('do-route','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage)
        assert all(file_sha(target/name)==digest for name,digest in copied.items());save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.is_file()
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    record['passed']=True;record['pipeline_completed']=True;save()
