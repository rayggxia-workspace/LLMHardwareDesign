import tempfile,tkinter
from pathlib import Path
root=Path(__file__).resolve().parents[3]
fixture=(root/'work/YUZE-LU/143/r-input-hold/restored-081/issue143-input-hold-restored.sdc').read_text()
script=root/'project/experiments/block_v2/r_input_hold_reset_guard.tcl'
for fail in (False,True):
    with tempfile.TemporaryDirectory() as tmp:
        t=tkinter.Tcl()
        t.setvar('fixture',fixture);t.setvar('env(RESULTS_DIR)',str(Path(tmp)).replace('\\','/'))
        t.eval('''
proc get_ports {pattern} {
 set result {}
 if {[string match *cmd_data* $pattern]} {for {set i 0} {$i<128} {incr i} {lappend result cmd_data\\[$i\\]}}
 if {[string match *reset* $pattern]} {lappend result reset}
 return $result
}
proc get_clocks {pattern} {return core}
set current_min 0.2
proc set_input_delay {args} {set ::current_min [lindex $args 1]}
proc write_sdc {path} {set s [open $path w];puts -nonewline $s $::fixture;close $s}
proc repair_timing_helper {args} {
 if {$::current_min!=0.0} {error "Guard absent during repair"}
 if {$args ne {arg1 arg2}} {error "Native arguments changed"}
 if {$::test_failure} {error "deliberate native repair failure"}
 return native_ok
}
''')
        t.setvar('test_failure',int(fail))
        t.call('source',str(script).replace('\\','/'))
        try:
            result=t.eval('repair_timing_helper arg1 arg2')
            assert not fail and result=='native_ok'
        except tkinter.TclError as error:
            assert fail and 'deliberate native repair failure' in str(error),error
        assert float(t.getvar('current_min'))==.2
        assert (Path(tmp)/'issue143-input-hold-guard.tsv').read_text().splitlines()==[
            'scope\tcmd_data+reset\t129\toptimized_min_ns\t0.000\tsignoff_min_ns\t0.200\tglobal_hold_ns\t0.020',
            'entered\t0.000','restored\t0.200']
print('PASS Tcl8.6 actual native SDC fixture:129 inputs; success/error both restore0.2; native args preserved')
