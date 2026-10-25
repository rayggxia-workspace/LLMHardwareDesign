"""Same physical endpoint under baseline/C1/C2, read-only full-clock-expanded report."""
import argparse
from common import *
p=argparse.ArgumentParser();p.add_argument('--stages',type=Path,nargs=3,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);m={'source':sources(),'resources':resource_snapshot(),'stages':[]}
for i,stage in enumerate(a.stages):
 sm=artifacts(stage);lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{stage}/final.odb}}',f'read_sdc {{{stage}/final.sdc}}',f'source {{{P}/setRC.tcl}}','estimate_parasitics -placement','puts "BEGIN_SAME_EXT79_FF_PATH"','report_checks -from [get_ports {ext_data[79]}] -to [get_pins {_70796_/D}] -path_delay min -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded -fields {capacitance slew fanout input} -digits 9','puts "END_SAME_EXT79_FF_PATH"'];f=a.out/f'path-{i}.tcl';f.write_text(tcl_script(lines));command(a.out,f'path-{i}',[OR,'-exit',f],300);m['stages'].append({'directory':str(stage),'manifest_sha256':sha(stage/'manifest.json'),'report':f'path-{i}.log'})
m['status']='SAME_PHYSICAL_PATH_REPORTED_NO_REPAIR';manifest(a.out,m);print(m['status'])
