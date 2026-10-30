"""Actual native constant-cell frontend control; does not qualify C8."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from io_slots import file_sha
from native_formal import inspect
from native_tie_projection import project
from structural_view import compare


def verify(root,out,cpus,run,polarity):
    assert cpus==1 and polarity in (0,1)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    before='module tie_probe(input clk,d,output q,y); wire t; LOGIC%d_X1 constant_before(.Z(t)); XOR2_X1 g(.A(d),.B(t),.Z(y)); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n'%polarity
    after=before.replace('constant_before','constant_after').replace('DFF_X1','DFF_X2')
    variants=dict(before=before,after=after,wrong_tie=after.replace('LOGIC%d_X1'%polarity,'LOGIC%d_X1'%(1-polarity)),wrong_clock=after.replace('.CK(clk)','.CK(d)'))
    paths={};proofs={}
    for name,text in variants.items():
        path=out/(name+'.v');path.write_text(text);original=out/(name+'.json')
        ys='read_liberty -lib '+str(lib)+'\nread_verilog '+str(path)+'\nhierarchy -check -top tie_probe\nwrite_json '+str(original)+'\n'
        script=out/(name+'-parse.ys');script.write_text(ys);run(['yosys','-s',str(script)],name+'-parse.log')
        data=json.loads(original.read_text());converted,proof=project(data,lib.read_text());assert proof['removed_count']==1
        graph=out/(name+'-literal.json');graph.write_text(json.dumps(converted)+'\n');target=out/(name+'-literal.v');reparsed=out/(name+'-reparsed.json')
        ys='read_json '+str(graph)+'\nwrite_verilog -norename -noattr -noexpr '+str(target)+'\ndesign -reset\nread_liberty -lib '+str(lib)+'\nread_verilog '+str(target)+'\nhierarchy -check -top tie_probe\nwrite_json '+str(reparsed)+'\n'
        script=out/(name+'-emit.ys');script.write_text(ys);run(['yosys','-s',str(script)],name+'-emit.log')
        proof['emitted_structural_proof']=compare(converted,json.loads(reparsed.read_text()));proofs[name]=proof;paths[name]=target
    results={}
    for name,left,right in [('original',out/'before.v',out/'after.v'),('positive',paths['before'],paths['after']),('wrong_tie',paths['before'],paths['wrong_tie']),('wrong_clock',paths['before'],paths['wrong_clock'])]:
        log=out/(name+'-kepler.log');config=out/(name+'-kepler.yml')
        config.write_text('format: verilog\ninput_paths:\n  - '+str(left)+'\n  - '+str(right)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(log)+'\n')
        with(out/(name+'-command.log')).open('w')as stream:code=subprocess.run([str(binary),'--config',str(config)],stdout=stream,stderr=subprocess.STDOUT).returncode
        received=inspect(log.read_text());received.update(returncode=code,log_sha256=file_sha(log));results[name]=received
        if name=='positive':assert code==0 and received['passed']is True,received
        else:assert received['passed']is False,received
        if name in ('wrong_tie','wrong_clock'):assert 'Found difference'in log.read_text()or'SAT solver finished: SAT'in log.read_text()
    (out/'native-tie-formal-control.json').write_text(json.dumps(dict(schema='block-v1-native-tie-formal-control/1',passed=True,polarity=polarity,
        library_sha256=file_sha(lib),binary_sha256=file_sha(binary),results=results,projection_proofs=proofs,
        qualified_hard_macro=False,scope='Actual renamed tie/resized DFF frontend probe, reversible constant function substitution and native strict positive/real wrong-tie/clock negatives; no complete C8 LEC qualification'),indent=2)+'\n')


def group(root,out,cpus):
    assert cpus==2
    def execute(bit):
        mode='native-tie-formal-control-'+str(bit);folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'1'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-tie-formal-control.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==1 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(polarity=bit,cpus=1,started=start,finished=time.time(),passed=passed,returncode=code,receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:children=list(pool.map(execute,[0,1]))
    record=dict(schema='block-v1-native-tie-formal-control-group/1',passed=all(c['passed']for c in children),children=children,allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=2,qualified_hard_macro=False)
    (out/'native-tie-formal-control-group.json').write_text(json.dumps(record,indent=2)+'\n');assert record['passed']
