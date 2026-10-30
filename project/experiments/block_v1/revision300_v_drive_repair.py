"""Reroute the one current V after two measured buffer drive corrections."""
import json
import re
import shutil
from pathlib import Path


def implement(root, out, cpus, run):
    from io_slots import file_sha, slot
    from revision300_v_drive_probe import TARGETS
    assert cpus == 16 and out.name == 'revision300-route-v'
    base = out.parents[2]
    policy = json.loads((root/'project/experiments/block_v1/revision300-v-drive-repair.json').read_text())
    assert policy == dict(schema='revision300-v-drive-repair/1',
                          native='block-v1-20261030-588/tasks/revision300-route-v',
                          probe='block-v1-20261031-628/tasks/revision300-v-drive-probe',
                          requires_fresh_final_acceptance=True)
    native = base/'block-v1-20261030-588/tasks/revision300-route-v'
    probe = base/'block-v1-20261031-628/tasks/revision300-v-drive-probe'
    nr = json.loads((native/'receipt.json').read_text())
    pr = json.loads((probe/'receipt.json').read_text())
    assert nr['passed'] and pr['passed']
    for folder, receipt, filename in ((native,nr,'revision300-native-flow.json'),
                                      (probe,pr,'revision300-v-drive-probe.json')):
        assert file_sha(folder/filename) == receipt['outputs'][filename]
    old = json.loads((native/'revision300-native-flow.json').read_text())
    proof = json.loads((probe/'revision300-v-drive-probe.json').read_text())
    assert proof['source_native_receipt_sha256'] == file_sha(native/'receipt.json')
    assert proof['targets'] == {k:list(v) for k,v in TARGETS.items()}
    assert proof['native_signal_pin_net_identity_preserved'] and proof['original_grt_unchanged']
    assert old['passed'] and old['pipeline_completed'] and len(old['stages'])==6
    for n,h in old['rtl_sha256'].items(): assert file_sha(root/n)==h
    relative = 'flow/results/nangate45/bv1_block_v1_v/base'
    results = out/relative
    results.mkdir(parents=True)
    for category in ('logs','reports','objects'):
        (out/'flow'/category/'nangate45/bv1_block_v1_v/base').mkdir(parents=True)
    copied = {}
    def copy_file(p, destination):
        name = str(p.relative_to(native))
        digest = file_sha(p)
        assert digest == nr['outputs'][name]
        with slot(base): shutil.copyfile(p,destination)
        assert file_sha(destination)==digest
        copied[name]=digest
    for name in ('1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','5_1_grt.odb',
                 '5_1_grt.sdc','route.guide','bv1-input-diodes.tsv',
                 'bv1-clock-policy.tsv','bv1-grt-adjustment.tsv'):
        copy_file(native/relative/name,results/name)
    assert file_sha(results/'5_1_grt.odb')==proof['original_grt_sha256']
    for name in ('input.v','input.sdc','pins.json','pins.tcl','input-diodes.tcl',
                 'clock-policy.tcl','grt-capacity.tcl','config.mk'):
        copy_file(native/name,out/name)
        if name.endswith(('.tcl','.mk')):
            (out/name).write_text((out/name).read_text().replace(str(native),str(out)))
    hook = '''global_route -start_incremental
proc drive_signal_pins {i} {
  set result {}
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] in {POWER GROUND}} {continue}
    set n [$t getNet]
    lappend result [list [$m getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]
  }
  return [lsort $result]
}
set b [ord::get_db_block]
'''
    for name,(old_master,new_master) in TARGETS.items():
        hook += '''set i [$b findInst {NAME}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "OLD"} {error "Unexpected current V measured driver NAME"}
set pins [drive_signal_pins $i]
set replacement [[ord::get_db] findMaster NEW]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Native driver swap failed NAME"}
if {[drive_signal_pins $i] ne $pins} {error "Driver signal pin/net identity changed NAME"}
puts "MEASURED_DRIVE_SWAP NAME OLD NEW"
'''.replace('NAME',name).replace('OLD',old_master).replace('NEW',new_master)
    hook += '''add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
'''
    for name in TARGETS: hook += 'set_dont_touch [get_cells {'+name+'}]\n'
    hook += '''detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
'''
    (out/'drive-repair.tcl').write_text(hook)
    config = (out/'config.mk').read_text()
    assert 'PRE_DETAIL_ROUTE_TCL' not in config
    config += '\nexport PRE_DETAIL_ROUTE_TCL = '+str(out/'drive-repair.tcl')+'\n'
    (out/'config.mk').write_text(config)
    record = dict(old,passed=False,pipeline_completed=False,final_files={},
                  stages=old['stages'][:4],inherited_physical_stages=old['stages'][:4],
                  reroute_stages=[],source_native_task=str(native),
                  source_native_receipt_sha256=file_sha(native/'receipt.json'),
                  drive_probe_receipt_sha256=file_sha(probe/'receipt.json'),
                  measured_driver_repair=TARGETS,sealed_grt_inputs=copied,
                  config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                  scope='One current V, unchanged RTL/die/pins/300MHz rules. Two measured buffer upsizes from sealed588 GRT after actual628 native compatibility probe. Fresh legalization/incremental guides/detailed route/RCX; every independent final gate and all-port evidence must be rerun.')
    command = ['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),
               'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    record['actual_variables']={}
    wanted={k:v.replace(str(native),str(out)) for k,v in old['actual_variables'].items()}
    wanted['PRE_DETAIL_ROUTE_TCL']=str(out/'drive-repair.tcl')
    for name,expected in wanted.items():
        log='variable-'+name+'.log'
        run(command+['print-'+name],log)
        value=re.search(r'(?m)^'+name+r': (.+)$',(out/log).read_text())[1].strip()
        assert value==expected,(name,value,expected)
        record['actual_variables'][name]=value
    def save(): (out/'revision300-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for stage in ('do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish'):
        run(command+[stage],stage+'.log')
        record['reroute_stages'].append(stage)
        if stage=='do-5_route.sdc': record['stages'].append('do-route')
        if stage=='do-finish': record['stages'].append(stage)
        save()
    detail = out/'flow/logs/nangate45/bv1_block_v1_v/base/5_2_route.log'
    for name,(old_master,new_master) in TARGETS.items():
        assert 'MEASURED_DRIVE_SWAP '+name+' '+old_master+' '+new_master in detail.read_text()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix)
        assert p.stat().st_size>0
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert all(file_sha(native/name)==digest for name,digest in copied.items())
    assert file_sha(native/'receipt.json')==record['source_native_receipt_sha256']
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True)
    save()
