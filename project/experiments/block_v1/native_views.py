"""Source-bound view generation, separately gated from model qualification.

OpenSTA's model has scalar input setup/hold and omits input wire resistance.
Fresh successful view readback therefore does not prove flat/abstract timing
equivalence or qualify a hard macro. Those gates remain explicit and separate.
"""
import json
from pathlib import Path


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


def generate(root,out,cpus,run,top,policy):
    from io_slots import file_sha,slot
    assert top in ('shared109','transaction6k')and policy in ('A','C')and cpus>=8
    base=out.parents[2];config=json.loads((root/'project/experiments/block_v1/native_pipeline.json').read_text())
    api=base/'block-v1-20261027-073/tasks/native-formal-control'
    control=json.loads((api/'receipt.json').read_text());assert control['passed']is True
    assert file_sha(api/'view-api.log')==control['outputs']['view-api.log']
    receiver=base/config['receiver_run']/('tasks/native-receive-'+top+'-'+policy.lower())
    accepted=json.loads((receiver/'receipt.json').read_text());assert accepted['passed']is True
    proof=receiver/'native-physical-receiver.json';assert file_sha(proof)==accepted['outputs'][proof.name]
    physical=json.loads(proof.read_text());assert physical['passed']is True and not physical['historical_input_contract']
    source=base/config['candidate_run']/('tasks/native-run-'+top+'-'+policy.lower())
    assert physical['source']==str(source)and file_sha(source/'receipt.json')==physical['source_receipt_sha256']
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    relative=Path('flow/results/nangate45')/('bv1_'+top+'_'+policy)/'base';results=source/relative
    inputs={}
    with slot(base):
        for name in ['6_final.odb','6_final.sdc','6_final.spef','6_final.v','6_final.def']:
            path=results/name;digest=file_sha(path);assert digest==receipt['outputs'][(relative/name).as_posix()]
            inputs[str(path)]=digest
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
    text+='set wanted_master {'+top+'}\nset wanted_library {'+library+'}\nsource {'+str(root/'project/experiments/block_v1/native_views.tcl')+'}\n'
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
        physical_receiver_sha256=file_sha(proof),inputs=inputs,
        actual_model_api_help_sha256=file_sha(api/'view-api.log'),
        views={name:dict(path=str(out/name),sha256=file_sha(out/name))for name in ['candidate.lib','candidate.lef']},
        native_gds=dict(path=str(gds),sha256=file_sha(gds)),flat_abstract_boundary_qualified=False,
        exact_final_function_qualified=False,twelve_layer_qualified=False,qualified_hard_macro=False,
        scope='Same-source candidate view generation and native-tool interface readback only; full boundary, function and twelve-layer qualification remain required')
    (out/'native-view-generation.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Generated native view interface mismatch'
