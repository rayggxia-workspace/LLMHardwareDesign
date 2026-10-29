"""All-input identity for the actual V normalization merge/RNE source."""
import json


def prove(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    rtl=root/'project/rtl/block_library_v1/block_v1_v.sv'
    text=rtl.read_text();functions=[]
    for name in ('add128_grouped','norm_merge_rne'):
        start=text.index(' function automatic signed [127:0] '+name+';')
        end=text.index(' endfunction',start)+len(' endfunction')
        functions.append(text[start:end])
    model='module proof(input signed [64:0] high,low,output ok,bad_ok);\n'
    model+='\n'.join(functions)+'\n'
    model+='''wire signed [127:0] high128={{63{high[64]}},high};
wire signed [127:0] low128={{63{low[64]}},low};
wire signed [127:0] merged=(high128<<<32)+low128;
wire signed [127:0] q=merged>>>32;
wire increment=(merged[31:0]>32'h80000000)||
               ((merged[31:0]==32'h80000000)&&q[0]);
wire signed [127:0] reference=q+increment;
wire signed [127:0] actual=norm_merge_rne(high,low);
assign ok=actual==reference;
assign bad_ok=(actual^128'h40000)==reference;
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
    report=dict(passed=True,rtl_sha256=file_sha(rtl),proof_model_sha256=file_sha(out/'proof.sv'),
        actual_source_functions_extracted=True,unconstrained_input_bits=130,
        full128bit_signed_merge_rne32_equivalent=True,
        actual_single_bit_negative_rejected=True,latency_or_register_change=False,
        qualified_final_timing=False,
        scope='All two-S65 inputs, full S128 result. Independent arithmetic reference; no range assumptions, saturation or cycle changes. Macro numerical, mapping and fresh final physical gates remain separate.')
    (out/'revision300-v-norm-proof.json').write_text(json.dumps(report,indent=2)+'\n')
