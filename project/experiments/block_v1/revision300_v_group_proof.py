"""All-input proof of the actual U130 group subtract and its selection guard."""
import json


def prove(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    rtl=root/'project/rtl/block_library_v1/block_v1_v_group.sv'
    text=rtl.read_text()
    start=text.index(' function automatic [130:0] subtract130_grouped;')
    end=text.index(' endfunction',start)+len(' endfunction')
    function=text[start:end]
    model='module proof(input [129:0] a,b,output ok,bad_ok);\n'+function+'\n'
    model+='''wire [130:0] actual=subtract130_grouped(a,b);
wire [130:0] reference={1'b0,a}+{1'b0,~b}+131'd1;
wire [129:0] selected=actual[130]?actual[129:0]:a;
wire [129:0] expected=(a>=b)?a-b:a;
assign ok=(actual==reference)&&(actual[130]==(a>=b))&&(selected==expected);
assign bad_ok=((actual^131'h40000)==reference);
endmodule
'''
    (out/'proof.sv').write_text(model)
    prefix='read_verilog -sv proof.sv\nprep -top proof\nflatten\nopt\n'
    for label,command in [('positive','sat -verify -prove ok 1 -show-inputs -show-outputs'),
                          ('single-bit-negative','sat -prove bad_ok 1 -show-inputs -show-outputs')]:
        (out/(label+'.ys')).write_text(prefix+command+'\n')
        run(['yosys','-s',out/(label+'.ys')],label+'.log',cwd=out)
    assert 'no model found: SUCCESS' in (out/'positive.log').read_text()
    assert 'model found: FAIL' in (out/'single-bit-negative.log').read_text()
    record=dict(passed=True,rtl_sha256=file_sha(rtl),
        proof_model_sha256=file_sha(out/'proof.sv'),actual_source_function_extracted=True,
        unconstrained_input_bits=260,full130bit_difference_and_no_borrow_and_selection_equivalent=True,
        actual_single_bit_negative_rejected=True,latency_or_register_change=False,
        qualified_final_timing=False,
        scope='Combinational all-input proof only. Full macro numerical/port tests, fresh mapping, physical and final gates remain required.')
    (out/'revision300-v-group-proof.json').write_text(json.dumps(record,indent=2)+'\n')
