"""Read-only real wire/PG/pin/OBS contexts for representative native markers."""
from decimal import Decimal
import json
from pathlib import Path
import re


def sample(root,out,source,candidate,run,sha):
    evidence=root/'work/YUZE-LU/143/r-input-hold/buffer-129'
    index=json.loads((evidence/'index.json').read_text())
    for n,h in index['files'].items():assert sha(evidence/n)==h
    text=(evidence/'candidate-native-drc.rpt').read_text()
    pattern=r'violation type: ([^\n]+)\n\s*srcs: net:([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)\n'
    markers=[];cursor=0
    for m in re.finditer(pattern,text):
        assert not text[cursor:m.start()].strip();cursor=m.end()
        category,name,*values,layer=m.groups();assert category=='Metal Spacing' and ' net:' not in name
        box=[Decimal(v)*2000 for v in values];assert all(v==int(v) for v in box)
        markers.append(dict(net=name,layer=layer,box_dbu=list(map(int,box))))
    assert len(markers)==822 and not text[cursor:].strip()
    chosen=[]
    for predicate in (lambda m:m['layer']=='metal1',lambda m:m['layer']=='metal2',lambda m:m['layer']=='metal3',
                      lambda m:m['layer']=='metal2' and m['net'].startswith('clknet'),
                      lambda m:m['layer']=='metal3' and m['net'].startswith('clknet'),lambda m:m['net'].startswith('bank0')):
        row=next(m for m in markers if predicate(m))
        if row not in chosen:chosen.append(row)
    odb=candidate/'candidate.odb';expected=index['large_remote_files']['candidate.odb']['sha256'];assert sha(odb)==expected
    helper=root/'project/experiments/block_v1'
    locator=(helper/'native_drc_locate.tcl').read_text()
    guard='  if {$transform ne ""} {error "This locator does not transform cell pin geometry"}\n'
    assert locator.count(guard)==1;locator=locator.replace(guard,'')
    anchor='  if {$x0 >= $x1 || $y0 >= $y1} {error "Degenerate native geometry"}'
    transform='''  if {[bvgeom::present $transform]} {
    set xs {};set ys {}
    foreach x [list $x0 $x1] {foreach y [list $y0 $y1] {
      set point [odb::new_Point $x $y];$transform apply $point
      lappend xs [$point getX];lappend ys [$point getY];odb::delete_Point $point
    }}
    set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
    set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  }
'''
    assert locator.count(anchor)==1;locator=locator.replace(anchor,transform+anchor)
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nsource {'+str(helper/'odb_geometry.tcl')+'}\nnamespace eval bvgeom {variable markers [dict create]}\nset context_boxes {}\n'
    for i,m in enumerate(chosen):
        a,b,c,d=m['box_dbu'];box=[a-2000,b-2000,c+2000,d+2000]
        script+='dict lappend bvgeom::markers '+m['layer']+' {'+str(i)+' '+' '.join(map(str,box))+'}\n'
        script+='lappend context_boxes {'+' '.join(map(str,box))+'}\n'
    script+=locator
    script+='''
set output [open marker-shapes.tsv a]
set selected 0
foreach inst [$block getInsts] {
 set box [$inst getBBox];set hit 0
 foreach context $context_boxes {
  lassign $context a b c d
  if {[$box xMin]<$c && $a<[$box xMax] && [$box yMin]<$d && $b<[$box yMax]} {set hit 1;break}
 }
 if {!$hit} {continue}
 incr selected
 set transform [$inst getTransform]
 foreach term [$inst getITerms] {
  set net [$term getNet]
  if {[bvgeom::present $net]} {set alias [native_hex [$net getName]]} else {set alias [native_hex "UNCONNECTED:[$inst getName]/[[$term getMTerm] getName]"]}
  foreach pin [[$term getMTerm] getMPins] {foreach shape [$pin getGeometry] {bvgeom::db_box $output $alias $shape instance-pin $transform}}
 }
 foreach shape [[$inst getMaster] getObstructions] {bvgeom::db_box $output [native_hex "OBS:[$inst getName]"] $shape instance-obs $transform}
}
close $output
puts "SAMPLE_INSTANCES $selected"
'''
    (out/'sample.tcl').write_text(script);(out/'sample-markers.json').write_text(json.dumps(chosen,indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'sample.tcl'],'sample.log')
    assert sha(odb)==expected
    return dict(sampled_markers=chosen,candidate_odb_sha256=expected,geometry_context_readonly=True)
