"""Bounded existing-tool capability and physical input probe, no design computation."""
import argparse,traceback
from common import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','source':sources(),'task':'probe','resources':resource_snapshot()}
 files=[LIB,TECH,LEF,P/'README.md',P/'setRC.tcl',P/'make_tracks.tcl',P/'fastroute.tcl',P/'rcx_patterns.rules',P/'grid_strategy-M1-M4-M7.tcl',P/'tapcell.tcl',P/'drc/FreePDK45.lydrc',OR,STA,D/'lib64/ld-linux-x86-64.so.2']
 try:
  config=load(HERE/'config.json');need(sha(LIB)==config['library_sha256'],'same research Liberty');need('purposely non-manufacturable'in(P/'README.md').read_text(),'explicit non-manufacturing boundary')
  names=['set_thread_count','initialize_floorplan','make_tracks','set_io_pin_constraint','place_pins','global_placement','detailed_placement','check_placement','estimate_parasitics','set_wire_rc','set_routing_layers','set_global_routing_layer_adjustment','clock_tree_synthesis','report_cts','global_route','detailed_route','check_antennas','define_process_corner','extract_parasitics','write_spef','read_spef','write_def','write_db','write_verilog','repair_design','repair_timing','find_timing_paths','report_check_types','report_clock_skew','report_clock_min_period','report_parasitic_annotation','write_sdc']
  lines=['puts "BEGIN_TOOL_CAPABILITY"','set_thread_count 8']
  for n in names:lines+=['puts {BEGIN_HELP_'+n+'}','help '+n,'puts {END_HELP_'+n+'}']
  lines+=['puts "END_TOOL_CAPABILITY"'];(a.out/'commands.tcl').write_text(tcl_script(lines));command(a.out,'commands',[OR,'-exit',a.out/'commands.tcl'],300)
  command(a.out,'openroad-version',[OR,'-version'],120);command(a.out,'sta-version',[STA,'-version'],120)
  m.update(status='EXISTING_TOOL_AND_PLATFORM_PROBED_NOT_DESIGN_QUALIFIED',inputs=[{'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q)}for q in files],lvs_deck_exists=(P/'lvs/FreePDK45.lylvs').exists(),config_sha256=sha(HERE/'config.json'),manufacturable=False)
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
