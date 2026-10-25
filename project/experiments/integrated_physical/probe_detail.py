"""Inspect installed detailed-route and RCX wrappers without changing a design."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
lines=['set_thread_count 8']
for n in ('detailed_route','design_is_routed','check_antennas','define_process_corner','extract_parasitics','write_spef','read_spef','read_guides'):
 lines+=['puts "BEGIN_API_'+n+'"','help '+n,'if {[llength [info procs '+n+']]} {puts [info body '+n+']}','puts "END_API_'+n+'"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],120)
files=[P/'rcx_patterns.rules',F/'scripts/detail_route.tcl',F/'scripts/final_report.tcl',P/'config.mk']
manifest(a.out,{'status':'EXISTING_DETAILED_ROUTE_RCX_API_READ_ONLY','source':sources(),'resources':resource_snapshot(),'files':[{'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q)}for q in files]})
print('EXISTING_DETAILED_ROUTE_RCX_API_READ_ONLY')
