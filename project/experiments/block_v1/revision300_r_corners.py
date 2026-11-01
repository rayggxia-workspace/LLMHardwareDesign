"""Bounded independent corner candidates on R828 copies; no qualification transfer."""
from pathlib import Path
from collections import Counter,defaultdict
import json,re
from revision300_v_clearance_corners import generate
from revision300_v_gds_repair import nonnet

def probe(root,out,cpus,run,shard):
    from pathlib import Path
    from collections import Counter
    import json,re
    from io_slots import file_sha
    from revision300_v_corner_probe import def_content,violations
    assert cpus==16 and shard in range(6)
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
    failure_filter=None
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
                diagnostic_only=True,physical_qualified=False,shard=shard,combined=False,failure_filter=failure_filter,
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
