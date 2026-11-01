"""Native integration control for protection plus constant Boolean encoding."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from io_slots import file_sha
from native_formal import inspect
from native_logic_projection import export,used_model_audit


def verify(root,out,cpus,run,polarity):
    assert cpus==1 and polarity in (0,1)
    library=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    before='module projection_probe(input clk,d,output q,y); wire t; LOGIC%d_X1 constant_before(.Z(t)); XOR2_X1 g(.A(d),.B(t),.Z(y)); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n'%polarity
    after=before.replace('constant_before','constant_after').replace('DFF_X1','DFF_X2').replace('endmodule','ANTENNA_X1 protection(.A(d)); endmodule')
    variants=dict(before=before,after=after,wrong_tie=after.replace('LOGIC%d_X1'%polarity,'LOGIC%d_X1'%(1-polarity)),wrong_clock=after.replace('.CK(clk)','.CK(d)'))
    paths={};proofs={};sources={}
    for name,text in variants.items():
        path=out/(name+'.v');path.write_text(text);sources[str(path)]=file_sha(path)
        target,proof=export(root,out,run,path,library,'projection_probe',name,constant_functions=True)
        assert proof['removed_count']==(0 if name=='before'else 1)
        assert proof['constant_functions']['removed_count']==1
        assert proof['projected_graph_sha256']==proof['constant_functions']['original_graph_sha256']
        assert proof['emitted_structural_proof']['passed'] is True and proof['used_model_audit']['passed'] is True
        proofs[name]=dict(path=str(out/(name+'-logic-proof.json')),sha256=file_sha(out/(name+'-logic-proof.json')))
        paths[name]=target
    results={}
    for name,other in [('positive','after'),('wrong_tie','wrong_tie'),('wrong_clock','wrong_clock')]:
        log=out/(name+'-kepler.log');config=out/(name+'-kepler.yml')
        config.write_text('format: verilog\ninput_paths:\n  - '+str(paths['before'])+'\n  - '+str(paths[other])+'\nliberty_files:\n - '+str(library)+'\nlog_file: '+str(log)+'\n')
        with(out/(name+'-command.log')).open('w')as stream:
            code=subprocess.run([str(binary),'--config',str(config)],stdout=stream,stderr=subprocess.STDOUT).returncode
        result=inspect(log.read_text());result.update(returncode=code,log_sha256=file_sha(log));results[name]=result
        if name=='positive':assert code==0 and result['passed'] is True
        else:
            assert result['passed'] is False
            assert 'Found difference'in log.read_text()or'SAT solver finished: SAT'in log.read_text()
    unsupported={}
    for construct in ['statetable (x,y,z) {}','state_function : "x";']:
        graph=dict(modules=dict(projection_probe=dict(cells=dict(u=dict(type='UNSUPPORTED')))))
        text='cell (UNSUPPORTED) { '+construct+' }'
        try:used_model_audit(graph,text)
        except AssertionError:unsupported[construct]=True
        else:raise AssertionError('Instantiated unsupported library model accepted')
    unchanged=all(file_sha(Path(p))==h for p,h in sources.items());assert unchanged
    record=dict(schema='block-v1-native-projection-control/1',passed=True,polarity=polarity,
        library_sha256=file_sha(library),binary_sha256=file_sha(binary),sources=sources,source_unchanged=unchanged,
        results=results,projection_proofs=proofs,unsupported_model_controls=unsupported,
        qualified_hard_macro=False,
        scope='Actual integrated protection removal plus true constant encoding, exact inverse and emitted graph comparison, strict positive and wrong-tie/clock SAT negatives; not a complete C8 qualification')
    (out/'native-projection-control.json').write_text(json.dumps(record,indent=2)+'\n')


def group(root,out,cpus):
    assert cpus==2
    def execute(polarity):
        mode='native-projection-control-'+str(polarity);folder=out.parent/mode;folder.mkdir(exist_ok=False);started=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'1'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-projection-control.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==1 and r['mode']==mode and file_sha(q)==r['outputs'][q.name]and json.loads(q.read_text())['passed'] is True
        return dict(polarity=polarity,cpus=1,started=started,finished=time.time(),returncode=code,passed=passed,
            receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:children=list(pool.map(execute,[0,1]))
    record=dict(schema='block-v1-native-projection-control-group/1',passed=all(c['passed']for c in children),children=children,
        allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=2,qualified_hard_macro=False)
    (out/'native-projection-control-group.json').write_text(json.dumps(record,indent=2)+'\n');assert record['passed']
