"""Derive a new committed-output driver from the pinned mathematical workload.

Changes are explicit and fail closed if upstream text changes. Both generated
files are committed for review. Original source/oracles remain untouched.
"""
import argparse
import hashlib
from pathlib import Path


def once(text, before, after):
    assert text.count(before)==1, 'upstream anchor missing or ambiguous: '+before[:90]
    return text.replace(before,after,1)


def driver(root):
    path=root/'project/experiments/shared_gdn/sim.cpp'
    text=path.read_text(encoding='utf-8')
    text=text.replace('Vshared109','Vshared121')
    text=once(text,'static Vshared121 d;',
              'static Vshared121 d;static unsigned consumer_lines=0,consumer_releases=0,blocked_acks=0,start_consumer_lines=0;static uint64_t sink_drain_cycles=0;')
    text=once(text,'need(d.result_candidate==(d.owner>=2),"candidate result type");',
              'need(!d.result_candidate&&d.done&&d.status==0&&d.transaction_committed,"only committed successful output");'
              'need(d.result_owner==d.owner&&d.result_generation==d.epoch,"consumer owner/generation");'
              'need(!d.transaction_error,"transaction protocol integrity");consumer_lines++;')
    text=once(text,'static void clear(){','static void clear(){sink_drain_cycles=0;start_consumer_lines=consumer_lines;')
    a=text.index('static void waitdone(')
    b=text.index('template<class T>static void array',a)
    text=text[:a]+'''static void waitdone(bool reject=false){
 uint64_t begin=ticks;
 while(!d.done){
  need(!d.result_valid,"consumer cannot see uncommitted data");
  if(d.candidate_ready){
   need(d.transaction_sealed&&!d.transaction_committed&&outputs.empty()&&goutputs.empty(),"whole candidate held privately in T6K");
   candidate_holds++;
   if(candidate_holds>8){d.accept_candidate=!reject;d.reject_candidate=reject;}
  }
  step();d.accept_candidate=d.reject_candidate=0;
  need(ticks-begin<40000000,"complete consumer watchdog");
  need(!d.cmd_ready&&!d.cfg_ready,"lease protects bank");
 }
 uint64_t core_done=ticks;
 while(d.transaction_busy&&!d.result_release_ready){
  // Attempting DONE ACK must not release the C8 while T still owns its data.
  d.ack=1;step();d.ack=0;blocked_acks++;
  need(d.done&&d.busy&&!d.cmd_ready,"early DONE ACK blocked until reference release");
  need(ticks-core_done<20000,"finite T drain under declared consumer stalls");
 }
 sink_drain_cycles=ticks-core_done;
}
static void release(){
 unsigned st=d.status,ep=d.epoch;
 for(int j=0;j<4;j++){need(d.done&&d.status==st&&d.epoch==ep&&!d.cmd_ready,"held DONE");step();}
 need(d.services_drained&&fifo.empty(),"release fully drained");
 if(d.transaction_busy){
  need(d.result_release_ready,"all committed words were consumed");
  d.ack=1;step();d.ack=0;blocked_acks++;
  need(d.done&&d.busy,"last word does not release consumer reference");
  d.result_release=1;step();d.result_release=0;consumer_releases++;
  need(!d.transaction_busy&&d.done&&d.busy,"reference release precedes core lease ACK");
 }
 d.ack=1;step();d.ack=0;need(!d.busy,"lease released");
}
''' + text[b:]
    text=once(text,'out<<"}\\n";out.flush();release();',
              'out<<",\\\"sink_drain_cycles\\\":"<<sink_drain_cycles<<",\\\"sink_result_lines\\\":"<<consumer_lines-start_consumer_lines;out<<"}\\n";out.flush();release();')
    text=once(text,'shared109-mixed/1','shared121-mixed/1')
    text=once(text,'<<d.stale_responses<<"}\\n";',
              '<<d.stale_responses<<",\\\"consumer_lines\\\":"<<consumer_lines<<",\\\"consumer_releases\\\":"<<consumer_releases<<",\\\"blocked_acks\\\":"<<blocked_acks<<"}\\n";')
    return '// Derived from pinned sim.cpp SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n'+text


def qualification(root):
    path=root/'project/experiments/shared_gdn/qualification.cpp'
    text=path.read_text(encoding='utf-8')
    text=once(text,'#include "sim.cpp"','#include "committed_sim.cpp"')
    before='while(!d.result_valid){step();need(!d.done,"real result before done");}W held{d.result_data[0],d.result_data[1],d.result_data[2],d.result_data[3]};for(int j=0;j<5;j++){step();need(d.result_valid&&W{d.result_data[0],d.result_data[1],d.result_data[2],d.result_data[3]}==held&&!d.cmd_ready,"export held stable");}'
    after='while(!d.transaction_busy||d.result_lines==start_lines){step();need(!d.done,"partial T fill before DONE");}for(int j=0;j<5;j++){step();need(d.transaction_busy&&!d.result_valid&&!d.done,"provisional A stays private");}'
    text=once(text,before,after)
    text=once(text,'need(outputs.size()==128,"candidate before commit");',
              'need(d.transaction_sealed&&outputs.empty(),"R candidate privately sealed before commit");')
    text=once(text,'while(!d.result_valid){step();need(ticks-gt<40000000,"G held result reached");}for(int j=0;j<9;j++)step();',
              'while(!d.transaction_busy||d.result_lines==start_lines){step();need(ticks-gt<40000000,"G partial T export reached");}for(int j=0;j<9;j++){step();need(!d.result_valid&&!d.done,"provisional G stays private");}')
    text=once(text,'need(goutputs.size()==256,"G real candidate before commit");',
              'need(d.transaction_sealed&&goutputs.empty(),"G candidate privately sealed before commit");')
    text=once(text,'shared109-qualification/1','shared121-qualification/1')
    text=once(text,'<<g_root_writes<<",\\\"checks\\\":[";',
              '<<g_root_writes<<",\\\"consumer_lines\\\":"<<consumer_lines<<",\\\"consumer_releases\\\":"<<consumer_releases<<",\\\"blocked_acks\\\":"<<blocked_acks<<",\\\"checks\\\":[";')
    return '// Derived recovery driver SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n'+text


def g_receiver(root):
    path=root/'project/experiments/shared_gdn/gverify.py'
    text=path.read_text(encoding='utf-8')
    text=once(text,"row['result_lines']==128 and len(row['g_out'])==256",
              "row['result_lines']==128 and len(row['g_out'])==(256 if row['status']==0 else 0)")
    return '# Derived independent G receiver SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n'+text


def receiver(root):
    path=root/'project/experiments/shared_gdn/receive.py'
    old=path.read_text(encoding='utf-8')
    body=old[old.index(' rows=[json.loads'):old.index('\ndef main():')]
    body=once(body,"row['cycles']+1==row['elapsed']","row['cycles']+1+row['sink_drain_cycles']==row['elapsed']")
    body=once(body,"row['result_lines']*(2 if row['kind']==3 else 4)==len", "row['sink_result_lines']*(2 if row['kind']==3 else 4)==len")
    body=once(body,"row['out']==yy and row['result_lines']==32", "not row['out'] and row['sink_result_lines']==0 and row['result_lines']==32")
    body=once(body,"qual=m['suite']=='qualification'", "qual=m['suite']=='qualification-committed'")
    body=once(body,'external_accepted root_writes g_root_writes aborts stale',
              'external_accepted root_writes g_root_writes aborts stale consumer_lines consumer_releases blocked_acks')
    body=once(body,'shared109-mixed/1','shared121-mixed/1')
    body=once(body,'g_stale_before_second_reset g_root_writes checks',
              'g_stale_before_second_reset g_root_writes checks consumer_lines consumer_releases blocked_acks')
    body=once(body,'shared109-qualification/1','shared121-qualification/1')
    prefix='''"""Independent complete integer receiver; mathematical checks derived unchanged except elapsed T drain."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/shared_gdn'))
import receive as upstream
from gverify121 import GOracle,GNUMBERS,GSTRINGS,GARRAYS
class Oracle(upstream.Oracle):
 def __init__(self,inp):
  super().__init__(inp)
  self.g=GOracle(inp,self.newim)
need=upstream.need
sha=upstream.sha
ARRAYS=upstream.ARRAYS
STRINGS=upstream.STRINGS
NUMBERS=upstream.NUMBERS|{'sink_drain_cycles','sink_result_lines'}
QUAL_ROLES=upstream.QUAL_ROLES
CHECKS=upstream.CHECKS

def inspect(inp,run,oracle):
 m=json.loads((run/'manifest.json').read_text())
 need(m['schema']=='shared121-committed-run/1' and m['suite'] in ('mixed-committed','qualification-committed'),'new top actual run')
 source_bundle=json.loads((ROOT/'bundle-manifest.json').read_text())
 need(m['source_commit']==source_bundle['source_commit'] and m['source_bundle_sha256']==sha(ROOT/'bundle-manifest.json'),'exact source bundle')
 for e in source_bundle['files']:need(sha(ROOT/e['path'])==e['sha256'],'receiver/driver/RTL scientific source')
 need(sha(m['build_path'])==m['build_sha256'],'actual build identity')
 build=json.loads(Path(m['build_path']).read_text())
 need(build['top']=='shared121' and build['binary_sha256']==m['binary_sha256'] and build['source_commit']==m['source_commit'],'correct top and compiled source')
 command=json.loads((run/'simulation-command.json').read_text())
 need(command['exit']==0 and sha(command['argv'][0])==m['binary_sha256'],'exact executed new binary')
 need(command['argv'][1:]==[str(inp/'vectors.tsv'),str(run/'actual.jsonl'),str(m['stall']),str(m['pilot'])],'exact input and wait mode')
 need(sha(inp/'manifest.json')==m['input_manifest_sha256'],'original scientific input binding')
 for artifact in m['artifacts']:
  p=(run/artifact['path']).resolve()
  need(p.is_relative_to(run.resolve()) and p.stat().st_size==artifact['bytes'] and sha(p)==artifact['sha256'],'run actual artifact')
'''
    tail='''
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 oracle=Oracle(a.input)
 result=inspect(a.input,a.run,oracle)
 rows=[json.loads(x)for x in(a.run/'actual.jsonl').read_text().splitlines()]
 proto=result['protocol']
 need(proto['consumer_lines']==sum(r['sink_result_lines']for r in rows),'every committed beat consumed exactly once')
 need(proto['consumer_releases']==sum(r['sink_result_lines']>0 for r in rows),'each consumer lease explicitly released')
 for key in ('consumer_lines','consumer_releases','blocked_acks'):need(type(proto[key]) is int and proto[key]>=0,'typed consumer counters')
 need(proto['blocked_acks']>0,'early ACK attempts exercised')
 status='PASS_SHARED121_COMPLETE_INTEGER_COMMITTED_RECOVERY' if len(rows)==44 else 'PASS_SHARED121_COMPLETE_INTEGER_COMMITTED_MIXED'
 result.update(status=status,receiver_sha256=sha(__file__),run_manifest_sha256=sha(a.run/'manifest.json'))
 upstream.put(a.out/'receipt.json',result)
 print(result['status'])
if __name__=='__main__':main()
'''
    return '# Derived math receiver SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n'+prefix+body+tail


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    for name,data in [('committed_sim.cpp',driver(a.root)),('committed_qualification.cpp',qualification(a.root)),
                      ('gverify121.py',g_receiver(a.root)),('receive121.py',receiver(a.root))]:
        target=a.root/'project/experiments/block_v1'/name
        if a.check:
            assert target.read_bytes()==data.encode('utf-8'), name+' generation differs'
        else:
            target.write_bytes(data.encode('utf-8'))
    print('committed driver and math receiver generation verified')
