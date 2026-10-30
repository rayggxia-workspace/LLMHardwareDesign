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
elf_evidence={}
if sys.argv[1]=='r02':
    outputs={}
    for name,args in [('header',['-W','-h']),('segments',['-W','-l'])]:
        result=subprocess.run(common+[IMAGE,'readelf']+args+[BIN],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/('actual_ELF_'+name+'.txt')).write_bytes(result.stdout);outputs[name]=result.stdout.decode(errors='replace')
        elf_evidence[name+'_returncode']=result.returncode
    loads=[int(line.split()[2],16) for line in outputs['segments'].splitlines() if line.strip().startswith('LOAD ')]
    entry=re.search(r'Entry point address:\s*(0x[\da-fA-F]+)',outputs['header'])
    if loads and entry:
        base=min(loads);entry=int(entry[1],16);shifted=[hex(int(a,16)+base) for a in addresses]
        result=subprocess.run(common+[IMAGE,'addr2line','-f','-C','-e',BIN]+shifted,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/'actual_addr2line_plus_min_LOAD_VA.txt').write_bytes(result.stdout)
        lines=result.stdout.decode(errors='replace').splitlines()
        elf_evidence.update({'minimum_LOAD_VA':hex(base),'ELF_entry_VA':hex(entry),
          'candidate_stack_offsets_plus_LOAD_VA':shifted,'shifted_addr2line_returncode':result.returncode,
          'shifted_last_frame_minus_ELF_entry_bytes':int(shifted[-1],16)-entry,
          'candidate_shifted_last_frame_symbol':lines[-2] if len(lines)>1 else None,
          'interpretation':'Raw and module-base-shifted candidates retained. Entrypoint/_start agreement supports an address-representation inference only; not an automatic software root-cause proof.'})
script=out/'api.tcl';script.write_text('set f [open '+tcl(out/'repair_timing.body.tcl')+' w];puts -nonewline $f [info body repair_timing];close $f\nhelp repair_timing\n')
rc=execute(common,script,out/'native_api.log',threads=1)
rec={'scope':'READ_ONLY_EXACT_NATIVE_VECTOR_CRASH_SYMBOLIZATION_AND_API_NOT_REPAIR_OR_ROOT_CAUSE_PROOF',
  'source_SHA':inputs,'actual_executable_SHA256':binary_sha,'native_stack_addresses':addresses,
  'addr2line_returncode':r.returncode,'native_API_returncode':rc,
  'ELF_address_interpretation_diagnosis':elf_evidence,
  'debug_symbols_and_source_may_be_unavailable':True,'active_jobs_not_attached_signalled_or_changed':True,
  'full_qualification':False,'all_closed_sources_unchanged':all(sha(Path(p))==v for p,v in inputs.items()),
  'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
  'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}}
(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
sys.exit(0 if rc==0 and rec['all_closed_sources_unchanged'] else 1)
