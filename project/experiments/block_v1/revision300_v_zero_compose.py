"""Actual31-source bounded via repairs; fresh geometry required."""
from pathlib import Path
from collections import Counter
import json,hashlib,re

def probe(root,out,cpus,run,plan_name="zero31-plan-762.json",mode="revision300-v-zero31-compose"):
    shard=6;combined=True;joint=False
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_custom31 import decode_custom
    def decode(record):return decode_custom(record,plan['custom_vias'])
    from revision300_v_via_batch import name_of,token_hash
    from revision300_v_via_bridge import path_key
    from revision300_v_corner_probe import violations
    assert cpus==16 and out.name==mode
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
    independent=[];excluded=set();failure_filter=[];computed=[];joint_prior=None;joint_native=None
    old_native=violations((source/'local-native-drc.rpt').read_text())
    for group in plan['groups']:
        config=root/'project/experiments/block_v1'/group['plan'];assert file_sha(config)==group['plan_sha256']
        source_plan=json.loads(config.read_text());group_excluded=set()
        for binding in group['bindings']:
            i=binding['shard'];p=base/('block-v1-20261031-'+str(group['stage']))/'tasks'/(group.get('mode_exact')or group['prefix']+str(i))
            assert file_sha(p/'receipt.json')==binding['receipt_sha256']
            r=json.loads((p/'receipt.json').read_text());assert r['mode']==p.name
            for name in ('revision300-v-local-vias.json','selected-via-edits.json')+(()if group['kind']=='custom'else('local-native-drc.rpt',)):assert file_sha(p/name)==r['outputs'][name]
            d=json.loads((p/'revision300-v-local-vias.json').read_text());assert d['passed']==r['passed']and d['original_native_count']==31
            assert d['source_receipt_sha256']==file_sha(source/'receipt.json')and d['plan_sha256']==file_sha(config)
            assert d['exact_normal_nets_headers_paths_rectangles']and d['original_inputs_unchanged']
            own=[v for v in source_plan['selected']if v['shard']==i];assert json.loads((p/'selected-via-edits.json').read_text())==own
            native_report=p/'local-native-drc.rpt'
            if group['kind']=='custom':
                audit=d['read_only_audit'];assert audit['eda_rerun']is False
                failed=Path(audit['original_failed_task']);assert base in failed.resolve().parents
                assert file_sha(failed/'receipt.json')==audit['original_failed_receipt_sha256']
                fr=json.loads((failed/'receipt.json').read_text());assert not fr['passed']
                command=audit['actual_openroad_command'];assert command in fr['commands']and command['returncode']==0 and command['argv'][0]=='openroad'
                for filename,h in audit['actual_output_sha256'].items():assert file_sha(failed/filename)==h==fr['outputs'][filename]
                native_report=failed/'local-native-drc.rpt'
            current=violations(native_report.read_text());added=current-old_native;removed=old_native-current
            assert d['added_markers']==sum(added.values())and d['removed_markers']==sum(removed.values())and d['candidate_native_count']==sum(current.values())
            assert r['passed']==(not bool(added)and bool(removed))
            modified={v['net']for v in own};implicated=set()
            for marker in added:
                targets={name.replace('\\','')for name in re.findall(r'net:([^ ]+)',marker)}&modified
                assert targets,'New marker without edited participant';implicated.update(targets)
            if not removed:implicated.update(modified)
            group_excluded.update(implicated)
            failure_filter.append(dict(kind=group['kind'],shard=i,passed=r['passed'],added=list(added.elements()),removed=sum(removed.values()),excluded=sorted(implicated)))
            independent.append(dict(kind=group['kind'],stage=group['stage'],shard=i,receipt_sha256=file_sha(p/'receipt.json')))
        assert sorted(group_excluded)==group['excluded_nets'];excluded.update(group_excluded)
        computed.extend(dict(v,kind=group['kind'])for v in source_plan['selected']if v['net']not in group_excluded and('eligible_shards'not in group or v['shard']in group['eligible_shards']))
    assert computed==plan['selected'];selected=computed
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
    used={e['new']['via']for p in selected if p['kind']=='custom'for e in p['edits']}
    for name in sorted(used):
        definition=plan['custom_vias'][name];old_name=definition['source'];target=definition['target'];rows=definition['boxes']
        assert name not in foot and target=='metal3'
        assert Counter((l,tuple(q))for l,q in rows if l!=target)==Counter((l,tuple(q))for l,q in foot[old_name]if l!=target)
        foot[name]=rows
        script+='if {[$block findVia '+name+'] != "NULL"} {error {Custom via already exists}}\n'
        script+='set custom [odb::dbVia_create $block '+name+']\n'
        for l,q in rows:script+='odb::dbBox_create $custom [$tech findLayer '+l+'] '+' '.join(map(str,q))+'\n'
        expected_rows=' '.join('{'+l+' '+' '.join(map(str,q))+'}'for l,q in rows)
        script+='set got {}\nforeach box [$custom getBoxes] {lappend got [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}\n'
        script+='if {[lsort $got] ne [lsort {'+expected_rows+'}]} {error {Custom via actual shape mismatch}}\n'
    for p in selected:
        if p['kind']!='custom':continue
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
        if p['kind']in('pad','custom'):
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
        else:
            assert p['kind']=='m3'
            header,paths,rects=originals[name];before=Counter(map(path_key,paths));removed=path_key(p['removed_via'])
            assert before[removed]==1
            assert p['moved_via']['via']==p['removed_via']['via']and p['moved_via']['points'][0][:2]==p['b']
            assert p['removed_via']['points'][0][:2]==p['a']
            assert set(v['layer']for v in p['bridges'])=={'metal3',p['retain_pad_layer']}
            from revision300_v_clearance_corners import intersect
            for contact in p['retained_target_contacts']:
                assert any(l==contact['layer']and intersect(box,contact['box'])for l,box in p['new_shapes'])
            after=list(paths);after.pop(next(i for i,v in enumerate(after)if path_key(v)==removed))
            additions=p['bridges']+[p['moved_via']]
            assert all(before[path_key(v)]==0 for v in additions)
            after.extend(additions);required=before.copy();required.subtract([removed]);required+=Counter(map(path_key,additions))
            assert Counter(map(path_key,after))==required
            assert all(required[key]==count for key,count in Counter(map(path_key,[v for v in paths if not v['via']])).items())
            # Retain the old adjacent-layer pad explicitly, including off-center contacts.
            rects=rects.copy();x,y=p['a']
            for l,(x0,y0,x1,y1)in foot[p['removed_via']['via']]:
                if l==p['retain_pad_layer']:rects[(l,x+x0,y+y0,x+x1,y+y1)]+=1
        expected[name]=(header,required,rects)
        script+='set net [dict get $selected [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
        for v in after:
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+v['layer']+'] ROUTED\n'
            for x,y,_ in v['points']:script+='odb::dbWireEncoder_addPoint $enc %d %d\n'%(x,y)
            if v['via']:
                if v['via']in plan['custom_vias']:script+='odb::dbWireEncoder_addVia $enc [$block findVia '+v['via']+']\n'
                else:script+='odb::dbWireEncoder_addTechVia $enc [$tech findVia '+v['via']+']\n'
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
    result=dict(passed=not new and exact and unchanged and not(new-old)and bool(old-new)and added_vs_prior==0 and(not joint or bool(joint_native-new)),physical_qualified=False,shard=shard,combined=combined,joint_prior_binding=joint_prior,added_vs_prior_current=added_vs_prior,independent_shard_receipts=independent,excluded_modified_nets=sorted(excluded),
                plan_sha256=file_sha(plan_path),source_receipt_sha256=file_sha(source/'receipt.json'),source_inputs_sha256={n:receipt['outputs'][n]for n in('local-candidate.odb','local-candidate.def','local-native-drc.rpt')},
                exact_normal_nets_headers_paths_rectangles=exact,original_inputs_unchanged=unchanged,normal_net_counts=[n0,n1],
                selected_markers=[p['original_index']for p in selected],selected_nets=len(selected),original_native_count=31,candidate_native_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope='Actual31-net joint; custom via envelopes exported as blockVIAS, exact cut/opposite-pad, target metal superset inside existing union.19 actual independent/audit receipts, everyNET/header/path/RECT. Full native zero mandatory; all final gates separate.')
    (out/'revision300-v-local-vias.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; independent queue tasks continue'
