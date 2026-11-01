"""Export complete actual composed-R neighborhoods; shared proven exporter logic."""
from collections import Counter
from decimal import Decimal
import json,re

def export(root,out,cpus,run,source,results,odb,defpath,report,inputs,expected_count,native_proof):
    from io_slots import file_sha
    from native_escape import records
    from native_rect_completion import rectangles
    assert cpus==16
    report_sha=file_sha(report)
    text = report.read_text();(out/report.name).write_bytes(report.read_bytes())
    pattern = (r'violation type: (?:Metal Spacing|NS Metal)\n\s*srcs: net:([^\n]+)\n'
               r'\s*bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)')
    markers=[]
    for m in re.finditer(pattern,text):
        name,*coords,layer=m.groups();box=[Decimal(v)*2000 for v in coords]
        assert all(v==int(v)for v in box)
        assert 'net:'not in name and not re.search(r'\s',name)
        markers.append(dict(net=name.replace('\\',''),layer=layer,bbox_dbu=list(map(int,box))))
    assert len(markers)==text.count('violation type:')==expected_count
    windows=[dict(index=i,net=m['net'],layer=m['layer'],bbox_dbu=[m['bbox_dbu'][0]-4000,m['bbox_dbu'][1]-4000,m['bbox_dbu'][2]+4000,m['bbox_dbu'][3]+4000])for i,m in enumerate(markers)]
    helper=root/'project/experiments/block_v1/odb_geometry.tcl'
    code=helper.read_text()
    header='    puts $output "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]]"\n'
    assert code.count(header)==1
    (out/'region-base.tcl').write_text(code.replace(header,''))
    grid=root/'project/experiments/block_v1/geometry_windows.tcl'
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nsource {'+str(out/'region-base.tcl')+'}\nsource {'+str(grid)+'}\n'
    for w in windows:script+='::region::add %d %s\n'%(w['index'],' '.join(map(str,w['bbox_dbu'])))
    script+=r'''
rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr ::region::scanned
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
  foreach index [::region::hits $x0 $y0 $x1 $y1] {
    puts $stream "$index\t$net\t[$layer getName]\t$kind\t$x0\t$y0\t$x1\t$y1"
    dict set ::region::aliases $net 1;incr ::region::emitted
  }
}
bvgeom::export neighborhood.tsv
set block [ord::get_db_block]
set f [open neighborhood.tsv a]
foreach inst [$block getInsts] {
  set boxes [[$inst getMaster] getObstructions]
  if {[llength $boxes]==0} {continue}
  set transform [$inst getTransform]
  foreach box $boxes {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obs [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obs getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $::region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$::region::scanned\t$::region::emitted";close $f
set tech [ord::get_db_tech]
set f [open layer-dimensions.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]\t[$layer getSpacing]"}
close $f
set f [open via-footprints.tsv w]
foreach via [$tech getVias] {
  foreach box [$via getBoxes] {puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
}
close $f
'''
    (out/'neighborhood.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'neighborhood.tcl'],'neighborhood.log')
    aliases={bytes.fromhex(encoded).decode().replace('\\',''):alias for alias,encoded in (line.split('\t')for line in(out/'net-aliases.tsv').read_text().splitlines())}
    assert len(set(aliases.values())) == len(aliases), 'Ambiguous normalized net aliases'
    assert all(w['net']in aliases for w in windows)
    explicit=[];nets=0;complement=[]
    for record in records(defpath):nets+=1;explicit.extend(rectangles(record))
    with(out/'neighborhood.tsv').open('a')as stream:
        for name,layer,x0,y0,x1,y1 in explicit:
            for w in windows:
                a,b,c,d=w['bbox_dbu']
                if x0>=c or a>=x1 or y0>=d or b>=y1:continue
                name=name.replace('\\','');alias=aliases.get(name)
                if alias is None:
                    alias='rect-'+name.encode().hex();aliases[name]=alias
                    with(out/'net-aliases.tsv').open('a')as names:names.write(alias+'\t'+name.encode().hex()+'\n')
                stream.write(f"{w['index']}\t{alias}\t{layer}\twire-rect\t{x0}\t{y0}\t{x1}\t{y1}\n")
                complement.append([w['index'],name,layer,x0,y0,x1,y1])
    same=Counter();foreign=Counter();kinds=Counter()
    for line in(out/'neighborhood.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        i,alias,layer,kind,*box=line.split('\t');i=int(i);assert len(box)==4
        assert all(int(box[n])<int(box[n+2])for n in (0,1))
        kinds[kind]+=1
        if alias==aliases[windows[i]['net']]:same[i]+=1
        elif not kind.endswith('obstruction'):foreign[i]+=1
    assert all(same[i]>0 for i in range(len(windows)))
    unchanged=all(file_sha(results/n)==h for n,h in inputs.items()) and file_sha(report)==report_sha
    result=dict(passed=unchanged,physical_qualified=False,diagnostic_only=True,
                source_final_task=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
                source_inputs_sha256=inputs,native_subcheck_snapshot_sha256=report_sha,
                native_subcheck_script_sha256=native_proof['script_sha256'],
                native_subcheck_before_after_def_sha256=native_proof.get('before_after_def_sha256'),
                whole_gate_receipt_required_for_acceptance=True,source_native_count=len(markers),
                markers=markers,windows=windows,normal_net_count=nets,
                explicit_rectangles_global_count=len(explicit),window_rect_complement=complement,
                same_net_shape_counts=dict(same),foreign_shape_counts=dict(foreign),shape_counts=dict(kinds),
                original_inputs_unchanged=unchanged,geometry_helper_sha256=file_sha(helper),grid_helper_sha256=file_sha(grid),
                scope=f'Readonly pinned actual{source.parent.parent.name} {expected_count} native-marker neighborhoods, all layers/all nets with transformed pins, PG/ports/OBS, native DEF RECT complement and exact via footprints. Spatial bins only prune candidates, full boxes retained. Bound to actual880 composed native report and exact DEF delta; final gates remain pending. This diagnostic grants no repair or physical qualification.')
    (out/'revision300-r-current-neighborhood.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
