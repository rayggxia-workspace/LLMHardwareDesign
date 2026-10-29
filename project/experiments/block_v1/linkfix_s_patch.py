"""Two exact same-net M2 corner fills in the repaired S experiment copy."""
import hashlib
import json
import shutil
from pathlib import Path
from interconnect_spef import sha
from linkclose_measure import bound

PATCHES = [('words[674][3]', b'words\\[674\\][3]', [362260, 1806770, 362460, 1806830]),
           ('words[232][62]', b'words\\[232\\][62]', [2875960, 2001090, 2876160, 2001160])]


def partition(path):
    outside = hashlib.sha256(); selected = {}; active = None
    for line in path.read_bytes().splitlines(keepends=True):
        for _, escaped, _ in PATCHES:
            if line.lstrip().startswith(b'- ' + escaped + b' '):
                assert active is None and escaped not in selected
                active = escaped; selected[active] = []
        if active is None:
            outside.update(line)
        else:
            selected[active].append(line)
            if b';' in line:
                active = None
    assert active is None and len(selected) == 2
    return outside.hexdigest(), {k: b''.join(v).split() for k, v in selected.items()}


def verify_def_change(before,after):
    old_outside,old=partition(before);new_outside,new=partition(after)
    assert old_outside==new_outside,'Unrelated DEF bytes changed'
    for _,escaped,(x0,y0,x1,y1)in PATCHES:
        extra=('NEW metal2 ( %d %d ) RECT ( 0 0 %d %d )'%(x0,y0,x1-x0,y1-y0)).encode().split()
        assert new[escaped]==old[escaped][:-1]+extra+[b';'],'Target route changed beyond exact RECT'
    return old_outside


def probe(root, out, cpus, run):
    assert cpus == 16
    source = out.parents[2] / 'block-v1-20261029-928/tasks/linkfix-native-s'
    flow, receipt = bound(source, 'linkfix-native.json')
    results = source / 'flow/results/nangate45/bv1_block_v1_s16k/base'
    odb = results / '5_2_route.odb'
    assert sha(odb) == receipt['outputs'][str(odb.relative_to(source))]
    script = 'set_thread_count 16\nread_db {' + str(odb) + '}\nwrite_def before.def\n'
    script += 'drt::check_drc_cmd before-native-drc.rpt 0 0 0 0 native_whole_drc\nset b [ord::get_db_block]\n'
    for plain, _, (x0, y0, x1, y1) in PATCHES:
        script += 'set matches {}\nforeach n [$b getNets] {if {[string map [list [format %c 92] {}] [$n getName]] eq {' + plain + '}} {lappend matches $n}}\n'
        script += 'if {[llength $matches]!=1} {error {Ambiguous target net}}\nset n [lindex $matches 0]\nset e [odb::new_dbWireEncoder]\n'
        script += 'odb::dbWireEncoder_append $e [$n getWire]\nodb::dbWireEncoder_newPath $e [[ord::get_db_tech] findLayer metal2] ROUTED\n'
        script += 'odb::dbWireEncoder_addPoint $e %d %d\nodb::dbWireEncoder_addRect $e 0 0 %d %d\n' % (x0, y0, x1-x0, y1-y0)
        script += 'odb::dbWireEncoder_end $e\nodb::delete_dbWireEncoder $e\n'
    script += 'write_db patched.odb\nwrite_def patched.def\n'
    (out / 'patch.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out / 'patch.tcl'], 'patch.log')
    # Never qualify in-memory OpenDB edits against a router initialized from
    # the pre-edit design. A new process must load the serialized candidate.
    (out/'patched-drc.tcl').write_text('set_thread_count 16\nread_db {'+str(out/'patched.odb')+'}\ndrt::check_drc_cmd patched-native-drc.rpt 0 0 0 0 native_whole_drc\n')
    run(['openroad','-no_init','-exit',out/'patched-drc.tcl'],'patched-drc.log')
    before = (out / 'before-native-drc.rpt').read_text()
    after = (out / 'patched-native-drc.rpt').read_text()
    assert before.count('violation type:') == 3 and all(escaped.decode() in before for _, escaped, _ in PATCHES)
    old_outside=verify_def_change(out / 'before.def',out / 'patched.def')
    assert sha(odb) == receipt['outputs'][str(odb.relative_to(source))]
    result = dict(passed=not after.strip(), source=str(source), source_receipt_sha256=sha(source/'receipt.json'),
        input_odb=str(odb), input_odb_sha256=sha(odb), patches=[dict(net=p, bbox_dbu=b) for p, _, b in PATCHES],
        outside_targets_def_sha256=old_outside, native_before=before, native_after=after,
        patched_odb_sha256=sha(out/'patched.odb'), patched_def_sha256=sha(out/'patched.def'),
        scope='Only two same-net M2 RECT additions in the experimental route copy. All other DEF bytes unchanged. Native whole-chip check required zero; fresh finish/RCX/full DRC/STA/function/LEC still required.')
    (out/'linkfix-s-patch.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['passed']


def finish(root, out, cpus, run):
    from io_slots import slot
    assert cpus == 16
    probe_dir = out.parent / 'linkfix-s-patch'
    patch, pr = bound(probe_dir, 'linkfix-s-patch.json')
    source = Path(patch['source']); old, sr = bound(source, 'linkfix-native.json')
    assert patch['source_receipt_sha256'] == sha(source/'receipt.json')
    old_results = source / 'flow/results/nangate45/bv1_block_v1_s16k/base'
    results = out / 'flow/results/nangate45/bv1_block_v1_s16k/base'
    results.mkdir(parents=True)
    for name in ('config.mk', 'pins.json', 'pins.tcl', 'input.sdc'):
        assert sha(source/name) == sr['outputs'][name]
        shutil.copyfile(source/name, out/name)
    for name in ('1_synth_lec.v', '1_2_yosys.v', '1_2_yosys.sdc', '5_1_grt.sdc', 'bv1-input-diodes.tsv', 'bv1-input-delay.tsv'):
        p = old_results/name
        if name == 'bv1-input-delay.tsv' and not p.exists():
            continue
        assert sha(p) == sr['outputs'][str(p.relative_to(source))]
        shutil.copyfile(p, results/name)
    assert sha(probe_dir/'patched.odb') == patch['patched_odb_sha256'] == pr['outputs']['patched.odb']
    with slot(out.parents[2]):
        shutil.copyfile(probe_dir/'patched.odb', results/'5_2_route.odb')
    record = dict(old, passed=False, inherited_stages=old['stages'], stages=[], files={},
                  inherited_repaired_source=str(source), inherited_repaired_source_receipt_sha256=sha(source/'receipt.json'),
                  patch_receipt_sha256=sha(probe_dir/'receipt.json'), fresh_detail_route=False,
                  scope='Inherited repaired detailed route plus exactly two same-net M2 RECTs; fresh fill/finish/RCX. No original production change or transferred geometry/timing acceptance.')
    def save():
        (out/'linkfix-native.json').write_text(json.dumps(record, indent=2)+'\n')
    save()
    command = ['make', '-C', '/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG='+str(out/'config.mk'), 'WORK_HOME='+str(out/'flow'), 'NUM_CORES=16']
    for stage in ('do-5_3_fillcell', 'do-5_route', 'do-5_route.sdc', 'do-finish'):
        run(command+[stage], stage+'.log'); record['stages'].append(stage); save()
    for suffix in ('v', 'sdc', 'def', 'odb', 'spef'):
        p = results/('6_final.'+suffix)
        record['files'][p.name] = dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
    script = 'set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\ndrt::check_drc_cmd final-native-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'quick-drc.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out/'quick-drc.tcl'], 'quick-drc.log')
    assert not (out/'final-native-drc.rpt').read_text().strip()
    assert record['files']['6_final.v']['sha256'] == old['files']['6_final.v']['sha256'], 'Geometry-only edit changed signal netlist'
    record.update(passed=True, native_whole_drc_zero_before_full_acceptance=True)
    save()
