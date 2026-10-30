"""All-bit SAT proof of the actual grouped addition and RNE source functions."""
import json


def prove(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    rtl=root/'project/rtl/block_library_v1/block_v1_v.sv'
    text=rtl.read_text();functions=[]
    for name in ('add128_grouped','rne'):
        start=text.index(' function automatic signed [127:0] '+name+';')
        end=text.index(' endfunction',start)+len(' endfunction')
        functions.append(text[start:end])
    start=text.index(' function automatic point_rne_increment;')
    end=text.index(' endfunction',start)+len(' endfunction')
    functions.append(text[start:end])
    model='module proof(input [127:0] a,b,input [6:0] sh,input carry_in,output ok,bad_ok);\n'
    model+='\n'.join(functions)+'\n'
    model+='''wire signed [127:0] q=$signed(a)>>>sh;
wire [127:0] remn=a&({128{1'b1}}>>(128-sh));
wire [127:0] half=128'd1<<(sh-1);
wire signed [127:0] reference=sh==0?$signed(a):q+((remn>half)||((remn==half)&&q[0]));
wire [127:0] actual=add128_grouped(a,b,carry_in);
wire signed [127:0] point_result=add128_grouped(q,{127'b0,point_rne_increment(a,sh)},1'b0);
assign ok=(actual==(a+b+carry_in))&&(add128_grouped(a,~b,1'b1)==(a-b))&&(rne(a,sh)==reference)&&(point_result==reference);
assign bad_ok=((actual^128'h40000)==(a+b+carry_in));
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
        actual_source_functions_extracted=True,unconstrained_input_bits=264,
        full128bit_add_sub_all_values_and_all128shifts_rne_equivalent=True,
        actual_single_bit_negative_rejected=True,latency_or_register_change=True,
        point_registered_quotient_and_increment_full128bit_equivalent=True,
        qualified_final_timing=False,
        scope='Combinational all-bit equivalence only. New RTL still requires numerical/port regression, mapping and fresh physical/final acceptance; no old physical qualification transfers.')
    (out/'revision300-v-carry-proof.json').write_text(json.dumps(report,indent=2)+'\n')
