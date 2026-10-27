"""Read-only localization of the actual S final M10 spacing failures."""
import json
from decimal import Decimal
import re
from pathlib import Path


def locate(root,out,cpus,run):
    from io_slots import file_sha
    from five_macro_receive import source
    assert cpus==16
    folder,receipt,_,results=source(out,'s',original=True)
    failed=out.parents[2]/'block-v1-20261027-207/tasks/five-macro-drc-s'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed']is False
    p=failed/'five-macro-drc.json';assert file_sha(p)==fr['outputs'][p.name]
    failure=json.loads(p.read_text())
    assert failure['source_receipt_sha256']==file_sha(folder/'receipt.json')
    assert failure['full_deck']['total_items']==10 and failure['full_deck']['categories']=={'METAL10.2':10}
    text=failure['native_report']
    expression=r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)\n'
    markers=[];cursor=0
    for match in re.finditer(expression,text):
        assert not text[cursor:match.start()].strip();cursor=match.end()
        category,names,*values,layer=match.groups();values=[Decimal(v)*2000 for v in values]
        assert all(v==int(v)for v in values)and layer=='metal10'
        box=list(map(int,values))
        markers.append(dict(category=category,names=names,layer=layer,reported_box_dbu=box,
                            context_box_dbu=[box[0]-2000,box[1]-2000,box[2]+2000,box[3]+2000]))
    assert len(markers)==7 and not text[cursor:].strip()
    helper=root/'project/experiments/block_v1'
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nsource {'+str(helper/'odb_geometry.tcl')+'}\n'
    script+='namespace eval bvgeom {variable markers [dict create]}\n'
    for i,m in enumerate(markers):script+='dict lappend bvgeom::markers metal10 {'+str(i)+' '+' '.join(map(str,m['context_box_dbu']))+'}\n'
    script+='source {'+str(helper/'native_drc_locate.tcl')+'}\n'
    (out/'locate.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'locate.tcl')],'locate.log')
    hits=[]
    for line in(out/'marker-shapes.tsv').read_text().splitlines():
        index,name,layer,kind,*box=line.split('\t')
        hits.append(dict(marker=int(index),net=bytes.fromhex(name).decode(),layer=layer,kind=kind,box_dbu=list(map(int,box))))
    assert hits and {'addr[6]','addr[7]','din[31]','din[43]','din[55]'}<={h['net']for h in hits}
    assert source(out,'s',original=True)[1]==receipt
    result=dict(passed=True,read_only=True,source_receipt_sha256=file_sha(folder/'receipt.json'),
                failure_receipt_sha256=file_sha(failed/'receipt.json'),markers=markers,hits=hits,
                qualified_hard_macro=False,scope='Exact native marker context only; no route or pin edits and no S acceptance.')
    (out/'five-macro-locate-s.json').write_text(json.dumps(result,indent=2)+'\n')


def spacing_plans(records):
    """Replace only the three measured M10 U-shaped pin approaches."""
    from native_escape import parse,signature
    old={
        'addr[7]':[((3390,85500,None),(3390,86540,0)),((3390,85500,None),(4990,85500,None)),
                   ((4990,85500,None),(4990,86540,None)),((4990,86540,None),(9790,86540,None))],
        'din[43]':[((1078590,1596940,None),(1080190,1596940,None)),((1080190,1596000,None),(1080190,1596940,None)),
                   ((1080190,1596000,None),(1081790,1596000,None)),((1081790,1596000,None),(1081790,1596940,0))],
        'din[55]':[((1078590,1603340,None),(1078590,1606540,None)),((1078590,1603340,None),(1080190,1603340,None)),
                   ((1080190,1601740,None),(1080190,1603340,None)),((1080190,1601740,None),(1081790,1601740,None)),
                   ((1081790,1601740,None),(1081790,1603340,0))],
    }
    new={
        'addr[7]':[((3390,86540,0),(9790,86540,None))],
        'din[43]':[((1078590,1596940,None),(1081790,1596940,0))],
        'din[55]':[((1078590,1603340,None),(1078590,1606540,None)),
                   ((1078590,1603340,None),(1081790,1603340,0))],
    }
    plans={}
    for name,expected in old.items():
        header,paths=parse(records[name])
        selected=[p for p in paths if p['layer']=='metal10'and p['via']is None]
        assert [tuple(p['points'])for p in selected]==expected,(name,selected)
        retained=[p for p in paths if not(p['layer']=='metal10'and p['via']is None)]
        added=[dict(layer='metal10',points=list(points),via=None)for points in new[name]]
        final=retained+added
        assert signature([p for p in final if p['layer']!='metal10'])==signature([p for p in paths if p['layer']!='metal10'])
        plans[name]=dict(header=header,original_paths=paths,final_paths=final)
    return plans


def repair(root,out,cpus,run):
    """Prefreeze S spacing repair with unchanged cells, BPin boxes and vias."""
    import collections
    import shutil
    from io_slots import file_sha,slot
    from five_macro_receive import source
    from native_escape import records,emit
    from native_escape_audit import readback,geometry,physical,def_inventory
    from native_escape_finish import FLOW_HASHES
    assert cpus==16
    folder,receipt,flow,results=source(out,'s',original=True)
    located=out.parents[2]/'block-v1-20261027-222/tasks/five-macro-locate-s'
    lr=json.loads((located/'receipt.json').read_text());assert lr['passed']is True
    p=located/'five-macro-locate-s.json';assert file_sha(p)==lr['outputs'][p.name]
    location=json.loads(p.read_text());assert location['passed']and location['read_only']
    assert location['source_receipt_sha256']==file_sha(folder/'receipt.json')
    names=['addr[7]','din[43]','din[55]'];helper=root/'project/experiments/block_v1'
    setup='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'
    setup+='set ::env(BV1_GEOMETRY_SOURCE) {'+str(helper/'odb_geometry.tcl')+'}\nsource {'+str(helper/'native_escape_geometry.tcl')+'}\n'
    selected=' '.join('{'+name+'}'for name in names)
    body='write_def before.def\nwrite_verilog before.v\nescape_geometry before-geometry.tsv {'+selected+'}\n'
    (out/'before.tcl').write_text(setup+body);run(['openroad','-no_init','-exit',str(out/'before.tcl')],'before.log')
    original={s.lstrip().split()[1]:s for s in records(out/'before.def')if s.lstrip().split()[1]in names}
    assert set(original)==set(names)
    plans=spacing_plans(original)
    (out/'spacing-plans.json').write_text(json.dumps(plans,indent=2)+'\n')
    patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN block_v1_s16k ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 3 ;\n'
    patch+=''.join(emit(plans[name]['header'],plans[name]['final_paths'])for name in names)+'END NETS\nEND DESIGN\n'
    (out/'patch.def').write_text(patch)
    body='read_def -floorplan_initialize {'+str(out/'patch.def')+'}\nwrite_def after.def\nwrite_db edited.odb\nwrite_verilog after.v\n'
    body+='escape_geometry after-geometry.tsv {'+selected+'}\ndrt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'edit.tcl').write_text(setup+body);run(['openroad','-no_init','-exit',str(out/'edit.tcl')],'edit.log')
    exact=readback(out/'before.def',out/'after.def',plans)
    assert file_sha(out/'before.v')==file_sha(out/'after.v')
    before=geometry(out/'before-geometry.tsv');after=geometry(out/'after-geometry.tsv')
    assert set(before)==set(after)
    for name in before:
        a,b=before[name],after[name]
        if name not in names:assert collections.Counter(a)==collections.Counter(b)
        else:
            assert collections.Counter(x for x in a if x[0]!='metal10'or x[1]!='wire')==collections.Counter(x for x in b if x[0]!='metal10'or x[1]!='wire')
    connectivity=physical(after,names);assert connectivity['passed']
    native=(out/'native-whole-drc.rpt').read_text()
    patch_proof=dict(passed=not native.strip(),source_receipt_sha256=file_sha(folder/'receipt.json'),
                     location_receipt_sha256=file_sha(located/'receipt.json'),native_def_readback=exact,
                     unchanged_signal_netlist=True,unchanged_all_bpin_boxes=True,unchanged_all_vias=True,
                     unchanged_non_target_routes=True,unchanged_other_layers=True,connectivity=connectivity,
                     native_whole_drc_report=native,edited_odb_sha256=file_sha(out/'edited.odb'),
                     qualified_hard_macro=False,scope='Only three measured unfrozen S M10 pin approaches; full final RCX and all independent gates still required.')
    (out/'five-macro-patch-s.json').write_text(json.dumps(patch_proof,indent=2)+'\n');assert patch_proof['passed']
    nickname='nangate45/bv1_block_v1_s16k/base';target=out/'flow/results'/nickname;target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'flow'/category/nickname).mkdir(parents=True)
    copied={}
    def copy(source_path,destination,digest):
        assert file_sha(source_path)==digest
        with slot(out.parents[2]):shutil.copyfile(source_path,destination)
        assert file_sha(destination)==digest;copied[str(destination.relative_to(out))]=digest
    copy(out/'edited.odb',target/'6_1_fill.odb',patch_proof['edited_odb_sha256'])
    for old,new in [('6_final.sdc','6_1_fill.sdc'),('1_synth_lec.v','1_synth_lec.v'),
                    ('1_2_yosys.v','1_2_yosys.v'),('1_2_yosys.sdc','1_2_yosys.sdc'),('bv1-input-diodes.tsv','bv1-input-diodes.tsv')]:
        source_path=results/old;copy(source_path,target/new,receipt['outputs'][str(source_path.relative_to(folder))])
    for name in ('pins.json','pins.tcl','input-diodes.tcl'):copy(folder/name,out/name,receipt['outputs'][name])
    config=(folder/'config.mk').read_text();assert config.count(str(folder/'input-diodes.tcl'))==1
    (out/'config.mk').write_text(config.replace(str(folder/'input-diodes.tcl'),str(out/'input-diodes.tcl')))
    native_flow=Path('/OpenROAD-flow-scripts/flow');assert {n:file_sha(native_flow/n)for n in FLOW_HASHES}==FLOW_HASHES
    record=dict(flow,passed=False,pipeline_completed=False,stages=[],final_files={},
                source_receipt_sha256=file_sha(folder/'receipt.json'),config_sha256=file_sha(out/'config.mk'),
                pins_sha256=file_sha(out/'pins.json'),spacing_patch_sha256=file_sha(out/'five-macro-patch-s.json'),
                accepted_edit_odb_sha256=patch_proof['edited_odb_sha256'],actual_flow_scripts=FLOW_HASHES,
                scope='Same S16KiB single1RW implementation; three M10 U-approach simplifications, unchanged pins/vias/cells/logic. Fresh final RCX and four same-source gates required.')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(native_flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log');record['stages'].append('do-6_report');save()
    body='read_db {'+str(target/'6_final.odb')+'}\nwrite_def final-readback.def\nwrite_verilog final-all.v\n'
    (out/'final-check.tcl').write_text(body);run(['openroad','-no_init','-exit',str(out/'final-check.tcl')],'final-check.log')
    assert def_inventory(out/'after.def')==def_inventory(out/'final-readback.def')
    assert file_sha(out/'after.v')==file_sha(out/'final-all.v')
    assert file_sha(target/'6_final.sdc')==file_sha(results/'6_final.sdc')
    shutil.copyfile(out/'native-whole-drc.rpt',out/'flow/reports'/nickname/'5_route_drc.rpt')
    for name,digest in copied.items():assert file_sha(out/name)==digest
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.stat().st_size>0
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert source(out,'s',original=True)[1]==receipt
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True,whole_native_drc_zero=True,
                  exact_accepted_geometry_and_hardware_unchanged=True);save()


def resume(root,out,cpus,run):
    """Finish the sealed, geometrically proved223 edit after its Python error."""
    import shutil
    from io_slots import file_sha,slot
    from five_macro_receive import source
    from native_escape_finish import FLOW_HASHES
    from native_escape_audit import def_inventory
    assert cpus==16
    original,original_receipt,flow,original_results=source(out,'s',original=True)
    # Actual223 CWD typo is historical and immutable; retain its explicit path.
    prior=out.parents[2]/'block-s1-20261027-223/tasks/five-macro-finish-s-spacing'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']is False
    assert receipt['error']=='''NameError("name 'Path' is not defined")'''
    p=prior/'five-macro-patch-s.json';assert file_sha(p)==receipt['outputs'][p.name]
    patch=json.loads(p.read_text());assert patch['passed']and patch['connectivity']['passed']
    assert patch['source_receipt_sha256']==file_sha(original/'receipt.json')
    for key in ('unchanged_signal_netlist','unchanged_all_bpin_boxes','unchanged_all_vias','unchanged_non_target_routes','unchanged_other_layers'):
        assert patch[key]is True
    assert patch['native_def_readback']['passed']and patch['native_def_readback']['changed_nets']==['addr[7]','din[43]','din[55]']
    assert not patch['native_whole_drc_report'].strip()
    assert file_sha(prior/'edited.odb')==receipt['outputs']['edited.odb']==patch['edited_odb_sha256']
    nickname='nangate45/bv1_block_v1_s16k/base';target=out/'flow/results'/nickname;target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'flow'/category/nickname).mkdir(parents=True)
    copied={}
    def copy(relative,destination):
        p=prior/relative;digest=file_sha(p);assert digest==receipt['outputs'][relative]
        with slot(out.parents[2]):shutil.copyfile(p,destination)
        assert file_sha(destination)==digest;copied[str(destination.relative_to(out))]=digest
    for name in ('6_1_fill.odb','6_1_fill.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv'):
        copy('flow/results/'+nickname+'/'+name,target/name)
    assert file_sha(target/'6_1_fill.odb')==patch['edited_odb_sha256']
    for name in ('pins.json','pins.tcl','input-diodes.tcl'):copy(name,out/name)
    copy('native-whole-drc.rpt',out/'native-source-drc.rpt')
    copy('five-macro-patch-s.json',out/'accepted-source-patch.json')
    config_path=prior/'config.mk';assert file_sha(config_path)==receipt['outputs']['config.mk']
    config=config_path.read_text();assert config.count(str(prior/'input-diodes.tcl'))==1
    (out/'config.mk').write_text(config.replace(str(prior/'input-diodes.tcl'),str(out/'input-diodes.tcl')))
    native_flow=Path('/OpenROAD-flow-scripts/flow');assert {n:file_sha(native_flow/n)for n in FLOW_HASHES}==FLOW_HASHES
    record=dict(flow,passed=False,pipeline_completed=False,stages=[],final_files={},
                source_receipt_sha256=file_sha(original/'receipt.json'),config_sha256=file_sha(out/'config.mk'),
                pins_sha256=file_sha(out/'pins.json'),spacing_patch_sha256=file_sha(p),
                partial_source_receipt_sha256=file_sha(prior/'receipt.json'),
                accepted_edit_odb_sha256=patch['edited_odb_sha256'],actual_flow_scripts=FLOW_HASHES,
                scope='Resume the exact proved223 S edit after missing Path import. Same16KiB/ports/cells/vias; fresh ordinary final RCX and all independent gates required.')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(native_flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log');record['stages'].append('do-6_report');save()
    body='read_db {'+str(target/'6_final.odb')+'}\nwrite_def final-readback.def\nwrite_verilog final-all.v\n'
    (out/'final-check.tcl').write_text(body);run(['openroad','-no_init','-exit',str(out/'final-check.tcl')],'final-check.log')
    assert def_inventory(prior/'after.def')==def_inventory(out/'final-readback.def')
    assert file_sha(prior/'after.v')==file_sha(out/'final-all.v')
    assert file_sha(target/'6_final.sdc')==file_sha(original_results/'6_final.sdc')
    shutil.copyfile(out/'native-source-drc.rpt',out/'flow/reports'/nickname/'5_route_drc.rpt')
    for name,digest in copied.items():assert file_sha(out/name)==digest
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.stat().st_size>0
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert source(out,'s',original=True)[1]==original_receipt
    assert file_sha(prior/'receipt.json')==record['partial_source_receipt_sha256']
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True,whole_native_drc_zero=True,
                  exact_accepted_geometry_and_hardware_unchanged=True);save()
