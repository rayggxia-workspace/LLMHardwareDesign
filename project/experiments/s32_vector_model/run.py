"""Original eight scenarios, frozen controls and partial native region timing."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import argparse,json,math,os,platform,shutil,subprocess,traceback
from pathlib import Path
from profile import read_profile,require,sha
CASES=('region_q2','s32q0','s32q2','s32q4')
WORK=(('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine'))
def once(s,a,b):
    require(s.count(a)==1,'model anchor '+a);return s.replace(a,b)
def generate(root,out,profile,prior):
    out.mkdir()
    for n,d in prior['generated_sha256'].items():
        require(sha(root/'frozen_model'/n)==d,'frozen source drift '+n);shutil.copyfile(root/'frozen_model'/n,out/n)
    header=r'''#pragma once
namespace e32 {
bool enabled=false;int depth=0;U ops=0,tiles=0,values=0,partial_tiles=0,removed_vector=0,removed_s_subcycles=0,native_cycles=0;
const U table[3][2]={@TABLE@};
void emit(std::ostream& o){o<<",\"native_E32\":{\"enabled\":"<<(enabled?"true":"false")<<",\"depth\":"<<depth
 <<",\"full_model_RTL_calibrated\":false,\"actual_model_values_verified\":false"
 <<",\"ops\":"<<ops<<",\"tiles\":"<<tiles<<",\"values\":"<<values<<",\"partial_tiles\":"<<partial_tiles
 <<",\"removed_vector_cycles\":"<<removed_vector<<",\"removed_s_subcycles\":"<<removed_s_subcycles<<",\"native_cycles\":"<<native_cycles
 <<",\"profile_sha256\":\"@SHA@\",\"RTL_source_commit\":\"@COMMIT@\"}";}
}
'''
    header=header.replace('@TABLE@',','.join('{'+','.join(map(str,row))+'}' for row in profile['table'])).replace('@SHA@',profile['result_sha256']).replace('@COMMIT@',profile['source_commit'])
    (out/'e32.hpp').write_text(header)
    shutil.copyfile(Path(__file__).with_name('e32.inc'),out/'e32.inc')
    p=out/'optimization.hpp';s=p.read_text();s=once(s,'namespace optimization {','#include "e32.hpp"\nnamespace optimization {')
    s=once(s,' else return false;',''' else if(name=="s32q0"||name=="s32q2"||name=="s32q4"){
  use_region=true;s16_mode=1;queue_depth=2;e32::enabled=true;e32::depth=name=="s32q0"?0:name=="s32q2"?2:4;
 }
 else return false;''');p.write_text(s)
    p=out/'model.cpp';s=p.read_text();s=once(s,' void vector_region(size_t begin,size_t end){','#include "e32.inc"\n void vector_region(size_t begin,size_t end){')
    s=once(s,'const auto& o=ops[i];if(o.kind=="Constant")continue;','const auto& o=ops[i];if(o.kind=="Constant")continue;\n    if(native_e32_eligible(o)){native_e32_tile(o,i,offset,n);continue;}')
    s=once(s,'optimization::emit(std::cout);','optimization::emit(std::cout);e32::emit(std::cout);');p.write_text(s)
def check(row,ref,name,workload,profile):
    b=row['native_E32'];native=name.startswith('s32q')
    require(b['enabled']==native and b['full_model_RTL_calibrated'] is False,'scope')
    for f in ['read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors','M_commands','M_tiles',
              'KV_state_write_bytes','M_work_ticks','adapter_work_ticks','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded']:
        require(row[f]==ref[f],'traffic/M/cache drift '+f)
    require(row['vector_work_ticks']==ref['vector_work_ticks']-b['removed_vector_cycles']+b['native_cycles'],'work conservation')
    eligibility=profile['trace_audit'][workload]
    require(b['ops']==(len(eligibility['matched']) if native else 0) and b['values']==(eligibility['values'] if native else 0),'strict trace coverage')
    require(math.isclose(row['tokens']/row['seconds'],row['tokens_per_second'],rel_tol=1e-10),'token rate')
    require(abs(row['seconds']*300e6-row['ticks'])<=1.1,'clock')
    require(row['max_outstanding_beats']<=32 and row['max_descriptor_queue']<=32,'finite DDR')
    pool=row['shared_pool_study'];require(pool['capacity_bytes']==32768 and pool['peak_bytes']<=32768 and pool['live_epoch']==0 and pool['live_workers']==0,'pool')
    for p in pool['P']:require(p['fifo_peak']<=4 and p['active']==0 and p['read_bytes']==p['consumed_bytes'],'pool conservation')
    clean=deepcopy(row);clean.pop('native_E32')
    if not native:require(clean==ref,'historical complete RESULT mismatch')
    return dict(conservation=True,finite_resources=True,baseline_exact=clean==ref)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);root=p.parse_args().root.resolve()
    out=root/'results';out.mkdir(exist_ok=False);cpus=int(os.environ.get('SLURM_CPUS_PER_TASK',0))
    require(os.environ.get('SLURM_JOB_ID') and 1<=cpus<=4,'Slurm required')
    manifest=json.loads((root/'inputs.json').read_bytes())
    for key,base in [('code_sha256',root/'source'),('input_sha256',root)]:
        for n,d in manifest[key].items():require(sha(base/n)==d,'locked file changed '+n)
    r=dict(passed=False,source_commit=manifest['source_commit'],job=os.environ['SLURM_JOB_ID'],node=platform.node(),cases=[],profile=read_profile(root))
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(cmd,log,env=None):
        cmd=list(map(str,cmd));q=subprocess.run(cmd,cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/log).write_bytes(q.stdout);s=q.stdout.decode(errors='replace');require(q.returncode==0,log+' '+s[-2500:]);return s
    try:
        require(sha(root/'run46-result.json')=='4be10c512c8d28e7e41eaaedab4a4f6803adbc4450458f0ec59f33c49b20c1cc','frozen run46 identity')
        prior=json.loads((root/'run46-result.json').read_bytes());require(prior['passed'],'prior gate')
        generated=out/'generated';generate(root,generated,r['profile'],prior)
        r['generated_sha256']={p.name:sha(p) for p in generated.iterdir()};save()
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        r['tools']=dict(gcc=execute(['g++','--version'],'gcc.log').splitlines()[0],SystemC_library_sha256=sha(prefix/'lib/libsystemc.so'))
        cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',generated/'model.cpp','-I'+str(generated),'-I'+str(prefix/'include'),
             '-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model']
        execute(cmd,'build.log');r['compile_command']=list(map(str,cmd));r['binary_sha256']=sha(out/'model')
        shutil.copyfile(root/'inputs/m-profile.log',out/'m-profile.log')
        def task(item):
            name,w,p,v,dual=item;key=f'{name}-{w}-{p}-'+('idealdual' if dual else 'shared')
            cmd=[out/'model',root/'inputs'/(w+'.trace'),p,v,8,1,1,16,int(dual),4,0,1,1,1,32,4,2,1]
            env=dict(os.environ,OPTIMIZATION_CASE=name);env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
            text=execute(cmd,key+'.log',env);rows=[json.loads(l[7:]) for l in text.splitlines() if l.startswith('RESULT ')]
            require(len(rows)==1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text,'SystemC output')
            refname='region_q2'
            ref=next(c['result'] for c in prior['cases'] if c['case']==refname and c['workload']==w and c['profile']==p and c['dual_ports']==dual)
            row=rows[0];audit=check(row,ref,name,w,r['profile']);neg=[]
            for f in ['read_bus_bytes','M_commands','M_work_ticks','vector_work_ticks','tokens_per_second']:
                bad=deepcopy(row);bad[f]+=1
                try:check(bad,ref,name,w,r['profile'])
                except ValueError:neg.append(f)
                else:raise ValueError('tamper not rejected '+f)
            value=dict(case=name,workload=w,profile=p,dual_ports=dual,result=row,audit=audit,negative_checks=neg,
                       command=list(map(str,cmd)),log=key+'.log',log_sha256=sha(out/(key+'.log')))
            (out/(key+'.json')).write_text(json.dumps(value,indent=2)+'\n');print('MODEL_CASE '+key+' '+str(row['tokens_per_second']),flush=True);return value
        for names in [CASES[:1],CASES[1:]]:
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for value in pool.map(task,[(n,w,p,v,d) for n in names for w,p,v in WORK for d in (False,True)]):r['cases'].append(value);save()
        require(len(r['cases'])==32 and sum(c['audit']['baseline_exact'] for c in r['cases'])==8,'case controls')
        r['passed']=True
    except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
    r['output_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json'}
    save();print(json.dumps(dict(passed=r['passed'],cases=len(r['cases']),error=r.get('error'))),flush=True);return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
