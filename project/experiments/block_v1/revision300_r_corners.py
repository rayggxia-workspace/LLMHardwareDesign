"""Bounded independent corner candidates on R828 copies; no qualification transfer."""
from pathlib import Path
from collections import Counter,defaultdict
import json,re
from revision300_v_clearance_corners import generate
from revision300_v_gds_repair import nonnet

def probe(root,out,cpus,run,shard,ns_case=None):
    from pathlib import Path
    from collections import Counter
    import json,re
    from io_slots import file_sha
    from revision300_v_corner_probe import def_content,violations
    assert cpus==16 and shard in range(7)and(ns_case is None or ns_case in range(9))
    base=out.parents[2]
    prior=base/'block-v1-20261101-851/tasks/revision300-r-current-neighborhood'
    receipt=json.loads((prior/'receipt.json').read_text())
    assert receipt['passed'] and receipt['mode']==prior.name
    names=('revision300-r-current-neighborhood.json','neighborhood.tsv','net-aliases.tsv','layer-dimensions.tsv','native-whole-drc.rpt')
    for name in names:assert file_sha(prior/name)==receipt['outputs'][name]
    report=json.loads((prior/names[0]).read_text())
    assert report['source_native_count']==584 and report['original_inputs_unchanged']
    source=Path(report['source_final_task'])
    assert source==base/'block-v1-20261101-828/tasks/revision300-final-source-r'
    assert report['source_receipt_sha256']=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    assert file_sha(source/'receipt.json')==report['source_receipt_sha256']
    results=source/'flow/results/nangate45/bv1_block_v1_r/base'
    for name,h in report['source_inputs_sha256'].items():assert file_sha(results/name)==h
    plan=generate(report,prior/'neighborhood.tsv',prior/'net-aliases.tsv',prior/'layer-dimensions.tsv')
    offgrid=[p for p in plan['selected']if any(v%10 for v in p['bbox_dbu'])]
    plan['rejected'] += [dict(index=p['index'],reason='not-on-frozen10DBU-grid')for p in offgrid]
    plan['selected']=[p for p in plan['selected']if p not in offgrid]
    plan['shards']=sorted({p['shard']for p in plan['selected']})
    selected=[p for p in plan['selected']if p['shard']==shard]
    failure_filter=[]
    if shard==6 and ns_case is None:
        excluded=set();covered=[]
        for s in range(6):
            task=base/('block-v1-20261101-857/tasks/revision300-r-clearance-corners-'+str(s))
            rr=json.loads((task/'receipt.json').read_text())
            for n in ('revision300-r-clearance-corners.json','selected-corners.json','corner-native-drc.rpt'):
                assert file_sha(task/n)==rr['outputs'][n]
            d=json.loads((task/'revision300-r-clearance-corners.json').read_text())
            assert d['shard']==s and d['passed']==rr['passed']and d['source_receipt_sha256']==report['source_receipt_sha256']
            assert d['exact_expected_rectangles_and_nonrect_net_routes']and d['original_inputs_unchanged']
            own=[p for p in plan['selected']if p['shard']==s]
            assert json.loads((task/'selected-corners.json').read_text())==own
            added=violations((task/'corner-native-drc.rpt').read_text())-violations((prior/'native-whole-drc.rpt').read_text())
            assert sum(added.values())==d['added_markers']and bool(added)==(not rr['passed'])
            participants=set()
            for marker in added:
                implicated=set(re.findall(r'net:([^ ]+)',marker))&{p['net'].replace('\\','')for p in own}
                assert implicated,'New marker has no edited participant; refuse blind composition'
                participants.update(implicated)
            excluded.update(participants);covered.extend(p['index']for p in own)
            failure_filter.append(dict(shard=s,receipt_sha256=file_sha(task/'receipt.json'),added_markers=list(added.elements()),excluded_nets=sorted(participants)))
        assert sorted(covered)==sorted(p['index']for p in plan['selected'])
        selected=[p for p in plan['selected']if p['net'].replace('\\','')not in excluded]
    if ns_case is not None:
        assert shard==6
        marker=report['markers'][583]
        assert marker==dict(net='net131530',layer='metal2',bbox_dbu=[3712720,1580599,3712800,1580601])
        boxes=[[3712720,1580590,3712800,1580610],[3712710,1580590,3712810,1580610],[3712720,1580530,3712800,1580670],
               [3712660,1580530,3712860,1580670],[3712660,1580460,3712860,1580740],[3712660,1580320,3712860,1580880],
               [3712660,1580530,3712800,1580670],[3712660,1580460,3712800,1580740],[3712660,1580390,3712860,1580810]]
        box=boxes[ns_case];assert all(v%10==0 for v in box)
        from revision300_v_clearance_corners import intersect,outside_area
        aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(prior/'net-aliases.tsv').read_text().splitlines())}
        own=aliases['net131530'];shapes=[]
        for line in(prior/'neighborhood.tsv').read_text().splitlines():
            if not line or line.startswith('#'):continue
            i,a,l,k,*coords=line.split('\t')
            if int(i)==583 and l=='metal2':shapes.append((a,k,list(map(int,coords))))
        coverage=[b for a,k,b in shapes if a==own and not k.endswith('obstruction')]
        if ns_case>=3:assert outside_area(coverage,box)>0,'Wider NS trial must add actual area, not repeat redundant seam coverage'
        spacing=dict((l,int(s))for l,w,s in(line.split('\t')for line in(prior/'layer-dimensions.tsv').read_text().splitlines()))['metal2']
        for a,k,b in shapes:
            if a==own:continue
            x0,y0,x1,y1=b;overlap=intersect(box,[x0-spacing,y0-spacing,x1+spacing,y1+spacing])
            assert not overlap or outside_area(coverage,overlap)==0,'NS patch creates new foreign clearance exposure'
        selected=[dict(index=583,net='net131530',layer='metal2',bbox_dbu=box,ns_case=ns_case)]
    assert selected,'Empty shard is not an executable EDA task'
    (out/'clearance-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'selected-corners.json').write_text(json.dumps(selected,indent=2)+'\n')
    groups=defaultdict(list)
    for p in selected:groups[p['net'].replace('\\','')].append(p)
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'
    script+='set block [ord::get_db_block]\nset tech [ord::get_db_tech]\nif {[$tech getManufacturingGrid]!=10} {error {Frozen grid mismatch}}\nset f [open actual-grid.tsv w];puts $f "[$tech getDbUnitsPerMicron]\\t[$tech getManufacturingGrid]";close $f\nset exact [dict create]\n'
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
    exact=after==before+expected and routes0==routes1 and n0==n1 and nonnet(results/'6_final.def')==nonnet(out/'corner-candidate.def')
    old=violations((prior/'native-whole-drc.rpt').read_text())
    new=violations((out/'corner-native-drc.rpt').read_text())
    unchanged=all(file_sha(results/name)==h for name,h in report['source_inputs_sha256'].items())
    result=dict(passed=exact and unchanged and not(new-old)and bool(old-new),
                diagnostic_only=True,physical_qualified=False,shard=shard,combined=shard==6 and ns_case is None,ns_case=ns_case,failure_filter=failure_filter,
                source_receipt_sha256=report['source_receipt_sha256'],source_inputs_sha256=report['source_inputs_sha256'],
                neighborhood_receipt_sha256=file_sha(prior/'receipt.json'),
                complete_plan_sha256=file_sha(out/'clearance-plan.json'),original_inputs_unchanged=unchanged,
                selected_corners=len(selected),selected_nets=len(groups),normal_net_counts=[n0,n1],
                exact_expected_rectangles_and_nonrect_net_routes=exact,
                original_native_count=sum(old.values()),candidate_native_count=sum(new.values()),
                added_markers=sum((new-old).values()),removed_markers=sum((old-new).values()),
                scope=f'Pinned {source.parent.parent.name} full-neighborhood-pruned fills on actual{report["source_native_count"]} source. Six disjoint net-hash shards are diagnostic only; later composition requires a fresh combined whole-native check, not a sum of independent counts. Full native0new and exact DEF delta required; remaining native items and all final gates still mandatory. No final qualification transfer.')
    (out/'revision300-r-clearance-corners.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Preserve failed shard; other independent tasks continue'
