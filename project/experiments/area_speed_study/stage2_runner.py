"""First complete actual context edge checks, then run the isolated RTL stage."""
import argparse
import json
from pathlib import Path
import os
import subprocess
import sys
from generate import generate, HERE
from run import execute, digest
from edge_cases import run_edges


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    stage1=json.loads((root/'stage1-result.json').read_text())
    assert stage1['passed'] and len(stage1['cases'])==35
    out=root/'results';out.mkdir(exist_ok=False)
    generated=out/'context';generated.mkdir()
    generate(generated)
    for name,value in stage1['generated_sha256'].items():
        assert digest(generated/name)==value, 'stage1 model source changed: '+name
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    execute(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',generated/'model.cpp',
             '-I'+str(generated),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
             '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',generated/'model'],out/'context-build.log',out)
    edges=run_edges(generated/'model',out)
    assert edges['passed']
    execute([sys.executable,'-B',HERE/'elastic/run_elastic.py','--repo',root/'source',
             '--out',out/'elastic','--workers',os.environ['SLURM_CPUS_PER_TASK'],
             '--stage1-result',root/'stage1-result.json','--deployment',root/'inputs.json'],
            out/'elastic-runner.log',out)
    elastic=json.loads((out/'elastic/result.json').read_text())
    assert elastic['passed']
    report=dict(passed=True,issue=247,source_commit=json.loads((root/'inputs.json').read_text())['source_commit'],
                stage1_sha256=digest(root/'stage1-result.json'),stage1_generated_sources_exact=True,
                edge_checks=edges,elastic=elastic,
                scope='actual SystemC candidate tail checks and isolated feeder/P RTL; no new SRAM capacity or physical signoff')
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('AREA_STAGE2_PASS',flush=True)


if __name__=='__main__':main()
