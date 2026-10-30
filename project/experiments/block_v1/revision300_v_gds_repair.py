"""Six bounded one-RECT candidates on copies of actual failed767 source."""
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

OLD = ('metal2', 995340, 145880, 996180, 145950)
CUTS = (995550, 995600, 995650, 995700, 995750, 995800)


def nonnet(path):
    # Keep all VIAS, COMPONENTS, SPECIALNETS, PINS and remaining sections.
    text = path.read_text()
    start = re.search(r'(?m)^NETS \d+ ;\s*$', text); assert start
    stop = text.index('END NETS', start.end()) + len('END NETS')
    return hashlib.sha256(re.sub(r'\s+', ' ', text[:start.start()]+text[stop:]).strip().encode()).hexdigest()


def probe(root, out, cpus, run, case):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of, token_hash
    from revision300_v_via_bridge import path_key
    assert cpus == 16 and case in range(6)
    base = out.parents[2]
    bindings = []
    for number, variant in ((793, 'odb'), (795, 'gds')):
        task = base/f'block-v1-20261031-{number}/tasks/revision300-v-gds-localize-{variant}'
        receipt = json.loads((task/'receipt.json').read_text()); assert receipt['passed']
        report = task/'revision300-v-gds-localization.json'
        assert file_sha(report) == receipt['outputs'][report.name]
        proof = json.loads(report.read_text())
        assert proof['passed'] and proof['original_inputs_unchanged'] and proof['diagnostic_only']
        assert proof['source_receipt_sha256'] == 'f06b8e147dfb8bde4e5cdd662bfbbad97b873e661b3b47c9667a6386a6d06005'
        bindings.append(dict(task=str(task), receipt_sha256=file_sha(task/'receipt.json'), report_sha256=file_sha(report)))
    source = base/'block-v1-20261031-767/tasks/revision300-final-source-v'
    assert file_sha(source/'receipt.json') == proof['source_receipt_sha256']
    sr = json.loads((source/'receipt.json').read_text()); assert sr['passed']
    flowpath = source/'revision300-final-source.json'
    assert file_sha(flowpath) == sr['outputs'][flowpath.name]
    flow = json.loads(flowpath.read_text())
    odb = Path(flow['final_files']['6_final.odb']['path'])
    definition = Path(flow['final_files']['6_final.def']['path'])
    for name, path in (('6_final.odb', odb), ('6_final.def', definition)):
        assert file_sha(path) == flow['final_files'][name]['sha256']
    assert file_sha(odb) == proof['input_odb_sha256'] and file_sha(definition) == proof['input_def_sha256']
    others = Counter(); target = None; count = 0
    for record in records(definition):
        count += 1
        if name_of(record) == 'net96230':
            assert target is None; target = record
        else:
            others[token_hash(record)] += 1
    assert count == 562494 and target is not None
    header, paths, rects = decode(target)
    assert rects[OLD] == 1 and all(p[2] is None for path in paths for p in path['points'])
    expected = rects.copy(); expected.subtract([OLD]); expected += Counter()
    replacement = (*OLD[:3], CUTS[case], OLD[4])
    expected[replacement] += 1
    assert OLD[1] < replacement[3] < OLD[3]
    script = 'set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset tech [ord::get_db_tech]\n'
    script += 'if {[$tech getManufacturingGrid] != 5} {error {Grid mismatch}}\nset net [$block findNet net96230]\nif {$net eq "NULL"} {error {Missing exact net}}\n'
    script += 'set enc [odb::new_dbWireEncoder]\nodb::dbWireEncoder_begin $enc [$net getWire]\n'
    for path in paths:
        script += 'odb::dbWireEncoder_newPath $enc [$tech findLayer '+path['layer']+'] ROUTED\n'
        for x,y,_ in path['points']:
            script += 'odb::dbWireEncoder_addPoint $enc %d %d\n' % (x,y)
        if path['via']:
            script += 'odb::dbWireEncoder_addTechVia $enc [$tech findVia '+path['via']+']\n'
    for (layer,x0,y0,x1,y1), n in expected.items():
        for _ in range(n):
            script += 'odb::dbWireEncoder_newPath $enc [$tech findLayer '+layer+'] ROUTED\nodb::dbWireEncoder_addPoint $enc %d %d\nodb::dbWireEncoder_addRect $enc 0 0 %d %d\n' % (x0,y0,x1-x0,y1-y0)
    script += 'odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\nwrite_db local-candidate.odb\nwrite_def local-candidate.def\ndrt::check_drc_cmd local-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'repair.tcl').write_text(script)
    (out/'expected-one-rect.json').write_text(json.dumps(dict(case=case,old=OLD,new=replacement,diagnostic_bindings=bindings),indent=2)+'\n')
    run(['openroad','-no_init','-exit',out/'repair.tcl'], 'repair.log')
    actual = Counter(); found = None; count1 = 0
    for record in records(out/'local-candidate.def'):
        count1 += 1
        if name_of(record) == 'net96230':
            assert found is None; found = decode(record)
        else:
            actual[token_hash(record)] += 1
    assert found is not None
    h,p,r = found
    exact = (count == count1 and actual == others and token_hash(h) == token_hash(header)
             and Counter(map(path_key,p)) == Counter(map(path_key,paths)) and r == expected
             and nonnet(definition) == nonnet(out/'local-candidate.def'))
    unchanged = file_sha(odb) == proof['input_odb_sha256'] and file_sha(definition) == proof['input_def_sha256']
    native = (out/'local-native-drc.rpt').read_text()
    result = dict(passed=exact and unchanged and not native.strip(), diagnostic_only=True,
        physical_qualified=False, case=case, source_receipt_sha256=proof['source_receipt_sha256'],
        source_inputs_sha256={'6_final.odb':proof['input_odb_sha256'],'6_final.def':proof['input_def_sha256']},
        diagnostic_bindings=bindings, old_rectangle=OLD, replacement_rectangle=replacement,
        normal_net_counts=[count,count1], exact_one_rect_and_all_other_def_geometry=exact,
        original_inputs_unchanged=unchanged, candidate_native_count=native.count('violation type:'),
        native_report=native,
        scope='One RECT shortened on copied actual767 source; original routes/vias and all other NETS/nonNET geometry exact. Full native check only. Fresh RCX/STA/complete unmodified GDS/function/LEC/sixfiles/fullview/interfaces still required; no qualification transfer.')
    (out/'revision300-v-gds-repair.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'], 'Preserve failed candidate and continue other independent queue cases'
