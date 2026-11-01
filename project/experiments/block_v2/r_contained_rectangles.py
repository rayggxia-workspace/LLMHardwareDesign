"""Bounded native wire representation experiment; never waive a DRC marker.

An explicit RECT may be added only when the entire reported rectangle is
already contained in one actual same-net, same-layer wire/via rectangle. No
new conductor area or logical connection is permitted. Native whole DRC and
all fresh final checks remain mandatory, even for a redundant rectangle.
"""
from collections import Counter
from decimal import Decimal
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re


def markers(text):
    pattern=r'violation type: ([^\n]+)\n\s*srcs: net:([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)\n'
    rows=[];cursor=0
    for m in re.finditer(pattern,text):
        assert not text[cursor:m.start()].strip();cursor=m.end()
        category,name,*values,layer=m.groups()
        assert category=='Metal Spacing' and ' net:' not in name and not any(c.isspace() for c in name)
        assert layer in ('metal1','metal2','metal3')
        box=[Decimal(v)*2000 for v in values];assert all(v==int(v) for v in box)
        a,b,c,d=map(int,box);assert 0<=a<c<=6000000 and 0<=b<d<=6000000 and c-a<=180 and d-b<=140
        rows.append(dict(net=name,layer=layer,box_dbu=[a,b,c,d]))
    assert rows and not text[cursor:].strip()
    assert len({(m['net'],m['layer'],*m['box_dbu']) for m in rows})==len(rows)
    return rows


def chunks(path):
    inside=False;record=[]
    with Path(path).open('rb') as f:
        for line in f:
            clean=line.lstrip()
            if clean.startswith(b'NETS '):assert not inside;inside=True;yield ('other',None,line);continue
            if clean.startswith(b'END NETS'):
                assert inside and not record;inside=False;yield ('other',None,line);continue
            if inside:
                if not record and not clean.strip():yield ('other',None,line);continue
                if not record:assert clean.startswith(b'- ')
                record.append(line)
                if clean.rstrip().endswith(b';'):
                    yield ('net',record[0].lstrip().split()[1].decode(),b''.join(record));record=[]
            else:yield ('other',None,line)
    assert not inside and not record


def compare(before,after,plan):
    wanted={}
    for row in plan:
        a,b,c,d=row['box_dbu'];path=f"{row['layer']} ( {a} {b} ) RECT ( 0 0 {c-a} {d-b} )".encode()
        wanted.setdefault(row['net'],Counter())[path]+=1
    changed=[];untouched=hashlib.sha256()
    def paths(data):
        m=re.search(rb'\+ ROUTED\s+',data);assert m
        header=data[:m.start()].rstrip();body=data[m.end():].strip();assert body.endswith(b';')
        return header,Counter(b' '.join(p.split()) for p in re.split(rb'\s+NEW\s+',body[:-1].strip()))
    for a,b in zip_longest(chunks(before),chunks(after)):
        assert a is not None and b is not None and a[:2]==b[:2], 'DEF record identity changed'
        if a[2]==b[2]:untouched.update(a[2]);continue
        assert a[0]=='net' and a[1] in wanted,'Unrelated DEF bytes changed'
        h,p=paths(a[2]);j,q=paths(b[2]);assert h==j and q==p+wanted[a[1]],'Original path/connection changed or unplanned geometry added'
        changed.append(a[1])
    assert set(changed)==set(wanted) and len(changed)==len(wanted)
    return dict(passed=True,changed_nets=len(changed),added_contained_rectangles=len(plan),
                unchanged_non_target_def_sha256=untouched.hexdigest(),all_original_paths_and_connections_preserved=True,
                identical_physical_conductor_union=True,scope='Only exact source-contained redundant RECT paths; source coverage is separately measured in actual OpenDB')


def implement(root,out,source,candidate,run,sha,partial=False):
    evidence=root/'work/YUZE-LU/143/r-input-hold/buffer-129'
    index=json.loads((evidence/'index.json').read_text())
    for n,h in index['files'].items():assert sha(evidence/n)==h
    report=evidence/'candidate-native-drc.rpt';all_plan=markers(report.read_text());assert len(all_plan)==822
    excluded=[]
    if partial:
        #133 rejected this exact one before any edits. It remains in every
        # whole-chip DRC check; this diagnostic does not claim final closure.
        expected=dict(net='net401579',layer='metal2',box_dbu=[4949580,4618320,4949760,4618390])
        assert all_plan[313]==expected
        excluded=[expected]
    plan=[m for m in all_plan if m not in excluded]
    baseline=root/'work/YUZE-LU/143/r-input-hold/geometry-130/native-whole-drc.rpt'
    assert sha(report)==sha(baseline)
    odb=candidate/'candidate.odb';expected=index['large_remote_files']['candidate.odb']['sha256'];assert sha(odb)==expected
    helper=root/'project/experiments/block_v1/odb_geometry.tcl'
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nsource {'+str(helper)+'}\nset plans {}\n'
    for row in plan:
        script+='lappend plans {'+row['net'].encode().hex()+' '+row['layer']+' '+' '.join(map(str,row['box_dbu']))+'}\n'
    script+='''
rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
 if {$transform ne ""} {error "Unexpected wire transform"}
 if {[$layer getName] ne $::target_layer} {return}
 set box [list [expr {[$object xMin]+$dx}] [expr {[$object yMin]+$dy}] [expr {[$object xMax]+$dx}] [expr {[$object yMax]+$dy}]]
 lassign $box a b c d;lassign $::target_box x y z w
 if {$a<=$x && $b<=$y && $c>=$z && $d>=$w && $::covered eq ""} {set ::covered [list $kind {*}$box]}
}
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron]!=2000} {error "Unexpected units"}
set itr [odb::new_dbWirePathItr];set path [odb::new_dbWirePath];set shape [odb::new_dbWirePathShape]
set f [open coverage.tsv w]
puts $f "index\\tnet_hex\\tsignal_type\\tlayer\\txmin\\tymin\\txmax\\tymax\\tcover_kind\\tcover_xmin\\tcover_ymin\\tcover_xmax\\tcover_ymax"
set resolved {};set failures 0;set number 0
foreach row $plans {
 lassign $row encoded target_layer x y z w
 set name [encoding convertfrom utf-8 [binary decode hex $encoded]]
 set net [$block findNet $name]
 if {$net eq "NULL" || [$net getSigType] ni {SIGNAL CLOCK} || [$net getWire] eq "NULL"} {error "Measured marker net missing or invalid"}
 set target_box [list $x $y $z $w];set covered ""
 $itr begin [$net getWire]
 while {[$itr getNextPath $path]} {
  while {[$itr getNextShape $shape]} {
   bvgeom::wire_shape $f $encoded [odb::dbWirePathShape_shape_get $shape]
   if {$covered ne ""} {break}
  }
  if {$covered ne ""} {break}
 }
 if {$covered eq ""} {incr failures;set covered [list UNCOVERED 0 0 0 0]}
 puts $f [join [list $number $encoded [$net getSigType] $target_layer $x $y $z $w {*}$covered] "\\t"]
 lappend resolved [list $net $target_layer $x $y $z $w];incr number
}
close $f
odb::delete_dbWirePathShape $shape;odb::delete_dbWirePath $path;odb::delete_dbWirePathItr $itr
if {$failures!=0 || $number!=822} {error "Containment guard rejected $failures markers before any edit"}
write_def before.def
foreach row $resolved {
 lassign $row net layer x y z w
 set enc [odb::new_dbWireEncoder]
 odb::dbWireEncoder_append $enc [$net getWire]
 odb::dbWireEncoder_newPath $enc [[ord::get_db_tech] findLayer $layer] ROUTED
 odb::dbWireEncoder_addPoint $enc $x $y
 odb::dbWireEncoder_addRect $enc 0 0 [expr {$z-$x}] [expr {$w-$y}]
 odb::dbWireEncoder_end $enc;odb::delete_dbWireEncoder $enc
}
write_def after.def
write_db reinforced.odb
drt::check_drc_cmd reinforced-native-drc.rpt 0 0 0 0 reinforced_native_drc
puts CONTAINED_RECTANGLE_EXPERIMENT_COMPLETE
'''
    script=script.replace('$number!=822','$number!='+str(len(plan)))
    (out/'reinforce.tcl').write_text(script);(out/'rectangle-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'unmodified-source-markers.json').write_text(json.dumps(excluded,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'reinforce.tcl'],'reinforce.log')
    geometry=compare(out/'before.def',out/'after.def',plan)
    text=(out/'reinforced-native-drc.rpt').read_text()
    assert sha(odb)==expected
    return dict(reinforcement_diagnostic=True,source_candidate_odb_sha256=expected,geometry=geometry,
                unmodified_source_markers=excluded,source_marker_count=822,selected_marker_count=len(plan),
                native_drc_count=text.count('violation type:'),native_drc_zero=not text.strip(),original_source_unchanged=True)
