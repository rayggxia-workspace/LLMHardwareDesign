"""Bounded transition/stack controls on the composed failed V copy only."""
from collections import Counter
import json,re


def decode(record):
    from native_escape import parse
    from native_rect_completion import rectangles
    start=re.search(r'\+ ROUTED\s+',record);assert start
    pieces=re.split(r'\s+NEW\s+',record[start.end():].strip().removesuffix(';').strip())
    nonrect=[p for p in pieces if not re.search(r'\bRECT\b',p)]
    header,paths=parse(record[:start.start()]+'+ ROUTED '+' NEW '.join(nonrect)+' ;')
    return header,paths,Counter((layer,*box)for _,layer,*box in rectangles(record))


def probe(root,out,cpus,run,case):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_via_batch import contains,name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    from revision300_v_transition_alternatives import CASES,build
    assert cpus==16 and(case in ('mixed','stack')or case in CASES)
    base=out.parents[2];prior=base/'block-v1-20261030-605/tasks/revision300-v-remaining'
    pr=json.loads((prior/'receipt.json').read_text());assert pr['passed']
    f=prior/'revision300-v-remaining.json';assert file_sha(f)==pr['outputs'][f.name]
    report=json.loads(f.read_text());assert report['passed']and report['native_marker_count']==172
    source=base/'block-v1-20261030-598/tasks/revision300-v-geometry-compose'
    sr=json.loads((source/'receipt.json').read_text());assert sr['passed']
    assert file_sha(source/'receipt.json')==report['source_receipt_sha256']
    for name in ('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt'):
        assert file_sha(source/name)==sr['outputs'][name]
    index,target=CASES[case]if case in CASES else((25,'net80238')if case=='mixed'else(27,'input_mem[237][25]'))
    row=report['markers'][index];marker=row['marker']
    assert marker['layer']==('metal2'if case.startswith('alt-corner-')else'metal3')
    assert marker['net'].replace('\\','')==target
    if case not in CASES:
        assert len(row['route_options'])==1
        a,b=[tuple(row['route_options'][0][k])for k in ('a','b')]
        assert (a[0]==b[0]or a[1]==b[1])and 0<abs(a[0]-b[0])+abs(a[1]-b[1])<=2000
    target=marker['net'].replace('\\','');others=Counter();record0=None;n0=0
    for record in records(source/'composed-candidate.def'):
        n0+=1
        if name_of(record)==target:assert record0 is None;record0=record
        else:others[token_hash(record)]+=1
    assert record0 is not None
    header,paths,rects=decode(record0)
    assert all(p[2]is None for path in paths for p in path['points'])
    assert Counter(map(path_key,paths))==Counter(map(path_key,row['nonrect_def_paths']))
    if case not in CASES:
        wires=[p for p in paths if contains(p,'metal3',a,b)];assert len(wires)==1
    def via(point,layer):
        found=[p for p in paths if p['layer']==layer and p['via']and len(p['points'])==1 and tuple(p['points'][0][:2])==point]
        assert len(found)==1;return found[0]
    if case in CASES:
        alternative=build(paths,row,case);remove=alternative['removed'];additions=alternative['added']
        keep=alternative['retained'];wires=[alternative['wire']];guard_vias=alternative['guards']
    elif case=='mixed':
        bridge=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None)
        keep=via(a,'metal3');remove=via(b,'metal2')
        assert keep['via'].startswith('via3_')and remove['via'].startswith('via2_')
        assert not any(p['via']and p['layer']=='metal2'and tuple(p['points'][0][:2])==a for p in paths)
        assert any(contains(p,'metal4',a,a)for p in paths)and any(contains(p,'metal2',b,b)for p in paths)
        moved=dict(layer='metal2',points=[(*a,None)],via=remove['via']);additions=[bridge,moved]
        guard_vias=[(keep['via'],'metal3','metal4'),(remove['via'],'metal2','metal3')]
    else:
        bridge=dict(layer='metal2',points=[(*a,None),(*b,None)],via=None)
        remove=via(a,'metal2');keep=via(b,'metal2');lower=via(a,'metal1')
        assert remove['via'].startswith('via2_')and keep['via'].startswith('via2_')and lower['via'].startswith('via1_')
        assert any(contains(p,'metal2',b,b)for p in paths)
        additions=[bridge];guard_vias=[(remove['via'],'metal2','metal3'),(keep['via'],'metal2','metal3'),(lower['via'],'metal1','metal2')]
    updated=[p for p in paths if p is not remove]+additions
    expected=Counter(map(path_key,paths));expected.subtract([path_key(remove)]);expected+=Counter(map(path_key,additions))
    assert Counter(map(path_key,updated))==expected and wires[0]in updated and keep in updated
    script='set_thread_count 16\nread_db {'+str(source/'composed-candidate.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    for name,bottom,top in guard_vias:
        script+='set v [$tech findVia '+name+'];set seen {}\nforeach part [$v getBoxes] {set layer [[$part getTechLayer] getName];if {[string match metal* $layer]} {lappend seen $layer}}\n'
        script+='if {[lsort -unique $seen] ne [lsort [list '+bottom+' '+top+']]} {error "Actual via metal layers mismatch"}\n'
    script+='set wanted [encoding convertfrom utf-8 [binary decode hex {'+target.encode().hex()+'}]]\nset selected {}\nforeach net [$block getNets] {if {[string map [list [format %c 92] {}] [$net getName]] eq $wanted} {lappend selected $net}}\nif {[llength $selected]!=1} {error "Ambiguous target"}\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [[lindex $selected 0] getWire]\n'
    for p in updated:
        script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
        for x,y,_ in p['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
        if p['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+p['via']+']\n'
    for (layer,x0,y0,x1,y1),count in rects.items():
        for _ in range(count):
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+layer+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
    script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\nwrite_db transition-candidate.odb\nwrite_def transition-candidate.def\ndrt::check_drc_cmd transition-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'transition.tcl').write_text(script)
    (out/'expected-edit.json').write_text(json.dumps(dict(case=case,marker=marker,removed=remove,added=additions,**{('retained_path'if case in CASES else'retained_via'):keep,('preserved_wire'if case in CASES else'preserved_m3_wire'):wires[0]},original_rectangles=list(rects.elements())),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'transition.tcl'],'transition.log')
    actual=Counter();n1=0;found=False;exact=False
    for record in records(out/'transition-candidate.def'):
        n1+=1
        if name_of(record)==target:
            assert not found;found=True;h,p,r=decode(record)
            exact=Counter(map(path_key,p))==expected and r==rects and re.sub(r'\s+',' ',h)==re.sub(r'\s+',' ',header)
        else:actual[token_hash(record)]+=1
    old=violations((source/'composed-native-drc.rpt').read_text());new=violations((out/'transition-native-drc.rpt').read_text())
    unchanged=all(file_sha(source/name)==sr['outputs'][name]for name in ('composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt'))
    exact=exact and found and n0==n1 and actual==others
    result=dict(passed=exact and unchanged and not(new-old)and sum(new.values())<sum(old.values()),
                diagnostic_only=True,physical_qualified=False,case=case,source_marker=marker,
                localization_receipt_sha256=file_sha(prior/'receipt.json'),source_receipt_sha256=file_sha(source/'receipt.json'),
                input_odb_sha256=sr['outputs']['composed-candidate.odb'],original_inputs_unchanged=unchanged,
                all_normal_nets_and_target_paths_rectangles_exact=exact,normal_net_counts=[n0,n1],
                native_original_count=sum(old.values()),native_candidate_count=sum(new.values()),added_markers=sum((new-old).values()),
                removed_markers=sum((old-new).values()),scope='One actual old523 composed-source transition control. Preserve all old wire metal and RECTs; explicit via/M2 alternate path only. No current588 or terminal-connectivity/RCX/STA/full GDS/function/LEC/delivery qualification.')
    (out/'revision300-v-transition.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Transition control rejected; preserve original and failure'
