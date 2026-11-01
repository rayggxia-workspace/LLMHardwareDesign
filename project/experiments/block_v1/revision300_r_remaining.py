"""Finite current-R alternatives; preserve exact DEF changes and failed copies."""
from collections import Counter
import json,re


def probe(root,out,cpus,run,variant,orientation=False,combined=False,gap=False,gap_combined=False):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    from revision300_v_gds_repair import nonnet
    assert cpus==16 and variant>=0
    gap=gap or gap_combined;combined=combined or gap_combined
    base=out.parents[2];source=base/('block-v1-20261101-903/tasks/revision300-r-current-compose' if gap else 'block-v1-20261101-880/tasks/revision300-r-composed-vias')
    planfile=root/'project/experiments/block_v1'/('r-gap-compose-plan-918.json' if gap_combined else 'r-gap-plan-912.json' if gap else 'r-current-plan-900.json' if combined else 'r-orientation-plan-896.json' if orientation else 'r-remaining-plan-893.json');plan=json.loads(planfile.read_text())
    assert variant<len(plan['variants'])and len(plan['variants'])==(1 if combined else 7 if gap else 6)
    assert file_sha(source/'receipt.json')==plan['source_receipt_sha256']
    if not gap:assert plan['source_receipt_sha256']=='4054eef392ce7c7a966b3774d51eb39d27540d88f6f7f52196692f520eac6938'
    rr=json.loads((source/'receipt.json').read_text());assert rr['passed']
    names=('remaining-candidate.odb','remaining-candidate.def','remaining-native-drc.rpt','revision300-r-remaining.json')if gap else('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt','revision300-r-composed-vias.json')
    odbname,defname,drcname,reportname=names;original_count=5 if gap else 55
    for n in names:assert file_sha(source/n)==rr['outputs'][n]
    if gap:
        prior=json.loads((source/reportname).read_text())
        assert rr['mode']=='revision300-r-current-compose'and prior['combined']and prior['passed']and prior['candidate_native_count']==5 and prior['added_markers']==0 and prior['source_receipt_sha256']=='4054eef392ce7c7a966b3774d51eb39d27540d88f6f7f52196692f520eac6938'
    # Bind the plan's actual exported geometry/routes and previously passed NS copy.
    mappings={'r-880-neighborhood-892':base/'block-v1-20261101-880/tasks/revision300-r-composed-neighborhood',
              'r-889-topology-891':base/'block-v1-20261101-889/tasks/revision300-r-composed-topology',
              'r-880-native-885':base/'block-v1-20261101-880',
              'r-894-alternatives-899':base/'block-v1-20261101-894',
              'r-897-orientation-901':base/'block-v1-20261101-897',
              'r-903-neighborhood-906':base/'block-v1-20261101-903/tasks/revision300-r-current-geometry',
              'r-903-topology-907':base/'block-v1-20261101-903/tasks/revision300-r-current-topology',
              'r-914-gap-917':base/'block-v1-20261101-914'}
    for path,h in plan['inputs_sha256'].items():
        tail=path.split('/review-20261028/')[1];folder,relative=tail.split('/',1)
        assert file_sha(mappings[folder]/relative)==h,path
    selected=plan['variants'][variant]['selected'];assert selected and len({p['net']for p in selected})==len(selected)
    assert plan['variants'][variant]['variant']==variant
    if combined:
        assert variant==0
        for p in selected:
            if p['net']not in plan['selection_provenance']:
                from decimal import Decimal
                assert gap_combined and p['net']=='net113322'and p in plan['untested_candidates']
                evidence=plan['untested_candidate_evidence'][p['net']];task=base/evidence['task'];report=json.loads((task/'revision300-r-remaining.json').read_text());receipt=json.loads((task/'receipt.json').read_text())
                assert not report['passed']and not receipt['passed']and report['source_receipt_sha256']==plan['source_receipt_sha256']and report['exact_normal_net_header_path_rect_and_nonnet_delta']and report['original_inputs_unchanged']
                for filename in ('revision300-r-remaining.json','remaining-native-drc.rpt','selected-edits.json'):assert file_sha(task/filename)==receipt['outputs'][filename]
                added=violations((task/'remaining-native-drc.rpt').read_text())-violations((source/drcname).read_text());assert sum(added.values())==1
                marker=next(iter(added));assert marker==evidence['actual_failed_added_marker']
                match=re.fullmatch(r'violation type: Metal Spacing srcs: net:net113322 bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer metal2',marker);assert match
                box=[int(Decimal(v)*2000)for v in match.groups()];previous=next(v for v in json.loads((task/'selected-edits.json').read_text())if v['net']==p['net']);assert len(previous['add_rectangles'])==1
                l,*oldbox=previous['add_rectangles'][0];assert oldbox[1]==box[3]
                union=[min(oldbox[0],box[0]),min(oldbox[1],box[1]),max(oldbox[2],box[2]),max(oldbox[3],box[3])]
                assert p['add_rectangles']==[[l]+union]and p['new_shapes']==[[l,union]]and not p['remove_paths']and not p['add_paths']
                continue
            evidence=plan['selection_provenance'][p['net']];task=base/evidence['task']
            actual=json.loads((task/'selected-edits.json').read_text());assert p in actual
            report=json.loads((task/'revision300-r-remaining.json').read_text());receipt=json.loads((task/'receipt.json').read_text())
            assert report['passed']==receipt['passed'] and report['source_receipt_sha256']==plan['source_receipt_sha256'] and report['exact_normal_net_header_path_rect_and_nonnet_delta'] and report['original_inputs_unchanged']
            for filename in ('revision300-r-remaining.json','remaining-native-drc.rpt','selected-edits.json'):assert file_sha(task/filename)==receipt['outputs'][filename]
            added=violations((task/'remaining-native-drc.rpt').read_text())-violations((source/drcname).read_text())
            assert sum(added.values())==report['added_markers']
            assert p['net']not in {n.replace('\\','')for marker in added for n in re.findall(r'net:(\S+)',marker)},'Reject every modified participant in an actual added marker'
    old=violations((source/drcname).read_text());assert sum(old.values())==original_count
    wanted={p['net']:p for p in selected};original={};others=Counter();n0=0
    for record in records(source/defname):
        n0+=1;name=name_of(record)
        if name not in wanted:others[token_hash(record)]+=1;continue
        assert name not in original;original[name]=decode(record)
    assert set(original)==set(wanted) and n0==1013372
    script='set_thread_count 16\nread_db {'+str(source/odbname)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nif {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}\nset selected [dict create]\n'
    script+='foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];dict lappend selected $name $net}\n'
    expected={}
    for name,p in wanted.items():
        header,paths,rects=original[name];before=Counter(map(path_key,paths));removed=Counter(map(path_key,p['remove_paths']));adds=Counter(map(path_key,p['add_paths']))
        assert all(before[k]==v==1 for k,v in removed.items()) and not (before&adds)
        required=before-removed+adds;after=[];remaining=removed.copy()
        for v in paths:
            key=path_key(v)
            if remaining[key]:remaining[key]-=1
            else:after.append(v)
        assert not +remaining;after.extend(p['add_paths']);assert Counter(map(path_key,after))==required
        assert all(required[path_key(v)]==before[path_key(v)] for v in p['preserved_source_wires'])
        rects=rects.copy()
        for row in p['add_rectangles']:rects[tuple(row)]+=1
        expected[name]=(header,required,rects)
        script+='set matches [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nif {[llength $matches]!=1} {error {Ambiguous target}}\nset net [lindex $matches 0]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,via in v['points']:
                assert via is None and x%10==y%10==0
                script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
        for (l,x0,y0,x1,y1),count in rects.items():
            assert all(v%10==0 for v in (x0,y0,x1,y1))
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+l+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db remaining-candidate.odb\nwrite_def remaining-candidate.def\ndrt::check_drc_cmd remaining-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'remaining.tcl').write_text(script);(out/'selected-edits.json').write_text(json.dumps(selected,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'remaining.tcl'],'remaining.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'remaining-candidate.def'):
        n1+=1;name=name_of(record)
        if name not in expected:actual[token_hash(record)]+=1;continue
        assert name not in found;found.add(name);header,paths,rects=decode(record);h,required,r=expected[name]
        exact=exact and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h) and Counter(map(path_key,paths))==required and rects==r
    exact=exact and actual==others and found==set(expected) and n0==n1 and nonnet(source/defname)==nonnet(out/'remaining-candidate.def')
    new=violations((out/'remaining-native-drc.rpt').read_text());unchanged=all(file_sha(source/n)==rr['outputs'][n] for n in names)
    result=dict(passed=exact and unchanged and not(new-old) and bool(old-new),physical_qualified=False,combined=combined,variant=variant,plan_sha256=file_sha(planfile),source_receipt_sha256=file_sha(source/'receipt.json'),source_files_sha256={n:rr['outputs'][n]for n in names},selected_nets=len(selected),exact_normal_net_header_path_rect_and_nonnet_delta=exact,original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],original_native_count=original_count,candidate_native_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),added=list((new-old).elements()),removed=list((old-new).elements()),scope='Actual receipt-bound source, all original paths/RECTs retained except explicitly planned via deletions, exact entire DEF delta, whole native DRC. Independent alternatives are not additive evidence. Fresh fullsignal/RCX/timing/fullGDS/function/LEC/interfaces still mandatory.')
    (out/'revision300-r-remaining.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed alternative for actual new-marker attribution'
