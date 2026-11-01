"""R-specific source-bound same-net via-pair copy probes; no final qualification."""
from collections import Counter
import hashlib,json,re


def probe(root,out,cpus,run,shard,alternate=False,stack=False):
    from pathlib import Path
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    from revision300_v_gds_repair import nonnet
    assert cpus==16 and shard in range(6)
    base=out.parents[2];top=base/'block-v1-20261101-857/tasks/revision300-r-topology'
    tr=json.loads((top/'receipt.json').read_text());assert tr['passed']and tr['mode']==top.name
    for n in ('revision300-r-topology.json','observed-routes.json','via-candidate-plan.json'):
        assert file_sha(top/n)==tr['outputs'][n]
    prior=json.loads((top/'revision300-r-topology.json').read_text())
    assert prior['passed']and prior['original_inputs_unchanged']and prior['selected_marker_count']==53
    source=base/'block-v1-20261101-828/tasks/revision300-final-source-r'
    assert file_sha(source/'receipt.json')==prior['source_receipt_sha256']=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    results=source/'flow/results/nangate45/bv1_block_v1_r/base'
    for n,h in prior['source_inputs_sha256'].items():assert file_sha(results/n)==h
    neigh=base/'block-v1-20261101-851/tasks/revision300-r-current-neighborhood'
    nr=json.loads((neigh/'receipt.json').read_text());assert nr['passed']and file_sha(neigh/'receipt.json')==prior['neighborhood_receipt_sha256']
    assert file_sha(neigh/'native-whole-drc.rpt')==nr['outputs']['native-whole-drc.rpt']
    assert not stack or alternate
    plan_path=root/('project/experiments/block_v1/r-stack-plan-873.json'if stack else 'project/experiments/block_v1/r-alternate-plan-869.json')if alternate else top/'via-candidate-plan.json'
    plan=json.loads(plan_path.read_text())
    assert len(plan['selected'])==len({p['net']for p in plan['selected']})==(94 if stack else 64 if alternate else 53)
    foot={}
    if alternate:
        assert plan['source_receipt_sha256']==prior['source_receipt_sha256']and plan['source_native_count']==584
        assert file_sha(top/'observed-routes.json')==plan['observed_sha256']and file_sha(neigh/'neighborhood.tsv')==plan['geometry_sha256']==nr['outputs']['neighborhood.tsv']
        for n,h in plan['inputs_sha256'].items():assert file_sha(neigh/n)==h==nr['outputs'][n]
        if stack:assert file_sha(root/'project/experiments/block_v1/r-alternate-plan-869.json')==plan['other_plan_sha256']
        for line in(neigh/'via-footprints.tsv').read_text().splitlines():
            v,l,*box=line.split('\t');foot.setdefault(v,[]).append((l,list(map(int,box))))
    selected=[p for p in plan['selected']if int(hashlib.sha256(p['net'].encode()).hexdigest(),16)%6==shard]
    assert selected,'No empty filler task'
    wanted={p['net']:p for p in selected};observed=json.loads((top/'observed-routes.json').read_text())
    original={};others=Counter();n0=0
    for record in records(results/'6_final.def'):
        n0+=1;name=name_of(record)
        if name not in wanted:others[token_hash(record)]+=1;continue
        header,paths,rects=decode(record);old=observed[name]
        assert name not in original and token_hash(record)==old['original_record_token_sha256']
        assert all(v is None for p in paths for x,y,v in p['points'])
        original[name]=(header,paths,rects)
    assert set(original)==set(wanted)and n0==prior['normal_net_count']
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nif {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}\nset selected [dict create]\n'
    script+='foreach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];dict lappend selected $name $net}\n'
    expected={}
    for name,p in wanted.items():
        header,paths,rects=original[name];before=Counter(map(path_key,paths));remove=path_key(p['removed_via']);add=p['added_bridge']if alternate else p['added_m2_wire']
        assert before[remove]==1 and before[path_key(add)]==0
        if p['retained_via']:
            keep=path_key(p['retained_via']);assert before[keep]==1 and keep!=remove and p['retained_via']['points'][0][:2]==p['b']
        assert p['removed_via']['points'][0][:2]==p['a']
        assert add==dict(layer=p['retain_pad_layer']if alternate else 'metal2',points=[p['a']+[None],p['b']+[None]],via=None)
        assert any(path_key(v)in before for v in p['preserved_source_wires'])
        additions=[add]+([p['moved_via']]if alternate and p['moved_via']else [])
        assert all(before[path_key(v)]==0 for v in additions)
        if alternate and p['moved_via']:assert p['moved_via']==dict(layer=p['removed_via']['layer'],points=[p['b']+[None]],via=p['removed_via']['via'])
        if stack:assert p['moved_via']is None and p['retain_pad_layer']=='metal2'and p['removed_via']['layer']=='metal2'and p['removed_via']['via']==p['retained_via']['via']
        after=list(paths);after.pop(next(i for i,v in enumerate(after)if path_key(v)==remove));after.extend(additions)
        required=before.copy();required.subtract([remove]);required+=Counter(map(path_key,additions))
        assert Counter(map(path_key,after))==required and all(required[path_key(v)]==before[path_key(v)]for v in p['preserved_source_wires'])
        rects=rects.copy()
        if alternate:
            x,y=p['a']
            for l,(x0,y0,x1,y1)in foot[p['removed_via']['via']]:
                if l==p['retain_pad_layer']:rects[(l,x+x0,y+y0,x+x1,y+y1)]+=1
        expected[name]=(header,required,rects)
        script+='set matches [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nif {[llength $matches]!=1} {error {Ambiguous net}}\nset net [lindex $matches 0]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,_ in v['points']:
                assert x%10==y%10==0
                script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
        for (l,x0,y0,x1,y1),count in rects.items():
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+l+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db via-candidate.odb\nwrite_def via-candidate.def\ndrt::check_drc_cmd via-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'via-probe.tcl').write_text(script);(out/'selected-vias.json').write_text(json.dumps(selected,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'via-probe.tcl'],'via-probe.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'via-candidate.def'):
        n1+=1;name=name_of(record)
        if name not in expected:actual[token_hash(record)]+=1;continue
        assert name not in found;found.add(name);header,paths,rects=decode(record);h,required,rr=expected[name]
        exact=exact and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h)and Counter(map(path_key,paths))==required and rects==rr
    exact=exact and actual==others and found==set(expected)and n0==n1 and nonnet(results/'6_final.def')==nonnet(out/'via-candidate.def')
    old=violations((neigh/'native-whole-drc.rpt').read_text());new=violations((out/'via-native-drc.rpt').read_text());assert sum(old.values())==584
    unchanged=all(file_sha(results/n)==h for n,h in prior['source_inputs_sha256'].items())
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),diagnostic_only=True,physical_qualified=False,combined=False,shard=shard,
                alternate=alternate,stack=stack,source_receipt_sha256=prior['source_receipt_sha256'],source_inputs_sha256=prior['source_inputs_sha256'],topology_receipt_sha256=file_sha(top/'receipt.json'),plan_sha256=file_sha(plan_path),
                original_inputs_unchanged=unchanged,exact_normal_net_header_path_rect_and_nonnet_delta=exact,normal_net_counts=[n0,n1],selected_markers=[p['index']for p in selected],selected_nets=len(selected),
                original_native_count=584,candidate_native_count=sum(new.values()),added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Actual R828 source-bound independent copies using current R851/857 geometry. Full source wires retained. Base: one via removed plus M2 alternate. Alternate: via moved with adjacent bridge and old adjacent pad retained. Six shards are diagnostic only. Combined interactions, full signal connectivity and every fresh final gate mandatory; no qualification transfer.')
    (out/'revision300-r-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; independent tasks continue'
