"""Original eight scenarios, frozen controls and partial native region timing."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import argparse,json,math,os,platform,shutil,subprocess,traceback
from pathlib import Path
from profile import read_profile,require,sha
CASES=('base','s16_measured','region_q0','region_q2','region_q4')
WORK=(('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine'))
def once(s,a,b):
    require(s.count(a)==1,'model anchor '+a);return s.replace(a,b)
def generate(root,out,profile,prior):
    out.mkdir()
    for n,d in prior['generated_sha256'].items():
        require(sha(root/'frozen_model'/n)==d,'frozen source drift '+n);shutil.copyfile(root/'frozen_model'/n,out/n)
    p=out/'optimization.hpp';s=p.read_text()
    s=once(s,'bool nexp8=false;',f'''bool use_region=false;int queue_depth=0;
U region_tile_cycles={profile['tile64_cycles']},region_count=0,region_tiles=0,removed_vector=0,removed_nexp=0,removed_s_subcycles=0,native_region_cycles=0;
bool nexp8=false;''')
    s=once(s,' else return false;', ''' else if(name=="region_q0"||name=="region_q2"||name=="region_q4"){
  use_region=true;s16_mode=1;queue_depth=name=="region_q2"?2:name=="region_q4"?4:0;
 }
 else return false;''')
    anchor='<<",\\\"nexp8\\\":"<<(nexp8?"true":"false")'
    extra=r'''
    <<",\"native_region\":{\"full_model_RTL_calibrated\":false,\"actual_model_values_verified\":false"
    <<",\"enabled\":"<<(use_region?"true":"false")<<",\"queue_depth\":"<<queue_depth<<",\"queue_E_gain_credited\":0"
    <<",\"regions\":"<<region_count<<",\"tiles\":"<<region_tiles<<",\"tile64_cycles\":"<<region_tile_cycles
    <<",\"removed_vector_cycles\":"<<removed_vector<<",\"removed_nexp_cycles\":"<<removed_nexp
    <<",\"removed_s_subcycles\":"<<removed_s_subcycles<<",\"native_region_cycles\":"<<native_region_cycles
    <<",\"profile_sha256\":\"@SHA@\",\"RTL_source_commit\":\"@COMMIT@\"}"'''
    extra=extra.replace('@SHA@',profile['result_sha256']).replace('@COMMIT@',profile['source_commit'])
    p.write_text(once(s,anchor,anchor+extra))
    shutil.copyfile(Path(__file__).with_name('region.inc'),out/'region.inc')
    p=out/'model.cpp';s=p.read_text();s=once(s,' void vector_region(size_t begin,size_t end){','#include "region.inc"\n void vector_region(size_t begin,size_t end){')
    anchor='     vector_region(i,i+1);const bool nexp_qualified='
    s=once(s,anchor,'     if(optimization::use_region&&o.in.size()==1&&tensors[o.in[0]].bits==16&&tensors[o.out].bits==32){native_nexp_region(o,i);++i;family="NExp";}else{\n'+anchor)
    s=once(s,'cycles(nexp_actual);++i;family="NExp";','cycles(nexp_actual);++i;family="NExp";}');p.write_text(s)
def check(row,ref,name,workload):
    m=row['optimization_sweep'];b=m['native_region'];native=name.startswith('region_')
    require(b['enabled']==native and b['full_model_RTL_calibrated'] is False and b['actual_model_values_verified'] is False,'scope')
    require(b['queue_E_gain_credited']==0,'unqualified E graph credit')
    for f in ['read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors','M_commands','M_tiles',
              'KV_state_write_bytes','M_work_ticks','adapter_work_ticks','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded']:
        require(row[f]==ref[f],'traffic/M/cache drift '+f)
    require(row['vector_work_ticks']==ref['vector_work_ticks']-b['removed_vector_cycles']-b['removed_nexp_cycles']+b['native_region_cycles'],'work conservation')
    require(b['native_region_cycles']==b['tiles']*b['tile64_cycles'],'native charge')
    require(b['regions']==(36 if native and workload=='prefill2' else 0),'region eligibility')
    require(b['tiles']==344*b['regions'],'tile coverage')
    require(math.isclose(row['tokens']/row['seconds'],row['tokens_per_second'],rel_tol=1e-10),'token rate')
    require(abs(row['seconds']*300e6-row['ticks'])<=1.1,'clock')
    require(row['max_outstanding_beats']<=32 and row['max_descriptor_queue']<=32,'finite DDR')
    pool=row['shared_pool_study'];require(pool['capacity_bytes']==32768 and pool['peak_bytes']<=32768,'pool capacity')
    require(pool['live_epoch']==0 and pool['live_workers']==0,'pool lifetime')
    for p in pool['P']:require(p['fifo_peak']<=4 and p['active']==0 and p['read_bytes']==p['consumed_bytes'],'pool conservation')
    clean=deepcopy(row);clean['optimization_sweep'].pop('native_region')
    if not native:require(clean==ref,'frozen complete RESULT mismatch')
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
        require(sha(root/'run42-result.json')=='59e272db682fff06f01d0f3ef170b9c93da24ca9d0a2d73338a366a8d1b017ec','frozen run42 identity')
        prior=json.loads((root/'run42-result.json').read_bytes());require(prior['passed'],'prior gate')
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
            refname=name if name in ['base','s16_measured'] else 's16_measured'
            ref=next(c['result'] for c in prior['cases'] if c['case']==refname and c['workload']==w and c['profile']==p and c['dual_ports']==dual)
            row=rows[0];audit=check(row,ref,name,w);neg=[]
            for f in ['read_bus_bytes','M_commands','M_work_ticks','vector_work_ticks','tokens_per_second']:
                bad=deepcopy(row);bad[f]+=1
                try:check(bad,ref,name,w)
                except ValueError:neg.append(f)
                else:raise ValueError('tamper not rejected '+f)
            value=dict(case=name,workload=w,profile=p,dual_ports=dual,result=row,audit=audit,negative_checks=neg,
                       command=list(map(str,cmd)),log=key+'.log',log_sha256=sha(out/(key+'.log')))
            (out/(key+'.json')).write_text(json.dumps(value,indent=2)+'\n');print('MODEL_CASE '+key+' '+str(row['tokens_per_second']),flush=True);return value
        for names in [CASES[:2],CASES[2:]]:
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for value in pool.map(task,[(n,w,p,v,d) for n in names for w,p,v in WORK for d in (False,True)]):r['cases'].append(value);save()
        require(len(r['cases'])==40 and sum(c['audit']['baseline_exact'] for c in r['cases'])==16,'case controls')
        for w,p,v in WORK:
            for d in (False,True):
                candidates=[deepcopy(c['result']) for c in r['cases'] if c['case'].startswith('region_') and c['workload']==w and c['profile']==p and c['dual_ports']==d]
                for c in candidates:c['optimization_sweep'].pop('case');c['optimization_sweep']['native_region'].pop('queue_depth')
                require(candidates[0]==candidates[1]==candidates[2],'unearned queue benefit')
        r['queue_graph_equal_pairs']=16;r['passed']=True
    except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
    r['output_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json'}
    save();print(json.dumps(dict(passed=r['passed'],cases=len(r['cases']),error=r.get('error'))),flush=True);return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
