"""Slurm-only RTL validation and full-trace SystemC ablations."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from prepare import restore, sha, REPO, BASE
from generate import generate
import numeric
import planner

HERE=Path(__file__).resolve().parent
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')


def execute(command, log, cwd, env=None, expected=0):
    command=list(map(str,command))
    p=subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    Path(log).write_bytes(p.stdout)
    if p.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(p.returncode)+'\n'+p.stdout.decode(errors='replace')[-3500:])
    return p.stdout.decode()


def main(root):
    assert os.environ.get('SLURM_JOB_ID'),'EDA must run inside Slurm'
    out=root/'results';out.mkdir(exist_ok=False)
    report=dict(passed=False,base_commit=BASE,source_commit=(root/'source-commit.txt').read_text().strip(),
                Slurm_job=os.environ['SLURM_JOB_ID'],rounds={},cases=[])
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        report['tools']={}
        env=dict(os.environ,VERILATOR_ROOT='/opt/verilator')
        # ORFS image provides verilator in PATH. Its compiled root is authoritative.
        env.pop('VERILATOR_ROOT',None)
        report['tools']['verilator']=execute([VERILATOR,'--version'],out/'verilator-version.log',out,env)
        report['tools']['gcc']=execute(['g++','--version'],out/'gcc-version.log',out).splitlines()[0]
        rtl=[]
        for bits in (8,16):
            vectors=out/('vectors'+str(bits)+'.txt');meta=numeric.vectors(vectors,bits)
            obj=out/('obj'+str(bits))
            cmd=[VERILATOR,'--cc','--exe','--build','-j','4','--top-module','w8_dot_candidate','-Wall',
                 '-GABITS='+str(bits),'-Mdir',obj,'-CFLAGS','-DABITS='+str(bits),
                 HERE/'w8_stream_mac.sv',HERE/'w8_weight_buffer.sv',HERE/'w8_dot_candidate.sv',HERE/'tb_w8.cpp']
            execute(cmd,out/('rtl-build'+str(bits)+'.log'),out,env)
            text=execute([obj/'Vw8_dot_candidate',vectors],out/('rtl'+str(bits)+'.log'),out,env)
            assert 'W8_RTL_PASS' in text
            rtl.append(dict(**meta,log=text.strip(),vectors_sha256=sha(vectors)))
        report['rounds']['RTL']=rtl;report['rounds']['numeric_contract']=numeric.check_contract()
        report['rounds']['DP_checks']=planner.test();save()
        requant=[]
        for bits in (8,16,32):
            folder=out/('requant'+str(bits));folder.mkdir()
            count=numeric.requant_vectors(folder/'requant-vectors.txt',bits);obj=folder/'obj'
            execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_requant4','-GQBITS='+str(bits),
                     '-Wall','-j','4','--Mdir',obj,HERE/'w8_requantize4.sv',HERE/'tb_requant4.sv'],folder/'build.log',folder,env)
            log=execute([obj/'Vtb_requant4'],folder/'rtl.log',folder,env)
            assert 'REQUANT_RTL_PASS' in log
            requant.append(dict(bits=bits,vectors=count,log=log,vectors_sha256=sha(folder/'requant-vectors.txt')))
        report['rounds']['requant_RTL']=requant;save()
        frozen=root/'restored';baseline=restore(frozen);candidate=generate(baseline,frozen/'candidate')
        (out/'m-profile.log').write_bytes((frozen/'inputs/m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        for label,folder in [('baseline',baseline),('candidate',candidate)]:
            execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',folder/'model.cpp',
                     '-I'+str(folder),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),
                     '-lsystemc','-o',out/label],out/(label+'-build.log'),out)
        old=json.loads(gzip.decompress(base64.b64decode((REPO/'work/Melodydt/247/speed-iterations/round04/run23/results/result.json.gz.b64').read_bytes())))
        def case(item):
            label,workload,dual,knobs=item
            command=[out/('baseline' if label=='frozen' else 'candidate'),frozen/'inputs'/(workload+'.trace'),
                     'queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,int(dual),4,0,1,1,1]
            env=dict(os.environ)
            for k in list(env):
                if k.startswith('SQ_'):env.pop(k)
            env.update({k:str(v) for k,v in knobs.items()})
            name=label+'-'+workload+'-'+str(int(dual))
            text=execute(command,out/(name+'.log'),out,env)
            rows=[json.loads(l[7:]) for l in text.splitlines() if l.startswith('RESULT ')]
            assert len(rows)==1 and 'MODEL_FAILURE' not in text
            row=rows[0]
            total=row['read_bus_bytes']+row['write_bus_bytes']
            bw=knobs.get('SQ_BW_MB',17100)*1e6
            record=dict(name=name,workload=workload,dual=dual,knobs=knobs,result=row,
                        average_bus_GB_s=total/row['seconds']/1e9,bus_utilization=total/row['seconds']/bw,
                        command=list(map(str,command)),log_sha256=sha(out/(name+'.log')))
            if label in ('frozen','off'):
                expected=[c['result'] for c in old['cases'] if c['workload']==workload and c['profile']=='queued_pipe_w8'
                          and c['dual_ports']==dual and c['iteration4_enabled']]
                assert len(expected)==1
                compare=dict(row);compare.pop('sq_study',None)
                assert compare==expected[0], 'disabled full RESULT drift'
                record['exact_R4_baseline']=True
            assert row['max_outstanding_beats']<=32 and row['P_scratch_peak_bytes']<=16384
            if knobs.get('SQ_DIRECT'):
                assert row['sq_study']['direct_weight_bus_bytes']>0
            print('SQ_CASE '+name+' tps='+str(row['tokens_per_second']),flush=True)
            return record
        work=['decode512','decode2048','prefill2']
        plans=[(label,w,d,{}) for label in ('frozen','off') for w in work for d in (False,True)]
        plans += [('r1-direct',w,False,dict(SQ_DIRECT=1)) for w in work]
        plans += [(f'r2-a{a}-k{k}-b{b}','decode512',False,dict(SQ_DIRECT=1,SQ_ABITS=a,SQ_CORE_K=k,SQ_BREAD=b))
                  for a in (8,16) for k,b in ((8,64),(16,64),(16,128))]
        plans += [(f'r3-a{a}-bw{bw}-p{p}','decode512',False,dict(SQ_DIRECT=1,SQ_ABITS=a,SQ_BREAD=128,SQ_BW_MB=bw,SQ_PCOUNT=p))
                  for a in (8,16) for bw in (17100,51200,102400) for p in (2,3)]
        plans += [(f'r3-wide-bw{bw}-p{p}','decode512',False,dict(SQ_DIRECT=1,SQ_ABITS=8,SQ_BREAD=128,SQ_BW_MB=bw,SQ_PCOUNT=p,SQ_BEAT=256))
                  for bw in (51200,102400) for p in (2,3)]
        plans += [(f'r3-striped-a{a}-bw{bw}-beat{beat}','decode512',False,
                   dict(SQ_DIRECT=1,SQ_ABITS=a,SQ_BREAD=128,SQ_BW_MB=bw,SQ_PCOUNT=3,SQ_BEAT=beat,SQ_STRIPE=1))
                  for a in (8,16) for bw in (51200,102400) for beat in (64,256)]
        report['compiler_plans']=[]
        for workload in work:
            for method in ('greedy','dp'):
                plan=planner.compile_plan(planner.graph(frozen/'inputs'/(workload+'.trace')),method)
                path=out/('plan-'+workload+'-'+method+'.txt');planner.emit(plan,path)
                planner.bundle(plan,out/('bundle-'+workload+'-'+method+'.json'))
                (out/('plan-'+workload+'-'+method+'.json')).write_text(json.dumps(plan,indent=2)+'\n')
                report['compiler_plans'].append(dict(workload=workload,method=method,estimated_cycles=plan['estimated_cycles'],peak_frontier=plan['peak_frontier'],plan_sha256=sha(path)))
                plans.append(('r4-'+method,workload,False,dict(SQ_DIRECT=1,SQ_PLAN=str(path))))
        for bits in (8,16):
            for method in ('greedy','dp'):
                plan=planner.compile_plan(planner.graph(frozen/'inputs/decode512.trace'),method,102400,3,bits)
                path=out/(f'plan-coupled-a{bits}-{method}.txt');planner.emit(plan,path)
                planner.bundle(plan,out/(f'bundle-coupled-a{bits}-{method}.json'),3,bits)
                (out/(f'plan-coupled-a{bits}-{method}.json')).write_text(json.dumps(plan,indent=2)+'\n')
                plans.append((f'r4-coupled-a{bits}-{method}','decode512',False,
                              dict(SQ_DIRECT=1,SQ_ABITS=bits,SQ_BREAD=128,SQ_BW_MB=102400,SQ_PCOUNT=3,SQ_BEAT=256,SQ_PLAN=str(path))))
        for batch in range(0,len(plans),4):
            with ThreadPoolExecutor(max_workers=4) as pool:
                report['cases'].extend(pool.map(case,plans[batch:batch+4]))
            save()
        for record in report['cases']:
            if record['name'].startswith('r1'):
                prior=next(c for c in report['cases'] if c['name']=='off-'+record['workload']+'-0')['result']
                for key in ('logical_read_bytes','logical_write_bytes','M_commands','M_work_ticks','KV_state_write_bytes'):
                    assert record['result'][key]==prior[key], 'R1 changed work: '+key
        report['passed']=True
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    main(parser.parse_args().root.resolve())
