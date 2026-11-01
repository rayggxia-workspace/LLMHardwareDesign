"""Apply only controlled mixed/stack transition forms to the old failed copy."""
from collections import Counter,defaultdict
import json,re


def choose(paths,a,b):
    from revision300_v_via_batch import contains
    def via(point,layer):
        found=[p for p in paths if p['layer']==layer and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==point]
        return found[0]if len(found)==1 else None
    wires=[p for p in paths if contains(p,'metal3',a,b)]
    if len(wires)!=1:return None
    bridge=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None)
    lower,upper=via(a,'metal2'),via(a,'metal3');other=via(b,'metal2')
    if other and other['via'].startswith('via2_')and any(contains(p,'metal2',b,b)for p in paths):
        if upper and upper['via'].startswith('via3_')and lower is None and any(contains(p,'metal4',a,a)for p in paths):
            moved=dict(layer='metal2',points=[(*a,None)],via=other['via'])
            return dict(case='mixed',removed=other,added=[bridge,moved],retained=upper,wire=wires[0],
                        guards=[(other['via'],'metal2','metal3'),(upper['via'],'metal3','metal4')])
        bottom=via(a,'metal1')
        if lower and lower['via'].startswith('via2_')and bottom and bottom['via'].startswith('via1_'):
            return dict(case='stack',removed=lower,added=[bridge],retained=other,wire=wires[0],
                        guards=[(lower['via'],'metal2','metal3'),(other['via'],'metal2','metal3'),(bottom['via'],'metal1','metal2')])
    return None


def probe(root,out,cpus,run,filtered=False):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    assert cpus==16
    base=out.parents[2];prior=base/'block-v1-20261030-605/tasks/revision300-v-remaining'
    pr=json.loads((prior/'receipt.json').read_text());assert pr['passed']
    f=prior/'revision300-v-remaining.json';assert file_sha(f)==pr['outputs'][f.name]
    d=json.loads(f.read_text());assert d['passed']and d['native_marker_count']==172
    source=base/'block-v1-20261030-598/tasks/revision300-v-geometry-compose'
    sr=json.loads((source/'receipt.json').read_text());assert sr['passed']and file_sha(source/'receipt.json')==d['source_receipt_sha256']
    for name in ('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt'):
        assert file_sha(source/name)==sr['outputs'][name]
    controls=[]
    for case in ('mixed','stack'):
        p=base/('block-v1-20261030-607/tasks/revision300-v-transition-'+case)
        r=json.loads((p/'receipt.json').read_text());assert r['passed']
        f=p/'revision300-v-transition.json';assert file_sha(f)==r['outputs'][f.name]
        c=json.loads(f.read_text());assert c['passed']and c['case']==case and c['native_original_count']==172 and c['native_candidate_count']==171 and c['added_markers']==0
        assert c['input_odb_sha256']==sr['outputs']['composed-candidate.odb']and c['localization_receipt_sha256']==file_sha(prior/'receipt.json')
        controls.append(dict(case=case,receipt_sha256=file_sha(p/'receipt.json')))
    excluded=set();filter_receipt=None
    if filtered:
        failed=base/'block-v1-20261030-610/tasks/revision300-v-transition-batch'
        fr=json.loads((failed/'receipt.json').read_text())
        assert not fr['passed'] and file_sha(failed/'receipt.json')=='a4678ab3659badbc8b71823f94cb162309335ce0300b09ccacc9e26b84713e90'
        for name in ('transition-batch-drc.rpt','expected-edits.json','revision300-v-transition-batch.json'):
            assert file_sha(failed/name)==fr['outputs'][name]
        evidence=json.loads((failed/'revision300-v-transition-batch.json').read_text())
        assert not evidence['passed'] and evidence['native_candidate_count']==188 and evidence['added_markers']==98
        prior_markers=violations((source/'composed-native-drc.rpt').read_text())
        added=violations((failed/'transition-batch-drc.rpt').read_text())-prior_markers
        edited={p['net']for p in json.loads((failed/'expected-edits.json').read_text())['patches']}
        for marker in added:
            names=re.search(r'srcs: (.*?) bbox =',marker).group(1).split(' net:')
            hit=edited.intersection(n.removeprefix('net:').replace('\\','')for n in names)
            assert hit,'New marker has no edited participant; filtering cannot explain it'
            excluded.update(hit)
        assert len(excluded)==46 and sum(added.values())==98
        filter_receipt=file_sha(failed/'receipt.json')
    wanted=defaultdict(list)
    for row in d['markers']:
        name=row['marker']['net'].replace('\\','')
        if row['marker']['layer']=='metal3'and row['route_options']and name not in excluded:wanted[name].append(row)
    originals={};others=Counter();n0=0
    for record in records(source/'composed-candidate.def'):
        n0+=1;name=name_of(record)
        if name in wanted:assert name not in originals;originals[name]=record
        else:others[token_hash(record)]+=1
    assert set(originals)==set(wanted)
    edits={};expected={};patches=[];skipped=[];guards=set()
    for name,record in originals.items():
        header,paths,rects=decode(record);initial=list(paths)
        assert all(p[2]is None for path in paths for p in path['points'])
        for row in wanted[name]:
            selected=None
            for option in row['route_options']:
                a,b=tuple(option['a']),tuple(option['b'])
                assert (a[0]==b[0]or a[1]==b[1])and 0<abs(a[0]-b[0])+abs(a[1]-b[1])<=2000
                selected=choose(paths,a,b)or choose(paths,b,a)
                if selected:break
            if selected is None:skipped.append(row['index']);continue
            before=Counter(map(path_key,paths));paths=[p for p in paths if p is not selected['removed']]+selected['added']
            required=before.copy();required.subtract([path_key(selected['removed'])]);required+=Counter(map(path_key,selected['added']))
            assert Counter(map(path_key,paths))==required and selected['wire']in paths and selected['retained']in paths
            guards.update(selected.pop('guards'));patches.append(dict(index=row['index'],net=name,**selected))
        if Counter(map(path_key,paths))!=Counter(map(path_key,initial)):
            edits[name]=(paths,rects);expected[name]=(header,Counter(map(path_key,paths)),rects)
        else:others[token_hash(record)]+=1
    assert len(patches)>2 and {25,27}.issubset({p['index']for p in patches})
    if filtered:assert len(patches)==36 and len(edits)==36 and not(set(edits)&excluded)
    script='set_thread_count 16\nread_db {'+str(source/'composed-candidate.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    for name,bottom,top in sorted(guards):
        script+='set v [$tech findVia '+name+'];set seen {}\nforeach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}\n'
        script+='if {[lsort -unique $seen] ne [lsort [list '+bottom+' '+top+']]} {error "Via layers mismatch"}\n'
    script+='set wanted [dict create]\n'
    for name in edits:script+='dict set wanted [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]] 1\n'
    script+='set selected [dict create]\nforeach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}\n'
    script+='if {[dict size $selected] != %d} {error "Missing target"}\n'%len(edits)
    for name,(paths,rects)in edits.items():
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for p in paths:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
            for x,y,_ in p['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if p['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+p['via']+']\n'
        for (layer,x0,y0,x1,y1),count in rects.items():
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+layer+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db transition-batch.odb\nwrite_def transition-batch.def\ndrt::check_drc_cmd transition-batch-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'transition-batch.tcl').write_text(script);(out/'expected-edits.json').write_text(json.dumps(dict(patches=patches,skipped_marker_indices=skipped),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'transition-batch.tcl'],'transition-batch.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'transition-batch.def'):
        n1+=1;name=name_of(record)
        if name in edits:
            assert name not in found;found.add(name);h,p,r=decode(record);header,paths,rects=expected[name]
            exact=exact and Counter(map(path_key,p))==paths and r==rects and re.sub(r'\s+',' ',h)==re.sub(r'\s+',' ',header)
        else:actual[token_hash(record)]+=1
    exact=exact and found==set(edits)and actual==others and n0==n1
    old=violations((source/'composed-native-drc.rpt').read_text());new=violations((out/'transition-batch-drc.rpt').read_text())
    unchanged=all(file_sha(source/name)==sr['outputs'][name]for name in ('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt'))
    result=dict(passed=exact and unchanged and not(new-old)and sum(new.values())<172,diagnostic_only=True,physical_qualified=False,
                source_receipt_sha256=file_sha(source/'receipt.json'),localization_receipt_sha256=file_sha(prior/'receipt.json'),controls=controls,
                original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],exact_paths_rectangles_headers_and_other_net_tokens=exact,
                patch_count=len(patches),changed_nets=len(edits),patch_cases=dict(Counter(p['case']for p in patches)),skipped_marker_indices=skipped,
                filtered_from_failure_receipt_sha256=filter_receipt,excluded_patch_nets=sorted(excluded),
                native_original_count=sum(old.values()),native_candidate_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Actual composition of two controlled transition forms on old523 derived source, bounded1um and preserving old wires/RECTs. Whole native checker required; independent counts are not added. No current588 or connectivity/RCX/STA/full GDS/function/LEC/delivery qualification.')
    (out/'revision300-v-transition-batch.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Batch rejected; preserve original and all actual failures'
