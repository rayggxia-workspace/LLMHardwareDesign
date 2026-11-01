"""Read-only tool inventory, executed inside an allocated container job."""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

def capture(argv):
 try:
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=30)
  return dict(argv=argv,returncode=p.returncode,output=p.stdout[-3500:])
 except Exception as e:return dict(argv=argv,error=repr(e))

names=('python3','pip3','klayout','ngspice','magic','netgen','calibre','openroad','yosys','verilator','make','gcc','git')
result=dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),job_id=os.environ.get('SLURM_JOB_ID'),affinity=sorted(os.sched_getaffinity(0)),tools={n:shutil.which(n)for n in names},python_packages={n:bool(importlib.util.find_spec(n))for n in ('openram','numpy','scipy','sklearn','coverage')},memory=Path('/proc/meminfo').read_text().splitlines()[:4],scope='tool inventory only; no SRAM or S qualification')
result['versions']=[capture(argv)for argv in [['python3','--version'],['klayout','-v'],['ngspice','--version'],['openroad','-version'],['yosys','-V'],['verilator','--version']]]
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
result['platform_ram_files']={kind:[str(p)for p in (platform/kind).glob('*ram*')][:80]for kind in ('gds','lef','lib')}
Path('probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
