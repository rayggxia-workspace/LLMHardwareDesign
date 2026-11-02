"""Generate real SRAM views in a NEW folder, retaining prerequisite failures.

python3 project/experiments/s_sram/generate_bank.py --compiler /path/to/OpenRAM/sram_compiler.py --out .local/new-bank
Requires an explicitly provisioned Linux OpenRAM/KLayout/ngspice environment.
This command never installs tools, disables checks or launches server jobs.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--internal-pins',action='store_true',help='Keep native signal access points; omit optional perimeter escape routing, retaining power routing and DRC/LVS')
 p.add_argument('--delay-chain-stages',type=int,choices=(9,25,31,49),default=9)
 p.add_argument('--spice-threads',type=int,choices=(1,8),default=1)
 p.add_argument('--words-per-row',type=int,choices=(2,4),default=4)
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 config=HERE/'openram_config.py';receipt=dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),config_sha256=sha(config),qualified=False,physical_acceptance=False)
 overlay=os.environ.get('S_SRAM_GRAPH_OVERLAY_RECEIPT')
 if overlay:
  proof=Path(overlay);data=json.loads(proof.read_text());assert data['passed']
  assert data['changed_files']==['compiler/router/graph.py']
  actual=Path(data['overlay_pythonpath'])/'openram/compiler/router/graph.py'
  assert sha(actual)==data['overlay_graph_sha256']
  receipt['tool_overlay']=dict(path=str(proof),sha256=sha(proof),graph_sha256=sha(actual))
 def save(): (out/'generation.json').write_text(json.dumps(receipt,indent=2)+'\n')
 tools={name:shutil.which(name)for name in ('klayout','ngspice')}
 missing=[name for name,v in tools.items()if not v]
 if not a.compiler.is_file():missing.append('OpenRAM compiler')
 if sys.platform!='linux':missing.append('Linux execution environment')
 receipt.update(tools=tools,missing=missing)
 if missing:
  receipt['status']='prerequisites_missing';save();print(json.dumps(receipt,indent=2));return 2
 # Preserve the requested checked configuration; only the destination changes.
 local=out/'run_config.py';local.write_text(config.read_text()+f'\noutput_path = {str(out/"bank")!r}\n'+('perimeter_pins = False\n' if a.internal_pins else '')+
     f'words_per_row = {a.words_per_row}\ndelay_chain_stages = {a.delay_chain_stages}\nnum_sim_threads = {a.spice_threads}\nuse_specified_corners = [("TT",1.1,25)]\n')
 receipt['control_delay_chain_stages']=a.delay_chain_stages
 receipt['spice_threads_requested']=a.spice_threads
 receipt['words_per_row_requested']=a.words_per_row
 runtime=os.environ.get('S_SRAM_RUNTIME_OVERLAY_RECEIPT')
 if runtime:
  proof=Path(runtime);data=json.loads(proof.read_text());actual=a.compiler.resolve().parent/'compiler/characterizer/stimuli.py'
  assert data['changed']==['compiler/characterizer/stimuli.py'] and sha(actual)==data['patched_sha256']
  receipt['runtime_overlay']=dict(path=str(proof),sha256=sha(proof),stimuli_sha256=sha(actual))
 search_overlay=os.environ.get('S_SRAM_SEARCH_OVERLAY_RECEIPT')
 if search_overlay:
  proof=Path(search_overlay);data=json.loads(proof.read_text())
  actual=a.compiler.resolve().parent/'technology/freepdk45/tech/tech.py'
  assert data['changed']==['technology/freepdk45/tech/tech.py']
  assert sha(actual)==data['patched_sha256']
  receipt['search_overlay']=dict(path=str(proof),sha256=sha(proof),tech_sha256=sha(actual),
      initial_feasible_period_ns=data['initial_feasible_period_ns'],
      scope='Only the initial search period changes; native checks, binary minimum-period search, load/slew grid and simulator tolerances retained')
 grid_overlay=os.environ.get('S_SRAM_GRID_OVERLAY_RECEIPT')
 if grid_overlay:
  proof=Path(grid_overlay);data=json.loads(proof.read_text())
  actual=a.compiler.resolve().parent/'compiler/characterizer/delay.py'
  assert data['changed']==['compiler/characterizer/delay.py'] and sha(actual)==data['patched_sha256']
  workers=int(os.environ['S_SRAM_GRID_WORKERS']);assert 1<workers<int(os.environ['SLURM_CPUS_PER_TASK'])
  receipt['grid_overlay']=dict(path=str(proof),sha256=sha(proof),delay_sha256=sha(actual),workers=workers)
 receipt['signal_pin_policy']='native_internal_access' if a.internal_pins else 'default_perimeter_escape'
 command=[sys.executable,str(a.compiler.resolve()),str(local)]
 receipt.update(compiler_sha256=sha(a.compiler),run_config_sha256=sha(local),argv=command,status='running');save()
 with (out/'compiler.log').open('w')as log:
  proc=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT)
 receipt['returncode']=proc.returncode
 if proc.returncode:
  receipt['status']='compiler_failed';save();return proc.returncode
 name='s_sram_256x128_freepdk45';views={}
 for ext in ('v','lef','gds','sp','lib'):
  matches=list((out/'bank').rglob(name+('*'if ext=='lib'else '')+'.'+ext))
  if len(matches)!=1:
   receipt.update(status='incomplete_views',missing_view=ext,matching_paths=[str(v)for v in matches]);save();return 3
  f=matches[0];views[ext]=dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f))
 # Reject empty/fake geometry; require actual FEOL active/poly and M1 shapes.
 data=Path(views['gds']['path']).read_bytes();pos=0;layers=set();cells=set()
 while pos<len(data):
  if pos+4>len(data):raise ValueError('truncated GDS header')
  size,kind,_=struct.unpack('>HBB',data[pos:pos+4])
  if size<4 or pos+size>len(data):raise ValueError('invalid GDS record')
  payload=data[pos+4:pos+size]
  if kind==6:cells.add(payload.rstrip(b'\0').decode('ascii'))
  if kind==13:layers.add(struct.unpack('>H',payload)[0])
  pos+=size
 if name not in cells or not {1,9,11}<=layers:
  receipt.update(status='rejected_empty_or_wrong_technology_gds',views=views,layers=sorted(layers));save();return 4
 receipt.update(status='views_generated_not_qualified',views=views,gds_layers=sorted(layers),gds_cells=len(cells),scope='Actual generated views and nonempty FreePDK45 FEOL checked. Macro DRC/LVS reports, characterized timing, wrapper physical implementation and qualification require separate audit.')
 save();print(json.dumps(receipt,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
