"""Repair a measured M hold violation within the same unfrozen implementation."""
import json
from pathlib import Path
import shutil


def patch_metal2(root,out,cpus,run):
    """One additive, pre-freeze notch fill on the measured M2 net only."""
    import collections
    from io_slots import file_sha
    from five_macro_receive import source
    from native_escape import records
    from native_escape_audit import geometry
    assert cpus==16
    folder,r,flow,results=source(out,'m')
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
    # DEF RECT coordinates are relative to this route point. Its exact native
    # readback is checked below; keep every original route/via/terminal.
    new=old.rstrip()[:-1].rstrip()+'\n      NEW metal2 ( 282580 531020 ) RECT ( -120 -420 70 140 ) ;\n'
    patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN '+flow['top']+' ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 1 ;\n'+new+'END NETS\nEND DESIGN\n'
    (out/'patch.def').write_text(patch)
    body='read_def -floorplan_initialize {'+str(out/'patch.def')+'}\nwrite_def after.def\nwrite_db edited.odb\nwrite_verilog after.v\nescape_geometry after-geometry.tsv {'+name+'}\n'
    body+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'edit.tcl').write_text(setup+body);run(['openroad','-no_init','-exit',str(out/'edit.tcl')],'edit.log')
    after_records={s.lstrip().split()[1]:s for s in records(out/'after.def')}
    assert set(before_records)==set(after_records)
    assert all(before_records[k]==after_records[k] for k in before_records if k!=name)
    assert file_sha(out/'before.v')==file_sha(out/'after.v')
    before=geometry(out/'before-geometry.tsv');after=geometry(out/'after-geometry.tsv')
    assert set(before)==set(after)
    for net in before:
        a=collections.Counter(before[net]);b=collections.Counter(after[net])
        assert not a-b,'A conductor was removed'
        if net==name:assert b-a==collections.Counter([('metal2','wire',tuple(box))])
        else:assert a==b,'Another net changed'
    report=(out/'native-whole-drc.rpt').read_text()
    result=dict(passed=not report.strip(),source_receipt_sha256=file_sha(folder/'receipt.json'),
                location_receipt_sha256=file_sha(located/'receipt.json'),net=name,added_metal2_box_dbu=box,
                source_unchanged=source(out,'m')[1]==r,unchanged_full_signal_netlist=True,
                all_other_routes_unchanged=True,no_original_conductors_removed=True,
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
    folder,r,flow,results=source(out,'m')
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
