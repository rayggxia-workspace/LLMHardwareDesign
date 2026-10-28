"""Read-only discovery of pinned OpenDB wire encoding APIs on a Slurm node."""
import json
from pathlib import Path


def probe(root, out, cpus, run):
    assert cpus == 16
    script = '''set_thread_count 16
foreach pattern {odb::*dbWireEncoder* odb::*dbWireDecoder* odb::*dbWire_*} {
  puts "API_PATTERN $pattern"
  puts [join [lsort [info commands $pattern]] "\\n"]
}
if {[llength [info commands odb::new_dbWireEncoder]] != 1} {
  error "Pinned tool has no exposed wire encoder constructor"
}
set encoder [odb::new_dbWireEncoder]
puts "ENCODER_OBJECT $encoder"
puts "ENCODER_DISPATCH [info commands $encoder]"
odb::delete_dbWireEncoder $encoder
puts PINNED_API_PROBE_PASS
'''
    (out/'wire-api.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out/'wire-api.tcl'], 'wire-api.log')
    text = (out/'wire-api.log').read_text()
    assert 'PINNED_API_PROBE_PASS' in text
    (out/'revision300-s-wire-api.json').write_text(json.dumps(dict(
        passed=True, diagnostic_only=True, original_databases_opened=False,
        physical_qualified=False, api_log=text), indent=2)+'\n')


def repair_probe(root, out, cpus, run):
    """Append one same-net M2 rectangle to a copy; require native zero DRC."""
    from io_slots import file_sha
    assert cpus == 16
    base = out.parents[2]
    api = base/'block-v1-20261029-278/tasks/revision300-s-wire-api'
    ar = json.loads((api/'receipt.json').read_text())
    assert ar['passed']
    ap = api/'revision300-s-wire-api.json'
    assert file_sha(ap) == ar['outputs'][ap.name]
    diagnostic = base/'block-v1-20261029-277/tasks/revision300-s-drc-localize-route'
    dr = json.loads((diagnostic/'receipt.json').read_text())
    assert dr['passed']
    dp = diagnostic/'revision300-s-drc-localization.json'
    assert file_sha(dp) == dr['outputs'][dp.name]
    d = json.loads(dp.read_text())
    odb = Path(d['input_odb'])
    before = file_sha(odb)
    assert before == d['input_odb_sha256'] and d['violation_count'] == 1
    # Public API semantics: append preserves existing wire encoding, whereas
    # begin overwrites it. Pinned command discovery is separately bound above.
    # RECT fills only the reported same-net M2 corner's 0.1 x 0.03um bbox;
    # it is not an exception, layer change, or foreign-net connectivity edit.
    script = '''set_thread_count 16
read_db {%s}
set block [ord::get_db_block]
set matches {}
foreach net [$block getNets] {
  if {[string map [list [format %%c 92] {}] [$net getName]] eq {words[674][3]}} {
    lappend matches $net
  }
}
if {[llength $matches] != 1} {error "Ambiguous target net"}
set net [lindex $matches 0]
set wire [$net getWire]
set encoder [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $encoder $wire
odb::dbWireEncoder_newPath $encoder [[ord::get_db_tech] findLayer metal2] ROUTED
odb::dbWireEncoder_addPoint $encoder 362260 1806770
odb::dbWireEncoder_addRect $encoder 0 0 200 60
odb::dbWireEncoder_end $encoder
odb::delete_dbWireEncoder $encoder
write_db patched.odb
write_def patched.def
drt::check_drc_cmd patched-native-drc.rpt 0 0 0 0 native_whole_drc
puts SAME_NET_PATCH_PROBE_COMPLETE
''' % odb
    (out/'patch.tcl').write_text(script)
    run(['openroad', '-no_init', '-exit', out/'patch.tcl'], 'patch.log')
    assert file_sha(odb) == before
    text = (out/'patched-native-drc.rpt').read_text()
    count = text.count('violation type:')
    result = dict(passed=count == 0, diagnostic_only=True,
        input_odb=str(odb), input_odb_sha256=before,
        localization_receipt_sha256=file_sha(diagnostic/'receipt.json'),
        api_receipt_sha256=file_sha(api/'receipt.json'),
        patch=dict(layer='metal2', net='words[674][3]', dbu=2000,
                   bbox_dbu=[362260,1806770,362460,1806830]),
        patched_odb_sha256=file_sha(out/'patched.odb'),
        native_drc_count=count, original_unchanged=True,
        physical_qualified=False,
        remaining='Same-net geometry diff/connectivity, fresh finish/RCX/STA, full GDS deck, final function and strict LEC are required; this probe is not final acceptance.')
    (out/'revision300-s-patch-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'], 'Patched copy still has native DRC; preserve failure'
