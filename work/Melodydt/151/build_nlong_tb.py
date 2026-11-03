"""Build N-long literal golden TB from independent math; never run RTL locally."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from nlong_integer_reference import CASES, PATTERN, GAMMA, EXP, expectation, isqrt, rne


def literal(x):
    return ("-16'sd" + str(-x)) if x < 0 else "16'sd" + str(x)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    legacy = a.root / 'project/tb/block_connection_w4/block_w4_n_tb.sv'
    text = legacy.read_text(encoding='utf-8')
    body = text[text.index(' function automatic integer native_word_index'):]
    golden = [expectation(i) for i in range(len(CASES))]
    # Independent hand facts, not produced by the SV controller or its loop.
    assert rne(-4, 3) == 0 and rne(-12, 3) == -2 and rne(4, 3) == 0 and rne(12, 3) == 2
    for n in [0, 1, 2, 3, 4, 65535, 65536, 65537, (1 << 32) - 1, 1 << 32, 1 << 56]:
        r = isqrt(n)
        assert r * r <= n < (r + 1) * (r + 1)
    assert golden[8]['exp_common'] == sum(32768 << (16 * i) for i in range(8))
    assert golden[8]['output_common'] == sum(16 << (16 * i) for i in range(8))
    assert golden[9]['output_common'] == 0 and golden[9]['output_last'] == 16384 << 96
    assert golden[12]['output_last'] == 32767 and golden[12]['saturated'] is True
    table = a.root / 'project/rtl/block_v2/block_v2_n_exp.svh'
    parsed = {int(i): int(v) for i, v in re.findall(r"11'd(\d+):exp_lut=16'd(\d+);", table.read_text(encoding='utf-8'))}
    assert parsed == dict(enumerate(EXP)), 'math EXP versus source fingerprint comparison'
    head = ['`timescale 1ns/1ps', '// Independent periodic full-group input; literal math expected outputs. No DUT-derived oracle.', 'module block_w4_n_long_tb;']
    def scalar(name, width, values):
        head.append(' function automatic %s %s;input integer vec;begin case(vec)' % (width, name))
        head.extend('  %d:%s=%s;' % (i, name, value) for i, value in enumerate(values))
        head.append('  default:%s=0;endcase end endfunction' % name)
    scalar('n_count', '[15:0]', [str(c[2]) for c in CASES])
    scalar('n_mode', '[1:0]', [str(c[1]) for c in CASES])
    scalar('n_words', '[7:0]', [str(g['words']) for g in golden])
    scalar('n_epsilon', '[31:0]', [str(g['epsilon']) for g in golden])
    scalar('n_sat', '', ["1'b%d" % g['saturated'] for g in golden])
    head.append(' function automatic signed [15:0] raw_code;input integer vec,element;begin case(vec)')
    for i, (_, _, count, recipe, last) in enumerate(CASES):
        pat = PATTERN if recipe == 'pattern' else [0] * 8 if recipe == 'zero' else [-1024] * 8 if recipe == 'low' else [-4096,-4081,-2048,-1025,-1024,-17,-16,-15] if recipe == 'scores' else [-32768,-16385,-16384,-16383,-17,-16,-15,0]
        head.append('  %d:begin if(element==%d)raw_code=%s;else case(element%%8)' % (i, count - 1, literal(last)))
        head.extend('   %d:raw_code=%s;' % (j, literal(x)) for j, x in enumerate(pat))
        head.append("   default:raw_code=0;endcase end")
    head.append('  default:raw_code=0;endcase end endfunction')
    head.append(' function automatic signed [15:0] gain_code;input integer vec,element;begin if(vec==12)gain_code=-16\'sd32768;else case(element%8)')
    head.extend('  %d:gain_code=%s;' % (j, literal(x)) for j, x in enumerate(GAMMA))
    head.append('  default:gain_code=0;endcase end endfunction')
    for name, code in [('n_raw', 'raw_code'), ('n_gamma', 'gain_code')]:
        head.append(' function automatic [127:0] %s;input integer vec,word;integer lane;begin %s=0;for(lane=0;lane<8;lane=lane+1)if(word*8+lane<n_count(vec))%s[16*lane+:16]=%s(vec,word*8+lane);end endfunction' % (name, name, name, code))
    for name, key in [('n_output', 'output'), ('n_expword', 'exp')]:
        head.append(' function automatic [127:0] %s;input integer vec,word;begin case(vec)' % name)
        head.extend("  %d:%s=word==n_words(vec)-1 ? 128'h%032x : 128'h%032x;" % (i, name, g[key + '_last'], g[key + '_common']) for i, g in enumerate(golden))
        head.append('  default:%s=0;endcase end endfunction' % name)
    scalar('case_name', '[8*100-1:0]', ['"' + c[0] + '"' for c in CASES])
    guard_ids = ['NL_GUARD_ZERO_COUNT','NL_GUARD_COUNT1025','NL_GUARD_MODE3','NL_GUARD_ZERO_EPSILON','NL_GUARD_RANGE_END','NL_GUARD_SRC_DST_OVERLAP','NL_GUARD_GAMMA_DST_OVERLAP','NL_GUARD_SRC_EXP_OVERLAP','NL_GUARD_SRC_GAMMA_OVERLAP','NL_GUARD_FULL1024_WRAP']
    scalar('guard_name', '[8*100-1:0]', ['"' + x + '"' for x in guard_ids])
    body = body.replace('block_w4_n_ctrl u_ctrl', 'block_w4_n_long_ctrl u_ctrl').replace('FAIL_W4_N', 'FAIL_NLONG').replace('PASS_W4_N', 'PASS_NLONG')
    body = body.replace('req_src_addr=100,req_gamma_addr=200,req_exp_addr=300,req_dst_addr=400', 'req_src_addr=0,req_gamma_addr=128,req_exp_addr=128,req_dst_addr=256')
    body = body.replace(' integer cycles=0', ' integer src_base=0,gamma_base=128,exp_base=128,dst_base=256;\n integer cycles=0')
    for old, new in [('expected_mem_addr=100+', 'expected_mem_addr=src_base+'), ('expected_mem_addr=200+', 'expected_mem_addr=gamma_base+'), ('expected_mem_addr=400+', 'expected_mem_addr=dst_base+'), ('?100:300', '?src_base:exp_base'), ('?300:400', '?exp_base:dst_base'), ('s_addr>=400?', 's_addr>=dst_base?'), ('s_addr-400', 's_addr-dst_base'), ('s_addr-300', 's_addr-exp_base'), ('store(100+k,raw);store(200+k,g);store(300+k,POISON);store(400+k,POISON);', 'store(src_base+k,raw);if(n_mode(ci)!=0)store(gamma_base+k,g);else store(exp_base+k,POISON);store(dst_base+k,POISON);'), ('req_src_addr=100;req_gamma_addr=200;req_exp_addr=300;req_dst_addr=400;', 'req_src_addr=src_base;req_gamma_addr=gamma_base;req_exp_addr=exp_base;req_dst_addr=dst_base;'), ('ram(400+k)', 'ram(dst_base+k)'), ('ram(300+k)', 'ram(exp_base+k)'), ('ma>=400', 'ma==dst_base+n_words(ci)-1'), ('1:req_count=258', '1:req_count=1025'), ('5:req_dst_addr=100', '5:req_dst_addr=src_base'), ('6:req_dst_addr=200', '6:req_dst_addr=gamma_base'), ('req_exp_addr=100;', 'req_exp_addr=src_base;'), ('7:begin req_mode=0;req_exp_addr=src_base;end endcase', "7:begin req_mode=0;req_exp_addr=src_base;end 8:req_gamma_addr=src_base;9:begin req_count=1024;req_src_addr=897;end endcase"), ('cycles>800000', 'cycles>2000000')]:
        if old not in body:
            raise AssertionError('legacy template anchor missing: ' + old)
        body = body.replace(old, new)
    initial = body.index(' integer i;\n initial begin')
    body = body[:initial]
    extra_ids = ['NL_NATIVE_COMMAND_HOLD','NL_NATIVE_RESPONSE_HOLD','NL_LAST_DST_ACK_GATE_1023','NL_HELPER_REQUEST_RESPONSE_HOLD','NL_REUSE_AFTER_ADMISSION_REJECTIONS','NL_NATIVE_ERROR_POISON_RESET_RECOVER','NL_MEMORY_READ_ERROR_POISON_RESET_RECOVER','NL_LATE_WRITE_ERROR_PARTIAL_PREFIX','NL_RESET_PENDING_EXP_WRITE_ACK','NL_RESET_HELD_NATIVE_RESPONSE','NL_SRC1024_END_AT1023','NL_DST1024_END_AT1023','NL_ONE_ITEM_ADDR1023']
    tail = ''' integer i;
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
  for(i=0;i<15;i=i+1)begin run(i,0);mark(case_name(i));end
  run(0,1);mark("NL_NATIVE_COMMAND_HOLD");run(4,2);mark("NL_NATIVE_RESPONSE_HOLD");run(9,3);mark("NL_LAST_DST_ACK_GATE_1023");run(1,4);mark("NL_HELPER_REQUEST_RESPONSE_HOLD");
  for(i=0;i<10;i=i+1)begin guard(i);mark(guard_name(i));end
  run(0,0);mark("NL_REUSE_AFTER_ADMISSION_REJECTIONS");
  prepare(0);strict=0;launch();wait(cv&&cop==1);@(negedge clk);corrupt_n=1;@(posedge clk);#1;@(negedge clk);corrupt_n=0;finish(1,1);
  if(writes!=w0||ram(dst_base)!==POISON)$fatal(1,"FAIL_NLONG native error wrote destination");
  hard_reset();run(4,0);mark("NL_NATIVE_ERROR_POISON_RESET_RECOVER");
  prepare(0);strict=0;launch();wait(hrv&&owner);@(negedge clk);inject_mem_error=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes!=w0)$fatal(1,"FAIL_NLONG read error wrote destination");hard_reset();run(0,0);mark("NL_MEMORY_READ_ERROR_POISON_RESET_RECOVER");
  prepare(1);strict=0;launch();wait(mv&&mw&&ma==dst_base+1);allow_mem_rsp=0;while(!hrv)@(negedge clk);@(negedge clk);inject_mem_error=1;allow_mem_rsp=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes-w0!=2||ram(dst_base)!==n_output(1,0)||ram(dst_base+1)!==n_output(1,1)||ram(dst_base+2)!==POISON)$fatal(1,"FAIL_NLONG partial accepted writes rollback/overrun");
  hard_reset();run(8,0);mark("NL_LATE_WRITE_ERROR_PARTIAL_PREFIX");
  prepare(9);launch();wait(mv&&mw&&ma==exp_base);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(0,0);mark("NL_RESET_PENDING_EXP_WRITE_ACK");
  prepare(0);allow_n_rsp=0;launch();while(!rv)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(6,0);mark("NL_RESET_HELD_NATIVE_RESPONSE");
  src_base=896;run(0,0);src_base=0;mark("NL_SRC1024_END_AT1023");
  dst_base=896;run(0,0);dst_base=256;mark("NL_DST1024_END_AT1023");
  src_base=1023;run(12,0);src_base=0;mark("NL_ONE_ITEM_ADDR1023");
  $display("NL_STATS cycles=%0d Sread=%0d Swrite=%0d Sack=%0d Ncmd=%0d Nrsp=%0d done=%0d",cycles,reads,writes,acks,commands,responses,completions);
  $display("PASS_NLONG cases=%0d",cases);$finish;
 end
endmodule
'''
    tb = '\n'.join(head) + '\n' + body + tail
    tb_path = a.output_dir / 'block_w4_n_long_tb.sv'
    tb_path.write_bytes(tb.encode('utf-8'))
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    summary = {'schema_version':1,'kind':'INDEPENDENT_INTEGER_EXPECTATIONS_NOT_RTL_EXECUTION','vectors':golden,
               'legacy_TB_sha256':sha(legacy),'reference_sha256':sha(Path(__file__).with_name('nlong_integer_reference.py')),
               'math_EXP1025_equals_selected_source':True,'EXP_source_sha256':sha(table),
               'hand_math_boundaries':{'signed_RNE_ties':4,'floor_root_bounds':11,'equalSoftmax1024_each_probability':16,'lastNewmax1023_fullrow_probability':16384,'RMS1_extreme_gamma_clips':True}}
    (a.output_dir / 'nlong-math-vectors.json').write_bytes((json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    ids = [x[0] for x in CASES] + guard_ids + extra_ids
    assert len(ids) == len(set(ids)) == 38
    contract = {'schema_version':1,'top_module':'block_w4_n_long_tb','pass_marker':'PASS_NLONG','expected_case_ids':ids,
                'testbench_path':'project/tb/block_connection_w4/block_w4_n_long_tb.sv','tb_sha256':sha(tb_path),
                'new_RTL':['project/rtl/block_connection_w4/block_w4_n_long_ctrl.sv'],
                'existing_RTL':['project/rtl/block_connection_p2/block_p2_s_ctrl.sv','project/rtl/block_feed_v1/block_feed_s16k.sv','project/rtl/block_v2/block_v2_n.sv'],
                'include_dirs':['project/rtl/block_v2'],'data':['project/rtl/block_v2/block_v2_n_exp.svh'],
                'scope':'full groups1..1024, three modes, true nativeN/S/helper; reset is coordinated abort mapping, no separate abortpin; not modelquality or RTL executed by builder'}
    contract['compile_sources'] = contract['existing_RTL'] + contract['new_RTL'] + [contract['testbench_path']]
    contract['reference_dependencies'] = ['work/Melodydt/151/nlong_integer_reference.py',
                                         'work/Melodydt/151/build_nlong_tb.py',
                                         'work/Melodydt/151/nlong-math-vectors.json']
    contract['input_paths'] = contract['compile_sources'] + contract['reference_dependencies'] + contract['data'] + ['project/tb/block_connection_w4/block_w4_n_tb.sv']
    (a.output_dir / 'nlong-tb-contract.json').write_bytes((json.dumps(contract,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS_BUILD_NLONG_MATH_ONLY vectors15 cases38 TBsha=' + sha(tb_path))


if __name__ == '__main__':
    main()
