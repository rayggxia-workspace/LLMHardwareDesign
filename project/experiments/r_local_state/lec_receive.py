"""Receive positive native LEC evidence, including every state boundary.

Default ORFS grep absence alone is insufficient. Require explicit UNSAT,
IDENTICAL and complete positive input/output correspondence. Controls mutate
actual data, clock and output connections of the real Liberty DFF model.
"""
import json
from pathlib import Path
import re


def inspect(text):
    # Kepler emits an early input summary and a second one during explicit
    # normalization. Receive exactly the normalization block, not both dumps.
    blocks=text.split('normalizeInputs: starting')
    normalized=blocks[-1]if len(blocks)==2 else ''
    def count(pattern):
        matches=re.findall(pattern+r'\s*$',normalized,re.M)
        return int(matches[0])if len(matches)==1 else None
    counts={kind:count(r'size of '+kind+r': (\d+)')for kind in
        ['common inputs','diff0 inputs','diff1 inputs','common outputs','diff0 outputs','diff1 outputs']}
    for kind in ['PIs','POs']:
        for design in [0,1]:counts[kind+str(design)]=count('size of '+kind+' in circuit '+str(design)+r': (\d+)')
    checks=dict(explicit_unsat=len(re.findall(r'SAT solver finished: UNSAT\s*$',text,re.M))==1,
        explicit_identical=len(re.findall(r'Circuits are IDENTICAL\s*$',text,re.M))==1,
        no_difference='Found difference'not in text,
        one_normalization_block=len(blocks)==2 and normalized.count('normalizeOutputs: starting')==1,
        complete_counts=all(v is not None for v in counts.values()))
    checks['positive_inputs']=counts['common inputs']is not None and counts['common inputs']>0
    checks['positive_outputs']=counts['common outputs']is not None and counts['common outputs']>0
    checks['no_unmatched_boundaries']=all(counts[k]==0 for k in ['diff0 inputs','diff1 inputs','diff0 outputs','diff1 outputs'])
    checks['all_inputs_matched']=counts['common inputs']==counts['PIs0']==counts['PIs1']
    checks['all_outputs_matched']=counts['common outputs']==counts['POs0']==counts['POs1']
    return dict(passed=all(checks.values()),checks=checks,counts=counts,
        scope='Native LEC combinational/state-boundary correspondence; reset/initial-state semantics and full mapped behavioral regression remain separate')


def fixture(root,out,run):
    import hashlib
    file_sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    assert binary.is_file()
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    before='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n'
    variants=dict(positive='module formal_probe(input clk,d,output q); wire di; BUF_X2 b0(.A(d),.Z(di)); DFF_X2 u0(.CK(clk),.D(di),.Q(q)); endmodule\n',
        data='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(1\'b0),.Q(q)); endmodule\n',
        clock='module formal_probe(input clk,d,output q); DFF_X1 u0(.CK(d),.D(d),.Q(q)); endmodule\n',
        output='module formal_probe(input clk,d,output q); wire qi; DFF_X1 u0(.CK(clk),.D(d),.Q(qi)); INV_X1 i0(.A(qi),.ZN(q)); endmodule\n')
    results={}
    for name,after in variants.items():
        folder=out/name;folder.mkdir()
        (folder/'before.v').write_text(before);(folder/'after.v').write_text(after)
        config='format: verilog\ninput_paths:\n  - '+str(folder/'before.v')+'\n  - '+str(folder/'after.v')+'\n'
        config+='liberty_files:\n - '+str(lib)+'\nlog_file: '+str(folder/'kepler.log')+'\n'
        (folder/'config.yml').write_text(config)
        # Kepler may use a nonzero code for a real difference. Preserve its
        # exact return code; the receiver still requires positive evidence.
        import subprocess
        with(folder/'command.log').open('w')as stream:
            result=subprocess.run([str(binary),'--config',str(folder/'config.yml')],stdout=stream,stderr=subprocess.STDOUT)
        path=folder/'kepler.log';assert path.is_file()
        text=path.read_text();received=inspect(text);received['returncode']=result.returncode
        if name=='positive':assert result.returncode==0 and received['passed'],received
        else:
            assert not received['passed']
            assert 'Found difference'in text or re.search(r'SAT solver finished: SAT\s*$',text,re.M),text[-1500:]
        results[name]=received
    positive=(out/'positive/kepler.log').read_text();faults={}
    for name,modified in [
        ('missing-unsat',positive.replace('SAT solver finished: UNSAT','SAT solver finished: UNKNOWN')),
        ('missing-identical',positive.replace('Circuits are IDENTICAL','No verdict')),
        ('zero-outputs',re.sub(r'size of common outputs: \d+','size of common outputs: 0',positive)),
        ('unmatched-input',positive.replace('size of diff1 inputs: 0','size of diff1 inputs: 1')),
        ('missing-normalization',positive.replace('normalizeInputs: starting','normalization absent'))]:
        assert modified!=positive
        faults[name]=inspect(modified);assert not faults[name]['passed']
    record=dict(schema='block-v1-native-lec-control/1',passed=True,results=results,report_faults=faults,
        binary=str(binary),binary_sha256=file_sha(binary),liberty_sha256=file_sha(lib),
        scope='Real buffered/resized DFF positive and actual D/CK/output mutations; no completed block claim')
    (out/'native-formal-control.json').write_text(json.dumps(record,indent=2)+'\n')

