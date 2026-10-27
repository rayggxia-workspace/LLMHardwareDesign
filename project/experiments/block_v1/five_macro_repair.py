"""Repair a measured M hold violation within the same unfrozen implementation."""
import json
from pathlib import Path
import shutil


def finish_patch(root,out,cpus,run):
    """Fresh native RCX/final outputs from the proved M patch, no rerouting."""
    from io_slots import file_sha,slot
    from five_macro_receive import source
    from native_escape_finish import FLOW_HASHES
    from native_escape_audit import def_inventory
    assert cpus==16
    original,r,old,results=source(out,'m',repaired=True)
    probe=out.parents[2]/'block-v1-20261027-204/tasks/five-macro-patch-m'
    pr=json.loads((probe/'receipt.json').read_text());assert pr['passed'] is True
    pp=probe/'five-macro-patch-m.json';assert file_sha(pp)==pr['outputs'][pp.name]
    p=json.loads(pp.read_text());assert p['passed'] and p['complete_gds_mask']['passed']
    assert p['exact_native_def_rect_readback'] and p['non_net_geometry_unchanged']
    assert p['unchanged_full_signal_netlist'] and p['all_other_routes_unchanged'] and p['no_original_conductors_removed']
    assert p['source_receipt_sha256']==file_sha(original/'receipt.json')
    assert not p['native_full_chip_drc_report'].strip()
    for name in ('edited.odb','after.def','after.v','patch-mask-readback.json'):
        assert file_sha(probe/name)==pr['outputs'][name]
    assert file_sha(probe/'edited.odb')==p['edited_odb_sha256']
    nickname='bv1_'+old['top'];target=out/'flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    copied={}
    def copy(a,b,digest):
        assert file_sha(a)==digest
        with slot(out.parents[2]):shutil.copyfile(a,b)
        assert file_sha(b)==digest;b.chmod(0o444);copied[str(b.relative_to(out))]=digest
    copy(probe/'edited.odb',target/'6_1_fill.odb',p['edited_odb_sha256'])
    copy(results/'6_final.sdc',target/'6_1_fill.sdc',r['outputs'][str((results/'6_final.sdc').relative_to(original))])
    for name in ('1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv'):
        copy(results/name,target/name,r['outputs'][str((results/name).relative_to(original))])
    for name in ('pins.json','pins.tcl','input-diodes.tcl'):
        copy(original/name,out/name,r['outputs'][name])
    config=(original/'config.mk').read_text()
    old_hook=str(original/'input-diodes.tcl');assert config.count(old_hook)==1
    (out/'config.mk').write_text(config.replace(old_hook,str(out/'input-diodes.tcl')))
    flow=Path('/OpenROAD-flow-scripts/flow')
    assert {name:file_sha(flow/name) for name in FLOW_HASHES}==FLOW_HASHES
    record=dict(old,passed=False,pipeline_completed=False,stages=[],final_files={},
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                pre_freeze_m2_patch=True,patch_receipt_sha256=file_sha(probe/'receipt.json'),
                patch_report_sha256=file_sha(pp),source_receipt_sha256=file_sha(original/'receipt.json'),
                accepted_edit_odb_sha256=p['edited_odb_sha256'],actual_flow_scripts=FLOW_HASHES,
                scope='Same M implementation, accepted single additive M2 patch; ordinary final-report/RCX only, all independent final gates required again')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-6_report'],'do-6_report.log');record['stages'].append('do-6_report');save()
    body='set_thread_count 16\nread_db {'+str(target/'6_final.odb')+'}\nwrite_def final-readback.def\nwrite_verilog final-all.v\n'
    body+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def checked-readback.def\n'
    (out/'final-check.tcl').write_text(body);run(['openroad','-no_init','-exit',str(out/'final-check.tcl')],'final-check.log')
    assert def_inventory(probe/'after.def')==def_inventory(out/'final-readback.def')
    assert file_sha(out/'final-readback.def')==file_sha(out/'checked-readback.def')
    assert file_sha(out/'final-all.v')==file_sha(probe/'after.v')
    assert file_sha(target/'6_final.sdc')==file_sha(results/'6_final.sdc')
    assert not (out/'native-whole-drc.rpt').read_text().strip()
    for name,digest in copied.items():assert file_sha(out/name)==digest
    report=out/'flow/reports/nangate45'/nickname/'base/5_route_drc.rpt'
    shutil.copyfile(out/'native-whole-drc.rpt',report)
    for suffix in ('v','sdc','def','odb','spef'):
        path=target/('6_final.'+suffix);assert path.stat().st_size>0
        record['final_files'][path.name]=dict(path=str(path),sha256=file_sha(path),bytes=path.stat().st_size)
    assert source(out,'m',repaired=True)[1]==r
    record.update(passed=True,pipeline_completed=True,regenerated_rc=True,
                  exact_accepted_geometry_and_hardware_unchanged=True,whole_native_drc_zero=True)
    save()


def patch_metal2(root,out,cpus,run):
    """One additive, pre-freeze notch fill on the measured M2 net only."""
    import collections
    from io_slots import file_sha
    from five_macro_receive import source
    from native_escape import records
    import re
    from native_escape_audit import geometry,def_inventory,connectivity,header_identity
    assert cpus==16
    folder,r,flow,results=source(out,'m',repaired=True)
    located=out.parents[2]/'block-v1-20261027-196/tasks/five-macro-locate-m'
    lr=json.loads((located/'receipt.json').read_text());assert lr['passed'] is True
    p=located/'five-macro-locate-m.json';assert file_sha(p)==lr['outputs'][p.name]
    location=json.loads(p.read_text());assert location['passed'] and location['read_only']
    assert location['source_receipt_sha256']==file_sha(folder/'receipt.json')
    name='$abc$226431$new_n33888';box=[282460,530600,282650,531160]
    assert {h['net'] for h in location['hits']}=={name}
    assert all(h['layer']=='metal2' for h in location['hits'])
    helper=root/'project/experiments/block_v1'
    setup='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'
    setup+='set ::env(BV1_GEOMETRY_SOURCE) {'+str(helper/'odb_geometry.tcl')+'}\nsource {'+str(helper/'native_escape_geometry.tcl')+'}\n'
    body='write_def before.def\nwrite_verilog before.v\nescape_geometry before-geometry.tsv {'+name+'}\n'
    (out/'before.tcl').write_text(setup+body);run(['openroad','-no_init','-exit',str(out/'before.tcl')],'before.log')
    before_records={s.lstrip().split()[1]:s for s in records(out/'before.def')}
    old=before_records[name];assert old.rstrip().endswith(';')
    # Installed dbWirePathItr omits DEF RECT (measured197); ordinary parallel
    # segments with the same union still fail native DRC (measured201).
    # Retain the real patch-wire representation and ADD independent exact
    # native DEF plus complete GDS polygon proof. Never count the iterator
    # alone as evidence that RECT was retained or omitted from fabrication.
    patch_path='NEW metal2 ( 282580 531020 ) RECT ( -120 -420 70 140 )'
    new=old.rstrip()[:-1].rstrip()+'\n      '+patch_path+' ;\n'
    patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN '+flow['top']+' ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 1 ;\n'+new+'END NETS\nEND DESIGN\n'
    (out/'patch.def').write_text(patch)
    body='read_def -floorplan_initialize {'+str(out/'patch.def')+'}\nwrite_def after.def\nwrite_db edited.odb\nwrite_verilog after.v\nescape_geometry after-geometry.tsv {'+name+'}\n'
    body+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'edit.tcl').write_text(setup+body);run(['openroad','-no_init','-exit',str(out/'edit.tcl')],'edit.log')
    after_records={s.lstrip().split()[1]:s for s in records(out/'after.def')}
    assert set(before_records)==set(after_records)
    assert all(before_records[k]==after_records[k] for k in before_records if k!=name)
    assert def_inventory(out/'before.def')[1]==def_inventory(out/'after.def')[1], 'Non-NETS geometry changed'
    assert file_sha(out/'before.v')==file_sha(out/'after.v')
    before=geometry(out/'before-geometry.tsv');after=geometry(out/'after-geometry.tsv')
    assert set(before)==set(after)
    for net in before:
        a=collections.Counter(before[net]);b=collections.Counter(after[net])
        assert not a-b,'A conductor was removed'
        assert a==b,'An original iterator-visible conductor changed'
    # Fresh native DEF writer reads RECT back from the edited ODB, with exact
    # coordinates; only connection serialization order may differ.
    old_header,old_route=old.split('+ ROUTED',1)
    new_header,new_route=after_records[name].split('+ ROUTED',1)
    assert header_identity(old_header)==header_identity(new_header)
    normalized=lambda s:' '.join(s.split())
    assert normalized(new_route)==normalized(old_route.rstrip().removesuffix(';')+patch_path+' ;')
    augmented=list(after[name])+[('metal2','wire',tuple(box))]
    connected=connectivity(augmented);assert connected['passed']
    # Source full GDS was independently exported in193, even though its two
    # native routing markers prevented qualification. Bind raw input hashes;
    # do not treat that failed DRC receipt as an accepted macro.
    failed=out.parents[2]/'block-v1-20261027-193/tasks/five-macro-drc-m'
    dr=json.loads((failed/'receipt.json').read_text());assert dr['passed'] is False
    dp=failed/'five-macro-drc.json';assert file_sha(dp)==dr['outputs'][dp.name]
    d=json.loads(dp.read_text());assert d['source_receipt_sha256']==file_sha(folder/'receipt.json')
    original_gds=Path(d['gds']['path']);assert file_sha(original_gds)==d['gds']['sha256']==dr['outputs'][str(original_gds.relative_to(failed))]
    nickname='bv1_'+flow['top'];target=out/'gds-flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    shutil.copyfile(out/'after.def',target/'6_final.def')
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    gds=target/'6_final.gds'
    tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/FreePDK45.lyt')
    assert "'metal2 : 13/0'" in tech.read_text()
    run(['klayout','-b','-rd','before_gds='+str(original_gds),'-rd','after_gds='+str(gds),'-rd','out='+str(out),
         '-r',str(helper/'native_patch_mask.rb')],'patch-mask.log')
    mask=json.loads((out/'patch-mask-readback.json').read_text());assert mask['passed']
    report=(out/'native-whole-drc.rpt').read_text()
    result=dict(passed=not report.strip(),source_receipt_sha256=file_sha(folder/'receipt.json'),
                location_receipt_sha256=file_sha(located/'receipt.json'),net=name,added_metal2_box_dbu=box,
                source_unchanged=source(out,'m',repaired=True)[1]==r,unchanged_full_signal_netlist=True,
                all_other_routes_unchanged=True,no_original_conductors_removed=True,
                non_net_geometry_unchanged=True,exact_native_def_rect_readback=True,complete_gds_mask=mask,
                source_gds_sha256=file_sha(original_gds),edited_gds_sha256=file_sha(gds),
                native_layer_mapping_sha256=file_sha(tech),
                target_net_connectivity=connected,
                native_full_chip_drc_report=report,edited_odb_sha256=file_sha(out/'edited.odb'),
                edited_def_sha256=file_sha(out/'after.def'),qualified_hard_macro=False,
                scope='One additive pre-freeze M2 notch fill, actual exact geometry and full native DRC only; new final outputs/RCX/STA/full deck/function/strict LEC still required')
    (out/'five-macro-patch-m.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def locate(root,out,cpus,run):
    """Localize every measured193 native marker without changing geometry."""
    from decimal import Decimal
    import re
    from io_slots import file_sha
    from five_macro_receive import source
    assert cpus==16
    folder,r,flow,results=source(out,'m',repaired=True)
    failed=out.parents[2]/'block-v1-20261027-193/tasks/five-macro-drc-m'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed'] is False
    p=failed/'five-macro-drc.json';assert file_sha(p)==fr['outputs'][p.name]
    report=json.loads(p.read_text());assert not report['passed']
    assert report['source_receipt_sha256']==file_sha(folder/'receipt.json')
    text=report['native_report'];expression=r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)\n'
    rows=[];cursor=0
    for match in re.finditer(expression,text):
        assert not text[cursor:match.start()].strip();cursor=match.end()
        category,names,*values,layer=match.groups();values=[Decimal(v)*2000 for v in values]
        assert all(v==int(v) for v in values);box=list(map(int,values))
        rows.append(dict(category=category,names=names,layer=layer,reported_box_dbu=box,
                         context_box_dbu=[box[0]-200,box[1]-200,box[2]+200,box[3]+200]))
    assert len(rows)==2 and not text[cursor:].strip()
    helper=root/'project/experiments/block_v1'
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nsource {'+str(helper/'odb_geometry.tcl')+'}\n'
    script+='namespace eval bvgeom {variable markers [dict create]}\n'
    for i,row in enumerate(rows):script+='dict lappend bvgeom::markers '+row['layer']+' {'+str(i)+' '+' '.join(map(str,row['context_box_dbu']))+'}\n'
    script+='source {'+str(helper/'native_drc_locate.tcl')+'}\n'
    (out/'locate.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'locate.tcl')],'locate.log')
    hits=[]
    for line in (out/'marker-shapes.tsv').read_text().splitlines():
        index,name,layer,kind,*box=line.split('\t')
        hits.append(dict(marker=int(index),net=bytes.fromhex(name).decode(),layer=layer,kind=kind,box_dbu=list(map(int,box))))
    assert hits and any(h['net']=='$abc$226431$new_n33888' for h in hits)
    result=dict(passed=True,read_only=True,source_receipt_sha256=file_sha(folder/'receipt.json'),
                measured_failure_sha256=file_sha(p),markers=rows,hits=hits,qualified_hard_macro=False)
    (out/'five-macro-locate-m.json').write_text(json.dumps(result,indent=2)+'\n')


def matrix_hold(root,out,cpus,run):
    from five_macro_receive import source
    from io_slots import file_sha,slot
    assert cpus==16
    original,r,old,results=source(out,'m',original=True)
    failed=out.parents[2]/'block-v1-20261027-191/tasks/five-macro-physical-m'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed'] is False
    p=failed/'five-macro-physical.json';assert file_sha(p)==fr['outputs'][p.name]
    failure=json.loads(p.read_text());assert failure['passed'] is False
    assert failure['source_receipt_sha256']==file_sha(original/'receipt.json')
    timing=failure['timing']['timed_endpoints']
    assert timing['minimum_hold_ns']<0 and timing['native_summary']['hold_checks']>0
    assert all(v for k,v in failure['checks'].items() if k!='all_real_timed_endpoints')
    assert all(v for k,v in timing['checks'].items() if k not in ('all_hold_nonnegative','native_hold_count_zero'))
    rtl='project/rtl/block_library_v1/block_v1_m.sv'
    assert file_sha(root/rtl)==r['inputs'][rtl]
    nickname='bv1_block_v1_m'
    target=out/'flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    copied={}
    with slot(out.parents[2]):
        for name in ('1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','4_cts.odb','4_cts.sdc'):
            source_path=results/name;digest=file_sha(source_path)
            assert digest==r['outputs'][str(source_path.relative_to(original))]
            dest=target/name;shutil.copyfile(source_path,dest);dest.chmod(0o444);copied[name]=digest
        for name in ('pins.json','pins.tcl','input-diodes.tcl'):
            assert file_sha(original/name)==r['outputs'][name]
            shutil.copyfile(original/name,out/name)
    # New pre-freeze repair target, same physical implementation, RTL,
    # footprint, pin geometry, CTS source and actual electrical limits.
    # The .020 target is a repair knob; it is NOT a relaxed acceptance limit.
    # Full-deck191 found the unprotected input clock antenna. Keep the
    # original hook intact; this repair protects the clock root as well.
    # All added cells/loads remain in final STA, PG, GDS and function views.
    hook=(root/'project/experiments/block_v1/native_input_diodes.tcl').read_text()
    skip='  if {[$port getName] eq "clk"} {continue}\n'
    assert hook.count(skip)==1
    (out/'input-diodes.tcl').write_text(hook.replace(skip,''))
    config=(original/'config.mk').read_text()
    assert str(original/'input-diodes.tcl') in config
    config=config.replace(str(original/'input-diodes.tcl'),str(out/'input-diodes.tcl'))
    config+='\nexport HOLD_SLACK_MARGIN = 0.020\n'
    (out/'config.mk').write_text(config)
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),
             'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['print-HOLD_SLACK_MARGIN'],'hold-variable.log')
    assert 'HOLD_SLACK_MARGIN: 0.020' in (out/'hold-variable.log').read_text()
    record=dict(old)
    record.update(passed=False,pipeline_completed=False,stages=[],final_files={},
                  config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),
                  repair_of=str(original),repair_source_receipt_sha256=file_sha(original/'receipt.json'),
                  measured_failure_sha256=file_sha(p),measured_failure_receipt_sha256=file_sha(failed/'receipt.json'),
                  measured_hold_ns=timing['minimum_hold_ns'],sealed_cts_inputs=copied,
                  repair_target_hold_ns=.020,implementation_count=1,clock_root_protection=True,
                  scope='Repair actual negative hold in same unfrozen M leaf, same RTL/die/pins/CTS; new route/RCX/final artifacts require every independent gate again')
    record['actual_variables']=dict(old['actual_variables'],HOLD_SLACK_MARGIN='0.020')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for stage in ('do-route','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage)
        assert all(file_sha(target/name)==digest for name,digest in copied.items());save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=target/('6_final.'+suffix);assert p.is_file()
        record['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    record['passed']=True;record['pipeline_completed']=True;save()
