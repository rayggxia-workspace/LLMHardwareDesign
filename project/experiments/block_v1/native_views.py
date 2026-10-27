"""Source-bound view generation, separately gated from model qualification.

OpenSTA's model has scalar input setup/hold and omits input wire resistance.
Fresh successful view readback therefore does not prove flat/abstract timing
equivalence or qualify a hard macro. Those gates remain explicit and separate.
"""
import json
from pathlib import Path


def received_contract(physical,source,source_receipt_sha256,pipeline,top,policy):
    """Reject partial, failed, historical or different-source physical proofs."""
    required={'timing','rc_coverage','mapped_to_final_lec','unplaced_zero',
              'all_pg_iterms_correct','pg_vdd','pg_vss','open_signal_inputs_zero',
              'exact_prefabricated_m10_pins','undriven_used_signal_nets_zero',
              'exact_native_layers','same_die','core_inside_die',
              'active_cell_area_within_cap','independent_native_drc_zero','native_drt_drc_zero'}
    checks=physical['checks']
    assert physical['passed']is True and required<=set(checks)
    assert all(value is True for value in checks.values())
    assert physical['historical_input_contract']is False
    assert (physical['top'],physical['policy'],physical['pipeline'])==(top,policy,pipeline)
    assert physical['source']==str(source)
    assert physical['source_receipt_sha256']==source_receipt_sha256
    assert physical['independent_drc_items']==0 and physical['rc_coverage_qualified']is True
    assert physical['mapped_to_final_lec']['passed']is True


def final_function_contract(proof,source,source_receipt_sha256,policy,netlist_sha256):
    """Bind the real, complete final T6K scoreboard to this physical source."""
    assert proof['schema']=='block-v1-native-final-function/1'and proof['passed']is True
    assert (proof['top'],proof['policy'],proof['pipeline'])==('transaction6k',policy,'native_pipeline_escape.json')
    assert proof['source']==str(source)and proof['source_receipt_sha256']==source_receipt_sha256
    assert proof['original_flow_netlist_sha256']==netlist_sha256
    formal=proof['formal'];assert formal['passed']is True and all(v is True for v in formal['checks'].values())
    assert formal['full_final_netlist_sha256']==netlist_sha256
    assert formal['physical_functional_view']['full_view_sha256']==proof['final_netlist_sha256']
    runs=proof['initial_state_runs'];assert set(runs)=={'all-ones','random-121','random-122'}
    reference=None
    for name,initial,seed in [('all-ones',1,121),('random-121',2,121),('random-122',2,122)]:
        row=runs[name];assert row['initial_mode']==initial and row['runtime_seed']==seed
        result=row['scoreboard'];assert result['passed']is True and result['seed']==1212026102 and result['transactions']==242
        assert all(type(result[k])is int and result[k]>0 for k in ['cycles','assertions'])
        if reference is None:reference=result
        assert result==reference


def library_interface_control(root,base):
    """Bind the actual installed-tool scope/bus proof, not timing accuracy."""
    from io_slots import file_sha
    control=base/'block-v1-20261027-145/tasks/native-timing-model-probe-group'
    bound=json.loads((control/'receipt.json').read_text())
    assert bound['passed']is True and bound['mode']=='native-timing-model-probe-group'and bound['cpus']==16
    path=control/'native-timing-model-probe-group.json'
    assert file_sha(path)==bound['outputs'][path.name]
    group=json.loads(path.read_text());assert group['passed']is True
    assert len(group['children'])==2 and all(c['passed']is True and c['returncode']==0 for c in group['children'])
    assert {c['mode']for c in group['children']}=={'native-timing-model-probe-a','native-timing-model-probe-c'}
    script='project/experiments/block_v1/native_lib_pins.tcl';digest=file_sha(root/script)
    assert bound['inputs'][script]==digest
    tools={p:h for p,h in bound['tool_hashes'].items()if Path(p).name=='openroad'}
    assert len(tools)==1 and all(file_sha(Path(p))==h for p,h in tools.items())
    reports={}
    for child in group['children']:
        folder=control.parent/child['mode'];receipt=folder/'receipt.json'
        assert file_sha(receipt)==child['receipt_sha256']
        accepted=json.loads(receipt.read_text())
        assert accepted['passed']is True and accepted['mode']==child['mode']and accepted['cpus']==8
        assert accepted['inputs'][script]==digest
        report=folder/'native-timing-model-probe.json'
        assert file_sha(report)==child['proof_sha256']==accepted['outputs'][report.name]
        result=json.loads(report.read_text())
        assert result['passed']is True and all(v is True for v in result['checks'].values())
        assert result['policy']==child['mode'][-1].upper()and result['lib_interface_script_sha256']==digest
        assert result['observed_signal_pin_count']==result['pin_count']and result['typed_bus_count']>0
        assert not result['missing_pins']and not result['extra_pins']and not result['wrong_directions']
        assert file_sha(folder/'lib-buses.tsv')==result['typed_bus_metadata_sha256']
        reports[result['policy']]=dict(receipt_sha256=file_sha(receipt),report_sha256=file_sha(report))
    return dict(group_receipt_sha256=file_sha(control/'receipt.json'),group_report_sha256=file_sha(path),
                lib_interface_script_sha256=digest,actual_openroad_sha256=tools,children=reports,
                scope='Actual installed-tool scoped lib-pin and typed bus readback only; no boundary accuracy qualification')


def interface(folder,pins,leaf,top,library):
    """Inspect native-tool readback of the actual generated Liberty and LEF."""
    expected={p['pin']:p for p in pins};terms={};boxes={};pg={};lib={};summary={};obs=set();seen=set();lib_seen=set()
    for line in(folder/'lef-interface.tsv').read_text().splitlines():
        fields=line.split('\t');kind=fields.pop(0)
        if kind=='term':
            name,direction,sigtype=fields;assert name not in seen;seen.add(name)
            if sigtype in ('POWER','GROUND'):pg[name]=sigtype
            else:terms[name]=direction.lower()
        elif kind=='box':
            name,layer,*coords=fields;assert len(coords)==4
            boxes.setdefault(name,[]).append((layer,list(map(int,coords))))
        elif kind=='obstruction':
            layer,*coords=fields;assert len(coords)==4
            assert all(-2000<=int(v)<=max(leaf['die_um'])*2000+2000 for v in coords)
            obs.add(layer)
        else:
            assert kind in ('width','height')and kind not in summary and len(fields)==1
            summary[kind]=int(fields[0])
    for line in(folder/'lib-interface.tsv').read_text().splitlines():
        full,direction=line.split('\t');prefix=library+'/'+top+'/'
        assert full.startswith(prefix);name=full[len(prefix):];assert name not in lib_seen;lib_seen.add(name)
        if name not in ('VDD','VSS'):lib[name]=direction.lower()
    geometry_equal=set(terms)==set(expected)
    for name,pin in expected.items():
        x,y=pin['xy_um'];w,h=pin['size_um']
        wanted=[round(v*2000)for v in [x-w/2,y-h/2,x+w/2,y+h/2]]
        geometry_equal &= boxes.get(name)==[('metal10',wanted)]
    directions={name:p['direction'].lower()for name,p in expected.items()}
    source_pg={}
    for line in(folder/'source-pg-pins.tsv').read_text().splitlines():
        name,layer,*coords=line.split('\t');assert name in ('VDD','VSS')and len(coords)==4
        source_pg.setdefault(name,set()).add((layer,tuple(map(int,coords))))
    pg_equal=set(source_pg)=={'VDD','VSS'}and all(source_pg[n]and source_pg[n]=={(l,tuple(c))for l,c in boxes.get(n,[])}for n in source_pg)
    checks=dict(nonempty_interface=bool(expected),lef_directions=terms==directions,lib_directions=lib==directions,
        exact_signal_pin_geometry=geometry_equal,clock_is_input=terms.get('clk')==lib.get('clk')=='input',
        exact_full_footprint=summary==dict(width=round(leaf['die_um'][0]*2000),height=round(leaf['die_um'][1]*2000)),
        native_supply_pins=pg=={'VDD':'POWER','VSS':'GROUND'},
        exact_source_supply_geometry=pg_equal,no_unresolved_boxes=set(boxes)<=seen,
        occupied_native_layers_obstructed={'metal%d'%i for i in range(1,11)}<=obs,
        no_new_layer_obstructions=obs<={'metal%d'%i for i in range(1,11)}|{'via%d'%i for i in range(1,10)})
    return dict(passed=all(checks.values()),checks=checks,signal_pin_count=len(expected),
        supply_pins=pg,obstruction_layers=sorted(obs))


def generate(root,out,cpus,run,top,policy,pipeline='native_pipeline.json'):
    from io_slots import file_sha,slot
    assert top in ('shared109','transaction6k')and policy in ('A','C')and cpus>=8
    assert pipeline in ('native_pipeline.json','native_pipeline_cap20.json','native_pipeline_cap40.json','native_pipeline_hold5.json','native_pipeline_diode.json',
                        'native_pipeline_const_protected.json','native_pipeline_viaonly.json','native_pipeline_escape.json')
    if pipeline=='native_pipeline_const_protected.json':assert top=='shared109'
    if pipeline in ('native_pipeline_viaonly.json','native_pipeline_escape.json'):assert top=='transaction6k'
    base=out.parents[2];config=json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
    interface_control=library_interface_control(root,base)if pipeline in ('native_pipeline_const_protected.json','native_pipeline_viaonly.json','native_pipeline_escape.json')else None
    api=base/'block-v1-20261027-073/tasks/native-formal-control'
    control=json.loads((api/'receipt.json').read_text());assert control['passed']is True
    assert file_sha(api/'view-api.log')==control['outputs']['view-api.log']
    receiver=base/config['receiver_run']/('tasks/'+config.get('receiver_task_prefix','native-receive-')+top+'-'+policy.lower())
    accepted=json.loads((receiver/'receipt.json').read_text());assert accepted['passed']is True
    proof=receiver/'native-physical-receiver.json';assert file_sha(proof)==accepted['outputs'][proof.name]
    physical=json.loads(proof.read_text())
    source=base/config['candidate_run']/('tasks/'+config.get('candidate_task_prefix','native-run-')+top+'-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    received_contract(physical,source,file_sha(source/'receipt.json'),pipeline,top,policy)
    relative=Path('flow/results/nangate45')/('bv1_'+top+'_'+policy)/'base';results=source/relative
    inputs={}
    with slot(base):
        for name in ['6_final.odb','6_final.sdc','6_final.spef','6_final.v','6_final.def']:
            path=results/name;digest=file_sha(path);assert digest==receipt['outputs'][(relative/name).as_posix()]
            inputs[str(path)]=digest
    function_control=None
    if pipeline=='native_pipeline_escape.json':
        function=base/config['receiver_run']/('tasks/native-escape-final-transaction6k-'+policy.lower())
        accepted_function=json.loads((function/'receipt.json').read_text())
        assert accepted_function['passed']is True and accepted_function['mode']=='native-escape-final-transaction6k-'+policy.lower()
        fp=function/'native-final-function.json';assert file_sha(fp)==accepted_function['outputs'][fp.name]
        received_function=json.loads(fp.read_text())
        final_function_contract(received_function,source,file_sha(source/'receipt.json'),policy,inputs[str(results/'6_final.v')])
        driver=root/'project/experiments/block_v1/test_transaction.cpp'
        assert file_sha(driver)==received_function['driver_sha256']==accepted_function['inputs'][str(driver.relative_to(root))]
        function_control=dict(path=str(function),receipt_sha256=file_sha(function/'receipt.json'),proof_sha256=file_sha(fp))
    library='BV1_'+top+'_'+policy
    platform='/OpenROAD-flow-scripts/flow/platforms/nangate45'
    text='set_thread_count %d\nread_liberty {%s/lib/NangateOpenCellLibrary_typical.lib}\n'%(cpus,platform)
    for command,name in [('read_db','6_final.odb'),('read_sdc','6_final.sdc'),('read_spef','6_final.spef')]:
        text+=command+' {'+str(results/name)+'}\n'
    text+='''set stream [open source-pg-pins.tsv w]
foreach term [[ord::get_db_block] getBTerms] {
  if {[$term getSigType] ni {POWER GROUND}} {continue}
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      if {[$box isVia]} {error "Unsupported via in source supply port"}
      puts $stream "[$term getName]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
    }
  }
}
close $stream
'''
    text+='set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
    text+='write_timing_model -library_name '+library+' -cell_name '+top+' candidate.lib\n'
    text+='write_abstract_lef -bloat_occupied_layers candidate.lef\n'
    (out/'generate-views.tcl').write_text(text)
    run(['openroad','-no_init','-exit','generate-views.tcl'],'generate-views.log')
    text='read_liberty candidate.lib\nread_lef {'+platform+'/lef/NangateOpenCellLibrary.tech.lef}\nread_lef candidate.lef\n'
    text+='set wanted_master {'+top+'}\nset wanted_library {'+library+'}\n'
    text+='set lib_interface_script {'+str(root/'project/experiments/block_v1/native_lib_pins.tcl')+'}\n'
    text+='source {'+str(root/'project/experiments/block_v1/native_views.tcl')+'}\n'
    (out/'readback-views.tcl').write_text(text)
    run(['openroad','-no_init','-exit','readback-views.tcl'],'readback-views.log')
    prep=base/config['preparation_run']/'tasks/native-prepare';bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    path=prep/(top+'-'+policy)/'pins.json';assert file_sha(path)==bound['outputs'][str(path.relative_to(prep))]
    pins=json.loads(path.read_text())['pins'];budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    received=interface(out,pins,budget['leaves'][top],top,library)
    gds=receiver/'gds-flow/results/nangate45'/('bv1_'+top+'_'+policy)/'base/6_final.gds'
    assert file_sha(gds)==physical['gds_sha256']==accepted['outputs'][str(gds.relative_to(receiver))]
    with slot(base):assert all(file_sha(Path(path))==digest for path,digest in inputs.items())
    record=dict(schema='block-v1-native-view-generation/1',passed=received['passed'],top=top,policy=policy,
        interface=received,source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
        physical_receiver=str(receiver),physical_receiver_sha256=file_sha(proof),
        physical_receiver_receipt_sha256=file_sha(receiver/'receipt.json'),pipeline=pipeline,
        pipeline_file_sha256=file_sha(root/'project/experiments/block_v1'/pipeline),
        generator_sha256=file_sha(Path(__file__)),readback_script_sha256=file_sha(root/'project/experiments/block_v1/native_views.tcl'),
        lib_interface_script_sha256=file_sha(root/'project/experiments/block_v1/native_lib_pins.tcl'),
        typed_bus_metadata_sha256=file_sha(out/'lib-buses.tsv'),library_interface_control=interface_control,inputs=inputs,
        actual_model_api_help_sha256=file_sha(api/'view-api.log'),
        views={name:dict(path=str(out/name),sha256=file_sha(out/name))for name in ['candidate.lib','candidate.lef']},
        native_gds=dict(path=str(gds),sha256=file_sha(gds)),flat_abstract_boundary_qualified=False,
        exact_final_function_qualified=function_control is not None,final_function_control=function_control,
        twelve_layer_qualified=False,qualified_hard_macro=False,
        scope='Same-source candidate view generation and native-tool interface readback only; full boundary, function and twelve-layer qualification remain required')
    (out/'native-view-generation.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Generated native view interface mismatch'
