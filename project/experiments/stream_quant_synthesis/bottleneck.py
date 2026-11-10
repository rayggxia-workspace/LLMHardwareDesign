"""Slurm-only DMA/bank factorial and native-G bounded rendezvous evaluation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import traceback
from prepare import restore, sha, REPO
from generate import generate
from bottleneck_generate import extend
from run import execute, VERILATOR

HERE = Path(__file__).resolve().parent


def main(root):
    assert os.environ.get('SLURM_JOB_ID'), 'EDA requires Slurm'
    out=root/'results';out.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),
                Slurm_job=os.environ['SLURM_JOB_ID'],cases=[],native_full_model_tokens_s=None,
                whole_model_numeric_replay=False)
    def save():(out/'bottleneck.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        env=dict(os.environ);env.pop('VERILATOR_ROOT',None)
        report['tools']=dict(verilator=execute([VERILATOR,'--version'],out/'verilator.log',out,env),
                             gcc=execute(['g++','--version'],out/'gcc.log',out).splitlines()[0])
        rtl=REPO/'project/rtl/block_v2'
        # Native leaf's existing exhaustive reference also exercises all functions.
        for label,top,sources in [
            ('native-g','block_v2_g',[rtl/'block_v2_g.sv',REPO/'project/experiments/block_v2/test_g.cpp']),
            ('rendezvous','bn_g_bridge',[rtl/'block_v2_g.sv',HERE/'bn_g_bridge.sv',HERE/'tb_bn_g.cpp'])]:
            obj=out/('obj-'+label)
            execute([VERILATOR,'--cc','--exe','--build','-j','4','--top-module',top,'-Wall',
                     '-I'+str(rtl),'-Mdir',obj,*sources],out/(label+'-build.log'),out,env)
            log=execute([obj/('V'+top)],out/(label+'.log'),out,env)
            report[label]=json.loads(log.strip().splitlines()[-1]);assert report[label]['passed'];save()
        model=extend(generate(restore(root/'restored'),root/'restored/candidate'))
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
        execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',model/'model.cpp',
                 '-I'+str(model),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                 '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'candidate'],out/'build.log',out)
        prior_path=root.parent/'issue248-stream-quant-20261110-13/results/metadata-audit.json'
        prior=json.loads(prior_path.read_text());assert prior['passed']
        report['prior_sha256']=sha(prior_path)
        def case(item):
            workload,bw,queued,release=item
            name=f'{workload}-bw{bw}-q{int(queued)}-release{release}'
            variant='prefix_pair_combine' if queued else 'adaptive_prefix_pair_combine'
            command=[out/'candidate',root/'restored/inputs'/(workload+'.trace'),'queued_pipe_w8',variant,8,1,1,16,0,4,0,1,1,1]
            env={k:v for k,v in os.environ.items() if not k.startswith(('SQ_','BN_'))}
            knobs=dict(SQ_DIRECT=1,SQ_ABITS=0,SQ_BREAD=128,SQ_BW_MB=bw,SQ_PCOUNT=3,SQ_BEAT=64,SQ_STRIPE=1,BN_RELEASE=release)
            env.update({k:str(v) for k,v in knobs.items()})
            log=execute(command,out/(name+'.log'),out,env)
            rows=[json.loads(x[7:]) for x in log.splitlines() if x.startswith('RESULT ')]
            assert len(rows)==1 and 'MODEL_FAILURE' not in log
            row=rows[0]
            assert row['max_outstanding_beats']<=32 and row['P_scratch_peak_bytes']<=16384
            if workload=='decode512' and bw==102400 and not queued and release==0:
                expected=next(x['result'] for x in prior['cases'] if x['name'].startswith('r3-striped-a0-'))
                assert row==expected,'default full RESULT drift'
            print('BN_CASE '+name+' '+str(row['tokens_per_second']),flush=True)
            return dict(name=name,workload=workload,knobs=knobs,queued=queued,release=release,
                        command=list(map(str,command)),result=row,log_sha256=sha(out/(name+'.log')))
        plans=[('decode512',bw,q,r) for bw in (51200,102400) for q in (False,True) for r in (0,1,2)]
        # Robustness at a longer context and multi-row input; same finite resources.
        plans += [(w,102400,q,r) for w in ('decode2048','prefill2') for q,r in ((False,0),(True,2))]
        for start in range(0,len(plans),4):
            with ThreadPoolExecutor(max_workers=4) as pool:report['cases'].extend(pool.map(case,plans[start:start+4]))
            save()
        invariant=('logical_read_bytes','logical_write_bytes','M_commands','M_work_ticks','KV_state_write_bytes')
        for c in report['cases']:
            ref=next(x['result'] for x in report['cases'] if x['workload']==c['workload'] and x['knobs']['SQ_BW_MB']==c['knobs']['SQ_BW_MB'] and not x['queued'] and x['release']==0)
            for k in invariant:assert c['result'][k]==ref[k],c['name']+' changed '+k
        report['work_invariants']=list(invariant)
        report['native_G_whole_model_admission']=dict(accepted=False,reason='S32 SiLU input is not native S16/Q5.10; conversion/scales not numerically qualified')
        report['full_FFN_one_pass_admission']=dict(accepted=False,mid_S32_bytes=11008*4,
            mid_S16_bytes=11008*2,down_full_K_psum_bytes=2048*12,S_bytes=16384,
            reason='Mid and full-K down accumulator state each exceed S; finite replay/spill or another numeric/storage contract is needed')
        report['passed']=True
    except Exception as e:
        report['error']=repr(e);report['traceback']=traceback.format_exc();raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    main(p.parse_args().root.resolve())
