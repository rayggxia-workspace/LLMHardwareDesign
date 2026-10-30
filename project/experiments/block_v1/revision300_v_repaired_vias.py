"""Native-check bounded observed via-pair alternatives on current630 copies."""
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
    base=out.parents[2];prior=base/'block-v1-20261031-664/tasks/revision300-v-repaired-topology'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']
    for n in('revision300-v-repaired-topology.json','observed-routes.json','via-candidate-plan.json'):
        assert file_sha(prior/n)==receipt['outputs'][n]
    topology=json.loads((prior/'revision300-v-repaired-topology.json').read_text())
    assert topology['passed']and topology['original_inputs_unchanged']
    source=base/'block-v1-20261031-630/tasks/revision300-final-source-v'
    assert file_sha(source/'receipt.json')==topology['source_receipt_sha256']
    results=source/'flow/results/nangate45/bv1_block_v1_v/base'
    for n,h in topology['source_inputs_sha256'].items():assert file_sha(results/n)==h
    neighborhood=base/'block-v1-20261031-655/tasks/revision300-v-repaired-neighborhood'
    assert file_sha(neighborhood/'receipt.json')==topology['neighborhood_receipt_sha256']
    nr=json.loads((neighborhood/'receipt.json').read_text());assert nr['passed']
    native=neighborhood/'native-whole-drc.rpt';assert file_sha(native)==nr['outputs'][native.name]
    observed=json.loads((prior/'observed-routes.json').read_text())
    plan=json.loads((prior/'via-candidate-plan.json').read_text())
    selected=[p for p in plan['selected']if int.from_bytes(hashlib.sha256(p['net'].encode()).digest()[:4],'big')%6==shard]
    assert selected and len({p['net']for p in selected})==len(selected)
    wanted={p['net']:p for p in selected};originals={};others=Counter();n0=0
    for record in records(results/'6_final.def'):
        n0+=1;name=name_of(record)
        if name in wanted:
            assert name not in originals
            header,paths,rects=decode(record);old=observed[name]
            assert token_hash(record)==old['original_record_token_sha256']and not rects and not old['rectangles']
            assert re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',old['header'])
            assert Counter(map(path_key,paths))==Counter(map(path_key,old['nonrect_paths']))
            originals[name]=(header,paths)
        else:others[token_hash(record)]+=1
    assert set(originals)==set(wanted)and n0==topology['normal_net_count']
    expected={};edits={}
    for name,p in wanted.items():
        header,paths=originals[name];before=Counter(map(path_key,paths))
        removed=path_key(p['removed_via']);kept=path_key(p['retained_via']);added=path_key(p['added_m2_wire'])
        assert removed!=kept and before[removed]==before[kept]==1 and before[added]==0
        assert all(v is None for path in paths for x,y,v in path['points'])
        after=list(paths);after.pop(next(i for i,q in enumerate(after)if path_key(q)==removed));after.append(p['added_m2_wire'])
        required=before.copy();required.subtract([removed]);required+=Counter([added])
        assert Counter(map(path_key,after))==required and required[kept]==1
        assert all(required[path_key(w)]==before[path_key(w)]for w in p['preserved_source_wires'])
        expected[name]=(header,required);edits[name]=after
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    script+='set wanted [dict create]\n'
    for name in edits:script+='dict set wanted [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]] 1\n'
    script+='set selected [dict create]\nforeach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}\n'
    script+='if {[dict size $selected] != %d} {error "Missing target"}\n'%len(edits)
    for via in sorted({p['removed_via']['via']for p in selected}):
        script+='set v [$tech findVia '+via+'];if {$v eq "NULL"} {error "Missing observed tech via"};set layers {}\nforeach box [$v getBoxes] {set layer [[$box getTechLayer] getName];if {[string match metal* $layer]} {lappend layers $layer}}\nif {[lsort -unique $layers] ne {metal2 metal3}} {error "Unexpected via metal layers"}\n'
    for name,paths in edits.items():
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for p in paths:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
            for x,y,_ in p['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if p['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+p['via']+']\n'
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db via-candidate.odb\nwrite_def via-candidate.def\ndrt::check_drc_cmd via-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'via-probe.tcl').write_text(script)
    (out/'selected-via-edits.json').write_text(json.dumps(selected,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'via-probe.tcl'],'via-probe.log')
    actual=Counter();found=set();n1=0;exact=True
    for record in records(out/'via-candidate.def'):
        n1+=1;name=name_of(record)
        if name in edits:
            assert name not in found;found.add(name);header,paths,rects=decode(record);h,required=expected[name]
            exact=exact and not rects and Counter(map(path_key,paths))==required and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h)
        else:actual[token_hash(record)]+=1
    exact=exact and actual==others and found==set(edits)and n0==n1
    old=violations(native.read_text());new=violations((out/'via-native-drc.rpt').read_text())
    assert sum(old.values())==471
    unchanged=all(file_sha(results/n)==h for n,h in topology['source_inputs_sha256'].items())
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),physical_qualified=False,diagnostic_only=True,
                shard=shard,selected_markers=[p['index']for p in selected],selected_nets=len(edits),normal_net_counts=[n0,n1],
                source_receipt_sha256=topology['source_receipt_sha256'],topology_receipt_sha256=file_sha(prior/'receipt.json'),
                source_inputs_sha256=topology['source_inputs_sha256'],original_inputs_unchanged=unchanged,
                exact_all_normal_nets_headers_paths_rectangles=exact,original_native_count=sum(old.values()),
                candidate_native_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Current630 bounded same-via2-pair alternatives on a copy; retained source M3 wire and second via, explicit alternate M2 bridge. Whole native0new/exact DEF required. Not combined with250 fills or other shards; terminal connectivity/RCX/STA/fullGDS/function/LEC/sixfiles/geometry/allport still required.')
    (out/'revision300-v-repaired-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed via shard; other independent tasks continue'
