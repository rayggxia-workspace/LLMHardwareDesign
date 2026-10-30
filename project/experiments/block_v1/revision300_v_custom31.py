"""Actual31-source bounded via repairs; fresh geometry required."""
from pathlib import Path
from collections import Counter
import json,hashlib,re

def probe(root,out,cpus,run,shard,combined=False,plan_name='custom31-plan-755.json',shard_run='756',mode_prefix='revision300-v-custom31-',compose_mode='revision300-v-custom31-compose',joint=False):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    assert not joint
    assert cpus==16 and shard in range(7)and combined==(shard==6)
    base=out.parents[2]
    source=base/'block-v1-20261031-705/tasks/revision300-v-joint-via-compose'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']
    source_names=('revision300-v-local-vias.json','local-candidate.odb','local-candidate.def','local-native-drc.rpt')
    for n in source_names:assert file_sha(source/n)==receipt['outputs'][n]
    prior=json.loads((source/source_names[0]).read_text())
    assert prior['passed']and prior['combined']and prior['candidate_native_count']==31 and prior['added_markers']==0
    plan_path=root/'project/experiments/block_v1'/plan_name
    plan=json.loads(plan_path.read_text());assert plan['source_native_count']==31 and plan['selected']
    neighborhood=base/'block-v1-20261031-710/tasks/revision300-v-latest-neighborhood'
    nr=json.loads((neighborhood/'receipt.json').read_text());assert nr['passed']
    for n in('revision300-v-latest-neighborhood.json','via-footprints.tsv','net-aliases.tsv','layer-dimensions.tsv','neighborhood.tsv'):
        assert file_sha(neighborhood/n)==nr['outputs'][n]
    assert file_sha(neighborhood/'neighborhood.tsv')==plan['geometry_sha256']
    topology=base/plan.get('observed_task','block-v1-20261031-664/tasks/revision300-v-repaired-topology')
    tr=json.loads((topology/'receipt.json').read_text());assert tr['passed']
    observed_hash=next(h for name,h in plan['inputs_sha256'].items()if name.endswith('/observed-routes.json'))
    assert file_sha(topology/'observed-routes.json')==tr['outputs']['observed-routes.json']==observed_hash
    if 'observed_receipt_sha256'in plan:assert file_sha(topology/'receipt.json')==plan['observed_receipt_sha256']
    for name,h in plan['inputs_sha256'].items():
        if name.split('/')[-1]in('revision300-v-latest-neighborhood.json','via-footprints.tsv','net-aliases.tsv','layer-dimensions.tsv'):
            assert file_sha(neighborhood/name.split('/')[-1])==h
        if name.startswith('project/'):
            assert file_sha(root/name)==h
        if name.endswith('/receipt.json'):assert file_sha(neighborhood/'receipt.json')==h
    observed=json.loads((topology/'observed-routes.json').read_text())
    independent=[];excluded=set();failure_filter=[]
    if combined:
        assert out.name==compose_mode
        covered=[]
        for s in range(6):
            folder=base/('block-v1-20261031-'+shard_run+'/tasks/'+mode_prefix+str(s))
            r=json.loads((folder/'receipt.json').read_text());assert r['mode']==folder.name
            for n in('revision300-v-local-vias.json','selected-via-edits.json','local-native-drc.rpt'):
                assert file_sha(folder/n)==r['outputs'][n]
            d=json.loads((folder/'revision300-v-local-vias.json').read_text())
            assert d['passed']==r['passed']and d['shard']==s and d['original_native_count']==31
            assert d['exact_normal_nets_headers_paths_rectangles']and d['original_inputs_unchanged']
            assert d['source_receipt_sha256']==file_sha(source/'receipt.json')and d['plan_sha256']==file_sha(plan_path)
            own=[p for p in plan['selected']if p['shard']==s]
            assert json.loads((folder/'selected-via-edits.json').read_text())==own
            assert d['selected_markers']==[p['original_index']for p in own]
            added=violations((folder/'local-native-drc.rpt').read_text())-violations((source/'local-native-drc.rpt').read_text())
            assert sum(added.values())==d['added_markers']and r['passed']==(not bool(added))
            modified={p['net']for p in own};participants=set()
            for marker in added:
                implicated=set(re.findall(r'net:([^ ]+)',marker))&modified
                assert implicated,'New marker has no attributed edited participant; do not blindly compose'
                participants.update(implicated)
            excluded.update(participants)
            failure_filter.append(dict(shard=s,passed=r['passed'],new_markers=list(added.elements()),excluded_modified_nets=sorted(participants)))
            covered.extend(d['selected_markers']);independent.append(dict(shard=s,passed=r['passed'],receipt_sha256=file_sha(folder/'receipt.json')))
        assert sorted(covered)==sorted(p['original_index']for p in plan['selected'])
    selected=[p for p in plan['selected']if p['net']not in excluded]if combined else[p for p in plan['selected']if p['shard']==shard]
    joint_prior=None;joint_native=None
    wanted={p['net']:p for p in selected};assert len(wanted)==len(selected)>0
    n0=0;originals={};others=Counter()
    for record in records(source/'local-candidate.def'):
        n0+=1;name=name_of(record)
        if name not in wanted:others[token_hash(record)]+=1;continue
        assert name not in originals
        header,paths,rects=decode(record);old=observed[name]
        assert Counter(map(path_key,paths))==Counter(map(path_key,old['nonrect_paths']))
        assert re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',old['header'])
        assert all(v is None for p in paths for x,y,v in p['points'])
        originals[name]=(header,paths,rects)
    assert set(originals)==set(wanted)and n0==562494
    script='set_thread_count 16\nread_db {'+str(source/'local-candidate.odb')+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\nset wanted [dict create]\n'
    if 'required_manufacturing_grid_dbu'in plan:
        script+='if {[$tech getManufacturingGrid] != %d} {error {Manufacturing grid mismatch}}\n'%plan['required_manufacturing_grid_dbu']
        assert all(v%plan['required_manufacturing_grid_dbu']==0 for edit in selected for layer,box in edit['new_shapes']for v in box)

    for name in wanted:script+='dict set wanted [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]] 1\n'
    script+='set selected [dict create]\nforeach net [$block getNets] {set name [string map [list [format %c 92] {}] [$net getName]];if {[dict exists $wanted $name]} {if {[dict exists $selected $name]} {error "Ambiguous target"};dict set selected $name $net}}\n'
    script+='if {[dict size $selected] != %d} {error "Missing target"}\n'%len(wanted)
    foot={}
    fp=neighborhood/'via-footprints.tsv'
    nr=json.loads((fp.parent/'receipt.json').read_text());assert nr['passed']and file_sha(fp)==nr['outputs'][fp.name]
    for line in fp.read_text().splitlines():
        v,l,*box=line.split('\t');foot.setdefault(v,[]).append((l,list(map(int,box))))
    from revision300_v_marker_probe import area
    geo_meta=json.loads((neighborhood/'revision300-v-latest-neighborhood.json').read_text())
    aliases={bytes.fromhex(v).decode().replace(chr(92),''):alias for alias,v in(line.split('\t')for line in(neighborhood/'net-aliases.tsv').read_text().splitlines())}
    shapes={}
    for line in(neighborhood/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,alias,layer,kind,*box=line.split('\t');shapes.setdefault(int(i),[]).append((alias,layer,kind,list(map(int,box))))
    used={e['new']['via']for p in selected for e in p['edits']}
    for name in sorted(used):
        definition=plan['custom_vias'][name];old_name=definition['source'];target=definition['target'];rows=definition['boxes']
        assert name not in foot and target=='metal3'
        assert Counter((l,tuple(q))for l,q in rows if l!=target)==Counter((l,tuple(q))for l,q in foot[old_name]if l!=target)
        foot[name]=rows
        script+='if {[$tech findVia '+name+'] != "NULL"} {error {Custom via already exists}}\n'
        script+='set custom [odb::dbTechVia_create $tech '+name+']\n'
        for l,q in rows:script+='odb::dbBox_create $custom [$tech findLayer '+l+'] '+' '.join(map(str,q))+'\n'
        expected_rows=' '.join('{'+l+' '+' '.join(map(str,q))+'}'for l,q in rows)
        script+='set got {}\nforeach box [$custom getBoxes] {lappend got [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}\n'
        script+='if {[lsort $got] ne [lsort {'+expected_rows+'}]} {error {Custom via actual shape mismatch}}\n'
    for p in selected:
        marker=geo_meta['markers'][p['original_index']];assert marker['net']==p['net']and marker['layer']=='metal3'
        own=[q for a,l,k,q in shapes[p['original_index']]if a==aliases[p['net']]and l=='metal3'and not k.endswith('obstruction')]
        for e in p['edits']:
            a=e['old_pad'];q=e['new_pad'];assert q[0]<=a[0]and q[1]<=a[1]and q[2]>=a[2]and q[3]>=a[3]
            assert area(own,q)==(q[2]-q[0])*(q[3]-q[1]),'New via enclosure must add zero metal union area'
            x,y=e['old']['points'][0][:2]
            assert [l for l,r in foot[e['new']['via']]if l=='metal3']==['metal3']
            assert next([r[0]+x,r[1]+y,r[2]+x,r[3]+y]for l,r in foot[e['new']['via']]if l=='metal3')==q
    expected={}
    for name,p in wanted.items():
        header,paths,rects=originals[name];before=Counter(map(path_key,paths));after=list(paths)
        for edit in p['edits']:
            old=edit['old'];new=edit['new'];changed=edit['changed_layer']
            assert old['points']==new['points']and old['layer']==new['layer']and old['via']!=new['via']
            assert before[path_key(old)]==1 and before[path_key(new)]==0
            old_fixed=Counter((l,tuple(box))for l,box in foot[old['via']]if l!=changed)
            new_fixed=Counter((l,tuple(box))for l,box in foot[new['via']]if l!=changed)
            assert old_fixed==new_fixed,'Cut and opposite-layer metal must remain identical'
            after[next(j for j,path in enumerate(after)if path_key(path)==path_key(old))]=new
        for proof in p['contact_proof']:
            from revision300_v_clearance_corners import intersect
            assert intersect(proof['old_pad'],proof['old_neighbor'])and intersect(proof['new_pad'],proof['new_neighbor'])
        required=Counter(map(path_key,after))
        assert Counter(map(path_key,[v for v in after if not v['via']]))==Counter(map(path_key,[v for v in paths if not v['via']]))
        assert Counter((v['layer'],tuple(tuple(p)for p in v['points']))for v in after if v['via'])==Counter((v['layer'],tuple(tuple(p)for p in v['points']))for v in paths if v['via'])
        expected[name]=(header,required,rects)
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,_ in v['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
        for (l,x0,y0,x1,y1),count in rects.items():
            for _ in range(count):script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+l+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db local-candidate.odb\nwrite_def local-candidate.def\ndrt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'remaining-vias.tcl').write_text(script);(out/'selected-via-edits.json').write_text(json.dumps(selected,indent=2)+'\n')
    (out/'failure-filter.json').write_text(json.dumps(dict(actual_shards=failure_filter,excluded_nets=sorted(excluded),retained=len(selected)),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'remaining-vias.tcl'],'remaining-vias.log')
    actual=Counter();found=set();exact=True;n1=0
    for record in records(out/'local-candidate.def'):
        n1+=1;name=name_of(record)
        if name not in expected:actual[token_hash(record)]+=1;continue
        assert name not in found;found.add(name)
        header,paths,rects=decode(record);h,required,rr=expected[name]
        exact=exact and re.sub(r'\s+',' ',header)==re.sub(r'\s+',' ',h)and Counter(map(path_key,paths))==required and rects==rr
    exact=exact and actual==others and found==set(expected)and n0==n1
    old=violations((source/'local-native-drc.rpt').read_text());new=violations((out/'local-native-drc.rpt').read_text());assert sum(old.values())==31
    unchanged=all(file_sha(source/n)==receipt['outputs'][n]for n in('local-candidate.odb','local-candidate.def','local-native-drc.rpt'))
    added_vs_prior=sum((new-joint_native).values())if joint else 0
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new)and added_vs_prior==0 and(not joint or bool(joint_native-new)),physical_qualified=False,shard=shard,combined=combined,joint_prior_binding=joint_prior,added_vs_prior_current=added_vs_prior,independent_shard_receipts=independent,excluded_modified_nets=sorted(excluded),
                plan_sha256=file_sha(plan_path),source_receipt_sha256=file_sha(source/'receipt.json'),source_inputs_sha256={n:receipt['outputs'][n]for n in('local-candidate.odb','local-candidate.def','local-native-drc.rpt')},
                exact_normal_nets_headers_paths_rectangles=exact,original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],
                selected_markers=[p['original_index']for p in selected],selected_nets=len(selected),original_native_count=31,candidate_native_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Actual custom via enclosures: same center/cut/opposite-pad, target pad is superset inside already existing same-net metal. No metal union added. Actual created via shape readback, everyNET/header/path/RECT and full native check. No final qualification transfer.')
    (out/'revision300-v-local-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; independent queue tasks continue'
