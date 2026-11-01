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
    from io_slots import file_sha
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


def receive(source,receipt,results,top,prep,logic_context=None,constant_functions=False):
    from io_slots import file_sha
    base=source.parents[2]
    control=base/'block-v1-20261027-073/tasks/native-formal-control'
    accepted=json.loads((control/'receipt.json').read_text());assert accepted['passed']is True
    path=control/'native-formal-control.json';assert file_sha(path)==accepted['outputs'][path.name]
    positive=json.loads(path.read_text());assert positive['passed']is True
    assert file_sha(Path(positive['binary']))==positive['binary_sha256']
    log=source/'flow/logs/nangate45'/results.parent.name/'base/6_final_lec_check.log'
    config=source/'flow/objects/nangate45'/results.parent.name/'base/6_final_lec_test.yml'
    paths=[log,config,results/'1_synth_lec.v',results/'6_final_lec.v',results/'6_final.v',results/'1_2_yosys.v']
    for path in paths:assert file_sha(path)==receipt['outputs'][str(path.relative_to(source))]
    text=config.read_text();inputs=re.findall(r'^  - (.+)$',text,re.M)
    assert inputs==[str(results/'1_synth_lec.v'),str(results/'6_final_lec.v')]
    lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    assert re.findall(r'^ - (.+)$',text,re.M)==[lib]
    assert re.findall(r'^log_file: (.+)$',text,re.M)==[str(log)]
    assert file_sha(results/'6_final.v')==file_sha(results/'6_final_lec.v'),'LEC view differs from actual final functional netlist'
    bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    original=prep/'inputs'/top/(top+'.v')
    assert file_sha(original)==bound['outputs'][str(original.relative_to(prep))]
    assert file_sha(results/'1_2_yosys.v')==file_sha(original)
    received=inspect(log.read_text());original_received=received
    projection=None
    physical_view=None
    constant_control=None
    if constant_functions:
        assert top=='shared109' and logic_context is not None
        from native_c8_qualification import replay_qualification
        constant_control=replay_qualification(logic_context[0],base)
        assert file_sha(Path(positive['binary']))==constant_control['binary_sha256']
        assert file_sha(Path(lib))==constant_control['library_sha256']
    if logic_context is not None:
        root,out,run=logic_context
        fixture=base/'block-v1-20261027-110/tasks/native-antenna-fixture'
        bound=json.loads((fixture/'receipt.json').read_text());assert bound['passed']is True
        control_path=fixture/'native-antenna-fixture.json';assert file_sha(control_path)==bound['outputs'][control_path.name]
        projection_control=json.loads(control_path.read_text());assert projection_control['passed']is True and projection_control['formal']['passed']is True
        assert len(projection_control['projection_faults'])==4
        from native_signal_view import export as export_physical
        full_functional,physical_view=export_physical(root,out,run,source,receipt,results,top,Path(lib))
        from native_logic_projection import export
        before,before_proof=export(root,out,run,results/'1_synth_lec.v',Path(lib),top,'formal-before',constant_functions=constant_functions)
        after,after_proof=export(root,out,run,full_functional,Path(lib),top,'formal-after',constant_functions=constant_functions)
        assert before_proof['removed_count']==0 and after_proof['removed_count']>0
        if constant_functions:
            assert all(p['constant_functions']['removed_count']>0 and p['constant_functions']['exact_inverse_reconstruction']
                       and p['used_model_audit']['passed'] for p in [before_proof,after_proof])
        config_text='format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+'\n'
        strict_log=out/'strict-projected-kepler.log';strict_config=out/'strict-projected-kepler.yml'
        config_text+='liberty_files:\n - '+lib+'\nlog_file: '+str(strict_log)+'\n'
        strict_config.write_text(config_text)
        run([str(Path(positive['binary'])),'--config',str(strict_config)],'strict-projected-formal.log')
        received=inspect(strict_log.read_text())
        projection=dict(before=before_proof,after=after_proof,strict_log_sha256=file_sha(strict_log),
            strict_config_sha256=file_sha(strict_config),control_receipt_sha256=file_sha(fixture/'receipt.json'))
        if constant_control is not None:projection['constant_control']=constant_control
    assert received['passed'],'Final native LEC lacks complete positive evidence'
    return dict(**received,log_sha256=file_sha(log),config_sha256=file_sha(config),
        full_final_netlist_sha256=file_sha(results/'6_final.v'),control_receipt_sha256=file_sha(control/'receipt.json'),
        original_full_view_received=original_received,boolean_projection=projection,
        physical_functional_view=physical_view)
