"""Replay observed gate-pin toggles when read_vcd loses aliases in a final ODB."""
import argparse
from pathlib import Path


def scalar_pin_activity(path, scope, table):
    """Preserve each distinct gate port, including shared VCD signal IDs."""
    parents = []
    pins = {}
    with path.open(encoding="ascii") as stream:
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "$scope":
                parents.append(parts[2])
            elif parts[0] == "$upscope":
                parents.pop()
            elif parts[0] == "$enddefinitions":
                break
            elif parts[0] == "$var" and parts[2] == "1" and parents[:-1] == scope:
                name = f"{parents[-1]}/{parts[4]}"
                assert name not in pins and not set(name) & set("{}\t\r\n")
                pins[name] = parts[3]

        codes = set(pins.values())
        assert codes
        value = {}
        changed_at = {}
        transitions = dict.fromkeys(codes, 0)
        high_ticks = dict.fromkeys(codes, 0)
        first = now = None
        for line in stream:
            row = line.strip()
            if row.startswith("#"):
                tick = int(row[1:])
                assert now is None or tick >= now
                if first is None:
                    first = tick
                now = tick
            elif row and row[0] in "01xXzZ" and row[1:] in codes:
                new, code = row[0], row[1:]
                assert new in "01" and now is not None, (path, code, now, new)
                if code not in value:
                    assert now == first
                    value[code], changed_at[code] = new, now
                elif new != value[code]:
                    transitions[code] += 1
                    if value[code] == "1":
                        high_ticks[code] += now - changed_at[code]
                    value[code], changed_at[code] = new, now
    assert value.keys() == codes and now > first
    duration_ps = now - first
    for code, last in value.items():
        if last == "1":
            high_ticks[code] += now - changed_at[code]
    with table.open("w", encoding="ascii", newline="\n") as output:
        for pin, code in sorted(pins.items()):
            output.write(f"{pin}\t{transitions[code] * 1e12 / duration_ps:.12g}\t"
                         f"{high_ticks[code] / duration_ps:.12g}\n")
    return len(pins), len(codes), duration_ps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    scope = ["test_e_s128_joint", "dut", "narrow_leaf", "arithmetic"]
    for mode in ("active", "idle", "active-clock-only"):
        waveform = "active" if mode == "active-clock-only" else mode
        table = args.output / f"{waveform}-gate-pin-activity.tsv"
        if mode == waveform:
            counts = scalar_pin_activity(args.input / f"{waveform}-tt300.vcd", scope, table)
            print(f"{mode} gate_ports={counts[0]} aliases={counts[1]} duration_ps={counts[2]}")
        source = (args.input / f"{waveform}-power.tcl").read_text()
        start = source.index("report_activity_annotation")
        source = (source[:start] + f"set port_table [open {{{table.resolve()}}} r]\n"
                  + f"set clocks_only {int(mode == 'active-clock-only')}\n") + r"""
set gates_set 0
set pins_missing 0
set active_clock_pins 0
set block [ord::get_db_block]
set slash [format %c 92]
set pin_to_db [lindex [info commands ::sta_to_db_pin] 0]
if {$pin_to_db eq ""} { set pin_to_db [lindex [info commands ::sta::sta_to_db_pin] 0] }
if {$pin_to_db eq ""} { error "missing STA-to-ODB pin conversion" }
while {[gets $port_table line] >= 0} {
  lassign [split $line "\t"] name density duty
  set split_at [string last / $name]
  set gate [string range $name 0 [expr {$split_at - 1}]]
  set port [string range $name [expr {$split_at + 1}] end]
  # write_verilog escapes an ODB backslash, and Verilator's VCD names
  # expose a single backslash. Keep a one-to-one exact terminal binding.
  set escaped [string map [list $slash "$slash$slash"] $gate]
  set terminals {}
  foreach spelling [lsort -unique [list $gate $escaped]] {
    set inst [$block findInst $spelling]
    if {$inst eq "NULL" || $inst eq ""} { continue }
    set t [$inst findITerm $port]
    if {$t ne "NULL" && $t ne ""} { lappend terminals $t }
  }
  if {[llength $terminals] == 0} {
    incr pins_missing
    continue
  }
  if {[llength $terminals] != 1} { error "ambiguous ODB gate-pin $name" }
  set terminal [lindex $terminals 0]
  set match [get_pins -quiet [list $name]]
  if {[llength $match] != 1 || [$pin_to_db [lindex $match 0]] ne $terminal} {
    error "gate-pin trace does not resolve to exact ODB terminal $name (matches=$match)"
  }
  set net [$terminal getNet]
  set clock_pin [expr {$net ne "NULL" && $net ne "" && [$net getSigType] eq "CLOCK"}]
  if {$clock_pin && $density > 0} { incr active_clock_pins }
  if {$clocks_only && !$clock_pin} { set density 0 }
  sta::set_power_pin_activity [lindex $match 0] $density $duty
  incr gates_set
}
close $port_table
puts "E_GATE_PIN_ACTIVITY matched=$gates_set trace_only=$pins_missing active_clock=$active_clock_pins clocks_only=$clocks_only"
if {$gates_set < 80000 || $active_clock_pins == 0} { error "insufficient exact gate-pin activity coverage" }
report_activity_annotation
report_power -digits 12
"""
        (args.output / f"{mode}-pins.tcl").write_text(source, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
