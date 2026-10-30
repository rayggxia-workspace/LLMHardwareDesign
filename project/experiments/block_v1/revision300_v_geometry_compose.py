"""Compose two measured repairs on the old failed V copy; never acceptance."""
from collections import Counter, defaultdict
import json


def probe(root, out, cpus, run):
    from io_slots import file_sha
    from revision300_v_corner_probe import def_content, violations
    assert cpus == 16
    base = out.parents[2]
    batch = base / 'block-v1-20261030-594/tasks/revision300-v-via-batch'
    corner = base / 'block-v1-20261030-568/tasks/revision300-v-corner-filter'
    bound = {}
    for directory, report in [(batch, 'revision300-v-via-batch.json'),
                              (corner, 'revision300-v-corner-probe.json')]:
        receipt = json.loads((directory / 'receipt.json').read_text())
        assert receipt['passed']
        for name in (report,):
            assert file_sha(directory / name) == receipt['outputs'][name]
        bound[str(directory)] = file_sha(directory / 'receipt.json')
    bd = json.loads((batch / 'revision300-v-via-batch.json').read_text())
    cd = json.loads((corner / 'revision300-v-corner-probe.json').read_text())
    assert bd['passed'] and cd['passed']
    assert bd['input_odb_sha256'] == cd['source_odb_sha256']
    assert bd['added_markers'] == cd['added_marker_count'] == 0
    br = json.loads((batch / 'receipt.json').read_text())
    cr = json.loads((corner / 'receipt.json').read_text())
    for name in ('batch-candidate.odb', 'batch-candidate.def', 'batch-native-drc.rpt'):
        assert file_sha(batch / name) == br['outputs'][name]
    chosen_file = corner / 'candidate-rectangles.json'
    assert file_sha(chosen_file) == cr['outputs'][chosen_file.name]
    chosen = json.loads(chosen_file.read_text())['chosen']
    assert len(chosen) == 232
    groups = defaultdict(list)
    for row in chosen:
        groups[row['net'].replace('\\', '')].append(row)
    script = ('set_thread_count 16\nread_db {' + str(batch / 'batch-candidate.odb') +
              '}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
              'set exact [dict create]\nforeach net [$block getNets] {\n'
              'set plain [string map [list [format %c 92] {}] [$net getName]]\n'
              'dict lappend exact $plain $net\n}\n')
    for name, rows in sorted(groups.items()):
        script += ('set matches [dict get $exact [encoding convertfrom utf-8 '
                   '[binary decode hex {' + name.encode().hex() + '}]]]\n'
                   'if {[llength $matches] != 1} {error "Ambiguous target"}\n'
                   'set enc [odb::new_dbWireEncoder]\n'
                   'odb::dbWireEncoder_append $enc [[lindex $matches 0] getWire]\n')
        for row in rows:
            x0, y0, x1, y1 = row['bbox_dbu']
            script += ('odb::dbWireEncoder_newPath $enc [$tech findLayer ' +
                       row['layer'] + '] ROUTED\n'
                       'odb::dbWireEncoder_addPoint $enc %d %d\n'
                       'odb::dbWireEncoder_addRect $enc 0 0 %d %d\n' %
                       (x0, y0, x1 - x0, y1 - y0))
        script += 'odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
    script += ('write_db composed-candidate.odb\nwrite_def composed-candidate.def\n'
               'drt::check_drc_cmd composed-native-drc.rpt 0 0 0 0 native_whole_drc\n')
    (out / 'compose.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out / 'compose.tcl'], 'compose.log')
    before, routes0, n0 = def_content(batch / 'batch-candidate.def')
    after, routes1, n1 = def_content(out / 'composed-candidate.def')
    expected = Counter((r['net'].replace('\\', ''), r['layer'], *r['bbox_dbu'])
                       for r in chosen)
    exact = after == before + expected and routes0 == routes1 and n0 == n1
    original_dir = base / 'block-v1-20261030-557/tasks/revision300-v-spacing-localize'
    original_receipt = json.loads((original_dir / 'receipt.json').read_text())
    original_report = original_dir / 'native-whole-drc.rpt'
    assert file_sha(original_report) == original_receipt['outputs'][original_report.name]
    old = violations(original_report.read_text())
    previous = violations((batch / 'batch-native-drc.rpt').read_text())
    new = violations((out / 'composed-native-drc.rpt').read_text())
    unchanged = all(file_sha(batch / name) == br['outputs'][name] for name in
                    ('batch-candidate.odb', 'batch-candidate.def', 'batch-native-drc.rpt'))
    result = dict(passed=exact and unchanged and not (new - old) and
                  not (new - previous) and sum(new.values()) < sum(previous.values()),
                  diagnostic_only=True, physical_qualified=False,
                  dependency_receipt_sha256=bound, original_odb_sha256=bd['input_odb_sha256'],
                  batch_inputs_unchanged=unchanged, appended_rectangles=len(chosen),
                  exact_rect_delta_and_nonrect_routes=exact, normal_net_counts=[n0, n1],
                  original_native_count=sum(old.values()), batch_native_count=sum(previous.values()),
                  composed_native_count=sum(new.values()),
                  added_vs_original=sum((new-old).values()), added_vs_batch=sum((new-previous).values()),
                  scope='Fresh whole native checker on actual composition of two measured old523 repairs. '
                        'Not a sum of independent counts; no current588 or final physical qualification. '
                        'Connectivity, RCX/STA, full GDS, function/LEC and delivery remain required.')
    (out / 'revision300-v-geometry-compose.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['passed'], 'Composition rejected; preserve the actual result'
