"""Independent, post-screen physical trial. Never writes production flow paths."""
from pathlib import Path
import subprocess,json,hashlib,shutil,os,argparse,re
P=Path(__file__).resolve().parent
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
def main():
 p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,default=256);p.add_argument('--candidate',choices=['A0','A1','A2g','B256','B1024'],default=None);a=p.parse_args();dest=Path.cwd()/'physical';dest.mkdir(exist_ok=False)
 candidate=a.candidate or('B'+str(a.capacity));top='r_stream'if candidate.startswith('B')else'block_v1_r';src=BASE/({'A0':'attempt001/results/A0-map','A1':'attempt035/results/A1-map','A2g':'attempt036/results/A2g-map'}.get(candidate,'attempt011/results/'+candidate[1:]));receipt=json.loads((src/'receipt.json').read_text());assert receipt['passed']and 'mapped_json_sha256'in receipt;
 if candidate in ['A1','A2g']:assert receipt['complete_proof']['passed']and receipt['complete_proof']['all_state_and_all_external_outputs']
 assert hashlib.sha256((src/'mapped.json').read_bytes()).hexdigest()==receipt['mapped_json_sha256']
 original=(src/'mapped.v').read_text();normalized=re.sub(r'\bwire signed\b','wire',original);(dest/'input.v').write_text(normalized);(dest/'NETLIST_NORMALIZATION.json').write_text(json.dumps(dict(kind='remove signed metadata on mapped wires for OpenSTA parser',source_sha256=hashlib.sha256(original.encode()).hexdigest(),output_sha256=hashlib.sha256(normalized.encode()).hexdigest(),replacements=original.count('wire signed'),cells_and_pin_connections_changed=False),indent=2));shutil.copyfile(P/'physical.sdc',dest/'input.sdc');shutil.copyfile(P/'physical_pins.tcl',dest/'pins.tcl')
 (dest/'config.mk').write_text(f"""export PLATFORM = nangate45
export DESIGN_NAME = {top}
export DESIGN_NICKNAME = rarch157_{candidate}
export VERILOG_FILES = {dest}/input.v
export SYNTH_NETLIST_FILES = {dest}/input.v
export SDC_FILE = {dest}/input.sdc
export DIE_AREA = 0 0 3000 3000
export CORE_AREA = 20 20 2980 2980
export PLACE_DENSITY = 0.25
export FOOTPRINT_TCL = {dest}/pins.tcl
export KEEP_VARS = 1
export GPL_TIMING_DRIVEN = 0
export ENABLE_PLACE_REPAIR_TIMING = 1
export CAP_MARGIN = 40
export HOLD_SLACK_MARGIN = 0.020
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none
override export MIN_ROUTING_LAYER = metal1
override export MAX_ROUTING_LAYER = metal10
export VIA_IN_PIN_MIN_LAYER = metal10
export VIA_IN_PIN_MAX_LAYER = metal10
export DETAILED_ROUTE_ARGS = -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10
""")
 # ORFS source/runtime read-only; all design results/logs/reports go here.
 env=os.environ.copy();env['NUM_CORES']='16';env['OMP_NUM_THREADS']='16'
 cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dest/'config.mk'),'WORK_HOME='+str(dest/'flow'),'finish']
 with(dest/'flow.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
 (dest/'receipt.json').write_text(json.dumps(dict(candidate=candidate,capacity=a.capacity if candidate.startswith('B')else 2048,exit=r.returncode,mapped_sha256=receipt['mapped_json_sha256'],qualification_transferred=False,command=cmd),indent=2)+'\n')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
