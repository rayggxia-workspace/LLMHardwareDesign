"""Read-only discovery of pinned OpenDB wire encoding APIs on a Slurm node."""
import json


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
