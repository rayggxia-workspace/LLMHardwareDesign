"""Read-only actual installed CTS/clock reporting Tcl API discovery."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'source':sources(),'resources':resource_snapshot()}
lines=[]
for name in ('clock_tree_synthesis','report_cts','set_propagated_clock','report_clock_skew','report_clock_latency','set_routing_layers','global_route','estimate_parasitics'):
 lines += ['puts "BEGIN_API_'+name+'"','help '+name,'if {[llength [info procs '+name+']]} {puts [info body '+name+']}','puts "END_API_'+name+'"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],120);m['status']='ACTUAL_CTS_API_CAPTURED_NO_PHYSICAL_WORK';manifest(a.out,m)
