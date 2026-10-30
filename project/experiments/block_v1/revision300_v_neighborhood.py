"""Read-only foreign-net, pin, obstruction and via geometry around remainder."""
from collections import Counter
import json


def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records
    from native_rect_completion import rectangles
    from revision300_v_corner_probe import violations
    from revision300_v_transition import decode
    from revision300_v_transition_alternatives import build
    from revision300_v_via_batch import name_of
    from revision300_v_via_bridge import path_key
    assert cpus==16
    base=out.parents[2];source=base/'block-v1-20261031-613/tasks/revision300-v-transition-filter'
    prior=base/'block-v1-20261030-605/tasks/revision300-v-remaining'
    original=base/'block-v1-20261030-598/tasks/revision300-v-geometry-compose'
    def bind(folder,names):
        r=json.loads((folder/'receipt.json').read_text());assert r['passed']
        for name in names:assert file_sha(folder/name)==r['outputs'][name]
        return r
    sr=bind(source,('transition-batch.odb','transition-batch.def','transition-batch-drc.rpt','revision300-v-transition-batch.json','expected-edits.json'))
    bind(prior,('revision300-v-remaining.json',));bind(original,('composed-native-drc.rpt',))
    previous=json.loads((prior/'revision300-v-remaining.json').read_text())
    actual=json.loads((source/'revision300-v-transition-batch.json').read_text())
    assert actual['passed']and actual['native_candidate_count']==136 and actual['added_markers']==0
    assert actual['source_receipt_sha256']==previous['source_receipt_sha256']==file_sha(original/'receipt.json')
    old=violations((original/'composed-native-drc.rpt').read_text());current=violations((source/'transition-batch-drc.rpt').read_text())
    assert len(old)==sum(old.values())==172 and sum(current.values())==136 and not(current-old)
    changed={p['net']for p in json.loads((source/'expected-edits.json').read_text())['patches']}
    selections={};keys=list(old)
    for i,row in enumerate(previous['markers']):
        name=row['marker']['net'].replace('\\','')
        if keys[i]not in current or name in changed:continue
        for case in ('alt-upper-plain','alt-upper-stack','alt-lower-stack','alt-both-stack'):
            if case in selections:continue
            try:edit=build(row['nonrect_def_paths'],row,case)
            except AssertionError:continue
            selections[case]=dict(index=i,net=name,row=row,edit=edit);break
        if len(selections)==4:break
    assert len(selections)==4
    wanted={v['net']:v for v in selections.values()};assert len(wanted)==4
    windows=[];via_names={'via2_5','via3_2','via4_0'};explicit=[];normal_nets=0
    for case,v in selections.items():
        box=v['row']['marker']['bbox_dbu'];windows.append(dict(case=case,index=v['index'],net=v['net'],bbox_dbu=[box[0]-4000,box[1]-4000,box[2]+4000,box[3]+4000]))
    for record in records(source/'transition-batch.def'):
        normal_nets+=1;explicit.extend(rectangles(record));name=name_of(record)
        if name in wanted:
            v=wanted.pop(name);_,paths,_=decode(record)
            assert Counter(map(path_key,paths))==Counter(map(path_key,v['row']['nonrect_def_paths']))
            via_names.update(p['via']for p in paths if p['via'])
    assert not wanted and normal_nets==557412 and len(explicit)==232
    helper=root/'project/experiments/block_v1/odb_geometry.tcl';code=helper.read_text()
    header='    puts $output "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]]"\n'
    assert code.count(header)==1;code=code.replace(header,'')
    (out/'region-base.tcl').write_text(code)
    # The existing exporter includes instance-pin transforms. Window filtering
    # must apply the same transform before clipping, unlike the old locator.
    script='set_thread_count 16\nread_db {'+str(source/'transition-batch.odb')+'}\nsource {'+str(out/'region-base.tcl')+'}\n'
    script+='namespace eval ::region {variable windows {};variable aliases {};variable scanned 0;variable hits 0}\n'
    for i,w in enumerate(windows):script+='lappend ::region::windows [list %d %s]\n'%(i,' '.join(map(str,w['bbox_dbu'])))
    script+=r'''
rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr ::region::scanned
  set name [$layer getName]
  if {$name ni {metal1 metal2 metal3 metal4 metal5 metal6 via1 via2 via3 via4 via5}} {return}
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
  if {[present $transform]} {
    set xs {};set ys {}
    foreach x [list $x0 $x1] {foreach y [list $y0 $y1] {
      set point [odb::new_Point $x $y];$transform apply $point
      lappend xs [$point getX];lappend ys [$point getY];odb::delete_Point $point
    }}
    set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  }
  if {$x0 >= $x1 || $y0 >= $y1} {error "Degenerate region shape"}
  foreach w $::region::windows {
    lassign $w index a b c d
    if {$x0 < $c && $a < $x1 && $y0 < $d && $b < $y1} {
      puts $stream "$index\t$net\t$name\t$kind\t$x0\t$y0\t$x1\t$y1"
      dict set ::region::aliases $net 1;incr ::region::hits
    }
  }
}
bvgeom::export neighborhood.tsv
set block [ord::get_db_block]
set f [open neighborhood.tsv a]
foreach inst [$block getInsts] {
  set box [$inst getBBox];set overlaps 0
  foreach w $::region::windows {lassign $w index a b c d
    if {[$box xMin] < $c && $a < [$box xMax] && [$box yMin] < $d && $b < [$box yMax]} {set overlaps 1;break}
  }
  if {!$overlaps} {continue}
  set transform [$inst getTransform]
  foreach box [[$inst getMaster] getObstructions] {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obstruction [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obstruction getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $::region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$::region::scanned\t$::region::hits";close $f
set tech [ord::get_db_tech]
set f [open layer-dimensions.tsv w]
foreach name {metal1 metal2 metal3 metal4 metal5 metal6 via1 via2 via3 via4 via5} {set layer [$tech findLayer $name];puts $f "$name\t[$layer getWidth]\t[$layer getSpacing]"}
close $f
set f [open via-footprints.tsv w]
'''
    for name in sorted(via_names):
        script+='set via [$tech findVia '+name+'];if {$via eq "NULL" || $via eq ""} {error "Missing actual via"}\n'
        script+='foreach box [$via getBoxes] {puts $f "'+name+'\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}\n'
    script+='close $f\n'
    (out/'neighborhood.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'neighborhood.tcl'],'neighborhood.log')
    aliases={bytes.fromhex(encoded).decode().replace('\\',''):alias for alias,encoded in (l.split('\t')for l in(out/'net-aliases.tsv').read_text().splitlines())}
    complemented=[]
    with(out/'neighborhood.tsv').open('a')as stream:
        for name,layer,x0,y0,x1,y1 in explicit:
            for i,w in enumerate(windows):
                a,b,c,d=w['bbox_dbu']
                if x0<c and a<x1 and y0<d and b<y1:
                    plain=name.replace('\\','');alias=aliases.get(plain)
                    if alias is None:
                        alias='rect-'+plain.encode().hex();aliases[plain]=alias
                        with(out/'net-aliases.tsv').open('a')as names:names.write(alias+'\t'+plain.encode().hex()+'\n')
                    stream.write(f'{i}\t{alias}\t{layer}\twire-rect\t{x0}\t{y0}\t{x1}\t{y1}\n');complemented.append((i,name,layer,x0,y0,x1,y1))
    shapes=Counter();foreign=Counter()
    for line in(out/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,alias,layer,kind,*box=line.split('\t');assert len(box)==4
        i=int(i);shapes[(i,kind)]+=1
        if alias!=aliases[windows[i]['net']]and not kind.endswith('obstruction'):foreign[i]+=1
    assert all(foreign[i]>0 and shapes[(i,'instance-pin')]>0 for i in range(4))
    unchanged=all(file_sha(source/name)==sr['outputs'][name]for name in('transition-batch.odb','transition-batch.def','transition-batch-drc.rpt'))
    result=dict(passed=unchanged,diagnostic_only=True,physical_qualified=False,source_receipt_sha256=file_sha(source/'receipt.json'),
                localization_receipt_sha256=file_sha(prior/'receipt.json'),source_native_count=136,original_inputs_unchanged=unchanged,
                normal_net_count=normal_nets,explicit_rectangles_global_count=len(explicit),window_rect_complement=complemented,
                windows=windows,foreign_shape_counts=dict(foreign),shape_counts={str(k):v for k,v in shapes.items()},
                geometry_helper_sha256=file_sha(helper),via_names=sorted(via_names),
                scope='Read-only actual613 four remainder neighborhoods: full-net wires/vias, transformed instance pins, ports, special wires, cell/block OBS and exact native DEF RECT supplement. Layer scalar width/spacing is only a pruning input, not all LEF rules or a clearance/DRC/route/terminal/RCX/STA/current588 qualification.')
    (out/'revision300-v-neighborhood.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
