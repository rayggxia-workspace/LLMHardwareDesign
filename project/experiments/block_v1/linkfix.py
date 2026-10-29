"""Repair-study copies: measured native launch strength and complete bus routes."""
import json
from pathlib import Path
import shutil
from interconnect_spef import sha


def native_source(root,kind):
    row=json.loads((root/'project/experiments/block_v1/interconnect-sources.json').read_text())['macros'][kind]
    accepted=Path(row['verilog']).parents[5]
    receipt=json.loads((accepted/'receipt.json').read_text());assert receipt['passed']
    proof=accepted/'revision300-final-source.json';assert sha(proof)==receipt['outputs'][proof.name]
    flow=json.loads(proof.read_text());assert flow['passed'] and flow['pipeline_completed']
    raw=Path(flow['raw_source'])
    grt_source=Path(flow['source_route_task']) if kind=='s' else raw
    grt=grt_source/'flow/results/nangate45'/('bv1_'+flow['top'])/'base/5_1_grt.odb'
    return row,accepted,receipt,flow,grt


def selected_port(kind,name):
    return name=='ready' if kind=='s' else name=='write_ready' or name.startswith(('read_data[','read_index[')) or name=='read_valid' if kind=='t' else name=='cmd_ready' or name.startswith(('rsp_data[','rsp_valid','rsp_error','rsp_saturated'))


def probe(root,out,cpus,run,kind):
    assert cpus==16 and kind in ('m','s','t')
    row,accepted,receipt,flow,grt=native_source(root,kind)
    final=Path(row['verilog']).parent/'6_final.odb';assert sha(final)==row['hashes'][final.name]
    original=grt.parents[5];r=json.loads((original/'receipt.json').read_text());assert r['passed']
    assert sha(grt)==r['outputs'][str(grt.relative_to(original))]
    for label,odb in [('final',final),('grt',grt)]:
        script='set_thread_count 16\nread_db {'+str(odb)+'}\nset b [ord::get_db_block]\nset f [open '+label+'-drivers.tsv w]\n'
        script+='''foreach bt [$b getBTerms] {
 if {[$bt getIoType] ne "OUTPUT" || [$bt getSigType] ne "SIGNAL"} {continue}
 set n [$bt getNet];set hits 0
 foreach it [$n getITerms] {
  if {[[$it getMTerm] getIoType] ne "OUTPUT"} {continue}
  set i [$it getInst];incr hits
  puts $f "[$bt getName]\t[$i getName]\t[[$i getMaster] getName]\t[$it getMTerm]\t[$i getLocation]\t[[$i getMaster] getWidth]\t[[$i getMaster] getHeight]"
 }
 if {$hits!=1} {error "Unexpected output drivers [$bt getName] $hits"}
}
close $f
'''
        script+='help detailed_placement\nhelp global_route\nhelp detailed_route\n'
        (out/(label+'-probe.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/(label+'-probe.tcl')],label+'-probe.log')
    drivers={}
    for label in ('final','grt'):
        values={}
        for line in (out/(label+'-drivers.tsv')).read_text().splitlines():
            port,inst,master,pin,xy,w,h=line.split('\t')
            if selected_port(kind,port):values[port]=dict(instance=inst,master=master,xy_dbu=list(map(int,xy.split())),size_dbu=[int(w),int(h)])
        drivers[label]=values
    assert set(drivers['final'])==set(drivers['grt'])
    assert len(drivers['grt'])==dict(m=132,t=140,s=1)[kind]
    assert all(v['master'].startswith('BUF_X')for v in drivers['grt'].values())
    (out/'linkfix-probe.json').write_text(json.dumps(dict(passed=True,kind=kind,top=flow['top'],
        accepted_source=str(accepted),accepted_receipt_sha256=sha(accepted/'receipt.json'),
        grt_source=str(original),grt_path=str(grt),grt_sha256=sha(grt),grt_receipt_sha256=sha(original/'receipt.json'),
        drivers=drivers,scope='Read-only exact native output-driver inventory. No ECO or physical acceptance yet.'),indent=2)+'\n')


def route(root,out,cpus,run,variant):
    from linkclose_route import route as actual
    assert variant in ('mf1','mf2','mf4','tf1','tf2')
    if variant.startswith('m'):
        layout=dict(t=[200,200],bridge=[200,1260],m=[200,1440],booster=[1260,400],**{'return':[1260,1100]})
        if variant=='mf4':layout.update(bridge=[320,1260],m=[320,1440])
        pair='mt'
    else:
        layout=dict(t=[200,200],bank=[200,1260],s=[200,1480],booster=[116,2000],**{'return':[116,1160]})
        pair='ts'
    actual(root,out,cpus,run,pair,layout=layout,guide_margin=128 if variant.endswith('1')else 384,iterations=24)


def rebind(root,out,cpus,run,key):
    """Instantiate accepted repaired leaves under the exact full-bus wires."""
    from linkclose_measure import bound
    from linkfix_channel import geometry
    from overlay import generate
    pair='mt'if key=='mq1'else'ts'
    if pair=='mt':original=out.parents[2]/'block-v1-20261029-928/tasks/linkclose-route-mf4'
    else:original=out.parents[2]/'block-v1-20261029-934/tasks/linkclose-route-tf9'
    proof,r=bound(original,'linkclose-route.json')
    inputs_path=original/'route-inputs.json';assert sha(inputs_path)==r['outputs'][inputs_path.name]
    inputs=json.loads(inputs_path.read_text());assert len(inputs['links'])==(275 if pair=='mt'else 281)
    rebinding={}
    for kind in pair:
        raw_view=key in ('tq2','tq3')
        accepted=out.parent/('linkfix-io-view-'+kind)if raw_view else out.parent/('linkfix-accept-'+kind)
        if not accepted.exists():accepted=out.parents[2]/(('block-v1-20261029-930'if kind=='m'else'block-v1-20261029-932')+'/tasks/linkfix-accept-'+kind)
        report,ar=bound(accepted,'linkfix-io-view.json'if raw_view else'linkfix-accept.json')
        source,receipt,flow,results=received_source(out,kind)
        assert report['source']==str(source) and report['source_receipt_sha256']==sha(source/'receipt.json')
        # Exact pin geometry was independently compared with the original
        # sealed pin contract. All wire endpoints and cell footprints persist.
        assert (report['pin_contract']if raw_view else report['physical']['pin_contract'])['passed'] and flow['die_um']==inputs['size'][kind]
        inputs['native'][kind]=dict(top=flow['top'],verilog=str(results/'6_final.v'),spef=str(results/'6_final.spef'),sdc=str(source/'input.sdc'),
            hashes={n:v['sha256']for n,v in flow['files'].items()},physical_receipt_path=str(accepted/'receipt.json'),physical_receipt_sha256=sha(accepted/'receipt.json'))
        lef=accepted/'candidate.lef';assert sha(lef)==ar['outputs'][lef.name]
        inputs['lefs'][kind]=dict(path=str(lef),sha256=sha(lef))
        rebinding[kind]=dict(report_sha256=sha(accepted/('linkfix-io-view.json'if raw_view else'linkfix-accept.json')),source_receipt_sha256=sha(source/'receipt.json'),complete_native_acceptance=not raw_view)
    (out/'route-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    assert sha(original/'routed.def')==r['outputs']['routed.def']
    (out/'input.def').write_bytes((original/'routed.def').read_bytes())
    spec=json.loads((root/'project/experiments/block_v1/technology-2um-v1.json').read_text())
    generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),spec,out/'technology')
    script='set_thread_count 16\nread_lef {'+str(out/'technology/research12.tech.lef')+'}\n'
    for i,lef in enumerate(dict.fromkeys(v['path']for v in inputs['lefs'].values())):
        p=out/('macro-%d.lef'%i);p.write_bytes(Path(lef).read_bytes());assert sha(p)==sha(Path(lef));script+='read_lef {'+str(p)+'}\n'
    script+='read_def {'+str(out/'input.def')+'}\nwrite_db routed.odb\nwrite_def routed.def\nsource {'+str(root/'project/experiments/block_v1/odb_geometry.tcl')+'}\nbvgeom::export geometry.tsv\n'
    (out/'route.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'route.tcl'],'route.log')
    # Check the actual recreated database, not just the planned endpoints.
    run(['klayout','-b','-r',root/'project/experiments/block_v1/linkclose_geometry.rb',
        '-rd','request='+str(out/'route-inputs.json'),'-rd','geometry='+str(out/'geometry.tsv'),
        '-rd','spec='+str(root/'project/experiments/block_v1/technology-2um-v1.json'),'-rd','report='+str(out/'geometry.json')],'geometry.log')
    check=json.loads((out/'geometry.json').read_text());assert check['passed'] and check['links']==len(inputs['links'])
    (out/'linkclose-route.json').write_text(json.dumps(dict(passed=True,pair=key,links=len(inputs['links']),
        original_route=str(original),original_route_receipt_sha256=sha(original/'receipt.json'),rebound_native=rebinding,geometry=check,
        inputs_sha256=sha(out/'route-inputs.json'),odb_sha256=sha(out/'routed.odb'),def_sha256=sha(out/'routed.def'),geometry_sha256=sha(out/'geometry.tsv'),
        complete_native_acceptance_included=not raw_view,scope='Complete bus on exact repaired native source and independently checked real I/O geometry. tq2/tq3 are electrical experiments prepared in parallel with independent full native acceptance; view receipts grant no DRC/LEC/PG acceptance. Final combination requires separate full acceptance receipts.'),indent=2)+'\n')


def implement(root,out,cpus,run,kind):
    """Upsize measured launch buffers in a copy of sealed GRT; reroute/RCX."""
    from native_escape_finish import FLOW_HASHES
    assert cpus==16 and kind in ('m','s','t')
    platform=Path('/OpenROAD-flow-scripts/flow')
    assert {n:sha(platform/n)for n in FLOW_HASHES}==FLOW_HASHES
    row,accepted,ar,flow,grt=native_source(root,kind)
    probe=out.parent/('linkfix-probe-'+kind)
    pr=json.loads((probe/'receipt.json').read_text());assert pr['passed']
    p=probe/'linkfix-probe.json';assert sha(p)==pr['outputs'][p.name]
    checked=json.loads(p.read_text());assert checked['passed'] and checked['grt_sha256']==sha(grt)
    original=Path(checked['grt_source']);r=json.loads((original/'receipt.json').read_text());assert r['passed']
    assert sha(original/'receipt.json')==checked['grt_receipt_sha256']
    results=out/'flow/results/nangate45'/('bv1_'+flow['top'])/'base';results.mkdir(parents=True)
    copied={}
    for name in ('1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','5_1_grt.odb','5_1_grt.sdc','route.guide','bv1-input-diodes.tsv','bv1-input-delay.tsv'):
        p=grt.parent/name
        if name=='bv1-input-delay.tsv' and not p.exists():continue
        assert sha(p)==r['outputs'][str(p.relative_to(original))]
        shutil.copyfile(p,results/name);copied[name]=sha(p)
    for name in ('pins.json','pins.tcl','input.sdc'):
        assert sha(accepted/name)==ar['outputs'][name]
        shutil.copyfile(accepted/name,out/name)
    # Preserve the immutable source hook inputs. Only the actual repair hook
    # and WORK_HOME change; no synthesis/floorplan/CTS is falsely claimed new.
    assert sha(original/'config.mk')==r['outputs']['config.mk']
    cfg=(original/'config.mk').read_text();assert 'PRE_DETAIL_ROUTE_TCL'not in cfg
    cfg+='\nexport PRE_DETAIL_ROUTE_TCL = '+str(out/'launch-repair.tcl')+'\n'
    (out/'config.mk').write_text(cfg)
    script='global_route -start_incremental\nset b [ord::get_db_block]\nset changed [open {'+str(out/'launch-changes.tsv')+'} w]\n'
    for port,d in sorted(checked['drivers']['grt'].items()):
        script+='set i [$b findInst {'+d['instance']+'}]\n'
        script+='if {$i eq "NULL" || [[$i getMaster] getName] ne {'+d['master']+'}} {error {Measured source driver changed}}\n'
        script+='set old [[$i getMaster] getName]\n$i setDoNotTouch false\n'
        script+='if {![$i swapMaster [[ord::get_db] findMaster BUF_X16]]} {error {Launch swap failed}}\n'
        script+='puts $changed "'+port+'\t[$i getName]\t$old\t[[$i getMaster] getName]"\n'
    script+='''close $changed
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
'''
    for d in checked['drivers']['grt'].values():script+='set_dont_touch [get_cells {'+d['instance']+'}]\n'
    script+='''detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
'''
    (out/'launch-repair.tcl').write_text(script)
    record=dict(passed=False,kind=kind,top=flow['top'],die_um=flow['die_um'],budget=flow['budget'],
        inherited_grt=str(grt),inherited_grt_sha256=sha(grt),probe_receipt_sha256=sha(probe/'receipt.json'),
        qualified_original_source=str(accepted),qualified_original_receipt_sha256=sha(accepted/'receipt.json'),
        inherited_files=copied,stages=[],files={},selected_drivers=checked['drivers']['grt'],
        scope='Experimental copy of original sealed native GRT, measured output buffers upsized to BUF_X16, PG reconnected and placement checked; fresh detail route/fill/finish/RCX required. Original production data immutable; no acceptance transfers.')
    def save():(out/'linkfix-native.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(platform),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    for stage in ('do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage);save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file() and p.stat().st_size
        record['files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    assert sha(grt)==checked['grt_sha256']
    record['passed']=True;save()


def received_source(out,kind):
    folder=out.parent/('linkfix-native-'+kind)
    if kind=='s' and (out.parent/'linkfix-s-finish').exists():folder=out.parent/'linkfix-s-finish'
    if not folder.exists():folder=out.parents[2]/('block-v1-20261029-928/tasks/linkfix-native-'+kind)
    r=json.loads((folder/'receipt.json').read_text());assert r['passed']
    report=folder/'linkfix-native.json';assert sha(report)==r['outputs'][report.name]
    flow=json.loads(report.read_text());assert flow['passed']
    results=folder/'flow/results/nangate45'/('bv1_'+flow['top'])/'base'
    for name,row in flow['files'].items():assert sha(Path(row['path']))==row['sha256']==r['outputs'][str(Path(row['path']).relative_to(folder))]
    return folder,r,flow,results


def accept(root,out,cpus,run,kind):
    from five_macro_receive import physical,drc
    from native_signal_view import export
    from native_logic_projection import export as projection
    from native_formal import inspect
    folder,receipt,flow,results=received_source(out,kind)
    physical(root,out,cpus,run,kind,selected=received_source,sdc_override=folder/'input.sdc')
    drc(root,out,cpus,run,kind,selected=received_source)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    target,view=export(root,out,run,folder,receipt,results,flow['top'],lib)
    before,bp=projection(root,out,run,results/'1_synth_lec.v',lib,flow['top'],'before',constant_functions=True)
    after,ap=projection(root,out,run,target,lib,flow['top'],'after',constant_functions=True)
    (out/'kepler.yml').write_text('format: verilog\ninput_paths:\n - '+str(before)+'\n - '+str(after)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(out/'kepler.log')+'\n')
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    run([binary,'--config',out/'kepler.yml'],'formal.log');formal=inspect((out/'kepler.log').read_text());assert formal['passed']
    # Inspect actual final drivers: a fixed load contract requires actual masters.
    script='read_db {'+str(results/'6_final.odb')+'}\nset b [ord::get_db_block]\nset f [open actual-launch-drivers.tsv w]\n'
    for port in sorted(flow['selected_drivers']):
        script+='set bt [$b findBTerm {'+port+'}]\nset n [$bt getNet]\nset hits 0\n'
        script+='foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {incr hits;set i [$t getInst];if {[[$i getMaster] getName] ne "BUF_X16"} {error {Unexpected launch driver}};puts $f "'+port+'\t[$i getName]\t[[$i getMaster] getName]"}}\nif {$hits!=1} {error {Unexpected driver count}}\n'
    script+='close $f\nwrite_abstract_lef -bloat_occupied_layers candidate.lef\n'
    (out/'launch-drivers.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'launch-drivers.tcl'],'launch-drivers.log')
    (out/'linkfix-accept.json').write_text(json.dumps(dict(passed=True,kind=kind,source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),
        physical=json.loads((out/'five-macro-physical.json').read_text()),drc=json.loads((out/'five-macro-drc.json').read_text()),
        complete_signal_view=view,strict_final_lec=formal,before_projection=bp,after_projection=ap,
        actual_launch_drivers_sha256=sha(out/'actual-launch-drivers.tsv'),scope='Experimental repaired copy only: full native physical, DRC and strict function equivalence. Full-bus route and RC/STA still separate.'),indent=2)+'\n')


def function_group(root,out,cpus):
    """Three independent tail checks need three slots, not an idle 96-CPU node."""
    import os
    from native_node_queue import validate,schedule
    from native_allocation_group import memory_snapshot
    assert cpus==48 and int(os.environ['SLURM_CPUS_PER_TASK'])==48
    manifest=root.parent/'node-queue.json';digest=sha(manifest)
    spec=json.loads(manifest.read_text());validate(spec,out.parents[2])
    assert spec['allocation_cpus']==48 and len(spec['tasks'])==3
    assert {t['mode']for t in spec['tasks']}=={'linkfix-function-'+k for k in 'mts'}
    assert all(t['cpus']==16 and not t['after']for t in spec['tasks'])
    spec=dict(spec,node_cpus=48)
    def measured():
        assert sha(manifest)==digest
        return memory_snapshot()
    owner=dict(job_id=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,worker=str(out),pid=os.getpid())
    result=schedule(spec,digest,out,owner,measured)
    assert result['passed'] and result['allocated_cpus']==48


def function(root,out,cpus,run,kind):
    """Retest the repaired final ODB against the unchanged three-state bench."""
    from five_macro_receive import function as final_function
    from revision300_rtl import sources
    _,_,_,original,_=native_source(root,kind)
    assert sha(sources(root,kind)[2])==original['bench_sha256']
    final_function(root,out,cpus,run,kind,selected=received_source)


def io_view(root,out,cpus,run,kind):
    """Closed actual ODB I/O extraction, without pretending native acceptance."""
    from pin_contract import inspect
    assert cpus==16
    folder,r,flow,results=received_source(out,kind)
    tail=(root/'project/experiments/block_v1/native_physical.tcl').read_text().split('set stream [open physical-input-diodes.tsv w]',1)[1]
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nset block [ord::get_db_block]\n'
    script+='if {[$block getDbUnitsPerMicron]!=2000} {error {Unexpected DBU}}\nset stream [open physical-input-diodes.tsv w]'+tail
    script+='set f [open actual-launch-drivers.tsv w]\n'
    for port in sorted(flow['selected_drivers']):
        script+='set bt [$block findBTerm {'+port+'}]\nset n [$bt getNet]\nset hits 0\n'
        script+='foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {incr hits;set i [$t getInst];if {[[$i getMaster] getName] ne "BUF_X16"} {error {Wrong actual driver}};puts $f "'+port+'\t[$i getName]\t[[$i getMaster] getName]"}}\nif {$hits!=1} {error {Unexpected driver count}}\n'
    script+='close $f\nwrite_abstract_lef -bloat_occupied_layers candidate.lef\n'
    (out/'io-view.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'io-view.tcl'],'io-view.log')
    pins=json.loads((folder/'pins.json').read_text());contract=inspect(pins,(folder/'pins.tcl').read_text(),(out/'physical-pins.tsv').read_text(),2000);assert contract['passed']
    expected=dict(line.split('\t')[:3][::2]for line in(results/'bv1-input-diodes.tsv').read_text().splitlines())
    actual=dict(line.split('\t')for line in(out/'physical-input-diodes.tsv').read_text().splitlines());assert actual==expected and actual
    (out/'linkfix-io-view.json').write_text(json.dumps(dict(passed=True,kind=kind,source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),pin_contract=contract,
        selected_driver_count=len(flow['selected_drivers']),passive_count=len(actual),complete_native_acceptance=False,
        scope='Read-only exact repaired final ODB pin/actual BUF_X16/passive inventory/LEF export only, for independent parallel electrical experiments. No native DRC, STA, PG or LEC qualification is granted.'),indent=2)+'\n')
