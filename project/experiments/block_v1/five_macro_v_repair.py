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


def probe_tail(root,out,cpus,run):
    """Measure the new222 flop limit and PG failures on a disposable database."""
    from five_macro_receive import source
    from io_slots import file_sha
    assert cpus==16
    folder,receipt,_,results=source(out,'v')
    failed=out.parents[2]/'block-v1-20261027-222/tasks/five-macro-physical-v'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed']is False
    p=failed/'five-macro-physical.json';assert file_sha(p)==fr['outputs'][p.name]
    failure=json.loads(p.read_text());assert failure['source_receipt_sha256']==file_sha(folder/'receipt.json')
    assert {k for k,v in failure['checks'].items()if not v}=={'all_real_timed_endpoints','all_pg_iterms_correct'}
    summary=failed/'physical-summary.tsv';assert file_sha(summary)==fr['outputs'][summary.name]
    assert 'incorrect_pg_iterms\t2\n'in summary.read_text()
    worst=failed/'electrical-worst.rpt';assert file_sha(worst)==fr['outputs'][worst.name]
    cap=worst.read_text().split('max capacitance\n',1)[1]
    rows=re.findall(r'(?m)^(\S+)/Q\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+) \(VIOLATED\)$',cap)
    assert len(rows)==1 and rows[0][0].endswith('slice$812988')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));caps={}
    for i,m in enumerate(starts):
        if m[1]not in ('DFF_X1','DFF_X2'):continue
        chunk=text[m.end():starts[i+1].start()if i+1<len(starts)else len(text)]
        caps[m[1]]=[float(v)for v in re.findall(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)',chunk)]
    assert caps['DFF_X1']and caps['DFF_X2']
    assert min(caps['DFF_X2'])>=float(rows[0][2])*1.2
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'+'''
set b [ord::get_db_block]
set f [open pg-before.tsv w]
set candidates {}
foreach i [$b getInsts] {
  if {[string match {*slice$812988} [$i getName]]} {lappend candidates $i}
  foreach t [$i getITerms] {
    set m [$t getMTerm];set type [$m getSigType]
    if {$type ni {POWER GROUND}} {continue}
    set n [$t getNet];set expected [expr {$type eq "POWER" ? "VDD" : "VSS"}]
    if {$n eq "NULL" || [$n getName] ne $expected} {
      set net_name [expr {$n eq "NULL" ? "NULL" : [$n getName]}]
      puts $f "[binary encode hex [$i getName]]\t[[$i getMaster] getName]\t[$m getName]\t$type\t$net_name"
    }
  }
}
close $f
if {[llength $candidates]!=1} {error "Measured flop is not unique"}
set i [lindex $candidates 0]
if {[[$i getMaster] getName] ne "DFF_X1"} {error "Unexpected measured flop master"}
proc tail_signals {i} {
  set result {}
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] in {POWER GROUND}} {continue}
    set n [$t getNet]
    if {$n eq "NULL" && [$m getIoType] in {INPUT INOUT}} {error "Open measured flop signal input"}
    set net_name [expr {$n eq "NULL" ? "NULL" : [$n getName]}]
    lappend result [list [$m getName] $net_name]
  }
  return [lsort $result]
}
set before [tail_signals $i]
set old [$i getMaster];set new [[ord::get_db] findMaster DFF_X2]
if {$new eq "NULL" || ![$i swapMaster $new]} {error "DFF_X2 native swap failed"}
if {[tail_signals $i] ne $before} {error "Flop functional pin/net identity changed"}
set f [open flop-probe.tsv w]
puts $f "[binary encode hex [$i getName]]\t[$old getName]\t[$old getWidth]\t[$old getHeight]\t[$new getName]\t[$new getWidth]\t[$new getHeight]"
close $f
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
set bad 0
foreach i [$b getInsts] {
  foreach t [$i getITerms] {
    set m [$t getMTerm];set type [$m getSigType]
    if {$type ni {POWER GROUND}} {continue}
    set n [$t getNet];set expected [expr {$type eq "POWER" ? "VDD" : "VSS"}]
    if {$n eq "NULL" || [$n getName] ne $expected} {incr bad}
  }
}
set f [open pg-after.txt w];puts $f $bad;close $f
if {$bad!=0} {error "Explicit native PG reconnection left failures"}
write_db disposable.odb
'''
    (out/'probe.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'probe.tcl')],'probe.log')
    pg=(out/'pg-before.tsv').read_text().splitlines();assert len(pg)==2
    fields=(out/'flop-probe.tsv').read_text().strip().split('\t');assert len(fields)==7
    assert fields[1]=='DFF_X1'and fields[4]=='DFF_X2'and fields[3]==fields[6]
    assert (out/'pg-after.txt').read_text().strip()=='0'
    assert source(out,'v')[1]==receipt
    result=dict(passed=True,source_receipt_sha256=file_sha(folder/'receipt.json'),
                physical_failure_receipt_sha256=file_sha(failed/'receipt.json'),
                measured_flop=dict(instance=bytes.fromhex(fields[0]).decode(),instance_hex=fields[0],old_master=fields[1],new_master=fields[4],
                                   old_size_dbu=list(map(int,fields[2:4])),new_size_dbu=list(map(int,fields[5:7])),
                                   limit_ff=float(rows[0][1]),cap_ff=float(rows[0][2]),slack_ff=float(rows[0][3])),
                liberty_sha256=file_sha(lib),flop_max_capacitance_ff=caps,
                pg_before=pg,pg_after_incorrect=0,native_signal_pin_net_identity_preserved=True,
                original_final_unchanged=True,qualified_hard_macro=False,
                scope='Disposable native DFF_X2 signal-pin swap and explicit PG API control; placement/reroute/RCX/full gates still required.')
    (out/'five-macro-probe-v-tail.json').write_text(json.dumps(result,indent=2)+'\n')


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


def finish_routed(root,out,cpus,run):
    """Resume the sealed215 detailed route through the omitted native stages."""
    from io_slots import file_sha,slot
    from five_macro_receive import source
    from native_escape_finish import FLOW_HASHES
    assert cpus==16
    original,original_receipt,_,_=source(out,'v',original=True)
    prior=out.parents[2]/'block-v1-20261027-215/tasks/five-macro-repair-v-drive'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']is False
    proof_path=prior/'five-macro-native-flow.json'
    assert file_sha(proof_path)==receipt['outputs'][proof_path.name]
    proof=json.loads(proof_path.read_text())
    assert proof['stages']==['do-5_2_route']and not proof['pipeline_completed']
    assert proof['source_receipt_sha256']==file_sha(original/'receipt.json')
    assert proof['measured_driver_repair']=={k:list(v)for k,v in TARGETS.items()}
    commands=receipt['commands'];assert commands[-2]['returncode']==0
    assert commands[-2]['argv'][-1]=='do-5_2_route'
    assert commands[-1]['argv'][-1]=='do-finish'and commands[-1]['returncode']==2
    failed_log=prior/'do-finish.log'
    assert file_sha(failed_log)==receipt['outputs'][failed_log.name]
    assert '[ERROR ORD-0007]'in failed_log.read_text()and '/base/5_route.odb does not exist.'in failed_log.read_text()
    flow=Path('/OpenROAD-flow-scripts/flow')
    assert {n:file_sha(flow/n)for n in FLOW_HASHES}==FLOW_HASHES
    nickname='nangate45/bv1_block_v1_v/base'
    # Preserve the installed flow text that defines the missing fill/copy steps.
    shutil.copyfile(flow/'Makefile',out/'native-flow-Makefile')
    target=out/'flow/results'/nickname;target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'flow'/category/nickname).mkdir(parents=True)
    copied={}
    def copy(relative,destination):
        p=prior/relative;digest=file_sha(p);assert digest==receipt['outputs'][relative]
        with slot(out.parents[2]):shutil.copyfile(p,destination)
        assert file_sha(destination)==digest;copied[str(destination.relative_to(out))]=digest
    for name in ('5_2_route.odb','5_1_grt.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv'):
        copy('flow/results/'+nickname+'/'+name,target/name)
    for name in ('pins.json','pins.tcl','input-diodes.tcl','drive-repair.tcl'):
        copy(name,out/name)
    copy('flow/reports/'+nickname+'/5_route_drc.rpt',out/'flow/reports'/nickname/'5_route_drc.rpt')
    copy('flow/logs/'+nickname+'/5_2_route.log',out/'sealed-detail-route.log')
    assert not(out/'flow/reports'/nickname/'5_route_drc.rpt').read_text().strip()
    config_path=prior/'config.mk';assert file_sha(config_path)==receipt['outputs']['config.mk']==proof['config_sha256']
    config=config_path.read_text()
    for name in ('input-diodes.tcl','drive-repair.tcl'):config=config.replace(str(prior/name),str(out/name))
    (out/'config.mk').write_text(config)
    record=dict(proof,passed=False,pipeline_completed=False,stages=[],final_files={},
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                routed_source_receipt_sha256=file_sha(prior/'receipt.json'),sealed_routed_inputs=copied,
                actual_flow_scripts=FLOW_HASHES,
                scope='Same V seven-buffer repair; resume sealed215 detailed route via installed fillcell/route aliases/final RCX. Every independent gate must use these new final files.')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    for stage in ('do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage);save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.stat().st_size>0
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    for name,digest in copied.items():assert file_sha(out/name)==digest
    assert source(out,'v',original=True)[1]==original_receipt
    assert file_sha(prior/'receipt.json')==record['routed_source_receipt_sha256']
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True);save()
