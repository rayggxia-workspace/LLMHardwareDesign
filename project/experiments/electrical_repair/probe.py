"""Probe exact installed OpenROAD commands and freeze research inputs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EDA=Path('/public/home/yuzelu/opt/eda');DOCKER=EDA/'cache/bazel-repacked/0472cb7817e9c4d6e974e10cde266a63/external/bazel-orfs++orfs_repositories+docker_orfs';ORFS=DOCKER/'OpenROAD-flow-scripts'
OR=ORFS/'tools/install/OpenROAD/bin/openroad';STA=ORFS/'tools/install/OpenROAD/bin/sta';LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib');TECH=ORFS/'flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef';LEF=ORFS/'flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source SHA')
 script=a.out/'commands.tcl';script.write_text('\n'.join('help '+n for n in('initialize_floorplan','repair_design','repair_tie_fanout','repair_timing','buffer_ports','set_wire_rc','estimate_parasitics','global_placement','detailed_placement','write_verilog','report_design_area','check_setup','report_checks','report_check_types'))+'\nexit\n')
 cmd=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind',str(EDA)+':/eda:ro','--pwd',str(a.out),str(EDA/'containers/orfs-26Q1-repacked.sif'),str(DOCKER/'lib64/ld-linux-x86-64.so.2'),'--library-path',str(DOCKER/'usr/lib/x86_64-linux-gnu'),str(OR),'-exit',str(script)]
 with (a.out/'commands.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=120,stdin=subprocess.DEVNULL)
 evidence={'source':binding,'command':cmd,'exit':r.returncode,'inputs':[{'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q)}for q in(LIB,TECH,LEF,OR,STA,DOCKER/'lib64/ld-linux-x86-64.so.2')],'constraint':'Existing read-only research tool/library probe, no repair applied.'};(a.out/'manifest.json').write_text(json.dumps(evidence,indent=2)+'\n')
 if r.returncode:raise ValueError('tool probe failed')
 print('TOOL_PROBE_EXECUTED')
if __name__=='__main__':main()