"""Independent issue130 actual-final reception, with fresh local controls.

The physical/DRC gates derive from the existing reviewed receiver. This version
uses its own controls and explicit source callback, never parent run selectors.
"""
import json
from pathlib import Path
import shutil

def receiver_audit(folder,out,results,run,plan):
    from io_slots import file_sha
    expected={}
    for line in (results/'feed-input-receivers.tsv').read_text().splitlines():
        name,port,root,internal,old_loads,x,y=line.split('\t');assert port not in expected
        expected[port]=dict(name=name,root=root,internal=internal,old_loads=int(old_loads))
    wanted={p['pin'] for p in plan if p['direction']=='input' and p['pin']!='clk'}
    assert set(expected)==wanted
    script='read_db {'+str(results/'6_final.odb')+'}\n'
    script+='''set block [ord::get_db_block]
set f [open input-receivers-actual.tsv w]
foreach port [$block getBTerms] {
 if {[$port getSigType] in {POWER GROUND} || [$port getIoType] ne "INPUT" || [$port getName] eq "clk"} {continue}
 set net [$port getNet];set receiver {};set diodes 0
 foreach term [$net getITerms] {
  set inst [$term getInst];set master [[$inst getMaster] getName]
  if {$master eq "ANTENNA_X1" && [[$term getMTerm] getName] eq "A"} {incr diodes;continue}
  if {$master ne "BUF_X8" || [[$term getMTerm] getName] ne "A" || $receiver ne ""} {error "Unexpected input-root load"}
  set receiver $inst
 }
 if {$receiver eq "" || $diodes!=1} {error "Incomplete actual input receiver/protection"}
 set internal [[$receiver findITerm Z] getNet]
 if {$internal eq "NULL" || [llength [$internal getITerms]]<2} {error "Disconnected receiver output"}
 puts $f "[$port getName]\\t[$receiver getName]\\t[$net getName]\\t[$internal getName]\\t[$receiver getLocation]"
}
close $f
'''
    (out/'receivers.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'receivers.tcl'],'receivers.log')
    actual={}
    for line in (out/'input-receivers-actual.tsv').read_text().splitlines():
        port,name,root,internal,location=line.split('\t');assert port not in actual
        assert (name,root,internal)==tuple(expected[port][k] for k in ['name','root','internal'])
        actual[port]=dict(name=name,location_dbu=list(map(int,location.split())))
    assert set(actual)==wanted
    return dict(passed=True,count=len(actual),master='BUF_X8',every_root_exactly_receiver_and_diode=True,
        declared_sha256=file_sha(results/'feed-input-receivers.tsv'),actual_sha256=file_sha(out/'input-receivers-actual.tsv'))

def fresh_controls(root,out,run):
    """Fresh actual native controls, not inherited pass flags."""
    from native_sta import fixture as sta_fixture
    from native_formal import fixture as lec_fixture
    from native_projection_control import verify as projection
    from revision300_constraints_control import control as boundary
    base=out/'controls';base.mkdir()
    for mode in ['sta','lec','projection-0','projection-1','boundary']:
        p=base/mode;p.mkdir()
        execute=lambda cmd,log:run(cmd,'control-'+mode+'-'+log)
        if mode=='sta':sta_fixture(root,p,execute)
        elif mode=='lec':lec_fixture(root,p,execute)
        elif mode.startswith('projection'):projection(root,p,1,execute,int(mode[-1]))
        else:boundary(root,p,16,execute)
    report=json.loads((base/'boundary/revision300-constraints-control.json').read_text())
    assert report['passed'];return report

def physical(root,out,cpus,run,kind,selected=None):
    from io_slots import file_sha
    from native_sta import inspect as sta_audit
    from native_annotation import inspect as annotation_audit
    from native_passive_endpoint import audit as passive_audit
    from native_driver_report import inspect as driver_audit
    from constraint_readback import audit as constraints
    assert cpus==16
    receive=source if selected is None else selected
    folder,r,flow,results=receive(out,kind)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    controls_report=fresh_controls(root,out,run)
    prefix=''.join('set ::env('+k+') {'+str(results/name)+'}\n' for k,name in [('BV1_ODB','6_final.odb'),('BV1_SDC','6_final.sdc'),('BV1_SPEF','6_final.spef')])
    if selected is not None:
        prefix+='rename write_sdc bv1_original_write_sdc\nproc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}\n'
    for name,body in [('sta','source {'+str(root/'project/experiments/block_v1/native_sta.tcl')+'}\n'),
                      ('physical','source {'+str(root/'project/experiments/block_v1/native_physical.tcl')+'}\n'),
                      ('drivers','read_db $::env(BV1_ODB)\nset ::env(BV1_UNDRIVEN_REPORT) {used-signal-drivers.tsv}\nsource {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n')]:
        (out/(name+'.tcl')).write_text(prefix+body);run(['openroad','-no_init','-exit',str(out/(name+'.tcl'))],name+'.log')
    inventory={}
    for line in (out/'passive-inventory.tsv').read_text().splitlines():
        name,master,typ,direction,net=line.split('\t');assert name not in inventory
        inventory[name]=dict(master=master,type=typ,direction=direction,net=net,pin=name.rsplit('/',1)[1])
    timing=passive_audit(out,out/'timed-endpoints',lib.read_text(),inventory)
    annotation=annotation_audit(out);drivers=driver_audit((out/'used-signal-drivers.tsv').read_text())
    summary={}
    for line in (out/'physical-summary.tsv').read_text().splitlines():
        k,*values=line.split('\t');assert k not in summary;summary[k]=values
    dbu=int(summary['dbu'][0]);assert dbu==2000
    from pin_contract import inspect as pin_audit
    pin_plan=json.loads((folder/'pins.json').read_text());plan=pin_plan['pins']
    assert file_sha(folder/'pins.tcl')==r['outputs']['pins.tcl']
    pin_contract=pin_audit(pin_plan,(folder/'pins.tcl').read_text(),(out/'physical-pins.tsv').read_text(),dbu)
    if pin_contract['passed']:
        from pin_contract_controls import exercise
        controls=exercise(pin_plan,(folder/'pins.tcl').read_text(),(out/'physical-pins.tsv').read_text())
        assert controls['passed']
        pin_contract['software_controls']={k:controls[k]for k in ('negative_controls','precise_serialization_preserves_original_coordinates','comparator_sha256','scope')}
    exact=pin_contract['passed']
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    if selected is not None:
        from revision300_constraint_readback import audit as precise_constraints
        budget=flow['budget']
        serialization=controls_report['serialization']
        constraints=lambda text,pins,approved: precise_constraints(text,pins,approved,serialization)
    boundary=constraints((out/'constraints-readback.sdc').read_text(),plan,budget)
    receivers=receiver_audit(folder,out,results,run,plan) if flow.get('repair') else None
    masters=[];active=0;physical_area=0
    for line in (out/'physical-masters.tsv').read_text().splitlines():
        name,typ,signal,w,h,count=line.split('\t');area=int(w)*int(h)*int(count)/dbu**2
        masters.append(dict(master=name,type=typ,signal=signal=='1',count=int(count),area_um2=area))
        if signal=='1':active+=area
        else:physical_area+=area
    expected=dict(line.split('\t')[:3][::2] for line in (results/'bv1-input-diodes.tsv').read_text().splitlines())
    observed=dict(line.split('\t') for line in (out/'physical-input-diodes.tsv').read_text().splitlines())
    checks=dict(fixed_input_receivers=(receivers is None or receivers['passed']),all_real_timed_endpoints=timing['passed'],rc_coverage=annotation['passed'],
                used_signal_drivers=drivers['passed'],exact_m10_pin_geometry=exact,
                exact_input_diode_roots=bool(expected) and expected==observed,
                all_pg_iterms_correct=summary['incorrect_pg_iterms']==['0'] and int(summary['pg_iterm_count'][0])>0,
                pg_vdd=summary['pg_VDD']==['1'],pg_vss=summary['pg_VSS']==['1'],
                all_placed=summary['unplaced']==['0'],no_open_signal_inputs=summary['open_signal_inputs']==['0'],
                exact_ten_layers=summary['routing_layers']==[','.join('metal'+str(i) for i in range(1,11))],
                exact_die=list(map(int,summary['die']))==[0,0,round(flow['die_um'][0]*dbu),round(flow['die_um'][1]*dbu)])
    receive(out,kind)
    result=dict(passed=all(checks.values()),top=flow['top'],checks=checks,timing=timing,rc_coverage=annotation,
                used_drivers=drivers,boundary=boundary,pin_contract=pin_contract,fixed_input_receivers=receivers,masters=masters,active_area_um2=active,
                physical_only_area_um2=physical_area,die_um=flow['die_um'],source=str(folder),
                source_receipt_sha256=file_sha(folder/'receipt.json'),exact_final_function_qualified=False,
                independent_full_deck_drc_qualified=False,qualified_hard_macro=False,
                scope='Actual final ODB/SDC/SPEF independent full endpoint/electrical/PG/connectivity/pin/RC reception; function/full-deck/strict LEC separate')
    (out/'five-macro-physical.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def drc(root,out,cpus,run,kind,selected=None):
    from io_slots import file_sha,slot
    from native_drc import summarize
    assert cpus==16
    receive=source if selected is None else selected
    folder,r,flow,results=receive(out,kind);nickname='bv1_'+flow['top']
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def before.def\n'
    script+='if {[llength [info commands ::drt::check_drc_cmd]] != 1} {error "Missing whole-chip DRC API"}\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
    (out/'native-drc.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'native-drc.tcl')],'native-drc.log')
    assert file_sha(out/'before.def')==file_sha(out/'after.def')
    # A route-stage zero is insufficient: reject actual final whole-chip
    # geometry violations before spending hours on the independent GDS deck.
    assert not (out/'native-whole-drc.rpt').read_text().strip(), 'Final whole-chip native DRC violations'
    target=out/'gds-flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    # Both queued and independent gate layouts keep their immediate parent in
    # the owned issue130 runtime. Never derive the common worktrees directory.
    with slot(out.parent):shutil.copyfile(results/'6_final.def',target/'6_final.def')
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    gds=target/'6_final.gds';deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full-deck.lyrdb'),'-r',str(deck)],'full-deck.log')
    summary=summarize(out/'full-deck.lyrdb');native=(out/'native-whole-drc.rpt').read_text()
    receive(out,kind)
    result=dict(passed=summary['total_items']==0 and not native.strip(),top=flow['top'],source=str(folder),
                source_receipt_sha256=file_sha(folder/'receipt.json'),native_report=native,full_deck=summary,
                deck_sha256=file_sha(deck),gds=dict(path=str(gds),sha256=file_sha(gds),bytes=gds.stat().st_size),
                qualified_hard_macro=False,scope='Actual final full-chip native DRC and complete unmodified FreePDK45 GDS deck; no exclusions')
    (out/'five-macro-drc.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']

