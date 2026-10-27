"""Read-only diagnosis of real rejected C8 state/input correspondence.

No LEC gate is changed. Graph parsing runs on allocated compute resources.
The report preserves explicit UNSAT and unmatched-boundary failure together.
"""
import collections
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from native_allocation_group import memory_snapshot,file_sha
from native_formal import inspect
from native_cell_gate import group as liberty_group


def verify(root,out,cpus,policy):
    assert cpus==2 and policy in ('A','C');base=out.parents[2]
    source=base/'block-v1-20261027-134/tasks'/('native-receive-shared109-'+policy.lower())
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is False
    assert receipt['error']=="AssertionError('Final native LEC lacks complete positive evidence')"
    inputs={}
    for name in ['strict-projected-kepler.log','strict-projected-kepler.yml','formal-before-logic.json','formal-after-logic.json','formal-before-logic-proof.json','formal-after-logic-proof.json']:
        path=source/name;digest=file_sha(path);assert digest==receipt['outputs'][name];inputs[name]=digest
    text=(source/'strict-projected-kepler.log').read_text();received=inspect(text)
    assert received['passed']is False and received['checks']['explicit_unsat']is True and received['checks']['explicit_identical']is True
    assert received['checks']['no_unmatched_boundaries']is False
    normalized=text.split('normalizeInputs: starting');assert len(normalized)==2
    unmatched={side:re.findall(r'diff'+side+r' input: (\S+)\s*$',normalized[-1],re.M)for side in ['0','1']}
    assert all(len(unmatched[s])==received['counts']['diff'+s+' inputs']for s in unmatched)
    library=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');lib=library.read_text()
    sequential={}
    for master in re.findall(r'\bcell\s*\(\s*"?([A-Za-z_0-9]+)"?\s*\)',lib):
        body=liberty_group(lib,'cell',master)
        if re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',body):sequential[master]=True
    assert sequential,'No real Liberty sequential masters classified'
    summaries={};states={};matches={}
    for side,label in [('0','before'),('1','after')]:
        data=json.loads((source/('formal-'+label+'-logic.json')).read_text());module=data['modules']['shared109'];cells=module['cells'];ports=module['ports'];netnames=module['netnames']
        state={name:dict(master=cell['type'],ports={p:len(bits)for p,bits in cell['connections'].items()},directions=cell['port_directions'])for name,cell in cells.items()if cell['type']in sequential}
        assert state,'No actual sequential instances found'
        floating=collections.Counter();examples=collections.defaultdict(list)
        for name,cell in cells.items():
            for pin,bits in cell['connections'].items():
                if cell['port_directions'][pin]!='input':continue
                for bit in bits:
                    if bit in ('x','z'):
                        key=cell['type']+'/'+pin+'/'+bit;floating[key]+=1
                        if len(examples[key])<12:examples[key].append(name)
        mapped=[];cell_names=set(cells);alias_names=set(netnames)
        for label_id in unmatched[side]:
            token=label_id.split('.')[0];candidates={token,'_'+token+'_'}
            mapped.append(dict(native_input=label_id,cell_candidates={n:cells[n]['type']for n in sorted(candidates&cell_names)},
                alias_candidates={n:netnames[n]['bits']for n in sorted(candidates&alias_names)}))
        matches[side]=mapped;states[side]=state
        summaries[side]=dict(cell_count=len(cells),masters=dict(collections.Counter(c['type']for c in cells.values())),
            top_ports={n:dict(direction=p['direction'],width=len(p['bits']))for n,p in ports.items()},sequential_cell_count=len(state),
            sequential_masters=dict(collections.Counter(v['master']for v in state.values())),literal_unknown_input_counts=dict(floating),literal_unknown_input_examples=dict(examples),
            sample_cell_names=list(cells)[:20],sample_alias_names=list(netnames)[:20],mapped_native_unmatched_count=sum(bool(v['cell_candidates']or v['alias_candidates'])for v in mapped))
        del data,module,cells,ports,netnames,cell_names,alias_names
    same=set(states['0'])&set(states['1'])
    state_delta=dict(before_only=sorted(set(states['0'])-set(states['1'])),after_only=sorted(set(states['1'])-set(states['0'])),
        changed_matched_instances={n:dict(before=states['0'][n],after=states['1'][n])for n in sorted(same)if states['0'][n]!=states['1'][n]},matched_instances=len(same))
    assert all(file_sha(source/name)==digest for name,digest in inputs.items())
    result=dict(schema='block-v1-native-c8-formal-diagnosis/1',passed=True,policy=policy,source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),
        inputs=inputs,liberty_sha256=file_sha(library),native_lec=received,unmatched_native_inputs=unmatched,graph_summaries=summaries,
        sequential_instance_delta=state_delta,lexical_native_label_candidates=matches,native_lec_qualified=False,qualified_hard_macro=False,
        scope='Read-only source-bound unmatched-input/state-instance diagnostic only; lexical candidates are not proved correspondence, no graph/physical edits or relaxed LEC gate')
    (out/'native-c8-formal-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')


def group(root,out,cpus):
    assert cpus==4
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=2*24*1024**3*1.2 else 1
    def execute(policy):
        mode='native-c8-formal-diagnose-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'2'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-c8-formal-diagnosis.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==2 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=2,started=start,finished=time.time(),passed=passed,returncode=code,
                    receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-c8-formal-diagnosis-group/1',passed=all(r['passed']for r in children),allocated_cpus=cpus,
                simultaneous_workers=parallel,maximum_concurrent_cpu_ceilings=2*parallel,memory_preflight=memory,
                per_child_memory_budget_bytes=24*1024**3,parallel_memory_safety_factor=1.2,children=children,qualified_hard_macro=False)
    (out/'native-c8-formal-diagnosis-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'C8 formal diagnostic child failed; independent peer retained'
