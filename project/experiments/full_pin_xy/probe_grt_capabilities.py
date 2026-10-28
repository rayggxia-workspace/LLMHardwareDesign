"""Read-only native API/source inventory; never attach to or alter active jobs."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent
out=ROOT/'tool_api'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
script=out/'probe.tcl'
script.write_text('''puts {NATIVE_GRT_COMMANDS_BEGIN}
foreach c [lsort [info commands grt::*]] {puts $c}
puts {NATIVE_GRT_COMMANDS_END}
foreach c {global_route set_routing_layers set_global_routing_layer_adjustment set_global_routing_region_adjustment} {
  puts "COMMAND_BODY $c"
  if {[catch {info body $c} body]} {puts $body} else {puts $body}
  catch {help $c}
}
catch {help *grid*}
foreach p {/OpenROAD-flow-scripts/tools/OpenROAD/src/grt/src/GlobalRouter.cpp /OpenROAD-flow-scripts/tools/OpenROAD/src/grt/src/Grid.cpp /OpenROAD-flow-scripts/tools/OpenROAD/src/grt/src/GlobalRouter.tcl} {
  puts [list SOURCE_AVAILABLE $p [file exists $p]]
}
''')
common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
rc=execute(common,script,out/'native.log',threads=1)
rec={'scope':'READ_ONLY_NATIVE_GRT_CAPABILITY_PROBE_NOT_PHYSICAL_REPAIR','native_returncode':rc,
  'no_active_process_attach_signal_or_input_mutation':True,'full_qualification':False,
  'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
  'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}}
(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
sys.exit(rc)
