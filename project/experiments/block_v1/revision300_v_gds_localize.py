"""Read-only localization of the one actual767 complete-GDS failure."""
import json
import re
from pathlib import Path

WINDOW_UM = [495, 70, 501, 76]
SOURCE_SHA = 'f06b8e147dfb8bde4e5cdd662bfbbad97b873e661b3b47c9667a6386a6d06005'
DECK_SHA = '4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'


def inspect(root, out, cpus, run, variant):
    from io_slots import file_sha
    assert cpus == 16 and variant in ('odb', 'gds')
    base = out.parents[2]
    source = base/'block-v1-20261031-767/tasks/revision300-final-source-v'
    gate = source.parent/'revision300-drc-v'
    assert file_sha(source/'receipt.json') == SOURCE_SHA
    sr = json.loads((source/'receipt.json').read_text()); assert sr['passed']
    fp = source/'revision300-final-source.json'
    assert file_sha(fp) == sr['outputs'][fp.name]
    flow = json.loads(fp.read_text())
    dr = json.loads((gate/'receipt.json').read_text()); assert not dr['passed']
    report = gate/'five-macro-drc.json'
    assert file_sha(report) == dr['outputs'][report.name]
    d = json.loads(report.read_text())
    assert not d['passed'] and d['native_report'] == ''
    assert d['source_receipt_sha256'] == SOURCE_SHA
    assert d['deck_sha256'] == DECK_SHA
    assert d['full_deck']['total_items'] == 1 and d['full_deck']['categories'] == {'METAL2.5': 1}
    assert d['full_deck']['items'][0]['values'] == [
        'edge-pair: (497.91,72.87;498.1466,72.87)/(498.09,72.94;497.8534,72.94)']
    files = {name: Path(row['path']) for name, row in flow['final_files'].items()}
    for name in ('6_final.odb', '6_final.def'):
        assert file_sha(files[name]) == flow['final_files'][name]['sha256']
    assert file_sha(Path(d['gds']['path'])) == d['gds']['sha256']
    (out/'failed-marker.json').write_text(json.dumps(d['full_deck'], indent=2)+'\n')
    result = dict(passed=False, diagnostic_only=True, variant=variant,
        source_receipt_sha256=SOURCE_SHA, failed_gate_receipt_sha256=file_sha(gate/'receipt.json'),
        actual_failure_report_sha256=file_sha(report), window_um=WINDOW_UM,
        input_odb_sha256=file_sha(files['6_final.odb']),
        input_def_sha256=file_sha(files['6_final.def']), input_gds_sha256=d['gds']['sha256'],
        full_library_qualified=False)
    if variant == 'odb':
        # Reuse the established complete exporter and window predicate. No
        # early net/layer filter may hide a foreign conductor or obstruction.
        helper = root/'project/experiments/block_v1/odb_geometry.tcl'
        code = helper.read_text()
        header = '    puts $output "# NET $alias [binary encode hex [encoding convertto utf-8 [$net getName]]]"\n'
        assert code.count(header) == 1
        (out/'region-base.tcl').write_text(code.replace(header, ''))
        script = 'set_thread_count 16\nread_db {'+str(files['6_final.odb'])+'}\n'
        script += 'source {'+str(out/'region-base.tcl')+'}\nsource {'+str(root/'project/experiments/block_v1/geometry_windows.tcl')+'}\n'
        script += '::region::add 0 '+' '.join(str(x*2000) for x in WINDOW_UM)+'\n'
        script += r'''
rename bvgeom::rectangle bvgeom::original_rectangle
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  incr ::region::scanned
  set x0 [expr {[$object xMin]+$dx}];set y0 [expr {[$object yMin]+$dy}]
  set x1 [expr {[$object xMax]+$dx}];set y1 [expr {[$object yMax]+$dy}]
  if {[bvgeom::present $transform]} {
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
  set transform [$inst getTransform]
  foreach box [[$inst getMaster] getObstructions] {bvgeom::db_box $f i[$inst getId] $box instance-obstruction $transform}
}
foreach obs [$block getObstructions] {bvgeom::db_box $f block-obstruction [$obs getBBox] block-obstruction}
close $f
set f [open net-aliases.tsv w]
foreach net [$block getNets] {set alias n[$net getId]
  if {[dict exists $::region::aliases $alias]} {puts $f "$alias\t[binary encode hex [encoding convertto utf-8 [$net getName]]]"}
}
close $f
set f [open scan-counts.tsv w];puts $f "$::region::scanned\t$::region::emitted";close $f
'''
        (out/'neighborhood.tcl').write_text(script)
        run(['openroad', '-no_init', '-exit', out/'neighborhood.tcl'], 'neighborhood.log')
        from native_escape import records
        from native_rect_completion import rectangles
        complement = []; count = 0; rect_count = 0
        a,b,c,e = [x*2000 for x in WINDOW_UM]
        for record in records(files['6_final.def']):
            count += 1
            for row in rectangles(record):
                rect_count += 1
                name, layer, x0,y0,x1,y1 = row
                if x0<c and a<x1 and y0<e and b<y1:
                    complement.append(row)
        assert count == 562494 and rect_count == 400
        (out/'native-rect-complement.json').write_text(json.dumps(complement,indent=2)+'\n')
        assert (out/'neighborhood.tsv').stat().st_size > 0
        result.update(normal_def_nets=count, native_def_rectangles=rect_count,
                      window_rect_complement=complement, all_net_layer_scan=True)
    else:
        deck = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
        assert file_sha(deck) == DECK_SHA
        text = deck.read_text(); (out/'unmodified-deck.txt').write_bytes(deck.read_bytes())
        mappings = re.findall(r'(?m)^\s*metal2\s*=\s*input\(\s*(\d+)\s*,\s*(\d+)\s*\)', text)
        assert len(mappings) == 1, 'Actual deck metal2 mapping not recognized'
        layer, datatype = mappings[0]
        lines = [line for line in text.splitlines() if 'METAL2.' in line]
        assert any('METAL2.5' in line for line in lines)
        (out/'metal2-rules.json').write_text(json.dumps(lines,indent=2)+'\n')
        ruby = '''require 'json'
layout=RBA::Layout.new
layout.read($gds)
top=layout.top_cell
raise 'Wrong top' unless top.name=='block_v1_v'
li=layout.find_layer($layer.to_i,$datatype.to_i)
raise 'Missing actual metal2 layer' if li.nil?
box=RBA::Box.new(*[495,70,501,76].map { |x| (x/layout.dbu).round })
region=RBA::Region.new(top.begin_shapes_rec(li))
clipped=(region & RBA::Region.new(box)).merged
rows=[]
clipped.each do |polygon|
  holes=[]
  polygon.holes.times do |i| holes << polygon.each_point_hole(i).map { |p| [p.x,p.y] } end
  rows << {'hull'=>polygon.each_point_hull.map { |p| [p.x,p.y] },'holes'=>holes}
end
raise 'Empty actual metal2 window' if rows.empty?
File.write('gds-metal2-window.json',JSON.pretty_generate({'dbu_um'=>layout.dbu,'clipped_window_um'=>[495,70,501,76],'layer'=>[$layer.to_i,$datatype.to_i],'polygons'=>rows})+"\\n")
'''
        (out/'gds-window.rb').write_text(ruby)
        run(['klayout', '-b', '-r', out/'gds-window.rb', '-rd', 'gds='+d['gds']['path'],
             '-rd', 'layer='+layer, '-rd', 'datatype='+datatype], 'gds-window.log')
        clipped = json.loads((out/'gds-metal2-window.json').read_text())
        assert clipped['polygons']
        result.update(unmodified_deck_sha256=DECK_SHA, actual_metal2_rules=lines,
                      metal2_gds_layer=[int(layer), int(datatype)],
                      clipped_polygon_count=len(clipped['polygons']))
    unchanged = (file_sha(files['6_final.odb']) == result['input_odb_sha256'] and
                 file_sha(files['6_final.def']) == result['input_def_sha256'] and
                 file_sha(Path(d['gds']['path'])) == result['input_gds_sha256'])
    result.update(passed=unchanged, original_inputs_unchanged=unchanged,
        scope='Read-only one actual767 METAL2.5 marker localization; original failed gate preserved. Window views do not grant full-chip qualification or repair.')
    (out/'revision300-v-gds-localization.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
