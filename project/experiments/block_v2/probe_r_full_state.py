"""Complete explicit-state partition diagnostic; does not grant physical acceptance.

All Q/QN pins are independent common inputs. Every D and CK and every primary
output must be proved. This is stronger than restricting QN to complementary Q.
Unchanged sequential cell semantics and exact reversible edits are prerequisites.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from probe_r_partition import inventory, explicit_view, sha
from native_formal import inspect
from native_cell_gate import group, attribute


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--states-per-part', type=int, default=2048)
    a=p.parse_args(); assert 1<=a.workers<=3 and a.states_per_part>0
    a.out.mkdir(parents=True, exist_ok=False)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    results=a.source/'flow/results/nangate45/bv1_block_v1_r/base'
    sources=[results/'1_synth_lec.v',results/'6_final_lec.v']
    report=dict(passed=False, diagnostic_only=True, native_leaf_accepted=False,
        started_unix=time.time(),parts=[], controls={}, source_sha256={str(x):sha(x) for x in sources},
        liberty_sha256=sha(lib),binary_sha256=sha(binary),strict_receiver_unchanged=True)
    def save():
        report['updated_unix']=time.time()
        temp=a.out/'report.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(a.out/'report.json')
    def prove(folder, left, right, names, selected):
        folder.mkdir()
        views=[explicit_view(s,lib,folder/n,names,selected) for s,n in zip((left,right),('before.v','after.v'))]
        log=folder/'kepler.log';config=folder/'config.yml'
        config.write_text('format: verilog\ninput_paths:\n  - '+str(folder/'before.v')+'\n  - '+str(folder/'after.v')+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(log)+'\n')
        started=time.time()
        with (folder/'command.log').open('w') as stream:
            proc=subprocess.run([str(binary),'--config',str(config)],cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
        text=log.read_text();row=inspect(text)
        row.update(returncode=proc.returncode,seconds=time.time()-started,views=views,
            log_sha256=sha(log),config_sha256=sha(config),folder=str(folder),
            explicit_difference=('Found difference' in text or bool(re.search(r'SAT solver finished: SAT\s*$',text,re.M))))
        (folder/'result.json').write_text(json.dumps(row,indent=2)+'\n')
        return row
    try:
        library=lib.read_text();inventories=[];models=[]
        for source in sources:
            text=source.read_text();rows,used=inventory(text,lib)
            # Reject every unhandled sequential/black-box primitive, including
            # other DFF spellings that the narrow conversion regexp would miss.
            masters=re.findall(r'(?m)^ ([A-Za-z_][A-Za-z_0-9]*) \S+\s+\(',text)
            for master in set(masters):
                model=group(library,'cell',master)
                if re.search(r'\b(?:ff|latch|statetable)\s*\(',model):
                    assert master in used,('unhandled sequential model',master)
                    assert not re.search(r'\b(?:clear|preset|clear_preset_var\d)\s*:',model)
                    assert attribute(group(model,'pin','Q'),'function')=='IQ'
                    assert attribute(group(model,'pin','QN'),'function')=='IQN'
            assert len(rows)==146402 and len(masters)>=len(rows)
            inventories.append(rows);models.append(used)
        names=sorted(inventories[0]);assert set(names)==set(inventories[1])
        for name in names:
            left,right=(rows[name] for rows in inventories)
            # Resizing is allowed only between audited same-function DFF models.
            assert left['master'] in models[0] and right['master'] in models[1]
        report['state_instances']=len(names)
        report['ordered_state_names_sha256']=hashlib.sha256(json.dumps(names).encode()).hexdigest()
        controls=a.out/'controls';controls.mkdir()
        before='module formal_probe(clk,d,q);\n input clk,d; output q; wire qi;\n DFF_X1 u0 (.CK(clk),.D(d),.Q(q));\nendmodule\n'
        variants=dict(positive=before.replace('DFF_X1','DFF_X2'),data=before.replace('.D(d)',".D(1'b0)"),
            clock=before.replace('.CK(clk)','.CK(d)'),output=before.replace('.Q(q)','.Q(qi)').replace('endmodule',' INV_X1 inv (.A(qi),.ZN(q));\nendmodule'))
        for name,text in variants.items():
            left=controls/(name+'-before.v');left.write_text(before)
            right=controls/(name+'-after.v');right.write_text(text)
            row=prove(controls/name,left,right,['u0'],['u0']);report['controls'][name]=row
            if name=='positive':assert row['returncode']==0 and row['passed']
            else:assert row['explicit_difference'] and not row['passed']
        parts=[names[i:i+a.states_per_part] for i in range(0,len(names),a.states_per_part)]
        assert len(set(x for part in parts for x in part))==len(names)
        assert [x for part in parts for x in part]==names
        report.update(expected_parts=len(parts),workers=a.workers,complete_state_coverage=True,
            expected_common_inputs=292950,primary_output_bits=132)
        save()
        def task(i):
            row=prove(a.out/('part-%03d'%i),*sources,names,parts[i])
            assert row['returncode']==0 and row['passed'],row
            assert row['counts']['common inputs']==292950
            assert row['counts']['common outputs']==2*len(parts[i])+132
            row['part']=i
            return row
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures={pool.submit(task,i):i for i in range(len(parts))}
            for future in concurrent.futures.as_completed(futures):
                report['parts'].append(future.result());save()
                print('PART',futures[future],'PASS',len(report['parts']),'/',len(parts),flush=True)
        assert sorted(row['part'] for row in report['parts'])==list(range(len(parts)))
        assert sum(row['views'][0]['selected_state_output_bits'] for row in report['parts'])==292804
        assert report['source_sha256']=={str(x):sha(x) for x in sources}
        report.update(passed=True,all_state_output_bits=292804,all_primary_output_bits=132,
            all_unique_output_bits=292936,original_files_unchanged=True,
            scope='Complete independently free Q/QN input and all D/CK plus primary output combinational equivalence; diagnostic only, not native producer completion or block acceptance')
    except Exception as error:
        report['error']=repr(error);raise
    finally:
        report['ended_unix']=time.time();save()


if __name__=='__main__':main()
