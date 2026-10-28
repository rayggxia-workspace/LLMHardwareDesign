"""Read-only symbol/API evidence from the exact failed VECTOR executable."""
from pathlib import Path
import datetime,json,os,re,subprocess,sys
from run_exports import ROOT,IMAGE,BIN,sha
from run_escape_fixture import execute
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent
source=ROOT/'vector_clone_probe/r01';rp=source/'execution.json';log=source/'native.log'
j=json.loads(rp.read_text());assert j.get('completed_utc') and j['native_returncodes']['clone_heuristic_probe']==-11
assert j['all_closed_sources_unchanged'] and sha(log)==j['files'][log.name]['sha256']
out=ROOT/'vector_clone_crash'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
inputs={str(p):sha(p) for p in [rp,log]}
addresses=[]
for line in log.read_text().splitlines():
    if BIN in line:
        for a in re.findall(r'\b0x[0-9A-Fa-f]+',line):
            if a not in addresses:addresses.append(a)
assert addresses
common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
binary_sha=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
assert binary_sha=='0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53'
cmd=common+[IMAGE,'addr2line','-f','-C','-e',BIN]+addresses
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'actual_addr2line.txt').write_bytes(r.stdout)
script=out/'api.tcl';script.write_text('set f [open '+tcl(out/'repair_timing.body.tcl')+' w];puts -nonewline $f [info body repair_timing];close $f\nhelp repair_timing\n')
rc=execute(common,script,out/'native_api.log',threads=1)
rec={'scope':'READ_ONLY_EXACT_NATIVE_VECTOR_CRASH_SYMBOLIZATION_AND_API_NOT_REPAIR_OR_ROOT_CAUSE_PROOF',
  'source_SHA':inputs,'actual_executable_SHA256':binary_sha,'native_stack_addresses':addresses,
  'addr2line_returncode':r.returncode,'native_API_returncode':rc,
  'debug_symbols_and_source_may_be_unavailable':True,'active_jobs_not_attached_signalled_or_changed':True,
  'full_qualification':False,'all_closed_sources_unchanged':all(sha(Path(p))==v for p,v in inputs.items()),
  'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
  'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}}
(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
sys.exit(0 if rc==0 and rec['all_closed_sources_unchanged'] else 1)
