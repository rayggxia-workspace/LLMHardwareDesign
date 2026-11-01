"""Read-only exact geometry of sealed V spacing failures and capacitance net.

This diagnostic never repairs geometry or grants acceptance to either source.
"""
import json
from pathlib import Path
import re


def diagnose(root, out, cpus, run, kind):
    from io_slots import file_sha
    assert cpus == 16 and kind in ('spacing', 'cap')
    base = out.parents[2]
    number = '523' if kind == 'spacing' else '538'
    tasks = base / ('block-v1-20261030-' + number) / 'tasks'
    source = tasks / 'revision300-final-source-v'
    sr = json.loads((source / 'receipt.json').read_text())
    assert sr['passed'] and sr['mode'] == source.name
    flow_path = source / 'revision300-final-source.json'
    assert file_sha(flow_path) == sr['outputs'][flow_path.name]
    flow = json.loads(flow_path.read_text())
    odb = Path(flow['final_files']['6_final.odb']['path'])
    expected = flow['final_files']['6_final.odb']['sha256']
    assert odb == source / 'flow/results/nangate45/bv1_block_v1_v/base/6_final.odb'
    assert file_sha(odb) == expected == sr['outputs'][str(odb.relative_to(source))]
    gate = tasks / ('revision300-drc-v' if kind == 'spacing' else 'revision300-physical-v')
    gr = json.loads((gate / 'receipt.json').read_text())
    assert not gr['passed'] and gr['mode'] == gate.name
    report_name = 'native-whole-drc.rpt' if kind == 'spacing' else 'electrical-violations.rpt'
    report_path = gate / report_name
    assert file_sha(report_path) == gr['outputs'][report_name]
    text = report_path.read_text()
    (out / report_name).write_bytes(report_path.read_bytes())
    markers = []
    if kind == 'spacing':
        pattern = (r'violation type: Metal Spacing\n\s*srcs: net:([^\n]+)\n'
                   r'\s*bbox = \(([-\d.]+), ([-\d.]+)\) - '
                   r'\(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)')
        from decimal import Decimal
        for match in re.finditer(pattern, text):
            name, x0, y0, x1, y1, layer = match.groups()
            coords = [Decimal(x) * 2000 for x in (x0, y0, x1, y1)]
            assert all(x == int(x) for x in coords)
            markers.append(dict(net=name, layer=layer, bbox_dbu=list(map(int, coords))))
        assert len(markers) == text.count('violation type:') == 445
        names = sorted({m['net'].replace('\\', '') for m in markers})
        select = 'set wanted [dict create]\n'
        for name in names:
            select += 'dict set wanted [encoding convertfrom utf-8 [binary decode hex {' + name.encode().hex() + '}]] 1\n'
        select += '''set selected {};set found [dict create]
  foreach candidate [$block getNets] {
    set plain [string map [list [format %c 92] {}] [$candidate getName]]
    if {[dict exists $wanted $plain]} {
      if {[dict exists $found $plain]} {error "Ambiguous normalized net"}
      dict set found $plain 1;lappend selected $candidate
    }
  }
  if {[dict size $found] != [dict size $wanted]} {error "Missing reported net"}
'''
    else:
        match = re.search(r'(?m)^max_cap173361/Z\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+)\s+\(VIOLATED\)', text)
        assert match and float(match.group(2)) > float(match.group(1))
        select = '''set inst [$block findInst max_cap173361]
  if {![present $inst]} {error "Missing actual capacitance driver"}
  set term [$inst findITerm Z]
  if {![present $term]} {error "Missing driver pin"}
  set selected [list [$term getNet]]
  if {![present [lindex $selected 0]]} {error "Disconnected driver"}
'''
    helper = root / 'project/experiments/block_v1/odb_geometry.tcl'
    code = helper.read_text()
    anchor = '  foreach net [$block getNets] {'
    assert code.count(anchor) == 1
    code = code.replace(anchor, '  ' + select + '  foreach net $selected {')
    anchor = '    set wire [$net getWire]'
    assert code.count(anchor) == 1
    code = code.replace(anchor, '''    foreach term [$net getITerms] {
      set inst [$term getInst];set mt [$term getMTerm]
      puts $terms "$alias\\t[binary encode hex [encoding convertto utf-8 [$inst getName]]]\\t[binary encode hex [encoding convertto utf-8 [[$inst getMaster] getName]]]\\t[binary encode hex [encoding convertto utf-8 [$mt getName]]]\\t[$mt getIoType]\\t[$mt getSigType]"
    }
''' + anchor)
    code = code.replace('  set output [open $destination w]', '  set output [open $destination w]\n  set terms [open selected-terminals.tsv w]')
    code = code.replace('  close $output', '  close $output;close $terms')
    (out / 'selected-geometry.tcl').write_text(code)
    script = ('set_thread_count 16\nread_db {' + str(odb) + '}\nsource {' +
              str(out / 'selected-geometry.tcl') + '}\nbvgeom::export selected-geometry.tsv\n')
    (out / 'localize.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out / 'localize.tcl'], 'localize.log')
    assert file_sha(odb) == expected
    aliases = {}; boxes = []
    for line in (out / 'selected-geometry.tsv').read_text().splitlines():
        if line.startswith('# NET '):
            _, _, alias, name = line.split();aliases[alias] = bytes.fromhex(name).decode()
        elif line and not line.startswith('#'):
            name, layer, shape, *coords = line.split('\t')
            boxes.append(dict(net=aliases[name], layer=layer, shape=shape, bbox_dbu=list(map(int, coords))))
    assert aliases and boxes
    located = []
    for marker in markers:
        x0, y0, x1, y1 = marker['bbox_dbu']
        nearby = [box for box in boxes if box['net'].replace('\\', '') == marker['net'].replace('\\', '')
                  and box['layer'] == marker['layer'] and box['bbox_dbu'][0] < x1 + 1000
                  and box['bbox_dbu'][2] > x0 - 1000 and box['bbox_dbu'][1] < y1 + 1000
                  and box['bbox_dbu'][3] > y0 - 1000]
        located.append(dict(marker=marker, same_net_nearby_rectangles=nearby))
    result = dict(passed=True, kind=kind, source_run=number, input_odb=str(odb), input_odb_sha256=expected,
                  source_receipt_sha256=file_sha(source / 'receipt.json'), failed_gate_receipt_sha256=file_sha(gate / 'receipt.json'),
                  failed_report_sha256=file_sha(report_path), geometry_helper_sha256=file_sha(helper),
                  source_database_unchanged=True, selected_nets=len(aliases), exported_rectangles=len(boxes),
                  markers=located, marker_windows_without_same_net_rectangles=[i for i, m in enumerate(located) if not m['same_net_nearby_rectangles']],
                  physical_qualified=False, scope='Exact selected-net wire/via/BPin/transformed cell-pin geometry and terminal identities only. 0.5um marker windows are diagnostic views, never rule exclusions; original full reports and databases retained. No DRC repair, waiver, capacitance fix or qualification transfer.')
    (out / 'revision300-v-physical-localization.json').write_text(json.dumps(result, indent=2) + '\n')
