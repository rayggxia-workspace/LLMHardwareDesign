"""Read-only bounded compact runtime comparison; never produces leaf acceptance.

The production strict receiver is unchanged. Its rejection of compact's missing
explicit output-difference fields is recorded, rather than hidden or waived.
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
from native_formal import inspect


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    report=dict(passed=False,diagnostic_only=True,native_leaf_accepted=False,
        strict_receiver_unchanged=True,started_unix=time.time(),controls={},
        binary_sha256=sha(binary),liberty_sha256=sha(lib))

    def compare(folder,before,after,timeout):
        folder.mkdir()
        command=[str(binary),'-verilog',str(before),str(after),str(lib),'--compact','--report-skipped-pos']
        with (folder/'command.log').open('w') as stream:
            result=subprocess.run(command,cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        logs=list(folder.glob('miter_log_*.txt'));assert len(logs)==1,logs
        data=logs[0].read_text();console=(folder/'command.log').read_text()
        assert 'Compact mode: enabled' in console
        row=dict(returncode=result.returncode,strict_production_receiver=inspect(data),
            explicit_unsat=len(re.findall(r'SAT solver finished: UNSAT\s*$',data,re.M))==1,
            explicit_identical=len(re.findall(r'Circuits are IDENTICAL\s*$',data,re.M))==1,
            explicit_difference=('Found difference' in data or bool(re.search(r'SAT solver finished: SAT\s*$',data,re.M))),
            command=command,log_path=str(logs[0]),log_sha256=sha(logs[0]))
        # Observations only. Do not invent absent diff-output counters.
        row['observed_counts']={key:[int(x) for x in re.findall(r'size of '+key+r': (\d+)\s*$',data,re.M)]
            for key in ('common inputs','diff0 inputs','diff1 inputs','common outputs',
                        'diff0 outputs','diff1 outputs','PIs in circuit 0','PIs in circuit 1',
                        'POs in circuit 0','POs in circuit 1')}
        assert not row['strict_production_receiver']['passed'],'Unexpected compact format: reassess separately'
        return row

    try:
        controls=args.out/'controls';controls.mkdir()
        before='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n'
        variants=dict(positive='module formal_probe(input clk,d,output q); wire di; BUF_X2 b0(.A(d),.Z(di)); DFF_X2 u0(.CK(clk),.D(di),.Q(q)); endmodule\n',
            data="module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(1'b0),.Q(q)); endmodule\n",
            clock='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(d),.D(d),.Q(q)); endmodule\n',
            output='module formal_probe(input clk,d,output q); wire qi; DFF_X1 u0(.CK(clk),.D(d),.Q(qi)); INV_X1 i0(.A(qi),.ZN(q)); endmodule\n')
        for name,after in variants.items():
            b=controls/(name+'-before.v');b.write_text(before)
            a=controls/(name+'-after.v');a.write_text(after)
            row=compare(controls/name,b,a,60);report['controls'][name]=row
            if name=='positive':assert row['returncode']==0 and row['explicit_unsat'] and row['explicit_identical']
            else:assert row['explicit_difference'] and not row['explicit_unsat']
        config=args.source/'flow/objects/nangate45/bv1_block_v1_r/base/4_rsz_lec_test.yml'
        baseline=args.source/'flow/logs/nangate45/bv1_block_v1_r/base/4_rsz_lec_check.log'
        paths=[Path(x) for x in re.findall(r'^  - (.+)$',config.read_text(),re.M)]
        assert len(paths)==2 and {p.name for p in paths}=={'4_before_rsz_lec.v','4_after_rsz_lec.v'}
        original={str(p):sha(p) for p in [config,*paths]};report['source_inputs']=original
        expected=inspect(baseline.read_text())['counts'];report['original_normalized_counts']=expected
        assert expected['common inputs']==expected['PIs0']==expected['PIs1']==292950
        assert expected['common outputs']==expected['POs0']==expected['POs1']==292936
        assert all(expected[k]==0 for k in ('diff0 inputs','diff1 inputs','diff0 outputs','diff1 outputs'))
        actual=compare(args.out/'actual-r',*paths,1800);report['actual_r']=actual
        assert actual['returncode']==0 and actual['explicit_unsat'] and actual['explicit_identical']
        assert not actual['explicit_difference']
        assert original=={str(p):sha(p) for p in [config,*paths]}
        report.update(diagnostic_runtime_completed=True,original_files_unchanged=True,
            scope='Compact runtime only; strict production receiver still rejects missing explicit fields. No final formal or physical qualification transferred.')
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        report['ended_unix']=time.time()
        (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
