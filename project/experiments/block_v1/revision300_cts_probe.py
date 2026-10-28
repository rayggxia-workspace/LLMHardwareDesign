"""Diagnose failed T CTS from a receipt-bound placement without qualifying it.

The only skipped optimization is CTS timing repair, solely to expose its input
paths. No final-route/acceptance entry point consumes this diagnostic result.
"""
import json
import shutil
from pathlib import Path


def probe(root, out, cpus, run, kind='t'):
    from io_slots import file_sha, slot
    assert cpus == 16 and kind in ('s','t')
    base = out.parents[2]
    source = base/('block-v1-20261028-234/tasks/revision300-route-'+kind)
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is False and receipt['mode'] == 'revision300-route-'+kind
    report = json.loads((source/'revision300-native-flow.json').read_text())
    assert report['passed'] is False and report['stages'] == ['do-1_synth', 'do-floorplan', 'do-place']
    assert file_sha(source/'revision300-native-flow.json') == receipt['outputs']['revision300-native-flow.json']
    relative = Path('flow/results/nangate45/'+('bv1_transaction6k'if kind=='t'else'bv1_block_v1_s16k')+'/base')
    destination = out/relative
    destination.mkdir(parents=True)
    originals = {}
    for name in ['config.mk', str(relative/'3_place.odb'), str(relative/'3_place.sdc')]:
        p = source/name
        assert file_sha(p) == receipt['outputs'][name]
        originals[name] = file_sha(p)
        if name != 'config.mk':
            with slot(base):
                shutil.copyfile(p, out/name)
    hook = out/'diagnostic.tcl'
    hook.write_text('cd {'+str(out)+'}\n'+'''# Post-CTS, before any timing repair. Placement RC only.
report_worst_slack -min -digits 9 > diagnostic-timing.rpt
report_worst_slack -max -digits 9 >> diagnostic-timing.rpt
report_checks -path_delay min_max -group_path_count 20 -digits 9 -format full_clock_expanded >> diagnostic-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > diagnostic-electrical.rpt
write_sdc -digits 12 diagnostic-readback.sdc
''')
    config = (source/'config.mk').read_text()
    config += '\nexport SKIP_CTS_REPAIR_TIMING = 1\nexport CTS_SNAPSHOTS = 1\nexport POST_CTS_TCL = '+str(hook)+'\n'
    (out/'config.mk').write_text(config)
    command = ['make', '-C', '/OpenROAD-flow-scripts/flow',
               'DESIGN_CONFIG='+str(out/'config.mk'), 'WORK_HOME='+str(out/'flow'), 'NUM_CORES=16']
    for key in ['SKIP_CTS_REPAIR_TIMING', 'CTS_SNAPSHOTS', 'POST_CTS_TCL']:
        run(command+['print-'+key], 'variable-'+key+'.log')
    run(command+['do-4_1_cts'], 'cts-probe.log')
    assert (out/'diagnostic-timing.rpt').is_file()
    for name, digest in originals.items():
        assert file_sha(source/name) == digest, 'Diagnostic mutated source'
    result = dict(passed=True, source_receipt_sha256=file_sha(source/'receipt.json'),
                  source_files_sha256=originals, source_unchanged=True,
                  config_sha256=file_sha(out/'config.mk'),
                  qualified_hard_macro=False, physical_implementation_completed=False,
                  scope='Post-CTS pre-repair diagnostic only; placement RC, repair intentionally skipped; no final acceptance')
    (out/'revision300-cts-probe.json').write_text(json.dumps(result, indent=2)+'\n')


def readback(root, out, cpus, run):
    """Resume only reports from the actual saved pre-repair snapshot."""
    from io_slots import file_sha
    assert cpus == 16
    base = out.parents[2]
    source = base/'block-v1-20261028-237/tasks/revision300-cts-probe'
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is False and receipt['mode'] == 'revision300-cts-probe'
    results = source/'flow/results/nangate45/bv1_transaction6k/base'
    files = [results/('4_1_pre_repair_setup_hold.'+suffix) for suffix in ['odb', 'sdc']]
    bound = {}
    for p in files:
        assert file_sha(p) == receipt['outputs'][str(p.relative_to(source))]
        bound[str(p)] = file_sha(p)
    platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    prefix = 'set_thread_count 16\nread_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    prefix += 'read_db {'+str(files[0])+'}\nread_sdc {'+str(files[1])+'}\n'
    prefix += 'source {'+str(platform/'setRC.tcl')+'}\nset_propagated_clock [all_clocks]\nestimate_parasitics -placement\n'
    body = '''report_worst_slack -min -digits 9 > diagnostic-timing.rpt
report_worst_slack -max -digits 9 >> diagnostic-timing.rpt
report_checks -path_delay min_max -group_path_count 20 -digits 9 -format full_clock_expanded >> diagnostic-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > diagnostic-electrical.rpt
write_sdc -digits 12 diagnostic-readback.sdc
'''
    (out/'readback.tcl').write_text(prefix+body)
    run(['openroad', '-no_init', '-exit', out/'readback.tcl'], 'readback.log')
    for name, digest in bound.items():
        assert file_sha(Path(name)) == digest
    result = dict(passed=True, source_receipt_sha256=file_sha(source/'receipt.json'),
                  source_files_sha256=bound, source_unchanged=True,
                  qualified_hard_macro=False, physical_implementation_completed=False,
                  scope='Read-only post-CTS pre-repair snapshot, placement RC only; no optimization or final acceptance')
    (out/'revision300-cts-readback.json').write_text(json.dumps(result, indent=2)+'\n')


def hold_probe(root,out,cpus,run):
    """Bound a diagnostic repair to 0.1% buffers; preserve before/after paths."""
    from io_slots import file_sha
    assert cpus==16
    base=out.parents[2]
    source=base/'block-v1-20261028-237/tasks/revision300-cts-probe'
    receipt=json.loads((source/'receipt.json').read_text())
    assert receipt['passed']is False
    results=source/'flow/results/nangate45/bv1_transaction6k/base'
    files=[results/('4_1_pre_repair_setup_hold.'+suffix)for suffix in ['odb','sdc']]
    hashes={str(p):file_sha(p)for p in files}
    for p in files:assert file_sha(p)==receipt['outputs'][str(p.relative_to(source))]
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    body='set_thread_count 16\nread_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
    body+='read_db {'+str(files[0])+'}\nread_sdc {'+str(files[1])+'}\nsource {'+str(platform/'setRC.tcl')+'}\n'
    body+='set_propagated_clock [all_clocks]\nestimate_parasitics -placement\n'
    body+='report_checks -path_delay min_max -group_path_count 4 -digits 9 -format full_clock_expanded > before.rpt\n'
    body+='set code [catch {repair_timing -hold -max_buffer_percent 0.1 -hold_margin 0.020 -verbose} message]\n'
    body+='set f [open repair-status.txt w]\nputs $f [list $code $message]\nclose $f\n'
    body+='report_checks -path_delay min_max -group_path_count 4 -digits 9 -format full_clock_expanded > after.rpt\n'
    body+='write_db diagnostic-after.odb\n'
    (out/'bounded-hold.tcl').write_text(body)
    run(['openroad','-no_init','-exit',out/'bounded-hold.tcl'],'bounded-hold.log')
    assert all(file_sha(p)==digest for p,digest in hashes.items())
    result=dict(passed=True,source_receipt_sha256=file_sha(source/'receipt.json'),source_files_sha256=hashes,
                source_unchanged=True,max_buffer_percent=.1,qualified_hard_macro=False,
                scope='Bounded placement-RC hold repair diagnosis; command failure caught for before/after inspection, never final acceptance')
    (out/'revision300-hold-probe.json').write_text(json.dumps(result,indent=2)+'\n')
