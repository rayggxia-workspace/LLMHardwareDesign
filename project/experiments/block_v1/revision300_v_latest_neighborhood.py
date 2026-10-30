"""Readonly complete current31-marker geometry and marked-net paths."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import json,re


def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records
    from native_rect_completion import rectangles
    assert cpus==16
    base=out.parents[2]
    source=base/'block-v1-20261031-705/tasks/revision300-v-joint-via-compose'
    sr=json.loads((source/'receipt.json').read_text());assert sr['passed']
    fp=source/'revision300-v-local-vias.json';assert file_sha(fp)==sr['outputs'][fp.name]
    prior=json.loads(fp.read_text());assert prior['passed']and prior['combined']and prior['candidate_native_count']==31 and prior['added_markers']==0 and prior['added_vs_prior_current']==0
    chain={source.parent.parent.name:file_sha(source/'receipt.json')}
    expected=prior['source_receipt_sha256']
    for stage,mode,report_name in [('683','revision300-v-remaining-via-compose','revision300-v-remaining-vias.json'),('672','revision300-v-repaired-via-compose','revision300-v-repaired-vias.json'),('630','revision300-final-source-v','revision300-final-source.json')]:
        parent=base/('block-v1-20261031-'+stage)/'tasks'/mode
        assert file_sha(parent/'receipt.json')==expected
        r=json.loads((parent/'receipt.json').read_text());assert r['passed']and file_sha(parent/report_name)==r['outputs'][report_name]
        data=json.loads((parent/report_name).read_text());chain[stage]=expected
        if stage!='630':expected=data['source_receipt_sha256']
        else:
            for name,digest in data['rtl_sha256'].items():assert file_sha(root/name)==digest
    inputs={}
    for name in('local-candidate.odb','local-candidate.def','local-native-drc.rpt'):
        inputs[name]=file_sha(source/name);assert inputs[name]==sr['outputs'][name]
    odb=source/'local-candidate.odb';report=source/'local-native-drc.rpt';report_sha=file_sha(report)
    expected_count=31
    assert report_sha=='6832038e3f9f5a772988f844df3a32da4e05d89078d7e35f5bbae326ae12ab39'
    text = report.read_text();(out/report.name).write_bytes(report.read_bytes())
    pattern = (r'violation type: Metal Spacing\n\s*srcs: net:([^\n]+)\n'
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
    assert all(w['net']in aliases for w in windows)
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    explicit=[];nets=0;complement=[];observed={};marked={m['net']for m in markers}
    for record in records(source/'local-candidate.def'):
        nets+=1;explicit.extend(rectangles(record));name=name_of(record)
        if name in marked:
            assert name not in observed
            header,paths,rects=decode(record)
            observed[name]=dict(header=header,nonrect_paths=paths,rectangles=list(rects.elements()),original_record_token_sha256=token_hash(record))
    assert set(observed)==marked and nets==562494
    (out/'observed-routes.json').write_text(json.dumps(observed,indent=2)+'\n')
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
    unchanged=all(file_sha(source/n)==h for n,h in inputs.items()) and file_sha(report)==report_sha
    result=dict(passed=unchanged,physical_qualified=False,diagnostic_only=True,
                source_final_task=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
                source_inputs_sha256=inputs,native_subcheck_snapshot_sha256=report_sha,
                source_chain_receipts_sha256=chain,whole_gate_receipt_required_for_acceptance=True,source_native_count=len(markers),
                markers=markers,windows=windows,normal_net_count=nets,
                explicit_rectangles_global_count=len(explicit),window_rect_complement=complement,
                same_net_shape_counts=dict(same),foreign_shape_counts=dict(foreign),shape_counts=dict(kinds),
                original_inputs_unchanged=unchanged,geometry_helper_sha256=file_sha(helper),grid_helper_sha256=file_sha(grid),
                scope='Readonly actual70531-marker source: fresh all-layer/all-net/pin/PG/OBS/nativeRECT/via geometry in bounded windows, plus exact current marked-net DEF paths. Includes actual prior70 and joint72 edits; no old-geometry substitution, mutation, native improvement or final qualification.')
    (out/'revision300-v-latest-neighborhood.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
