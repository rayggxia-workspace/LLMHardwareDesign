"""Independently receive a sealed native candidate, without editing the source.

This cannot qualify twelve-layer RC or final-netlist functionality by itself.
"""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from constraint_readback import audit as boundary_audit
from io_slots import slot,file_sha
from native_sta import inspect as sta_audit
from native_annotation import inspect as annotation_audit
from native_formal import receive as formal_audit


def verify(root,out,cpus,run,top,policy,historical=False,pipeline=None):
    pipeline=pipeline or ('native_pipeline_057.json' if historical else 'native_pipeline.json')
    assert pipeline in ('native_pipeline.json','native_pipeline_057.json','native_pipeline_cap20.json','native_pipeline_cap40.json','native_pipeline_hold5.json','native_pipeline_diode.json','native_pipeline_diode_full.json','native_pipeline_const.json')
    config=json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
    diode=config.get('input_diode_master')=='ANTENNA_X1'
    assert bool(config.get('historical_input_contract',False))==historical
    base=out.parents[2];source=base/config['candidate_run']/('tasks/'+config.get('candidate_task_prefix','native-run-')+top+'-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    proof=base/'block-v1-20261027-066/tasks/native-sta-control'
    control=json.loads((proof/'receipt.json').read_text());assert control['passed']is True
    assert file_sha(proof/'native-sta-control.json')==control['outputs']['native-sta-control.json']
    accepted=json.loads((proof/'native-sta-control.json').read_text())
    assert accepted['positive']['passed']and not accepted['bad_capacitance']['passed']and not accepted['bad_setup']['passed']
    assert len(accepted['report_fault_controls'])==4 and all(not r['passed']for r in accepted['report_fault_controls'].values())
    assert accepted['annotation']['positive']['passed']and not accepted['annotation']['missing_input_rc']['passed']
    relative=Path('flow/results/nangate45')/('bv1_'+top+'_'+policy)/'base'
    results=source/relative;inputs={}
    with slot(base):
        for name in ['6_final.odb','6_final.sdc','6_final.v','6_final.spef','6_final.def']:
            path=results/name;digest=file_sha(path)
            assert digest==receipt['outputs'][(relative/name).as_posix()]
            inputs[str(path)]=digest
    (out/'input-sha256.json').write_text(json.dumps(inputs,indent=2)+'\n')
    # Each OpenROAD process reloads actual files; no resynthesis or repair.
    def script(name,body):
        (out/(name+'.tcl')).write_text(body)
        run(['openroad','-no_init','-exit',name+'.tcl'],name+'.log')
    prefix=''.join('set ::env('+key+') {'+str(results/name)+'}\n'for key,name in
        [('BV1_ODB','6_final.odb'),('BV1_SDC','6_final.sdc'),('BV1_SPEF','6_final.spef')])
    script('independent-sta',prefix+'source {'+str(root/'project/experiments/block_v1/native_sta.tcl')+'}\n')
    timing=sta_audit(out)
    coverage=annotation_audit(out)
    script('independent-physical',prefix+'source {'+str(root/'project/experiments/block_v1/native_physical.tcl')+'}\n')
    script('independent-drivers',prefix+'read_db $::env(BV1_ODB)\n'
           +'set ::env(BV1_UNDRIVEN_REPORT) {used-signal-drivers.tsv}\n'
           +'source {'+str(root/'project/experiments/block_v1/native_undriven.tcl')+'}\n')
    from native_driver_report import inspect as driver_audit
    drivers=driver_audit((out/'used-signal-drivers.tsv').read_text())
    summary={}
    for line in(out/'physical-summary.tsv').read_text().splitlines():
        name,*values=line.split('\t');assert name not in summary;summary[name]=values
    scale=int(summary['dbu'][0]);assert scale==2000
    masters=[];active=0;physical=0;active_count=0;physical_count=0
    for line in(out/'physical-masters.tsv').read_text().splitlines():
        name,kind,signal,w,h,count=line.split('\t');area=int(w)*int(h)*int(count)/scale**2
        row=dict(master=name,type=kind,has_signal_term=signal=='1',count=int(count),area_um2=area);masters.append(row)
        if signal=='1':active+=area;active_count+=int(count)
        else:physical+=area;physical_count+=int(count)
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text());leaf=budget['leaves'][top]
    prep=base/config['preparation_run']/'tasks/native-prepare'
    bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    pins_path=prep/(top+'-'+policy)/'pins.json'
    flow_config=prep/(top+'-'+policy)/'config.mk'
    assert file_sha(flow_config)==bound['outputs'][str(flow_config.relative_to(prep))]
    if config.get('repair_variant'):
        from native_reroute import checked_config
        flow_config=checked_config(source,receipt,flow_config,margin=config.get('cap_margin',20),hold_margin=config.get('hold_margin_ns'),diode=diode)
    assert file_sha(pins_path)==bound['outputs'][str(pins_path.relative_to(prep))]
    pins=json.loads(pins_path.read_text())['pins'];wanted={p['pin']:p for p in pins};got={}
    for line in(out/'physical-pins.tsv').read_text().splitlines():
        name,layer,*coordinates=line.split('\t');assert name not in got;got[name]=(layer,list(map(int,coordinates)))
    pins_equal=set(got)==set(wanted)
    for name,pin in wanted.items():
        x,y=pin['xy_um'];w,h=pin['size_um']
        expected=[round(v*scale)for v in [x-w/2,y-h/2,x+w/2,y+h/2]]
        pins_equal &= got.get(name)==('metal10',expected)
    boundary=boundary_audit((out/'constraints-readback.sdc').read_text(),pins,budget)
    formal=formal_audit(source,receipt,results,top,prep,logic_context=(root,out,run)if diode else None)
    layers=summary['routing_layers'][0].split(',')
    die=list(map(int,summary['die']));w,h=leaf['die_um']
    core=list(map(int,summary['core']))
    checks=dict(timing=timing['passed'],rc_coverage=coverage['passed'],mapped_to_final_lec=formal['passed'],unplaced_zero=summary['unplaced']==['0'],
        all_pg_iterms_correct=summary['incorrect_pg_iterms']==['0']and int(summary['pg_iterm_count'][0])>0,
        pg_vdd=summary['pg_VDD']==['1'],pg_vss=summary['pg_VSS']==['1'],
        open_signal_inputs_zero=summary['open_signal_inputs']==['0'],exact_prefabricated_m10_pins=pins_equal,
        undriven_used_signal_nets_zero=drivers['passed'],
        exact_native_layers=layers==['metal%d'%i for i in range(1,11)],
        same_die=die==[0,0,round(w*scale),round(h*scale)],
        core_inside_die=die[0]<core[0]<core[2]<die[2]and die[1]<core[1]<core[3]<die[3],
        active_cell_area_within_cap=0<active<=leaf['max_stdcell_area_um2'])
    if diode:
        inserted=results/'bv1-input-diodes.tsv'
        assert file_sha(inserted)==receipt['outputs'][str(inserted.relative_to(source))]
        rows=[line.split('\t')for line in inserted.read_text().splitlines()]
        expected={r[0]:r[2]for r in rows}
        got=dict(line.split('\t')for line in(out/'physical-input-diodes.tsv').read_text().splitlines())
        checks['all_input_diodes_preserved_on_exact_root_nets']=bool(expected)and got==expected and len(rows)==len(expected)
    # Build GDS in a new output tree using explicit do-targets only. Source
    # final DEF and all previous-run files stay unchanged.
    folder=out/'gds-flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base';folder.mkdir(parents=True)
    # Explicit do-gds does not run the ordinary flow directory setup target.
    # Keep the independent export self-contained without invoking synthesis.
    for category in ['logs','reports','objects']:
        (out/'gds-flow'/category/'nangate45'/('bv1_'+top+'_'+policy)/'base').mkdir(parents=True,exist_ok=True)
    with slot(base):shutil.copyfile(results/'6_final.def',folder/'6_final.def')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(flow_config),
             'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES='+str(cpus),'do-gds']
    run(command,'independent-gds.log')
    gds=folder/'6_final.gds';assert gds.is_file()
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'native-drc.lyrdb'),'-r',str(deck)],'independent-drc.log')
    database=ET.parse(out/'native-drc.lyrdb').getroot();items=database.find('items');assert items is not None
    from native_drc import summarize
    drc_summary=summarize(out/'native-drc.lyrdb')
    assert drc_summary['total_items']==len(items)
    (out/'native-drc-summary.json').write_text(json.dumps(drc_summary,indent=2)+'\n')
    checks['independent_native_drc_zero']=len(items)==0
    reports=source/'flow/reports/nangate45'/('bv1_'+top+'_'+policy)/'base'
    drc=reports/'5_route_drc.rpt';assert file_sha(drc)==receipt['outputs'][str(drc.relative_to(source))]
    checks['native_drt_drc_zero']=not drc.read_text().strip()
    # Every source input is checked again after independent readers finish.
    with slot(base):assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    result=dict(schema='block-v1-native-physical-receiver/1',passed=all(checks.values()),checks=checks,top=top,policy=policy,
        timing=timing,rc_coverage=coverage,boundary=boundary,mapped_to_final_lec=formal,source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
        used_signal_driver_audit=drivers,used_signal_driver_report_sha256=file_sha(out/'used-signal-drivers.tsv'),
        active_cell_count=active_count,active_area_um2=active,physical_only_cell_count=physical_count,physical_only_area_um2=physical,
        all_instance_area_um2=active+physical,die_area_um2=w*h,masters=masters,
        core_bbox_dbu=core,core_area_um2=(core[2]-core[0])*(core[3]-core[1])/scale**2,
        independent_drc_items=len(items),independent_drc_categories=drc_summary['categories'],
        independent_drc_summary_sha256=file_sha(out/'native-drc-summary.json'),
        native_deck_sha256=file_sha(deck),gds_sha256=file_sha(gds),
        rc_coverage_qualified=coverage['passed'],exact_final_function_qualified=False,twelve_layer_qualified=False,
        historical_input_contract=historical,pipeline=pipeline,
        qualified_hard_macro=False,scope='Native final ODB/SDC/SPEF physical gates; RC coverage, final function, macro views and twelve-layer research qualification remain separate')
    (out/'native-physical-receiver.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Independent native physical gate failed; preserve candidate and reports'
