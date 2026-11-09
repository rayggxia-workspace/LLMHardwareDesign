"""Slurm-only real four-bank finite-M RTL and finite-control calibration."""
import argparse,hashlib,json,os,platform,re,shutil,subprocess,traceback
from pathlib import Path
from generate import generate
from vectors import generate as vectors_generate
from replay import sha,split_control,compare,service_events

HERE=Path(__file__).resolve().parent
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
STORE='project/rtl/s_sram/block_feed_s16k_sram.sv'
STORE_SHA='a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef'
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
RUN19_SHA='b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098'
GATES=('numeric','lifecycle','finite_resources','source_identity','real_S','control_replay','single_double_fairness')

def rows(text,prefix):
 return [{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)} for line in text.splitlines() if line.startswith(prefix+' ')]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
 root=args.root.resolve();repo=root/'source';out=root/'results';cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
 if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('actual Slurm1..4cores allocation required')
 manifest=json.loads((root/'inputs.json').read_bytes())
 if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('source commit missing')
 for key,base in (('code_sha256',repo),('input_sha256',root)):
  if not manifest.get(key):raise ValueError('empty manifest '+key)
  for name,digest in manifest[key].items():
   if sha(base/name)!=digest:raise ValueError('deployment drift '+name)
 if sha(root/'run19-result.json')!=RUN19_SHA or json.loads((root/'run19-result.json').read_bytes()).get('passed') is not True:raise ValueError('prior result identity')
 if sha(BANK)!=BANK_SHA or sha(repo/STORE)!=STORE_SHA:raise ValueError('real SRAM model drift')
 control_identity=re.search(r'rtl_sha256="([0-9a-f]{64})"',(HERE/'control/finite_control.hpp').read_text(encoding='utf8'))
 if not control_identity or control_identity[1]!=sha(HERE/'r3_m_finite.sv'):raise ValueError('control model targets a different RTL source')
 for p in (HERE/'r3_m_finite.sv',HERE/'m_s32_stream_candidate.sv',HERE/'tb_r3_m_finite.sv',HERE/'control/finite_control.hpp',HERE/'control/control_probe.cpp',repo/STORE):
  if p.relative_to(repo).as_posix() not in manifest['code_sha256']:raise ValueError('source omitted '+str(p))
 out.mkdir(exist_ok=False)
 report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
  prior_run19_sha256=RUN19_SHA,scope='R3 actual finite S32/W8/S96 K16 local service; no full P/DMA or physical qualification',
  rtl_source_sha256={p.relative_to(repo).as_posix():sha(p) for p in (HERE/'r3_m_finite.sv',HERE/'m_s32_stream_candidate.sv',repo/STORE)},
  control_source_sha256={p.name:sha(p) for p in (HERE/'control/finite_control.hpp',HERE/'control/control_probe.cpp')},
  bank_sha256=BANK_SHA,commands=[],runs=[],gates={name:False for name in GATES},physical_qualified=False,
  full_P_DMA_integration=False,resource_ledger=json.loads((HERE/'resource-ledger.json').read_bytes()),
  versions=dict(python=platform.python_version(),verilator=subprocess.check_output([VERILATOR,'--version'],text=True).strip(),gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]))
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 def call(command,log,cwd=None,stdin=None):
  command=list(map(str,command));path=out/log;path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('w',encoding='utf8') as dest:
   if stdin:
    with Path(stdin).open() as source:r=subprocess.run(command,cwd=cwd or repo,stdin=source,stdout=dest,stderr=subprocess.STDOUT)
   else:r=subprocess.run(command,cwd=cwd or repo,stdout=dest,stderr=subprocess.STDOUT)
  rec=dict(command=command,cwd=str(cwd or repo),log=log,exit_code=r.returncode,log_sha256=sha(path))
  if stdin:rec.update(stdin=str(stdin),stdin_sha256=sha(stdin))
  report['commands'].append(rec);save()
  if r.returncode:raise RuntimeError('command failed '+log)
  return path.read_text(encoding='utf8'),rec
 try:
  report['generation']=generate(repo,out/'generated')
  vectors=vectors_generate(out/'vectors');report['vectors']={k:v for k,v in vectors.items() if k!='cases'}
  report['vectors']['case_count']=len(vectors['cases']);report['vectors']['metadata_sha256']=sha(out/'vectors/vectors.json')
  if not vectors['oracle']['passed']:raise ValueError('independent numeric oracle failed')
  probe=out/'control_probe'
  call(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',HERE/'control/control_probe.cpp','-o',probe],'control-build.log')
  profile_rows=[];nominal_read=set();nominal_write=set();timings={};fair={}
  for buffers in (1,2):
   obj=out/('obj-buf'+str(buffers));top='tb_r3_m_finite'
   call([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wall','-Wno-fatal',
     '--x-initial','unique','--x-assign','unique','-j',cpus,'--top-module',top,'-GBUFFERS='+str(buffers),'--Mdir',obj,
     HERE/'tb_r3_m_finite.sv',HERE/'r3_m_finite.sv',HERE/'m_s32_stream_candidate.sv',repo/STORE,BANK],f'buf{buffers}-build.log')
   for mode,seed in ((1,143),(2,143),(2,144)):
    label=f'buf{buffers}-{mode}-{seed}';folder=out/label;folder.mkdir()
    shutil.copyfile(out/'vectors/vectors.txt',folder/'vectors.txt')
    if sha(folder/'vectors.txt')!=vectors['vectors_sha256']:raise ValueError('stimulus differs')
    text,cmd=call([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],label+'/rtl.log',folder)
    if '%Error' in text or 'FAIL' in text:raise ValueError('RTL failure marker')
    proof=rows(text,'R3_PASS');measured=rows(text,'R3_CASE')
    if len(proof)!=1 or proof[0].get('cases')!=len(vectors['cases']) or proof[0].get('checks',0)<=0 or proof[0].get('reset_cases')!=20:raise ValueError('R3 functional/lifecycle gate missing')
    if len(measured)!=len(vectors['cases']) or sorted(q.get('case') for q in measured)!=list(range(len(vectors['cases']))):raise ValueError('case coverage missing')
    count=split_control(folder/'control.txt',folder/'inputs.txt',folder/'actual.txt')
    _,probe_cmd=call([probe,str(buffers)],label+'/probe.log',folder,folder/'inputs.txt')
    # The probe writes one status line on stderr after the CONTROL rows. Retain
    # its exact raw output and compare only explicitly recognized CONTROL rows.
    raw=(folder/'probe.log').read_text(encoding='utf8').splitlines()
    markers=[s for s in raw if s.startswith('FINITE_CONTROL_REPLAY_PASS ')]
    if len(markers)!=1 or rows('\n'.join(markers),'FINITE_CONTROL_REPLAY_PASS')!=[{'cycles':count}]:raise ValueError('control probe completion absent')
    if any(not s.startswith(('CONTROL ','FINITE_CONTROL_REPLAY_PASS ')) for s in raw):raise ValueError('unexpected control probe output')
    (folder/'probe-control.txt').write_text('\n'.join(s for s in raw if s.startswith('CONTROL '))+'\n',encoding='utf8')
    replay=compare(folder/'inputs.txt',folder/'actual.txt',folder/'probe-control.txt');replay.update(matched=True,probe_command=probe_cmd,raw_control_sha256=sha(folder/'control.txt'))
    try:compare(folder/'inputs.txt',folder/'actual.txt',folder/'probe-control.txt',mutation='read_address')
    except ValueError as err:
     if not str(err).startswith('control mismatch'):raise
     replay['tampered_address_rejected']=True
    else:raise ValueError('control replay accepted corrupted valid address')
    case_reports=[]
    for measured_row in measured:
     fixture=vectors['cases'][measured_row['case']];q=dict(measured_row)
     for key in ('commands','valid','invalid','read_lines','write_words'):
      if q.get(key)!=fixture[key]:raise ValueError('fixture work differs '+key+' '+str(q['case']))
     expected={'leaf_accepts':fixture['valid'],'commits':fixture['valid'],'completions':fixture['commands'],'read_acks':fixture['read_lines'],'write_acks':fixture['write_words']}
     for key,value in expected.items():
      if q.get(key)!=value:raise ValueError('finite work not conserved '+key)
     if not 0<q['peak_buffers']<=buffers or not 0<q['peak_reads']<=2 or not 0<q['peak_reservations']<=8:raise ValueError('finite bound exceeded')
     if q['accepted_to_done_cycles']!=q['last_done']-q['first_accept']:raise ValueError('latency arithmetic mismatch')
     if q.get('accepted_to_next_ready_cycles',-1)<q['accepted_to_done_cycles']:raise ValueError('next legal ready not measured')
     derived=service_events(folder/'inputs.txt',folder/'actual.txt',q['first_accept'],q['last_done'])
     for key in ('commands','read_lines','write_words','read_acks','write_acks','leaf_accepts','commits','completions','peak_buffers','peak_reads','peak_reservations','accepted_to_done_cycles'):
      if derived[key]!=q[key]:raise ValueError('independent control-derived mismatch '+key+' case'+str(q['case']))
     events=derived.pop('events');event_path=folder/('case-%03d-events.json'%q['case']);event_path.write_text(json.dumps(events,separators=(',',':'))+'\n',encoding='utf8')
     q.update(label=fixture['label'],qualified=fixture['qualified'],read_delay=fixture['read_delay'],ack_delay=fixture['ack_delay'],done_hold=fixture['done_hold'],derived=derived,events_file=event_path.relative_to(out).as_posix(),events_sha256=sha(event_path))
     case_reports.append(q)
     work=tuple(q[k] for k in ('commands','valid','invalid','read_lines','write_words','leaf_accepts','commits','completions'))
     if q['case'] in fair and fair[q['case']]!=work:raise ValueError('single/double work unfair')
     fair[q['case']]=work
     if q['qualified']:
      key=(buffers,q['case']);timing=(q['accepted_to_done_cycles'],q['accepted_to_next_ready_cycles'])
      if key in timings and timings[key]!=timing:raise ValueError('qualified timing depends on initialization')
      timings[key]=timing
      if any((q['read_delay'],q['ack_delay'],q['done_hold'])):raise ValueError('headline uses artificial hold')
      nominal_read.update(derived['read_ack_cycle_deltas']);nominal_write.update(derived['write_ack_cycle_deltas'])
      profile_rows.append(dict(BUFFERS=buffers,mode=mode,seed=seed,measurement=q,log=cmd['log'],log_sha256=cmd['log_sha256'],control_sha256=replay['raw_control_sha256'],events_sha256=q['events_sha256']))
    entry=dict(BUFFERS=buffers,mode=mode,seed=seed,passed=True,command=cmd['command'],log=cmd['log'],log_sha256=cmd['log_sha256'],control=replay,case_measurements=case_reports,checks=proof[0])
    report['runs'].append(entry);save();print('R3_RTL_RUN_PASS '+label,flush=True)
  if len(nominal_read)!=1 or len(nominal_write)!=1:raise ValueError('nominal actual S latency is not a singleton; requires backend FSM, not minimum')
  qualified_cases=[x for x in vectors['cases'] if x['qualified']]
  if {x['label'] for x in qualified_cases}!={'qualified_ctx1_K2048','qualified_ctx1_K11008','qualified_ctx8_K2048','qualified_ctx8_K11008'}:raise ValueError('required same-context/multi-context full-K qualification missing')
  if len(profile_rows)!=len(qualified_cases)*6:raise ValueError('qualified profile misses buffer/seed coverage')
  report['profile']=dict(schema_version=1,passed=True,scope='actual finite M controller plus real four-bank S; replace whole qualified local service, not leaf-only II',
   shape_contract=dict(A_bits=32,W_bits=8,logical_rows=1,N=8,K_packet=16,shift=16,old_tile_packets=16,old_tile_K=256,full_K=[2048,11008]),
   buffer_choices=[1,2],source_packet_bytes=256,S_bytes=16384,S_bank_count=4,S_bank_mode='1RW',read_metadata=2,completion_reservations=8,
   nominal_read_bytes_per_packet=192,final_write_words=2,final_write_word_bytes=16,
   ack_delays=dict(nominal_read_accept_to_consumed_ack_cycles=sorted(nominal_read),nominal_write_accept_to_consumed_ack_cycles=sorted(nominal_write),
    derivation='FIFO pairing of actual accepted requests and consumed responses inside qualified no-artificial-hold cases; all source rows bound below'),
   control_source_sha256=report['control_source_sha256'],rows=profile_rows)
  report['gates']={name:True for name in GATES};report['passed']=True
 except Exception as err:report['error']=repr(err);report['traceback']=traceback.format_exc();raise
 finally:save()
 print('ROUND3_FINITE_M_RTL_PASS',flush=True)

if __name__=='__main__':main()
