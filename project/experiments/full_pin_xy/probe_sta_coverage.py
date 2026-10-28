"""Inventory the installed STA checks before extending source-bound audits.

This does not read a design or declare any timing/clock rule passed. Missing
commands and Liberty check types remain coverage gaps, not zero violations.
"""
from pathlib import Path
import datetime,json,os,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent
out=ROOT/'sta_coverage_api'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
script=out/'probe.tcl'
script.write_text('set audit_out '+tcl(out)+'\n'+r'''
puts [list ACTUAL_EXECUTABLE [info nameofexecutable]]
puts [exec sha256sum [info nameofexecutable]]
foreach pattern {*pulse* *period* *gating* *skew* *check* *clock*} {
 puts [list NATIVE_STA_COMMANDS $pattern [lsort [info commands sta::$pattern]]]
}
foreach c {report_check_types report_checks check_setup report_clock_properties report_clock_min_period report_clock_skew report_clock_latency report_pulse_width_checks report_clock_gating_checks report_min_period_checks} {
 puts [list NATIVE_COMMAND_AVAILABLE $c [expr {[llength [info commands $c]]>0}]]
 puts [list HELP_BEGIN $c];set code [catch {help $c} error];puts [list HELP_END $c $code $error]
 if {![catch {info body $c} body]} {set f [open $audit_out/$c.body.tcl w];puts -nonewline $f $body;close $f}
}
set lib /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
puts [list ACTUAL_TYPICAL_LIB_SHA [exec sha256sum $lib]]
set f [open $lib r];set text [read $f];close $f
foreach name {min_pulse_width minimum_period clock_gating_setup_rising clock_gating_setup_falling clock_gating_hold_rising clock_gating_hold_falling recovery_rising recovery_falling removal_rising removal_falling setup_rising setup_falling hold_rising hold_falling} {
 set pattern [format {timing_type\s*:\s*%s\s*;} $name]
 puts [list TYPICAL_LIB_TIMING_TYPE_DECLARATIONS $name [regexp -all $pattern $text]]
}
puts {NO_DESIGN_LOADED_NO_CLOCK_OR_TIMING_PASS_INFERRED}
''')
common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
rc=execute(common,script,out/'native.log',threads=1)
rec={'scope':'INSTALLED_STA_CAPABILITIES_AND_ACTUAL_LIBERTY_DECLARATIONS_ONLY_NOT_DESIGN_RULE_PASS',
 'native_returncode':rc,'no_design_loaded':True,'full_qualification':False,
 'absent_check_interpretation':'UNKNOWN_OR_NOT_DEFINED_NOT_ZERO_VIOLATIONS',
 'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
 'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}}
(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
sys.exit(rc)
