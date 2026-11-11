"""Old evaluation with actual S16 frame fees and explicit unclosed U target."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import argparse,json,math,os,platform,re,shutil,subprocess,traceback
from pathlib import Path
from profile import read_profile,require,sha

CASES=('base','s16_measured','s16_full_u_bound','s16_vector8_target')
WORK=(('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine'))
def once(s,a,b):
    require(s.count(a)==1,'model anchor '+a)
    return s.replace(a,b)
def check(row,ref,name):
    m=row['optimization_sweep'];b=m['native_S16']
    require(b['scope']=='local_frame_only' and b['full_model_RTL_calibrated'] is False,'qualification scope')
    for f in ['read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors',
        'M_commands','M_tiles','KV_state_write_bytes','M_work_ticks','adapter_work_ticks','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded']:
        require(row[f]==ref[f],'traffic/M drift '+f)
    require(row['vector_work_ticks']==ref['vector_work_ticks']-m['vector_old']+m['vector_new']-m['nexp_old']+m['nexp_new'],'work conservation')
    require(math.isclose(row['tokens']/row['seconds'],row['tokens_per_second'],rel_tol=1e-10),'token rate')
    require(abs(row['seconds']*300e6-row['ticks'])<=1.1,'clock')
    require(row['max_outstanding_beats']<=32 and row['max_descriptor_queue']<=32,'finite DDR')
    pool=row['shared_pool_study'];require(pool['capacity_bytes']==32768 and pool['peak_bytes']<=32768,'pool capacity')
    require(pool['live_epoch']==0 and pool['live_workers']==0,'pool lifetime')
    for p in pool['P']:require(p['fifo_peak']<=4 and p['active']==0 and p['read_bytes']==p['consumed_bytes'],'pool conservation')
    clean=deepcopy(row);clean['optimization_sweep'].pop('native_S16')
    if name=='base':require(clean==ref,'historical complete RESULT mismatch')
    return dict(conservation=True,finite_resources=True,baseline_exact=clean==ref)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);root=p.parse_args().root.resolve()
    out=root/'results';out.mkdir(exist_ok=False)
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK',0));require(os.environ.get('SLURM_JOB_ID') and 1<=cpus<=4,'Slurm required')
    manifest=json.loads((root/'inputs.json').read_bytes())
    for key,base in [('code_sha256',root/'source'),('input_sha256',root)]:
        for n,d in manifest[key].items():require(sha(base/n)==d,'locked input/source changed '+n)
    r=dict(passed=False,source_commit=manifest['source_commit'],job=os.environ['SLURM_JOB_ID'],node=platform.node(),
        commands=[],cases=[],profile=read_profile(root),scope='old conditional model with measured local S16 fees; no native full graph proof')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(command,log,env=None,expected=0):
        command=list(map(str,command));proc=subprocess.run(command,cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/log).write_bytes(proc.stdout);text=proc.stdout.decode(errors='replace')
        require(proc.returncode==expected,log+' '+text[-2000:]);return text
    try:
        prior=json.loads((root/'run35-result.json').read_bytes())
        require(sha(root/'run35-result.json')=='2a5a21953b1be5f607d0c3ab1dd459415e9f29c215a7e4398410280c8f8e8f75' and prior['passed'],'frozen run35 control changed')
        generated=out/'generated';generated.mkdir()
        for f in (root/'frozen_model').iterdir():
            require(sha(f)==prior['generation']['generated_sha256'][f.name],'frozen generated source drift '+f.name)
            shutil.copyfile(f,generated/f.name)
        p=generated/'optimization.hpp';s=p.read_text()
        s=once(s,'bool nexp8=false;','bool nexp8=false;int s16_mode=0;U s16_values=0,s16_frames=0;')
        s=once(s,' else return false;', ''' else if(name=="s16_measured")s16_mode=1;
 else if(name=="s16_full_u_bound")s16_mode=2;
 else if(name=="s16_vector8_target"){s16_mode=1;lanes=8;}
 else return false;''')
        s=once(s,'U nexp_cost(U count,bool qualified,U old_cost){','U nexp_cost(U count,bool qualified,U old_cost,bool is_s16){')
        compute=','.join(map(str,r['profile']['frame_compute_cycles']));full=','.join(map(str,r['profile']['frame_full_U_cycles']))
        s=once(s,'const U cost=nexp8&&qualified?ceildiv(count,8)*7:old_cost;',f'''U cost=nexp8&&qualified?ceildiv(count,8)*7:old_cost;
 if(s16_mode&&is_s16){{
  const U compute[9]={{{compute}}},full[9]={{{full}}};const U* table=s16_mode==2?full:compute;
  cost=(count/8)*table[8]+table[count%8];s16_values+=count;s16_frames+=ceildiv(count,8);
 }}''')
        anchor='<<",\\\"nexp8\\\":"<<(nexp8?"true":"false")'
        extra='''
    <<",\\\"native_S16\\\":{\\\"scope\\\":\\\"local_frame_only\\\",\\\"full_model_RTL_calibrated\\\":false"
    <<",\\\"mode\\\":"<<s16_mode<<",\\\"values\\\":"<<s16_values<<",\\\"frames\\\":"<<s16_frames
    <<",\\\"profile_sha256\\\":\\\"@SHA@\\\",\\\"RTL_source_commit\\\":\\\"@COMMIT@\\\""
    <<",\\\"vector8_target_only\\\":"<<(lanes==8?"true":"false")<<"}"'''
        extra=extra.replace('@SHA@',r['profile']['result_sha256']).replace('@COMMIT@',r['profile']['source_commit'])
        s=once(s,anchor,anchor+extra);p.write_text(s)
        p=generated/'model.cpp';s=p.read_text();s=once(s,'optimization::nexp_cost(o.elements,nexp_qualified,nexp_extra)',
            'optimization::nexp_cost(o.elements,nexp_qualified,nexp_extra,o.in.size()==1&&tensors[o.in[0]].bits==16&&tensors[o.out].bits==32)');p.write_text(s)
        r['generated_sha256']={p.name:sha(p) for p in generated.iterdir()};save()
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        r['tools']=dict(gcc=execute(['g++','--version'],'gcc.log').splitlines()[0],SystemC_library_sha256=sha(prefix/'lib/libsystemc.so'))
        compile_cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',generated/'model.cpp','-I'+str(generated),
            '-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model']
        execute(compile_cmd,'build.log');r['compile_command']=list(map(str,compile_cmd));r['binary_sha256']=sha(out/'model')
        shutil.copyfile(root/'inputs/m-profile.log',out/'m-profile.log')
        def task(item):
            name,w,p,v,dual=item;key=f'{name}-{w}-{p}-'+('idealdual' if dual else 'shared')
            cmd=[out/'model',root/'inputs'/(w+'.trace'),p,v,8,1,1,16,int(dual),4,0,1,1,1,32,4,2,1]
            env=dict(os.environ,OPTIMIZATION_CASE=name);env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
            text=execute(cmd,key+'.log',env);rows=[json.loads(l[7:]) for l in text.splitlines() if l.startswith('RESULT ')]
            require(len(rows)==1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text,'invalid SystemC output')
            ref=next(c['result'] for c in prior['cases'] if c['optimization']=='base' and c['workload']==w and c['profile']==p and c['dual_ports']==dual)
            row=rows[0];audit=check(row,ref,name);neg=[]
            for f in ['read_bus_bytes','M_commands','M_work_ticks','vector_work_ticks','tokens_per_second']:
                bad=deepcopy(row);bad[f]+=1
                try:check(bad,ref,name)
                except ValueError:neg.append(f)
                else:raise ValueError('tamper not rejected '+f)
            result=dict(case=name,workload=w,profile=p,dual_ports=dual,result=row,audit=audit,negative_checks=neg,
                command=list(map(str,cmd)),log=key+'.log',log_sha256=sha(out/(key+'.log')))
            (out/(key+'.json')).write_text(json.dumps(result,indent=2)+'\n');print('MODEL_CASE '+key+' '+str(row['tokens_per_second']),flush=True)
            return result
        for names in [('base',),CASES[1:]]:
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for value in pool.map(task,[(n,w,p,v,d) for n in names for w,p,v in WORK for d in (False,True)]):r['cases'].append(value);save()
        require(len(r['cases'])==32,'case coverage');r['passed']=True
    except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
    r['output_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json'}
    save();print(json.dumps({'passed':r['passed'],'cases':len(r['cases']),'error':r.get('error')}),flush=True)
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
