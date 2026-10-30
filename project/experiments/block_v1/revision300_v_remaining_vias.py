"""Bounded alternatives on the actual173-marker composition; no qualification."""
from collections import Counter
import hashlib,json,re


def probe(root,out,cpus,run,shard):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    assert cpus==16 and shard in range(6)
    base=out.parents[2]
    source=base/'block-v1-20261031-672/tasks/revision300-v-repaired-via-compose'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']
    for n in('revision300-v-repaired-vias.json','via-candidate.odb','via-candidate.def','via-native-drc.rpt'):
        assert file_sha(source/n)==receipt['outputs'][n]
    prior=json.loads((source/'revision300-v-repaired-vias.json').read_text())
    assert prior['passed']and prior['combined']and prior['candidate_native_count']==173 and prior['added_markers']==0
    plan=json.loads((root/'project/experiments/block_v1/remaining-via-plan-680.json').read_text())
    assert plan['source_native_count']==173 and len(plan['selected'])==70
    locations={
        'selected-corners.json':base/'block-v1-20261031-665/tasks/revision300-v-repaired-compose/selected-corners.json',
        'via-candidate-plan.json':base/'block-v1-20261031-664/tasks/revision300-v-repaired-topology/via-candidate-plan.json',
        'revision300-v-current-neighborhood.json':base/'block-v1-20261031-655/tasks/revision300-v-repaired-neighborhood/revision300-v-current-neighborhood.json'}
    for n,h in plan['inputs_sha256'].items():
        if n.split('/')[-1]in locations:assert file_sha(locations[n.split('/')[-1]])==h
    topology=base/'block-v1-20261031-664/tasks/revision300-v-repaired-topology'
    tr=json.loads((topology/'receipt.json').read_text());assert tr['passed']and file_sha(topology/'receipt.json')==prior['topology_receipt_sha256']
    assert file_sha(topology/'observed-routes.json')==tr['outputs']['observed-routes.json']
    observed=json.loads((topology/'observed-routes.json').read_text())
    selected=[p for p in plan['selected']if int.from_bytes(hashlib.sha256(p['net'].encode()).digest()[:4],'big')%6==shard]
    wanted={p['net']:p for p in selected};assert len(wanted)==len(selected)>0
    n0=0;originals={};others=Counter()
    for record in records(source/'via-candidate.def'):
        n0+=1;name=name_of(record)
        if name not in wanted:others[token_hash(record)]+=1;continue
        assert name not in originals
        header,paths,rects=decode(record);old=observed[name]
        assert Counter(map(path_key,paths))==Counter(map(path_key,old['nonrect_paths']))
        assert re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',old['header'])
        assert all(v is None for p in paths for x,y,v in p['points'])
        originals[name]=(header,paths,rects)
    assert set(originals)==set(wanted)and n0==562494
    script='set_thread_count 16\nread_db {'+str(source/'via-candidate.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nset wanted [dict create]\n'
    for name in wanted:script+='dict set wanted [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]] 1\n'
    script+='set selected [dict create]\nforeach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}\n'
    script+='if {[dict size $selected] != %d} {error "Missing target"}\n'%len(wanted)
    foot={}
    fp=base/'block-v1-20261031-655/tasks/revision300-v-repaired-neighborhood/via-footprints.tsv'
    nr=json.loads((fp.parent/'receipt.json').read_text());assert nr['passed']and file_sha(fp)==nr['outputs'][fp.name]
    for line in fp.read_text().splitlines():
        v,l,*box=line.split('\t');foot.setdefault(v,[]).append((l,list(map(int,box))))
    expected={}
    for name,p in wanted.items():
        header,paths,rects=originals[name];before=Counter(map(path_key,paths));removed=path_key(p['removed_via'])
        assert before[removed]==1 and before[path_key(p['retained_via'])]==1
        after=list(paths);after.pop(next(i for i,v in enumerate(after)if path_key(v)==removed))
        additions=[p['added_m2_wire']]+([p['moved_via']]if p['moved_via']else[])
        assert all(before[path_key(v)]==0 for v in additions)
        after.extend(additions);required=before.copy();required.subtract([removed]);required+=Counter(map(path_key,additions))
        assert Counter(map(path_key,after))==required
        assert all(required[path_key(v)]==before[path_key(v)]for v in p['preserved_source_wires'])
        # Retain the removed via's lower metal pad explicitly, preserving off-center contacts.
        rects=rects.copy();x,y=p['a']
        for l,(x0,y0,x1,y1)in foot[p['removed_via']['via']]:
            if l=='metal2':rects[(l,x+x0,y+y0,x+x1,y+y1)]+=1
        expected[name]=(header,required,rects)
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,_ in v['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
        for (l,x0,y0,x1,y1),count in rects.items():
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+l+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db remaining-candidate.odb\nwrite_def remaining-candidate.def\ndrt::check_drc_cmd remaining-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'remaining-vias.tcl').write_text(script);(out/'selected-via-edits.json').write_text(json.dumps(selected,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'remaining-vias.tcl'],'remaining-vias.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'remaining-candidate.def'):
        n1+=1;name=name_of(record)
        if name not in expected:actual[token_hash(record)]+=1;continue
        assert name not in found;found.add(name)
        header,paths,rects=decode(record);h,required,rr=expected[name]
        exact=exact and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h)and Counter(map(path_key,paths))==required and rects==rr
    exact=exact and actual==others and found==set(expected)and n0==n1
    old=violations((source/'via-native-drc.rpt').read_text());new=violations((out/'remaining-native-drc.rpt').read_text());assert sum(old.values())==173
    unchanged=all(file_sha(source/n)==receipt['outputs'][n]for n in('via-candidate.odb','via-candidate.def','via-native-drc.rpt'))
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),physical_qualified=False,shard=shard,
                source_receipt_sha256=file_sha(source/'receipt.json'),source_inputs_sha256={n:receipt['outputs'][n]for n in('via-candidate.odb','via-candidate.def','via-native-drc.rpt')},
                exact_normal_nets_headers_paths_rectangles=exact,original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],
                selected_markers=[p['index']for p in selected],selected_nets=len(selected),original_native_count=173,candidate_native_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Actual672173-marker copy; current250fills/45bridges retained. Bounded mixed/same-via alternatives, retain M3 wire and lower metal pad. Native0new/exact DEF required. No final connectivity/RCX/STA/GDS/function/LEC/interface qualification or transfer.')
    (out/'revision300-v-remaining-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; independent queue tasks continue'
