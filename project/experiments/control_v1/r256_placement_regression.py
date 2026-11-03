"""Preserve actual legacy placement and reject undeclared R256 search inputs."""
import json,os,subprocess
from pathlib import Path

def run(a,root,sha):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False);b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');inputs={}
    def bind(p,expected=None):
        p=Path(p);v=sha(p)
        if expected is not None:assert v==expected,str(p)
        inputs[str(p)]=v;return v
    r=dict(passed=False,inputs=inputs,whole_system_qualified=False,commands=[])
    try:
        bind(Path(__file__));old=b/'source-258/project/experiments/control_v1/electrical_floorplan.cpp';new=Path(__file__).with_name('electrical_floorplan.cpp')
        manifest=b/'source-258/source-manifest.json';bind(manifest);bind(old,json.loads(manifest.read_text())['files']['project/experiments/control_v1/electrical_floorplan.cpp']);bind(new)
        legacy=b/'s-ready-composition-01/1391/cap-capacity-candidates/1970';receipt=legacy/'receipt.json';bind(receipt);proof=json.loads(receipt.read_text());assert proof['passed']
        inp=legacy/'electrical-placement-input.txt';bind(inp,proof['outputs'][inp.name])
        assert inp.read_text().split()[0]=='26'
        for label,source in [('old',old),('new',new)]:
            binary=a.out/label;subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
            with(a.out/(label+'.log')).open('w')as log:subprocess.run([str(binary),str(inp),str(a.out/(label+'.txt')),'162'],stdout=log,stderr=subprocess.STDOUT,check=True)
            bind(binary);bind(a.out/(label+'.log'));bind(a.out/(label+'.txt'))
        assert (a.out/'old.txt').read_bytes()==(a.out/'new.txt').read_bytes(),'Legacy full search output changed'
        invalid=['29 11122 60000 64 0 .35','29 11123 60000 64 0 .35 0 0 29','29 11122 60000 64 1 .35 0 0 29','26 11122 60000 64 0 .35 0 0 29','29 11122 60000 64 0 .35 0 0 28']
        for index,header in enumerate(invalid):
            p=a.out/('invalid-'+str(index)+'.txt');p.write_text(header+'\n');result=subprocess.run([str(a.out/'new'),str(p),str(a.out/('invalid-'+str(index)+'-output.txt')),'162'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            assert result.returncode!=0 and (b'envelope'in result.stdout or b'declared scene'in result.stdout)
            (a.out/('invalid-'+str(index)+'.log')).write_bytes(result.stdout);r['commands'].append(dict(header=header,returncode=result.returncode,log_sha256=sha(a.out/('invalid-'+str(index)+'.log'))))
        r.update(passed=True,actual_legacy_full_search_byte_identical=True,invalid_scene_inputs_rejected=len(invalid),new_R_positive_gate_required_separately=True,scope='Search input contract and actual26-macro byte replay only; each actual29-macro candidate separately requires16 independent Python cost/nonoverlap checks. No physical/system qualification.')
    finally:
        r['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()};(a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
