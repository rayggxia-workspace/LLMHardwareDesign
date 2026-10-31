"""Bounded read-only alternate SAT solver diagnosis, never leaf acceptance."""
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
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--solver',choices=['kissat','glucose'],default='glucose');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    report=dict(passed=False,diagnostic_only=True,native_leaf_accepted=False,
        started_unix=time.time(),solver=a.solver,compact_mode=False,
        binary_sha256=sha(binary),liberty_sha256=sha(lib),controls={})
    def compare(folder,before,after,timeout):
        folder.mkdir()
        config=folder/'config.yml';log=folder/'kepler.log'
        config.write_text('format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+
            '\nliberty_files:\n - '+str(lib)+'\nsolver: '+a.solver+'\nlog_file: '+str(log)+'\n')
        command=[str(binary),'--config',str(config)]
        with (folder/'command.log').open('w') as stream:
            result=subprocess.run(command,cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        console=(folder/'command.log').read_text()
        assert 'Solver: '+a.solver.upper() in console and 'Compact mode: disabled' in console
        row=inspect(log.read_text())
        row.update(returncode=result.returncode,command=command,log_path=str(log),log_sha256=sha(log))
        return row
    try:
        controls=a.out/'controls';controls.mkdir()
        before='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n'
        variants=dict(positive='module formal_probe(input clk,d,output q); wire di; BUF_X2 b0(.A(d),.Z(di)); DFF_X2 u0(.CK(clk),.D(di),.Q(q)); endmodule\n',
            data="module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(1'b0),.Q(q)); endmodule\n",
            clock='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(d),.D(d),.Q(q)); endmodule\n',
            output='module formal_probe(input clk,d,output q); wire qi; DFF_X1 u0(.CK(clk),.D(d),.Q(qi)); INV_X1 i0(.A(qi),.ZN(q)); endmodule\n')
        for name,after in variants.items():
            b=controls/(name+'-before.v');b.write_text(before)
            c=controls/(name+'-after.v');c.write_text(after)
            row=compare(controls/name,b,c,60);report['controls'][name]=row
            text=Path(row['log_path']).read_text()
            if name=='positive':assert row['returncode']==0 and row['passed'],row
            else:
                assert not row['passed']
                assert 'Found difference' in text or re.search(r'SAT solver finished: SAT\s*$',text,re.M)
        native=a.source/'flow'
        config=native/'objects/nangate45/bv1_block_v1_r/base/4_rsz_lec_test.yml'
        baseline=native/'logs/nangate45/bv1_block_v1_r/base/4_rsz_lec_check.log'
        paths=[Path(x) for x in re.findall(r'^  - (.+)$',config.read_text(),re.M)]
        assert len(paths)==2 and all(p.parent.name=='base' and p.name in ('4_before_rsz_lec.v','4_after_rsz_lec.v') for p in paths)
        original={str(f):sha(f) for f in [config,*paths]}
        report['source_inputs']=original
        expected=inspect(baseline.read_text())['counts']
        assert expected['common inputs']==expected['PIs0']==expected['PIs1']==292950
        assert expected['common outputs']==expected['POs0']==expected['POs1']==292936
        assert all(expected[k]==0 for k in ('diff0 inputs','diff1 inputs','diff0 outputs','diff1 outputs'))
        report['expected_all_original_boundaries']=expected
        actual=compare(a.out/'actual-r',*paths,1800)
        report['actual_r']=actual
        assert actual['returncode']==0 and actual['passed'],actual
        assert actual['counts']==expected,'Alternate solver changed observed boundary coverage'
        assert original=={str(f):sha(f) for f in [config,*paths]}
        report.update(passed=True,original_files_unchanged=True,
            scope='All original CTS state/combinational boundary counts and strict UNSAT/IDENTICAL plus real D/CK/output controls; diagnostic only, no physical/function/DRC or final-leaf acceptance')
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        report['ended_unix']=time.time()
        (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
