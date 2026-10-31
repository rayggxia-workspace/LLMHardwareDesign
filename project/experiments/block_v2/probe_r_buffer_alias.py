"""Read-only native SAT diagnosis after exact Liberty identity-buffer aliases.

No physical file changes. No arithmetic/state cutpoints. Every original flop,
signal port and nonbuffer instance remains, and the unmodified strict native
receiver must match every original state boundary. This is diagnostic only.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
from native_cell_gate import group,attribute
from native_formal import inspect


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def alias_view(source,lib,target):
    text=source.read_text();library=lib.read_text();models={};rows=[];parts=[];last=0;position=0;retained={}
    pattern=re.compile(r'(?m)^ (BUF_X\d+|CLKBUF_X\d+) (\S+)\s+\(([\s\S]*?)\);\n')
    for match in pattern.finditer(text):
        master,name,body=match.groups()
        if master not in models:
            model=group(library,'cell',master)
            assert not re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',model)
            pins=re.findall(r'\bpin\s*\(\s*"?([A-Za-z_][A-Za-z_0-9]*)"?\s*\)',model)
            assert set(pins)=={'A','Z'} and len(pins)==2
            a=group(model,'pin','A');z=group(model,'pin','Z')
            assert attribute(a,'direction')=='input' and attribute(a,'function',False) is None
            assert attribute(z,'direction')=='output' and attribute(z,'function')=='A'
            models[master]=dict(A='input',Z='output',function='Z=A',liberty_model_sha256=hashlib.sha256(model.encode()).hexdigest())
        ports=re.findall(r'\.([A-Za-z0-9_]+)\(([^()]*)\)',body)
        # CTS creates real capacitive dummy loads with intentionally unbound Z.
        # Keep those instances byte for byte, including the actual A loading.
        if len(ports)==1 and ports[0][0]=='A':
            assert master.startswith('CLKBUF_') and re.fullmatch(r'clkload\d+',name),(master,name,ports)
            retained[name]=dict(master=master,ports=ports)
            continue
        assert len(ports)==2 and {k for k,v in ports}=={'A','Z'}
        assert not re.sub(r'\.([A-Za-z0-9_]+)\(([^()]*)\)','',body).strip(' ,\t\r\n')
        ports={k:v.strip() for k,v in ports};assert all(ports.values())
        prefix=text[last:match.start()];parts.append(prefix);position+=len(prefix)
        replacement=' assign '+ports['Z']+' = '+ports['A']+' ;\n'
        rows.append(dict(master=master,instance=name,ports=ports,source_offset=match.start(),
                         output_offset=position,original=match.group(0),replacement=replacement))
        parts.append(replacement);position+=len(replacement);last=match.end()
    assert rows,'No identity buffer instances matched'
    parts.append(text[last:]);result=''.join(parts)
    inverse=[];last=0
    for row in rows:
        start=row['output_offset'];end=start+len(row['replacement'])
        assert result[start:end]==row['replacement']
        inverse.extend((result[last:start],row['original']));last=end
    inverse.append(result[last:]);assert ''.join(inverse)==text
    target.write_text(result)
    ledger=target.with_suffix('.aliases.json.gz')
    with gzip.open(ledger,'wt',encoding='utf-8') as stream:json.dump(rows,stream)
    counts={}
    for row in rows:counts[row['master']]=counts.get(row['master'],0)+1
    proof=dict(passed=True,input_sha256=sha(source),output_sha256=sha(target),liberty_sha256=sha(lib),
        original=str(source),output=str(target),ledger=str(ledger),ledger_sha256=sha(ledger),
        identity_models=models,buffer_counts=counts,buffer_count=len(rows),exact_inverse_reconstruction=True,
        intentionally_unconnected_clock_loads_retained=retained,
        scope='Only audited stateless Z=A cell instances replaced by Verilog aliases; every other source byte and all sequential instances retained')
    target.with_suffix('.proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    report=dict(passed=False,diagnostic_only=True,native_leaf_accepted=False,controls={},started_unix=time.time(),
        binary_sha256=sha(binary),liberty_sha256=sha(lib),strict_receiver_unchanged=True)
    def compare(folder,before,after,timeout):
        folder.mkdir();a=folder/'before.v';b=folder/'after.v'
        views=[alias_view(before,lib,a),alias_view(after,lib,b)]
        log=folder/'kepler.log';config=folder/'config.yml'
        config.write_text('format: verilog\ninput_paths:\n  - '+str(a)+'\n  - '+str(b)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(log)+'\n')
        with (folder/'command.log').open('w') as stream:
            result=subprocess.run([str(binary),'--config',str(config)],cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        text=log.read_text();row=inspect(text)
        row.update(returncode=result.returncode,views=views,log_sha256=sha(log),
            explicit_difference=('Found difference' in text or bool(re.search(r'SAT solver finished: SAT\s*$',text,re.M))))
        return row
    try:
        controls=args.out/'controls';controls.mkdir()
        before='module formal_probe(input clk,d,output q); wire di;\n BUF_X1 b0 (.A(d), .Z(di));\n DFF_X1 u0(.CK(clk),.D(di),.Q(q)); endmodule\n'
        variants=dict(positive='module formal_probe(input clk,d,output q); wire di;\n BUF_X2 b0 (.A(d), .Z(di));\n DFF_X2 u0(.CK(clk),.D(di),.Q(q)); endmodule\n',
            data=before.replace('.D(di)',".D(1'b0)"),clock=before.replace('.CK(clk)','.CK(d)'),
            output=before.replace('.Q(q)', '.Q(qi)').replace('wire di;','wire di,qi;').replace('endmodule','INV_X1 inv(.A(qi),.ZN(q)); endmodule'))
        for name,text in variants.items():
            a=controls/(name+'-before.v');a.write_text(before)
            b=controls/(name+'-after.v');b.write_text(text)
            row=compare(controls/name,a,b,60);report['controls'][name]=row
            if name=='positive':assert row['returncode']==0 and row['passed']
            else:assert row['explicit_difference'] and not row['passed']
        config=args.source/'flow/objects/nangate45/bv1_block_v1_r/base/4_rsz_lec_test.yml'
        baseline=args.source/'flow/logs/nangate45/bv1_block_v1_r/base/4_rsz_lec_check.log'
        paths=[Path(x) for x in re.findall(r'^  - (.+)$',config.read_text(),re.M)]
        assert len(paths)==2 and {p.name for p in paths}=={'4_before_rsz_lec.v','4_after_rsz_lec.v'}
        original={str(p):sha(p) for p in [config,*paths]};report['source_inputs']=original
        expected=inspect(baseline.read_text())['counts'];report['expected_original_boundaries']=expected
        assert expected['common inputs']==expected['PIs0']==expected['PIs1']==292950
        assert expected['common outputs']==expected['POs0']==expected['POs1']==292936
        assert all(expected[k]==0 for k in ('diff0 inputs','diff1 inputs','diff0 outputs','diff1 outputs'))
        row=compare(args.out/'actual-r',*paths,1800);report['actual_r']=row
        assert row['returncode']==0 and row['passed'] and row['counts']==expected
        assert original=={str(p):sha(p) for p in [config,*paths]}
        report.update(passed=True,original_files_unchanged=True,
            scope='Read-only exact buffer-alias runtime diagnosis; strict native full-boundary proof and real D/CK/output controls, no physical qualification')
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        report['ended_unix']=time.time();(args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
