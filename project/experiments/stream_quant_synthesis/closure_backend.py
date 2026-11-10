"""Slurm-only RTL and finite-resource SystemC evaluation of closure candidates."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
import shutil
import traceback
from prepare import restore,sha
from generate import generate
from bottleneck_generate import extend as bank_extend
from closure_generate import extend
from numeric import pack
from run import execute,VERILATOR

HERE=Path(__file__).resolve().parent
QUALITY_ROOT=Path('/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-22')


def partial_vectors(path):
    rng=random.Random(248128);rows=[]
    for case in range(600):
        n=case%8+1;p=[rng.randrange(-(1<<35),1<<35) for _ in range(8)]
        m=[rng.randrange(1,2048) for _ in range(8)];s=[rng.randrange(0,65) for _ in range(8)]
        old=[rng.randrange(-(1<<110),1<<110) for _ in range(8)]
        if case%30==0:s[0]=127
        if case%31==0:m[0]=0
        if case%37==0:old[0]=(1<<127)-1;p[0]=1;m[0]=1;s[0]=0
        new=[old[i]+((p[i]*m[i])<<s[i]) if i<n else 0 for i in range(8)]
        bad=any(not m[i] or not -(1<<127)<=((p[i]*m[i])<<s[i])<(1<<127) or not -(1<<127)<=new[i]<(1<<127) for i in range(n))
        rows.append(f'{n} {pack(p,40)} {pack(m,11)} {pack(s,7)} {pack(old,128)} {pack(new,128)} {int(bad)}')
    path.write_text('\n'.join(rows)+'\n');return len(rows)


def context_vectors(path):
    rng=random.Random(24816);rows=[];state=[[0]*8 for _ in range(16)]
    for wave in range(4):
        for k in range(16):
            for c in range(16):
                p=[rng.randrange(-(1<<28),1<<28) for _ in range(8)]
                m=[rng.randrange(1,2048) for _ in range(8)];s=[rng.randrange(0,45) for _ in range(8)]
                if k==0:state[c]=[0]*8
                state[c]=[a+((b*d)<<e) for a,b,d,e in zip(state[c],p,m,s)]
                rows.append(f'{c} {int(k==0)} {int(k==15)} {wave+1} {pack(p,40)} {pack(m,11)} {pack(s,7)} {pack(state[c],128)} 0')
    # Continuing an inactive context must fault rather than invent prior data.
    rows.append(f'0 0 1 99 {pack([1]*8,40)} {pack([1]*8,11)} {pack([0]*8,7)} 0 1')
    path.write_text('\n'.join(rows)+'\n');return len(rows)


def main(root,stage):
    assert os.environ.get('SLURM_JOB_ID')
    out=root/'results';out.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),job=os.environ['SLURM_JOB_ID'],cases=[])
    def save():(out/'closure-backend.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        if stage!='timing':
            qroot=QUALITY_ROOT/'quality';quality=json.loads((qroot/'closure-quality.json').read_text())
            assert quality['passed'],'quality experiment incomplete'
            selected=next(p for p in quality['profiles'] if p['bits']==16)
            report['quality_sha256']=sha(qroot/'closure-quality.json');report['quality_admitted']=selected['numerical_study_admitted']
            # Timing can still diagnose an unqualified profile, but is never reported
            # as quality-admitted throughput unless its predeclared gate passes.
            env=dict(os.environ);env.pop('VERILATOR_ROOT',None)
            report['verilator']=execute([VERILATOR,'--version'],out/'verilator.log',out,env)
            for name in ('g32-lut.hex','closure-g-vectors.txt','closure-m-vectors.txt'):
                assert sha(qroot/name)==quality['retained_artifacts'][name]['sha256'];shutil.copyfile(qroot/name,out/name)
            obj=out/'obj-G32'
            execute([VERILATOR,'--cc','--exe','--build','-j','4','--top-module','closure_g32','-Wall','-Mdir',obj,
                     HERE/'closure_g32.sv',HERE/'tb_closure_g.cpp'],out/'G32-build.log',out,env)
            report['G32']=[]
            for stalls in (0,1):
                text=execute([obj/'Vclosure_g32',out/'closure-g-vectors.txt',stalls],out/f'G32-{stalls}.log',out,env)
                r=json.loads(text.strip().splitlines()[-1]);assert r['passed'] and r['packets']==quality['G_frames'];report['G32'].append(r)
            # Reuse the independently validated M pipeline on actual grouped inputs.
            obj=out/'obj-M16'
            execute([VERILATOR,'--cc','--exe','--build','-j','4','--top-module','w8_dot_candidate','-Wall',
                     '-GABITS=16','-Mdir',obj,'-CFLAGS','-DABITS=16',HERE/'w8_stream_mac.sv',HERE/'w8_weight_buffer.sv',
                     HERE/'w8_dot_candidate.sv',HERE/'tb_w8.cpp'],out/'M-build.log',out,env)
            text=execute([obj/'Vw8_dot_candidate',out/'closure-m-vectors.txt'],out/'M.log',out,env)
            assert 'W8_RTL_PASS' in text;report['M']=dict(log=text,packets=quality['M_packets'])
            count=partial_vectors(out/'partial-vectors.txt');obj=out/'obj-partial'
            execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_closure_partial','-Wall','-j','4','--Mdir',obj,
                     HERE/'closure_partial128.sv',HERE/'tb_closure_partial.sv'],out/'partial-build.log',out,env)
            text=execute([obj/'Vtb_closure_partial'],out/'partial.log',out,env);assert f'checks={count}' in text
            report['partial']=dict(checks=count,log=text);save()
            obj=out/'obj-controller'
            execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_closure_controller','-Wall','-Wno-BLKSEQ','-j','4','--Mdir',obj,
                     HERE/'closure_partial128.sv',HERE/'closure_psum_controller.sv',HERE/'tb_closure_controller.sv'],out/'controller-build.log',out,env)
            text=execute([obj/'Vtb_closure_controller'],out/'controller.log',out,env)
            assert f'checks={count}' in text;report['controller']=dict(checks=count,log=text);save()
            count=context_vectors(out/'context-vectors.txt');obj=out/'obj-context'
            execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_closure_context','-Wall','-j','4','--Mdir',obj,
                     HERE/'closure_partial128.sv',HERE/'closure_context16.sv',HERE/'tb_closure_context.sv'],out/'context-build.log',out,env)
            text=execute([obj/'Vtb_closure_context'],out/'context.log',out,env)
            assert f'checks={count}' in text;report['context']=dict(checks=count,log=text);save()
            report['weight_banks']=[]
            for banks in (2,4,8):
                obj=out/f'obj-banks{banks}'
                execute([VERILATOR,'--binary','--timing','--assert','--top-module','tb_closure_banks','-Wall',f'-GBANKS={banks}','-j','4','--Mdir',obj,
                         HERE/'closure_weight_banks.sv',HERE/'tb_closure_banks.sv'],out/f'banks{banks}-build.log',out,env)
                text=execute([obj/'Vtb_closure_banks'],out/f'banks{banks}.log',out,env)
                assert f'checks={banks*24}' in text;report['weight_banks'].append(dict(banks=banks,checks=banks*24,log=text));save()
        if stage=='rtl':
            report['passed']=True;return
        model=extend(bank_extend(generate(restore(root/'restored'),root/'restored/candidate')))
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',model/'model.cpp','-I'+str(model),
                 '-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'candidate'],out/'build.log',out)
        plans=[('decode512',5,issue,bw,banks) for bw in (102400,51200) for issue,banks in ((1,2),(2,2),(2,4),(2,8))]
        plans += [('decode512',4,2,102400,2),('decode2048',5,2,102400,8)]
        def run(item):
            workload,mode,issue,bw,banks=item;name=f'{workload}-mode{mode}-issue{issue}-bw{bw}-banks{banks}'
            env={k:v for k,v in os.environ.items() if not k.startswith(('SQ_','BN_','CL_'))}
            knobs=dict(SQ_DIRECT=1,SQ_ABITS=16 if mode else 0,SQ_BREAD=128,SQ_BW_MB=bw,SQ_PCOUNT=3,SQ_BEAT=64,
                       SQ_STRIPE=1,BN_RELEASE=2,CL_MODE=mode,CL_ISSUE=issue,CL_BANKS=banks)
            env.update({k:str(v) for k,v in knobs.items()})
            command=[out/'candidate',root/'restored/inputs'/(workload+'.trace'),'queued_pipe_w8','prefix_pair_combine',8,1,1,16,0,4,0,1,1,1]
            text=execute(command,out/(name+'.log'),out,env)
            lines=[json.loads(x[7:]) for x in text.splitlines() if x.startswith('RESULT ')]
            assert len(lines)==1 and 'MODEL_FAILURE' not in text
            value=lines[0];assert value['max_outstanding_beats']<=32 and value['P_scratch_peak_bytes']<=16384
            assert value['closure']['bank_peak']<=banks and value['closure']['S_peak']<=16384
            if mode>=2 and workload.startswith('decode'):assert value['closure']['FFNs']==36
            print('CLOSURE_TIMING '+name+' '+str(value['tokens_per_second']),flush=True)
            return dict(name=name,knobs=knobs,workload=workload,result=value,log_sha256=sha(out/(name+'.log')))
        for start in range(0,len(plans),4):
            with ThreadPoolExecutor(max_workers=4) as pool:report['cases'].extend(pool.map(run,plans[start:start+4]))
            save()
        report['physical_qualified']=False;report['full_integer_LLM']=False
        report['native_full_model_tokens_s']=None;report['energy_J_token']=None;report['passed']=True
    except Exception as e:
        report['error']=repr(e);report['traceback']=traceback.format_exc();raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',choices=('all','timing','rtl'),default='all')
    a=p.parse_args();main(a.root,a.stage)
