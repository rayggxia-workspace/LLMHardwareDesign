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


def verify(root,out,cpus,run,top,policy):
    config=json.loads((root/'project/experiments/block_v1/native_pipeline.json').read_text())
    base=out.parents[2];source=base/config['candidate_run']/('tasks/native-run-'+top+'-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    proof=base/'block-v1-20261027-063/tasks/native-sta-control'
    control=json.loads((proof/'receipt.json').read_text());assert control['passed']is True
    assert file_sha(proof/'native-sta-control.json')==control['outputs']['native-sta-control.json']
    accepted=json.loads((proof/'native-sta-control.json').read_text())
    assert accepted['positive']['passed']and not accepted['bad_capacitance']['passed']and not accepted['bad_setup']['passed']
    assert len(accepted['report_fault_controls'])==4 and all(not r['passed']for r in accepted['report_fault_controls'].values())
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
    layers=summary['routing_layers'][0].split(',')
    die=list(map(int,summary['die']));w,h=leaf['die_um']
    checks=dict(timing=timing['passed'],rc_coverage=coverage['passed'],unplaced_zero=summary['unplaced']==['0'],
        all_pg_iterms_correct=summary['incorrect_pg_iterms']==['0']and int(summary['pg_iterm_count'][0])>0,
        pg_vdd=summary['pg_VDD']==['1'],pg_vss=summary['pg_VSS']==['1'],
        open_signal_inputs_zero=summary['open_signal_inputs']==['0'],exact_prefabricated_m10_pins=pins_equal,
        exact_native_layers=layers==['metal%d'%i for i in range(1,11)],
        same_die=die==[0,0,round(w*scale),round(h*scale)],
        active_cell_area_within_cap=0<active<=leaf['max_stdcell_area_um2'])
    # Build GDS in a new output tree using explicit do-targets only. Source
    # final DEF and all previous-run files stay unchanged.
    folder=out/'gds-flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base';folder.mkdir(parents=True)
    with slot(base):shutil.copyfile(results/'6_final.def',folder/'6_final.def')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(prep/(top+'-'+policy)/'config.mk'),
             'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES='+str(cpus),'do-gds']
    run(command,'independent-gds.log')
    gds=folder/'6_final.gds';assert gds.is_file()
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'native-drc.lyrdb'),'-r',str(deck)],'independent-drc.log')
    database=ET.parse(out/'native-drc.lyrdb').getroot();items=database.find('items');assert items is not None
    checks['independent_native_drc_zero']=len(items)==0
    reports=source/'flow/reports/nangate45'/('bv1_'+top+'_'+policy)/'base'
    drc=reports/'5_route_drc.rpt';assert file_sha(drc)==receipt['outputs'][str(drc.relative_to(source))]
    checks['native_drt_drc_zero']=not drc.read_text().strip()
    # Every source input is checked again after independent readers finish.
    with slot(base):assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    result=dict(schema='block-v1-native-physical-receiver/1',passed=all(checks.values()),checks=checks,top=top,policy=policy,
        timing=timing,rc_coverage=coverage,boundary=boundary,source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
        active_cell_count=active_count,active_area_um2=active,physical_only_cell_count=physical_count,physical_only_area_um2=physical,
        all_instance_area_um2=active+physical,die_area_um2=w*h,masters=masters,
        independent_drc_items=len(items),native_deck_sha256=file_sha(deck),gds_sha256=file_sha(gds),
        rc_coverage_qualified=coverage['passed'],exact_final_function_qualified=False,twelve_layer_qualified=False,
        qualified_hard_macro=False,scope='Native final ODB/SDC/SPEF physical gates; RC coverage, final function, macro views and twelve-layer research qualification remain separate')
    (out/'native-physical-receiver.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Independent native physical gate failed; preserve candidate and reports'
