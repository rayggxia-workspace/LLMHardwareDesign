"""Targeted rebuild after output-label/operand-requirement corrections.

No scheduling logic changed. Re-run the two representative precision paths and
require the complete RESULT (apart from explicitly renamed metadata) to match
the immutable 65-case run12. This is not another optimization sweep.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from prepare import restore,sha
from generate import generate
from run import execute


def main(root):
    assert os.environ.get('SLURM_JOB_ID')
    out=root/'results';out.mkdir(exist_ok=False)
    prior=root.parent/'issue248-stream-quant-20261110-12/results/result.json'
    old=json.loads(prior.read_text());assert old['passed'] and len(old['cases'])==65
    assert old['source_commit']=='a76a402589ea4a907084246f2e265a8f55de1385'
    model=generate(restore(root/'restored'),root/'restored/candidate')
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',model/'model.cpp',
             '-I'+str(model),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
             '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'candidate'],out/'build.log',out)
    report=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),
                Slurm_job=os.environ['SLURM_JOB_ID'],prior_result_sha256=sha(prior),cases=[])
    names=['r3-striped-a0-bw102400-beat64-decode512-0','r3-striped-a16-bw102400-beat64-decode512-0']
    for name in names:
        case=next(x for x in old['cases'] if x['name']==name)
        env={k:v for k,v in os.environ.items() if not k.startswith('SQ_')}
        env.update({k:str(v) for k,v in case['knobs'].items()})
        command=[out/'candidate',root/'restored/inputs/decode512.trace','queued_pipe_w8',
                 'adaptive_prefix_pair_combine',8,1,1,16,0,4,0,1,1,1]
        text=execute(command,out/(name+'.log'),out,env)
        row=[json.loads(x[7:]) for x in text.splitlines() if x.startswith('RESULT ')]
        assert len(row)==1
        current=row[0];sq=dict(current['sq_study']);expected=case['result']
        assert sq.pop('static_weight_Dot_core_K')==(16 if case['knobs']['SQ_ABITS'] else 8)
        sq['core_K']=sq.pop('configured_candidate_core_K')
        compare=dict(current,sq_study=sq);assert compare==expected,'metadata correction changed performance/work'
        report['cases'].append(dict(name=name,exact_prior_RESULT_except_labels=True,result=current,log_sha256=sha(out/(name+'.log'))))
    report['passed']=True
    (out/'metadata-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('METADATA_AUDIT_PASS '+json.dumps(dict(cases=len(report['cases']),prior_result_sha256=sha(prior))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    main(p.parse_args().root.resolve())
