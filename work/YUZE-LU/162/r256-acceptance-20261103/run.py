"""Issue162 side acceptance audit: frozen source inputs, never qualify absent system."""
from pathlib import Path
import concurrent.futures as cf
import subprocess,json,hashlib,os,itertools,time,re
R=Path.cwd();P=R/'work/YUZE-LU/162/r256-acceptance-20261103'
O=R/'results';O.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((R/'INPUTS.json').read_text())
for n,h in manifest.items():assert sha(R/n)==h,n
cores=sorted(os.sched_getaffinity(0));assert len(cores)>=24
V=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
def call(args,log):
 with log.open('w') as f:return subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT).returncode
start=time.time()
# These are actual module instances in the existing top, not documentation IDs.
system=(R/'project/rtl/control_v1/control_system.sv').read_text()
clean=re.sub(r'//[^\n]*|/\*.*?\*/','',system,flags=re.S)
instances=re.findall(r'\b(block_v2_[mneg]|block_feed_s_macro|transaction6k|r_stream_local|block_v1_r)\s+(\w+)\s*\(',clean)
r_present=any(a in ('r_stream_local','block_v1_r') for a,b in instances)
adapter_present=(R/'project/rtl/control_v1/control_adapter_r.sv').exists()
qual=json.loads((P/'R256_QUALIFICATION.json').read_text())
assert qual['passed'] and qual['capacity']==256
contracts={
 'M':{'relation':'projection->format/scale conversion->R load','direct_connection_qualified':False},
 'N':{'relation':'R S32->E narrow->S16 N; scale chosen per task','direct_connection_qualified':False},
 'E':{'relation':'R read128 ready/valid -> E op13 S32-to-S16; real pair tested below','direct_connection_qualified':False},
 'G':{'relation':'R->E->two-lane activation; serializer and fixed-point contract required','direct_connection_qualified':False},
 'S':{'relation':'128-bit packet width matches; shared port arbitration and acknowledgments required','direct_connection_qualified':False},
 'T':{'relation':'128-bit packet width matches; begin/fill/commit/drain/release controller required','direct_connection_qualified':False}}
audit={'input_sha256':manifest,'actual_existing_top_instances':instances,'r256_single_macro_qualification':qual['passed'],
 'r_instance_in_existing_top':r_present,'r_adapter_in_existing_source':adapter_present,'contracts':contracts,
 'system_acceptance_passed':False,'reasons':[]}
if not r_present:audit['reasons'].append('Frozen control_system has only M/N/E/G/S/T; R is not instantiated.')
if not adapter_present:audit['reasons'].append('No actual control_adapter_r in frozen control source.')
audit['reasons'].append('No seven-macro physical top, routed M11/M12, full cross-macro extracted STA or source-bound seven-macro delivery was supplied; cannot qualify system.')
(O/'STRUCTURAL_ACCEPTANCE.json').write_text(json.dumps(audit,indent=2)+'\n')
build=[V,'--cc','--exe','--build','-j','12','--threads','1','--x-initial','unique','--x-assign','unique','-Wno-fatal',
 '--top-module','pair_re','--Mdir',O/'obj','-CFLAGS','-std=c++17 -O1',P/'pair_re.sv',P/'r_stream_local.sv',P/'r_state_store.sv',R/'project/rtl/block_v2/block_v2_e.sv',P/'test_pair.cpp']
assert call(build,O/'build.log')==0,'pair compile failed; see build.log'
binary=O/'obj/Vpair_re';bhash=sha(binary)
def run_case(t):
 shift,bank,stall,init=t;name=f's{shift}-b{bank}-p{stall}-i{init}';log=O/(name+'.log')
 rc=call([binary,shift,bank,stall,'+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(162+init)],log)
 rec={'case':t,'exit_code':rc,'log_sha256':sha(log),'passed':False}
 if rc==0:
  rec['result']=json.loads(log.read_text());rec['passed']=rec['result']['passed']
 return rec
with cf.ThreadPoolExecutor(max_workers=24) as pool:rows=list(pool.map(run_case,itertools.product(range(32),range(2),range(2),range(3))))
# Independent wrong-scale negative control must be detected by numeric oracle.
neg=call([binary,6,0,1,7,'+verilator+rand+reset+2'],O/'wrong-scale-negative.log')
for n,h in manifest.items():assert sha(R/n)==h,n
ok=all(x['passed'] for x in rows)
result={'execution_completed':True,'pair_re_rtl_passed':ok,'case_count':len(rows),'passed_cases':sum(x['passed']for x in rows),
 'packets_checked':sum(x.get('result',{}).get('packets',0)for x in rows),'checks':sum(x.get('result',{}).get('checks',0)for x in rows),
 'wrong_scale_negative_rejected':neg!=0,'binary_sha256':bhash,'verilator_version':subprocess.check_output([V,'--version'],text=True).strip(),
 'allocated_cpu_affinity':cores,'independent_workers':24,'elapsed_seconds':time.time()-start,
 'physical_qualified':False,'seven_macro_system_accepted':False,'rejection_reasons':audit['reasons'],
 'scope':'Actual frozen qualified R256 behavioral RTL directly wired to actual E RTL. State readback path only; no R arithmetic command, other five-macro integration, C/D dispatch or physical interconnect test.',
 'cases':rows,'inputs_after_equal':True}
(O/'RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
assert ok and neg!=0,'Pair regression failure; system remains unqualified in either case.'
print(json.dumps({k:v for k,v in result.items()if k!='cases'}))
