"""Repair measured V driver limits within its one existing footprint/interface."""
import json
from pathlib import Path
import re
import shutil


TARGETS={
    'place81609':('BUF_X1','BUF_X4'),
    'place67728':('BUF_X1','BUF_X2'),
    'place53406':('BUF_X2','BUF_X4'),
    'wire109242':('BUF_X4','BUF_X8'),
    'place55219':('BUF_X2','BUF_X4'),
    'place58201':('BUF_X2','BUF_X4'),
    'place55816':('BUF_X2','BUF_X4'),
}


def swap_script():
    body='''proc drive_pin_snapshot {i} {
  set rows {}
  foreach t [$i getITerms] {
    set n [$t getNet]
    set net [expr {$n eq "NULL" ? "NULL" : [$n getName]}]
    lappend rows [list [[$t getMTerm] getName] $net]
  }
  return [lsort $rows]
}
set drive_block [ord::get_db_block]
'''
    for name,(old,new)in TARGETS.items():
        body+='''set i [$drive_block findInst {NAME}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "OLD"} {error "Unexpected measured driver NAME"}
set before [drive_pin_snapshot $i]
set replacement [[ord::get_db] findMaster NEW]
if {$replacement eq "NULL"} {error "Missing buffer master NEW"}
if {![$i swapMaster $replacement]} {error "Buffer master swap failed NAME"}
if {[drive_pin_snapshot $i] ne $before} {error "Buffer pin/net connectivity changed NAME"}
puts "DRIVE_SWAP NAME OLD NEW"
'''.replace('NAME',name).replace('OLD',old).replace('NEW',new)
    return body


def probe(root,out,cpus,run):
    from five_macro_receive import source
    from io_slots import file_sha
    assert cpus==16
    folder,r,flow,results=source(out,'v',original=True)
    failed=out.parents[2]/'block-v1-20261027-208/tasks/five-macro-physical-v'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed']is False
    p=failed/'five-macro-physical.json';assert file_sha(p)==fr['outputs'][p.name]
    f=json.loads(p.read_text());assert not f['passed']and f['source_receipt_sha256']==file_sha(folder/'receipt.json')
    t=f['timing']['timed_endpoints']
    assert t['electrical']['capacitance']['count']==7 and t['electrical']['slew']['count']==1
    assert all(v for k,v in f['checks'].items()if k!='all_real_timed_endpoints')
    assert all(v for k,v in t['checks'].items()if k not in ('capacitance_count_zero','capacitance_margin_nonnegative','slew_count_zero','slew_margin_nonnegative'))
    report=failed/'electrical-violations.rpt';assert file_sha(report)==fr['outputs'][report.name]
    text=report.read_text().split('max capacitance\n',1)[1]
    measured={}
    for m in re.finditer(r'(?m)^(\S+)/Z\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+) \(VIOLATED\)$',text):
        name,limit,cap,slack=m.groups();assert name not in measured
        measured[name]=dict(limit_ff=float(limit),cap_ff=float(cap),slack_ff=float(slack))
    assert set(measured)==set(TARGETS)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    liberty=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',liberty));caps={}
    for i,m in enumerate(starts):
        name=m.group(1)
        if name not in {v for pair in TARGETS.values()for v in pair}:continue
        chunk=liberty[m.end():starts[i+1].start()if i+1<len(starts)else len(liberty)]
        assert re.findall(r'\bfunction\s*:\s*"([^"]+)"',chunk)==['A']
        caps[name]=float(re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)',chunk).group(1))
    for name,(old,new)in TARGETS.items():
        assert abs(measured[name]['limit_ff']-caps[old])<1e-3
        assert caps[new]>=measured[name]['cap_ff']*1.2
    grt=results/'5_1_grt.odb';assert file_sha(grt)==r['outputs'][str(grt.relative_to(folder))]
    script='set_thread_count 16\nread_db {'+str(grt)+'}\n'+swap_script()
    script+='write_db {'+str(out/'probe-resized.odb')+'}\n'
    (out/'probe.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'probe.tcl')],'probe.log')
    assert file_sha(grt)==r['outputs'][str(grt.relative_to(folder))]
    result=dict(passed=True,source_receipt_sha256=file_sha(folder/'receipt.json'),
                failure_receipt_sha256=file_sha(failed/'receipt.json'),measured=measured,
                targets=TARGETS,liberty_sha256=file_sha(lib),buffer_max_capacitance_ff=caps,
                native_pin_connectivity_preserved=True,original_grt_unchanged=True,
                disposable_edited_odb_sha256=file_sha(out/'probe-resized.odb'),
                scope='Disposable native swapMaster API/pin/capacity control; no placement, route or repaired-leaf acceptance.')
    (out/'five-macro-probe-v-drive.json').write_text(json.dumps(result,indent=2)+'\n')


def repair(root,out,cpus,run):
    from five_macro_receive import source
    from io_slots import file_sha,slot
    assert cpus==16
    original,r,old,results=source(out,'v',original=True)
    probe=out.parents[2]/'block-v1-20261027-214/tasks/five-macro-probe-v-drive';pr=json.loads((probe/'receipt.json').read_text());assert pr['passed']
    p=probe/'five-macro-probe-v-drive.json';assert file_sha(p)==pr['outputs'][p.name]
    proof=json.loads(p.read_text());assert proof['passed']and proof['source_receipt_sha256']==file_sha(original/'receipt.json')
    assert proof['targets']=={k:list(v)for k,v in TARGETS.items()}
    target=out/'flow/results/nangate45/bv1_block_v1_v/base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):
        (out/'flow'/category/'nangate45/bv1_block_v1_v/base').mkdir(parents=True)
    copied={}
    with slot(out.parents[2]):
        for name in ('1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','5_1_grt.odb','5_1_grt.sdc','route.guide','bv1-input-diodes.tsv'):
            p=results/name;digest=file_sha(p);assert digest==r['outputs'][str(p.relative_to(original))]
            shutil.copyfile(p,target/name);assert file_sha(target/name)==digest;copied[name]=digest
        for name in ('pins.json','pins.tcl','input-diodes.tcl'):
            assert file_sha(original/name)==r['outputs'][name];shutil.copyfile(original/name,out/name)
    hook='global_route -start_incremental\n'+swap_script()
    for name in TARGETS:hook+='set_dont_touch [get_cells {'+name+'}]\n'
    hook+='''detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
'''
    (out/'drive-repair.tcl').write_text(hook)
    config=(original/'config.mk').read_text()
    assert 'PRE_DETAIL_ROUTE_TCL'not in config
    config=config.replace(str(original/'input-diodes.tcl'),str(out/'input-diodes.tcl'))
    config+='\nexport PRE_DETAIL_ROUTE_TCL = '+str(out/'drive-repair.tcl')+'\n'
    (out/'config.mk').write_text(config)
    record=dict(old,passed=False,pipeline_completed=False,stages=[],final_files={},
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                source_receipt_sha256=file_sha(original/'receipt.json'),drive_probe_receipt_sha256=file_sha(probe/'receipt.json'),
                measured_driver_repair=TARGETS,sealed_grt_inputs=copied,implementation_count=1,
                scope='Same V RTL/die/pins, measured seven BUF drive repair from sealed GRT. Fresh route/RCX and all independent gates required.')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['print-PRE_DETAIL_ROUTE_TCL'],'hook-variable.log')
    assert 'PRE_DETAIL_ROUTE_TCL: '+str(out/'drive-repair.tcl')in(out/'hook-variable.log').read_text()
    for stage in ('do-5_2_route','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage);save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.stat().st_size>0
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert source(out,'v',original=True)[1]==r
    record.update(passed=True,pipeline_completed=True);save()
