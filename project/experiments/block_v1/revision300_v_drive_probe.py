"""Probe the two actual588 cap drivers on a disposable sealed GRT database."""
import json
import re
from pathlib import Path


TARGETS = {'place84364': ('BUF_X2', 'BUF_X4'),
           'place76249': ('BUF_X1', 'BUF_X2')}


def probe(root, out, cpus, run):
    from io_slots import file_sha
    assert cpus == 16
    base = out.parents[2]
    native = base/'block-v1-20261030-588/tasks/revision300-route-v'
    physical = base/'block-v1-20261030-589/tasks/revision300-physical-v'
    source = base/'block-v1-20261030-589/tasks/revision300-final-source-v'
    receipts = {}
    reports = {}
    for folder, name, passed in ((native, 'revision300-native-flow.json', True),
                                  (physical, 'five-macro-physical.json', False),
                                  (source, 'revision300-final-source.json', True)):
        receipt = json.loads((folder/'receipt.json').read_text())
        assert receipt['passed'] is passed
        assert file_sha(folder/name) == receipt['outputs'][name]
        receipts[folder.name] = receipt
        reports[folder.name] = json.loads((folder/name).read_text())
    flow = reports[native.name]
    final = reports[source.name]
    failure = reports[physical.name]
    assert final['source_native_receipt_sha256'] == file_sha(native/'receipt.json')
    assert failure['source_receipt_sha256'] == file_sha(source/'receipt.json')
    for n, h in flow['rtl_sha256'].items():
        assert file_sha(root/n) == h
    report = physical/'electrical-violations.rpt'
    assert file_sha(report) == receipts[physical.name]['outputs'][report.name]
    cap = report.read_text().split('max capacitance\n', 1)[1]
    rows = re.findall(r'(?m)^(place\d+)/Z\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+) \(VIOLATED\)$', cap)
    measured = {n: dict(limit_ff=float(l), cap_ff=float(c), slack_ff=float(s)) for n,l,c,s in rows}
    assert set(measured) == set(TARGETS)
    library = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    text = library.read_text()
    assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)', text)
    starts = list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{', text))
    caps = {}
    for k,m in enumerate(starts):
        if m[1] not in {v for pair in TARGETS.values() for v in pair}: continue
        chunk = text[m.start():starts[k+1].start() if k+1<len(starts) else len(text)]
        assert re.findall(r'\bfunction\s*:\s*"([^"]+)"', chunk) == ['A']
        caps[m[1]] = float(re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)', chunk)[1])
    for name, (old,new) in TARGETS.items():
        assert abs(measured[name]['limit_ff']-caps[old]) < .01
        assert caps[new] >= measured[name]['cap_ff']*1.2
    results = native/'flow/results/nangate45/bv1_block_v1_v/base'
    grt = results/'5_1_grt.odb'
    before_sha = file_sha(grt)
    assert before_sha == receipts[native.name]['outputs'][str(grt.relative_to(native))]
    script = 'set_thread_count 16\nread_db {'+str(grt)+'}\n'
    script += '''proc signal_pins {i} {
  set rows {}
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] in {POWER GROUND}} {continue}
    set n [$t getNet]
    lappend rows [list [$m getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]
  }
  return [lsort $rows]
}
set b [ord::get_db_block]
set f [open driver-probe.tsv w]
'''
    for name,(old,new) in TARGETS.items():
        script += '''set i [$b findInst {NAME}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "OLD"} {error "Measured GRT driver NAME differs from final"}
set pins [signal_pins $i]
set old [$i getMaster]
set replacement [[ord::get_db] findMaster NEW]
if {$replacement eq "NULL" || ![$i swapMaster $replacement]} {error "Measured driver swap failed NAME"}
if {[signal_pins $i] ne $pins} {error "Measured driver signal connectivity changed NAME"}
puts $f [join [list NAME OLD NEW [$old getWidth] [$old getHeight] [$replacement getWidth] [$replacement getHeight]] "\\t"]
'''.replace('NAME',name).replace('OLD',old).replace('NEW',new)
    script += 'close $f\n'
    (out/'probe.tcl').write_text(script)
    run(['openroad','-no_init','-exit',str(out/'probe.tcl')], 'probe.log')
    rows = [line.split('\t') for line in (out/'driver-probe.tsv').read_text().splitlines()]
    assert len(rows) == 2 and {row[0] for row in rows} == set(TARGETS)
    assert all(len(row)==7 and row[1:3]==list(TARGETS[row[0]]) and row[4]==row[6] for row in rows)
    assert file_sha(grt) == before_sha
    result = dict(passed=True, physical_qualified=False, targets=TARGETS, measured=measured,
                  original_grt_sha256=before_sha, original_grt_unchanged=True,
                  native_signal_pin_net_identity_preserved=True, liberty_sha256=file_sha(library),
                  buffer_max_capacitance_ff=caps, actual_native_master_geometry=rows,
                  source_native_receipt_sha256=file_sha(native/'receipt.json'),
                  source_final_receipt_sha256=file_sha(source/'receipt.json'),
                  physical_failure_receipt_sha256=file_sha(physical/'receipt.json'),
                  scope='Two actual current588/589 drivers only. Disposable native swapMaster probe; no placement/reroute/RCX/STA/DRC or final qualification. New routing and all final gates required.')
    (out/'revision300-v-drive-probe.json').write_text(json.dumps(result,indent=2)+'\n')
