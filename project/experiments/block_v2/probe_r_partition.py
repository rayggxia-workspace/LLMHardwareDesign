"""Bounded read-only experiment on a subset of explicit state-output cones.

Every DFF Q/QN is an independent input, as in the native combinational-state
boundary check. D and CK are outputs. All primary ports remain. A diagnostic
subset is NOT a completed proof: native_leaf_accepted is always false.
"""
import argparse
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

TAG='issue143_explicit_state'
CELL=re.compile(r'(?m)^ (DFF_X\d+) (\S+)\s+\(([\s\S]*?)\);\n')


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def inventory(text,lib):
    rows={};models={};library=lib.read_text()
    for m in CELL.finditer(text):
        master,name,body=m.groups();assert name not in rows
        ports=re.findall(r'\.([A-Za-z0-9_]+)\(([^()]*)\)',body)
        assert len(ports)==len({k for k,v in ports})
        assert not re.sub(r'\.([A-Za-z0-9_]+)\(([^()]*)\)','',body).strip(' ,\t\r\n')
        ports={k:v.strip() for k,v in ports}
        assert {'D','CK'}<=set(ports)<={'D','CK','Q','QN'} and ports['D'] and ports['CK']
        if master not in models:
            model=group(library,'cell',master)
            assert len(re.findall(r'\bff\s*\(',model))==1
            assert re.search(r'\bnext_state\s*:\s*"D"',model)
            assert re.search(r'\bclocked_on\s*:\s*"CK"',model)
            names=re.findall(r'\bpin\s*\(\s*"?([A-Za-z_][A-Za-z_0-9]*)"?\s*\)',model)
            assert set(names)=={'D','CK','Q','QN'} and len(names)==4
            assert {k:attribute(group(model,'pin',k),'direction') for k in names}==dict(D='input',CK='input',Q='output',QN='output')
            models[master]=hashlib.sha256(model.encode()).hexdigest()
        rows[name]=dict(master=master,ports=ports,start=m.start(),end=m.end(),original=m.group(0))
    assert rows and TAG not in text
    return rows,models


def explicit_view(source,lib,target,names,selected):
    text=source.read_text();rows,models=inventory(text,lib)
    assert set(rows)==set(names) and len(selected)>0 and set(selected)<=set(names)
    state={name:i for i,name in enumerate(names)};outputs={name:i for i,name in enumerate(selected)}
    header=re.search(r'\bmodule (\S+)\s*\(([\s\S]*?)\);',text)
    assert header and not re.search(r'\b(input|output|inout)\b',header.group(2))
    replacement='module '+header.group(1)+' ('+header.group(2)+', '+TAG+'_in, '+TAG+'_out);\n'
    replacement+=' input ['+str(2*len(names)-1)+':0] '+TAG+'_in;\n'
    replacement+=' output ['+str(2*len(selected)-1)+':0] '+TAG+'_out;\n'
    edits=[dict(start=header.start(),end=header.end(),original=header.group(0),replacement=replacement)]
    for name,row in rows.items():
        lines=[];ports=row['ports'];index=state[name]
        for offset,pin in enumerate(('Q','QN')):
            if ports.get(pin):lines.append(' assign '+ports[pin]+' = '+TAG+'_in['+str(2*index+offset)+'] ;\n')
        if name in outputs:
            for offset,pin in enumerate(('D','CK')):
                lines.append(' assign '+TAG+'_out['+str(2*outputs[name]+offset)+'] = '+ports[pin]+' ;\n')
        edits.append(dict(start=row['start'],end=row['end'],original=row['original'],replacement=''.join(lines)))
    edits.sort(key=lambda x:x['start']);parts=[];last=0;position=0
    for row in edits:
        assert row['start']>=last and text[row['start']:row['end']]==row['original']
        prefix=text[last:row['start']];parts.append(prefix);position+=len(prefix)
        row['output_offset']=position;parts.append(row['replacement']);position+=len(row['replacement']);last=row['end']
    parts.append(text[last:]);result=''.join(parts);inverse=[];last=0
    for row in edits:
        start=row['output_offset'];end=start+len(row['replacement']);assert result[start:end]==row['replacement']
        inverse.extend((result[last:start],row['original']));last=end
    inverse.append(result[last:]);assert ''.join(inverse)==text
    assert not CELL.search(result)
    target.write_text(result)
    report=dict(passed=True,input_sha256=sha(source),output_sha256=sha(target),liberty_sha256=sha(lib),models=models,
        state_instances=len(names),state_input_bits=2*len(names),selected_instances=len(selected),
        selected_state_output_bits=2*len(selected),exact_inverse_reconstruction=True,
        ordered_all_state_names_sha256=hashlib.sha256(json.dumps(names).encode()).hexdigest(),
        ordered_selected_names=selected,scope='Exact explicit Q/QN input and D/CK output boundary conversion; subset is diagnostic only')
    target.with_suffix('.proof.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    report=dict(passed=False,diagnostic_only=True,native_leaf_accepted=False,controls={},started_unix=time.time(),strict_receiver_unchanged=True)
    def compare(folder,before,after,limit,timeout):
        folder.mkdir();a=folder/'before.v';b=folder/'after.v'
        left,_=inventory(before.read_text(),lib);right,_=inventory(after.read_text(),lib)
        assert set(left)==set(right);names=sorted(left);selected=names[:limit]
        views=[explicit_view(before,lib,a,names,selected),explicit_view(after,lib,b,names,selected)]
        config=folder/'config.yml';log=folder/'kepler.log'
        config.write_text('format: verilog\ninput_paths:\n  - '+str(a)+'\n  - '+str(b)+'\nliberty_files:\n - '+str(lib)+'\nlog_file: '+str(log)+'\n')
        with (folder/'command.log').open('w') as stream:
            result=subprocess.run([str(binary),'--config',str(config)],cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        text=log.read_text();row=inspect(text)
        row.update(returncode=result.returncode,views=views,log_sha256=sha(log),
            explicit_difference=('Found difference' in text or bool(re.search(r'SAT solver finished: SAT\s*$',text,re.M))))
        return row
    try:
        controls=args.out/'controls';controls.mkdir()
        before='module formal_probe(clk,d,q);\n input clk,d; output q; wire qi;\n DFF_X1 u0 (.CK(clk),.D(d),.Q(q));\nendmodule\n'
        variants=dict(positive=before.replace('DFF_X1','DFF_X2'),data=before.replace('.D(d)',".D(1'b0)"),
            clock=before.replace('.CK(clk)','.CK(d)'),output=before.replace('.Q(q)','.Q(qi)').replace('endmodule',' INV_X1 inv (.A(qi),.ZN(q));\nendmodule'))
        for name,text in variants.items():
            a=controls/(name+'-before.v');a.write_text(before);b=controls/(name+'-after.v');b.write_text(text)
            row=compare(controls/name,a,b,1,60);report['controls'][name]=row
            if name=='positive':assert row['returncode']==0 and row['passed']
            else:assert row['explicit_difference'] and not row['passed']
        config=args.source/'flow/objects/nangate45/bv1_block_v1_r/base/4_rsz_lec_test.yml'
        baseline=args.source/'flow/logs/nangate45/bv1_block_v1_r/base/4_rsz_lec_check.log'
        paths=[Path(x) for x in re.findall(r'^  - (.+)$',config.read_text(),re.M)]
        assert len(paths)==2 and {p.name for p in paths}=={'4_before_rsz_lec.v','4_after_rsz_lec.v'}
        original={str(p):sha(p) for p in [config,*paths]};report['source_inputs']=original
        expected=inspect(baseline.read_text())['counts'];assert expected['common inputs']==292950 and expected['common outputs']==292936
        row=compare(args.out/'actual-r',*paths,2048,600);report['actual_r_subset']=row
        assert row['returncode']==0 and row['passed']
        assert row['views'][0]['state_instances']==row['views'][1]['state_instances']==146402
        assert row['counts']['common inputs']==292950 and row['counts']['common outputs']==4228
        assert original=={str(p):sha(p) for p in [config,*paths]}
        report.update(passed=True,original_files_unchanged=True,
            scope='Diagnostic 4096 state D/CK outputs plus all 132 primary outputs only; all 292950 state/primary inputs retained. Not a full R proof or physical acceptance.')
    except Exception as error:
        report['error']=str(error);raise
    finally:
        report['ended_unix']=time.time();(args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
