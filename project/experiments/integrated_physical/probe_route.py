"""Read only installed global-route API and finite97 residual diagnostic."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'source':sources(),'resources':resource_snapshot()};artifacts(a.stage)
lines=[]
for n in('global_route','write_global_route_segments','report_wire_length','estimate_parasitics','report_parasitic_annotation'):
 lines += ['puts "BEGIN_API_'+n+'"','help '+n,'if {[llength [info procs '+n+']]} {puts [info body '+n+']}','puts "END_API_'+n+'"']
lines += [f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}',f'source {{{P}/setRC.tcl}}','estimate_parasitics -placement','puts "BEGIN_RESIDUAL97_HOLD"','report_checks -path_delay min -group_path_count 2 -format full_clock_expanded -fields {capacitance slew fanout input} -digits 9','puts "END_RESIDUAL97_HOLD"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],120);m.update(status='ACTUAL_ROUTE_API_AND_RESIDUAL97_CAPTURED_NO_TRANSFORMATION',stage_manifest_sha256=sha(a.stage/'manifest.json'));manifest(a.out,m)
