"""Generate bounded corner fills from complete current-source neighborhoods.

Scalar spacing and exact foreign geometry prune candidates only. They never
replace whole-chip native DRC, GDS DRC, connectivity or electrical reception.
"""
from collections import defaultdict
import hashlib
from revision300_v_corner_probe import candidates
from revision300_v_marker_probe import area


def intersect(a,b):
    r=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    return r if r[0]<r[2] and r[1]<r[3] else None


def outside_area(known,box):
    return (box[2]-box[0])*(box[3]-box[1])-area(known,box)


def generate(report, geometry, names, dimensions):
    assert report['passed'] and report['original_inputs_unchanged']
    aliases={}
    for alias,encoded in (line.split('\t')for line in names.read_text().splitlines()):
        name=bytes.fromhex(encoded).decode().replace('\\','')
        assert name not in aliases,'Ambiguous normalized net identity'
        aliases[name]=alias
    spacing={layer:int(s) for layer,w,s in (line.split('\t')for line in dimensions.read_text().splitlines())}
    shapes=defaultdict(list)
    for line in geometry.read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,alias,layer,kind,*box=line.split('\t')
        shapes[int(i)].append(dict(alias=alias,layer=layer,shape=kind,bbox_dbu=list(map(int,box))))
    rows=[]
    for i,m in enumerate(report['markers']):
        own=aliases[m['net']]
        rows.append(dict(marker=m,same_net_nearby_rectangles=[r for r in shapes[i]if r['alias']==own and r['layer']==m['layer']]))
    proposed,skipped=candidates(rows)
    retained=[];rejected=[]
    for p in proposed:
        i=p['index'];window=report['windows'][i];box=p['bbox_dbu'];s=spacing[p['layer']]
        assert s>0 and window['index']==i
        a,b,c,d=window['bbox_dbu']
        # Full inflated proposal must remain in the exported window. A clipped
        # export cannot authorize clearance outside its observed neighborhood.
        if box[0]-s<a or box[1]-s<b or box[2]+s>c or box[3]+s>d:
            rejected.append(dict(index=i,reason='proposal-margin-outside-observed-window'));continue
        alias=aliases[p['net'].replace('\\','')]
        own=[r['bbox_dbu']for r in shapes[i]if r['alias']==alias and r['layer']==p['layer'] and not r['shape'].endswith('obstruction')]
        collisions=[]
        for r in shapes[i]:
            if r['layer']!=p['layer'] or r['alias']==alias:continue
            x0,y0,x1,y1=r['bbox_dbu']
            overlap=intersect(box,[x0-s,y0-s,x1+s,y1+s])
            if overlap and outside_area(own,overlap)>0:
                collisions.append(dict(alias=r['alias'],shape=r['shape'],bbox_dbu=r['bbox_dbu']))
        if collisions:
            rejected.append(dict(index=i,reason='new-area-enters-foreign-spacing-or-obs',collisions=collisions));continue
        p=dict(p,scalar_spacing_dbu=s,own_coverage_boxes=own)
        retained.append(p)
    # Individually clear fills can conflict with one another. Prune those
    # interactions before splitting by net; the combined native check remains
    # mandatory even after every individual shard passes.
    conflicts=set()
    for i,p in enumerate(retained):
        for q in retained[:i]:
            if p['net']==q['net'] or p['layer']!=q['layer']:continue
            a,b,c,d=q['bbox_dbu'];s=max(p['scalar_spacing_dbu'],q['scalar_spacing_dbu'])
            overlap=intersect(p['bbox_dbu'],[a-s,b-s,c+s,d+s])
            if overlap and outside_area(p['own_coverage_boxes'],overlap)>0:
                conflicts.update((p['index'],q['index']))
    selected=[]
    for p in retained:
        if p['index']in conflicts:
            rejected.append(dict(index=p['index'],reason='new-proposal-pair-spacing-conflict'));continue
        p.pop('own_coverage_boxes')
        p['shard']=int.from_bytes(hashlib.sha256(p['net'].encode()).digest()[:4],'big')%6
        selected.append(p)
    assert len({p['index']for p in selected})==len(selected)
    return dict(selected=selected,skipped=skipped,rejected=rejected,
                shards=sorted({p['shard']for p in selected}),physical_qualified=False,
                scope='Complete-neighborhood, bounded scalar-spacing/new-area pruning only. Six disjoint net-hash shards permit independent16CPU native checks; combined whole-native check and all final gates remain mandatory. No blanket layer upgrade or source qualification transfer.')


def probe(root,out,cpus,run,shard,repaired=False):
    from pathlib import Path
    from collections import Counter
    import json,re
    from io_slots import file_sha
    from revision300_v_corner_probe import def_content,violations
    assert cpus==16 and shard in range(7)
    assert not(repaired and shard==6),'Repaired-source compose requires its own actual shard receipts'
    assert shard!=6 or out.name=='revision300-v-clearance-compose'
    base=out.parents[2]
    prior=base/('block-v1-20261031-655/tasks/revision300-v-repaired-neighborhood' if repaired else
                'block-v1-20261031-638/tasks/revision300-v-current-neighborhood')
    receipt=json.loads((prior/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode']==prior.name
    names=('revision300-v-current-neighborhood.json','neighborhood.tsv','net-aliases.tsv','layer-dimensions.tsv','native-whole-drc.rpt')
    for name in names:assert file_sha(prior/name)==receipt['outputs'][name]
    report=json.loads((prior/names[0]).read_text())
    assert report['source_native_count']==(471 if repaired else 467) and report['original_inputs_unchanged']
    source=Path(report['source_final_task'])
    assert source==base/('block-v1-20261031-630/tasks/revision300-final-source-v' if repaired else
                         'block-v1-20261030-589/tasks/revision300-final-source-v')
    assert file_sha(source/'receipt.json')==report['source_receipt_sha256']
    results=source/'flow/results/nangate45/bv1_block_v1_v/base'
    for name,h in report['source_inputs_sha256'].items():assert file_sha(results/name)==h
    plan=generate(report,prior/'neighborhood.tsv',prior/'net-aliases.tsv',prior/'layer-dimensions.tsv')
    selected=[p for p in plan['selected']if p['shard']==shard]
    failure_filter=None
    if shard==6:
        old=violations((prior/'native-whole-drc.rpt').read_text())
        modified={p['net'].replace('\\','')for p in plan['selected']};affected=set();evidence=[]
        for n in range(6):
            folder=base/('block-v1-20261031-641/tasks/revision300-v-clearance-corners-'+str(n))
            r=json.loads((folder/'receipt.json').read_text())
            for filename in ('revision300-v-clearance-corners.json','corner-native-drc.rpt','clearance-plan.json'):
                assert file_sha(folder/filename)==r['outputs'][filename]
            previous=json.loads((folder/'revision300-v-clearance-corners.json').read_text())
            assert previous['source_receipt_sha256']==report['source_receipt_sha256']
            assert previous['neighborhood_receipt_sha256']==file_sha(prior/'receipt.json')
            assert json.loads((folder/'clearance-plan.json').read_text())==plan
            assert previous['passed']==r['passed'] and previous['shard']==n
            new=violations((folder/'corner-native-drc.rpt').read_text());added=new-old
            assert sum(added.values())==previous['added_markers']
            assert bool(added)==(not r['passed'])
            participants={v.replace('\\','')for block in added for v in re.findall(r'net:(\S+)',block)}
            changed=participants&modified
            if added:assert changed
            affected.update(changed)
            evidence.append(dict(shard=n,receipt_sha256=file_sha(folder/'receipt.json'),added=list(added.elements()),modified_participant_nets=sorted(changed)))
        selected=[p for p in plan['selected']if p['net'].replace('\\','')not in affected]
        assert len(affected)==5 and len(selected)==253
        failure_filter=dict(affected_modified_nets=sorted(affected),actual_independent_differences=evidence,
                            filtered_indices=[p['index']for p in plan['selected']if p not in selected],
                            scope='Remove all modified nets in actual641 added markers; fresh combined check, not sum of independent removals.')
        (out/'failure-filter.json').write_text(json.dumps(failure_filter,indent=2)+'\n')
    assert selected,'Empty shard is not an executable EDA task'
    (out/'clearance-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'selected-corners.json').write_text(json.dumps(selected,indent=2)+'\n')
    groups=defaultdict(list)
    for p in selected:groups[p['net'].replace('\\','')].append(p)
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'
    script+='set block [ord::get_db_block]\nset tech [ord::get_db_tech]\nset exact [dict create]\n'
    script+='foreach net [$block getNets] {set plain [string map [list [format %c 92] {}] [$net getName]];dict lappend exact $plain $net}\n'
    for name,rows in sorted(groups.items()):
        script+='set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {'+name.encode().hex()+'}]]]\n'
        script+='if {[llength $matches]!=1} {error "Ambiguous or missing target net"}\nset net [lindex $matches 0]\n'
        script+='if {[$net getWire] eq "NULL"} {error "Target wire missing"}\nset enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_append $enc [$net getWire]\n'
        for p in rows:
            x0,y0,x1,y1=p['bbox_dbu']
            script+='odb::dbWireEncoder_newPath $enc [$tech findLayer '+p['layer']+'] ROUTED\n'
            script+='odb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n'%(x0,y0,x1-x0,y1-y0)
        script+='odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script+='write_db corner-candidate.odb\nwrite_def corner-candidate.def\n'
    script+='drt::check_drc_cmd corner-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'corner-probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'corner-probe.tcl'],'corner-probe.log')
    before,routes0,n0=def_content(results/'6_final.def')
    after,routes1,n1=def_content(out/'corner-candidate.def')
    expected=Counter((p['net'].replace('\\',''),p['layer'],*p['bbox_dbu'])for p in selected)
    exact=after==before+expected and routes0==routes1 and n0==n1
    old=violations((prior/'native-whole-drc.rpt').read_text())
    new=violations((out/'corner-native-drc.rpt').read_text())
    unchanged=all(file_sha(results/name)==h for name,h in report['source_inputs_sha256'].items())
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),
                diagnostic_only=True,physical_qualified=False,shard=shard,combined=shard==6,failure_filter=failure_filter,
                source_receipt_sha256=report['source_receipt_sha256'],source_inputs_sha256=report['source_inputs_sha256'],
                neighborhood_receipt_sha256=file_sha(prior/'receipt.json'),
                complete_plan_sha256=file_sha(out/'clearance-plan.json'),original_inputs_unchanged=unchanged,
                selected_corners=len(selected),selected_nets=len(groups),normal_net_counts=[n0,n1],
                exact_expected_rectangles_and_nonrect_net_routes=exact,
                original_native_count=sum(old.values()),candidate_native_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope=f'Pinned {source.parent.parent.name} full-neighborhood-pruned fills on actual{report["source_native_count"]} source. Shard6, when enabled, binds its own actual failures before combined checking, not an independent-count sum. Full native0new and exact DEF delta required; remaining native items and all final gates still mandatory. No final qualification transfer.')
    (out/'revision300-v-clearance-corners.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; other independent tasks continue'
