`timescale 1ns/1ps
// Independent periodic full-group input; literal math expected outputs. No DUT-derived oracle.
module block_w4_n_long_tb;
 function automatic [15:0] n_count;input integer vec;begin case(vec)
  0:n_count=1024;
  1:n_count=1023;
  2:n_count=513;
  3:n_count=257;
  4:n_count=1024;
  5:n_count=1023;
  6:n_count=513;
  7:n_count=257;
  8:n_count=1024;
  9:n_count=1023;
  10:n_count=513;
  11:n_count=257;
  12:n_count=1;
  13:n_count=1;
  14:n_count=1024;
  default:n_count=0;endcase end endfunction
 function automatic [1:0] n_mode;input integer vec;begin case(vec)
  0:n_mode=1;
  1:n_mode=1;
  2:n_mode=1;
  3:n_mode=1;
  4:n_mode=2;
  5:n_mode=2;
  6:n_mode=2;
  7:n_mode=2;
  8:n_mode=0;
  9:n_mode=0;
  10:n_mode=0;
  11:n_mode=0;
  12:n_mode=1;
  13:n_mode=0;
  14:n_mode=1;
  default:n_mode=0;endcase end endfunction
 function automatic [7:0] n_words;input integer vec;begin case(vec)
  0:n_words=128;
  1:n_words=128;
  2:n_words=65;
  3:n_words=33;
  4:n_words=128;
  5:n_words=128;
  6:n_words=65;
  7:n_words=33;
  8:n_words=128;
  9:n_words=128;
  10:n_words=65;
  11:n_words=33;
  12:n_words=1;
  13:n_words=1;
  14:n_words=128;
  default:n_words=0;endcase end endfunction
 function automatic [31:0] n_epsilon;input integer vec;begin case(vec)
  0:n_epsilon=1;
  1:n_epsilon=1;
  2:n_epsilon=1;
  3:n_epsilon=1;
  4:n_epsilon=1;
  5:n_epsilon=1;
  6:n_epsilon=1;
  7:n_epsilon=1;
  8:n_epsilon=0;
  9:n_epsilon=0;
  10:n_epsilon=0;
  11:n_epsilon=0;
  12:n_epsilon=1;
  13:n_epsilon=0;
  14:n_epsilon=1;
  default:n_epsilon=0;endcase end endfunction
 function automatic  n_sat;input integer vec;begin case(vec)
  0:n_sat=1'b1;
  1:n_sat=1'b0;
  2:n_sat=1'b0;
  3:n_sat=1'b0;
  4:n_sat=1'b0;
  5:n_sat=1'b0;
  6:n_sat=1'b0;
  7:n_sat=1'b0;
  8:n_sat=1'b0;
  9:n_sat=1'b0;
  10:n_sat=1'b0;
  11:n_sat=1'b0;
  12:n_sat=1'b1;
  13:n_sat=1'b0;
  14:n_sat=1'b0;
  default:n_sat=0;endcase end endfunction
 function automatic signed [15:0] raw_code;input integer vec,element;begin case(vec)
  0:begin if(element==1023)raw_code=16'sd30000;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  1:begin if(element==1022)raw_code=-16'sd32768;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  2:begin if(element==512)raw_code=16'sd32767;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  3:begin if(element==256)raw_code=-16'sd32768;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  4:begin if(element==1023)raw_code=16'sd16384;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  5:begin if(element==1022)raw_code=-16'sd32768;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  6:begin if(element==512)raw_code=16'sd32767;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  7:begin if(element==256)raw_code=-16'sd32768;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  8:begin if(element==1023)raw_code=16'sd0;else case(element%8)
   0:raw_code=16'sd0;
   1:raw_code=16'sd0;
   2:raw_code=16'sd0;
   3:raw_code=16'sd0;
   4:raw_code=16'sd0;
   5:raw_code=16'sd0;
   6:raw_code=16'sd0;
   7:raw_code=16'sd0;
   default:raw_code=0;endcase end
  9:begin if(element==1022)raw_code=16'sd32767;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=-16'sd1024;
   2:raw_code=-16'sd1024;
   3:raw_code=-16'sd1024;
   4:raw_code=-16'sd1024;
   5:raw_code=-16'sd1024;
   6:raw_code=-16'sd1024;
   7:raw_code=-16'sd1024;
   default:raw_code=0;endcase end
  10:begin if(element==512)raw_code=16'sd5120;else case(element%8)
   0:raw_code=-16'sd4096;
   1:raw_code=-16'sd4081;
   2:raw_code=-16'sd2048;
   3:raw_code=-16'sd1025;
   4:raw_code=-16'sd1024;
   5:raw_code=-16'sd17;
   6:raw_code=-16'sd16;
   7:raw_code=-16'sd15;
   default:raw_code=0;endcase end
  11:begin if(element==256)raw_code=16'sd0;else case(element%8)
   0:raw_code=-16'sd32768;
   1:raw_code=-16'sd16385;
   2:raw_code=-16'sd16384;
   3:raw_code=-16'sd16383;
   4:raw_code=-16'sd17;
   5:raw_code=-16'sd16;
   6:raw_code=-16'sd15;
   7:raw_code=16'sd0;
   default:raw_code=0;endcase end
  12:begin if(element==0)raw_code=-16'sd32768;else case(element%8)
   0:raw_code=-16'sd1024;
   1:raw_code=16'sd1024;
   2:raw_code=16'sd2048;
   3:raw_code=-16'sd2048;
   4:raw_code=16'sd3;
   5:raw_code=-16'sd3;
   6:raw_code=16'sd7;
   7:raw_code=-16'sd7;
   default:raw_code=0;endcase end
  13:begin if(element==0)raw_code=16'sd32767;else case(element%8)
   0:raw_code=16'sd0;
   1:raw_code=16'sd0;
   2:raw_code=16'sd0;
   3:raw_code=16'sd0;
   4:raw_code=16'sd0;
   5:raw_code=16'sd0;
   6:raw_code=16'sd0;
   7:raw_code=16'sd0;
   default:raw_code=0;endcase end
  14:begin if(element==1023)raw_code=16'sd0;else case(element%8)
   0:raw_code=16'sd0;
   1:raw_code=16'sd0;
   2:raw_code=16'sd0;
   3:raw_code=16'sd0;
   4:raw_code=16'sd0;
   5:raw_code=16'sd0;
   6:raw_code=16'sd0;
   7:raw_code=16'sd0;
   default:raw_code=0;endcase end
  default:raw_code=0;endcase end endfunction
 function automatic signed [15:0] gain_code;input integer vec,element;begin if(vec==12)gain_code=-16'sd32768;else case(element%8)
  0:gain_code=16'sd1024;
  1:gain_code=-16'sd1024;
  2:gain_code=16'sd512;
  3:gain_code=-16'sd512;
  4:gain_code=16'sd2048;
  5:gain_code=-16'sd2048;
  6:gain_code=16'sd0;
  7:gain_code=16'sd32767;
  default:gain_code=0;endcase end endfunction
 function automatic [127:0] n_raw;input integer vec,word;integer lane;begin n_raw=0;for(lane=0;lane<8;lane=lane+1)if(word*8+lane<n_count(vec))n_raw[16*lane+:16]=raw_code(vec,word*8+lane);end endfunction
 function automatic [127:0] n_gamma;input integer vec,word;integer lane;begin n_gamma=0;for(lane=0;lane<8;lane=lane+1)if(word*8+lane<n_count(vec))n_gamma[16*lane+:16]=gain_code(vec,word*8+lane);end endfunction
 function automatic [127:0] n_output;input integer vec,word;begin case(vec)
  0:n_output=word==n_words(vec)-1 ? 128'h7fff00000004000402c502c5fd3bfd3b : 128'hff6500000004000402c502c5fd3bfd3b;
  1:n_output=word==n_words(vec)-1 ? 128'h000000000004000402aa02aafd56fd56 : 128'hff6b00000004000402aa02aafd56fd56;
  2:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000004712 : 128'hff8400000003000302390239fdc7fdc7;
  3:n_output=word==n_words(vec)-1 ? 128'h0000000000000000000000000000c807 : 128'hff9e00000003000301c001c0fe40fe40;
  4:n_output=word==n_words(vec)-1 ? 128'h3441000000000000001a001affe6ffe6 : 128'hfffa000000000000001a001affe6ffe6;
  5:n_output=word==n_words(vec)-1 ? 128'h000000000000000000150015ffebffeb : 128'hfffb00000000000000150015ffebffeb;
  6:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000000323 : 128'hfffb00000000000000190019ffe7ffe7;
  7:n_output=word==n_words(vec)-1 ? 128'h0000000000000000000000000000fc82 : 128'hfffa000000000000001c001cffe4ffe4;
  8:n_output=word==n_words(vec)-1 ? 128'h00100010001000100010001000100010 : 128'h00100010001000100010001000100010;
  9:n_output=word==n_words(vec)-1 ? 128'h00004000000000000000000000000000 : 128'h00000000000000000000000000000000;
  10:n_output=word==n_words(vec)-1 ? 128'h0000000000000000000000000000180b : 128'h002900290029000f000f000600010001;
  11:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000000080 : 128'h0080007f007e007e0000000000000000;
  12:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000007fff : 128'h00000000000000000000000000007fff;
  13:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000004000 : 128'h00000000000000000000000000004000;
  14:n_output=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  default:n_output=0;endcase end endfunction
 function automatic [127:0] n_expword;input integer vec,word;begin case(vec)
  0:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  1:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  2:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  3:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  4:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  5:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  6:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  7:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  8:n_expword=word==n_words(vec)-1 ? 128'h80008000800080008000800080008000 : 128'h80008000800080008000800080008000;
  9:n_expword=word==n_words(vec)-1 ? 128'h00008000000000000000000000000000 : 128'h00000000000000000000000000000000;
  10:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000008000 : 128'h00d900d900d900510051001e00040004;
  11:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000008000 : 128'h80007e247e047de50000000000000000;
  12:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  13:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000008000 : 128'h00000000000000000000000000008000;
  14:n_expword=word==n_words(vec)-1 ? 128'h00000000000000000000000000000000 : 128'h00000000000000000000000000000000;
  default:n_expword=0;endcase end endfunction
 function automatic [8*100-1:0] case_name;input integer vec;begin case(vec)
  0:case_name="NL_RMS1024_GLOBAL_LAST";
  1:case_name="NL_RMS1023_TAIL7";
  2:case_name="NL_RMS513_TAIL1";
  3:case_name="NL_RMS257_TAIL1";
  4:case_name="NL_L2_1024_GLOBAL_LAST";
  5:case_name="NL_L2_1023_TAIL7";
  6:case_name="NL_L2_513_TAIL1";
  7:case_name="NL_L2_257_TAIL1";
  8:case_name="NL_SOFTMAX1024_EQUAL_U16";
  9:case_name="NL_SOFTMAX1023_LAST_NEWMAX";
  10:case_name="NL_SOFTMAX513_INTERPOLATE";
  11:case_name="NL_SOFTMAX257_CUTOFF";
  12:case_name="NL_RMS1_EXTREME_GAMMA";
  13:case_name="NL_SOFTMAX1_U16";
  14:case_name="NL_RMS1024_ZERO_SIGNED_GAMMA";
  default:case_name=0;endcase end endfunction
 function automatic [8*100-1:0] guard_name;input integer vec;begin case(vec)
  0:guard_name="NL_GUARD_ZERO_COUNT";
  1:guard_name="NL_GUARD_COUNT1025";
  2:guard_name="NL_GUARD_MODE3";
  3:guard_name="NL_GUARD_ZERO_EPSILON";
  4:guard_name="NL_GUARD_RANGE_END";
  5:guard_name="NL_GUARD_SRC_DST_OVERLAP";
  6:guard_name="NL_GUARD_GAMMA_DST_OVERLAP";
  7:guard_name="NL_GUARD_SRC_EXP_OVERLAP";
  8:guard_name="NL_GUARD_SRC_GAMMA_OVERLAP";
  9:guard_name="NL_GUARD_FULL1024_WRAP";
  default:guard_name=0;endcase end endfunction
 function automatic integer native_word_index;input integer ix;integer w;begin w=n_words(ci);if(ix>=1&&ix<=w)native_word_index=ix-1;else if(n_mode(ci)!=0)native_word_index=ix-w-2;else if(ix<=2*w+1)native_word_index=ix-w-2;else native_word_index=ix-2*w-3;end endfunction

 reg clk=0;always #5 clk=~clk;
 reg reset=1,owner=0,service_active=0,strict=1;
 reg allow_mem_req=1,allow_mem_rsp=1,allow_s_ack=1,allow_n_cmd=1,allow_n_rsp=1;
 reg corrupt_n=0,inject_mem_error=0;
 reg req_valid=0,rsp_ready=0;wire req_ready,rsp_valid,rsp_error,rsp_saturated,busy;
 reg [1:0] req_mode;reg [15:0] req_count;reg [31:0] req_epsilon;
 reg [9:0] req_src_addr=0,req_gamma_addr=128,req_exp_addr=128,req_dst_addr=256;
 wire mv,mr,mw,mrv,mrr,mre;wire [9:0] ma;wire [127:0] md,mrd;
 wire cv,cr,leaf_cr,rv,rr,re,rsat;wire [3:0] cop,ccount;wire [31:0] cp;wire [127:0] cd,ca,rd;
 wire hv,hr,hw,hrv,hrr,hre;wire [9:0] ha;wire [127:0] hd,hrd;
 reg host_valid=0,host_write=1,host_rsp_ready=0;reg [9:0] host_addr;reg [127:0] host_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_take;wire [9:0] s_addr;wire [127:0] s_din,s_dout;
 assign hv=!reset&&allow_mem_req&&(owner?mv:host_valid);assign hw=owner?mw:host_write;
 assign ha=owner?ma:host_addr;assign hd=owner?md:host_data;assign mr=!reset&&owner&&allow_mem_req&&hr;
 assign mrv=!reset&&owner&&allow_mem_rsp&&hrv;assign mrd=hrd;assign mre=hre||inject_mem_error;
 assign hrr=!reset&&allow_mem_rsp&&(owner?mrr:host_rsp_ready);
 assign cr=leaf_cr&&allow_n_cmd;assign s_take=helper_take&&allow_s_ack;
 block_w4_n_long_ctrl u_ctrl(.clk(clk),.reset(reset),.req_valid(req_valid),.req_ready(req_ready),.req_mode(req_mode),.req_count(req_count),.req_epsilon(req_epsilon),.req_src_addr(req_src_addr),.req_gamma_addr(req_gamma_addr),.req_exp_addr(req_exp_addr),.req_dst_addr(req_dst_addr),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated),.busy(busy),.n_cmd_valid(cv),.n_cmd_ready(cr),.n_cmd_op(cop),.n_cmd_count(ccount),.n_cmd_param(cp),.n_cmd_data(cd),.n_cmd_aux(ca),.n_rsp_valid(rv&&allow_n_rsp),.n_rsp_ready(rr),.n_rsp_data(rd),.n_rsp_error(re),.n_rsp_saturated(rsat),.mem_req_valid(mv),.mem_req_ready(mr),.mem_req_write(mw),.mem_req_addr(ma),.mem_req_data(md),.mem_rsp_valid(mrv),.mem_rsp_ready(mrr),.mem_rsp_data(mrd),.mem_rsp_error(mre));
 block_v2_n u_n(.clk(clk),.reset(reset),.cmd_valid(cv&&allow_n_cmd),.cmd_ready(leaf_cr),.cmd_op(corrupt_n?4'd15:cop),.cmd_count(ccount),.cmd_param(cp),.cmd_data(cd),.cmd_aux(ca),.rsp_valid(rv),.rsp_ready(rr&&allow_n_rsp),.rsp_data(rd),.rsp_error(re),.rsp_saturated(rsat),.busy());
 block_p2_s_ctrl u_helper(.clk(clk),.resetn(!reset),.req_valid(hv),.req_ready(hr),.req_write(hw),.req_addr(ha),.req_data(hd),.rsp_valid(hrv),.rsp_ready(hrr),.rsp_data(hrd),.rsp_error(hre),.s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_rsp_ready(helper_take),.s_ready(s_ready),.s_rsp_valid(s_valid&&allow_s_ack),.s_dout(s_dout));
 block_feed_s16k u_s(.clk(clk),.reset(reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),.ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),.wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b1),.wide_dout());
 localparam [127:0] POISON=128'hdeadbeef0123456789abcdeffeedface;
 integer src_base=0,gamma_base=128,exp_base=128,dst_base=256;
 integer cycles=0,cases=0,ci=0,reads=0,writes=0,acks=0,commands=0,responses=0,completions=0;
 integer r0,w0,a0,c0,p0,d0,mem_index=0,cmd_index=0;
 reg pending=0,pending_write;reg [127:0] pending_data;reg [9:0] pending_addr;
 reg hold_cmd=0,hold_mem=0,hold_rsp=0,hold_native=0,hold_s=0;
 reg [127:0] old_cd,old_ca,old_md,old_rd,old_sd;reg [3:0] old_op,old_count;reg [31:0] old_param;reg [9:0] old_addr;
 reg old_mw,old_error,old_sat,old_ne,old_ns;
 function automatic [127:0] ram;
  input integer addr;begin case(addr%4)
   0:ram=u_s.bank0[addr/4];1:ram=u_s.bank1[addr/4];2:ram=u_s.bank2[addr/4];3:ram=u_s.bank3[addr/4];
  endcase end
 endfunction
 function automatic integer expected_op;
  input integer index;integer words;begin words=n_words(ci);
   if(index==0)expected_op=0;else if(index<=words)expected_op=1;else if(index==words+1)expected_op=2;
   else if(n_mode(ci)!=0)expected_op=5;
   else if(index<=2*words+1)expected_op=3;else if(index==2*words+2)expected_op=4;else expected_op=6;
  end
 endfunction
 function automatic integer expected_mem_addr;
  input integer index;integer w,k,t;begin w=n_words(ci);
   if(index<w)expected_mem_addr=src_base+index;
   else if(n_mode(ci)!=0)begin t=index-w;k=t/3;case(t%3)0:expected_mem_addr=src_base+k;1:expected_mem_addr=gamma_base+k;2:expected_mem_addr=dst_base+k;endcase end
   else if(index<3*w)begin t=index-w;k=t/2;expected_mem_addr=(t%2==0?src_base:exp_base)+k;end
   else begin t=index-3*w;k=t/2;expected_mem_addr=(t%2==0?exp_base:dst_base)+k;end
  end
 endfunction
 function automatic expected_mem_write;
  input integer index;integer w;begin w=n_words(ci);if(index<w)expected_mem_write=0;
   else if(n_mode(ci)!=0)expected_mem_write=((index-w)%3==2);
   else if(index<3*w)expected_mem_write=((index-w)%2==1);else expected_mem_write=((index-3*w)%2==1);
  end
 endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>2000000)$fatal(1,"FAIL_NLONG watchdog");
  if(reset)begin pending=0;hold_cmd=0;hold_mem=0;hold_rsp=0;hold_native=0;hold_s=0;end else begin
   if(hold_cmd&&(!cv||cop!==old_op||ccount!==old_count||cp!==old_param||cd!==old_cd||ca!==old_ca))$fatal(1,"FAIL_NLONG command changed under stall");
   if(hold_mem&&(!mv||ma!==old_addr||md!==old_md||mw!==old_mw))$fatal(1,"FAIL_NLONG mem request changed under stall");
   if(hold_rsp&&(!rsp_valid||rsp_error!==old_error||rsp_saturated!==old_sat))$fatal(1,"FAIL_NLONG completion changed under stall");
   if(hold_native&&(!rv||rd!==old_rd||re!==old_ne||rsat!==old_ns))$fatal(1,"FAIL_NLONG native response changed under stall");
   if(hold_s&&(!s_valid||s_dout!==old_sd))$fatal(1,"FAIL_NLONG S ACK changed under stall");
   hold_cmd=cv&&!cr;old_op=cop;old_count=ccount;old_param=cp;old_cd=cd;old_ca=ca;
   hold_mem=owner&&mv&&!mr;old_addr=ma;old_md=md;old_mw=mw;
   hold_rsp=rsp_valid&&!rsp_ready;old_error=rsp_error;old_sat=rsp_saturated;
   hold_native=rv&&!(rr&&allow_n_rsp);old_rd=rd;old_ne=re;old_ns=rsat;
   hold_s=s_valid&&!s_take;old_sd=s_dout;
   if(rsp_valid&&rsp_ready)completions=completions+1;
   if(s_req&&s_ready)begin
    if(pending)$fatal(1,"FAIL_NLONG multiple S owners");pending=1;pending_write=s_we;pending_data=s_din;pending_addr=s_addr;
    if(service_active)begin
     if(strict)begin
      if(s_addr!=expected_mem_addr(mem_index)||s_we!==expected_mem_write(mem_index))$fatal(1,"FAIL_NLONG mem sequence ci%0d step%0d got%0d wr%0d expected%0d",ci,mem_index,s_addr,s_we,expected_mem_addr(mem_index));
      if(s_we&&s_din!==(s_addr>=dst_base?n_output(ci,s_addr-dst_base):n_expword(ci,s_addr-exp_base)))$fatal(1,"FAIL_NLONG write math mismatch ci%0d addr%0d got%032h",ci,s_addr,s_din);
     end
     mem_index=mem_index+1;if(s_we)writes=writes+1;else reads=reads+1;
    end
   end
   if(s_valid&&s_take)begin
    if(!pending)$fatal(1,"FAIL_NLONG response without request");
    if(pending_write&&s_dout!==pending_data)$fatal(1,"FAIL_NLONG write ACK echo");
    pending=0;if(service_active)acks=acks+1;
   end
   if(cv&&cr)begin
    if(strict)begin
     if(cop!=expected_op(cmd_index))$fatal(1,"FAIL_NLONG command phase ci%0d index%0d op%0d",ci,cmd_index,cop);
     if(cop==0&&(cp!==n_mode(ci)||cd[31:0]!==n_epsilon(ci)))$fatal(1,"FAIL_NLONG BEGIN captured params");
     if(cop==1||cop==3||cop==5||cop==6)begin
      if(ccount!=(n_count(ci)-8*native_word_index(cmd_index)>8?8:n_count(ci)-8*native_word_index(cmd_index)))$fatal(1,"FAIL_NLONG native count/tail");
      if(cd!==(cop==6?n_expword(ci,native_word_index(cmd_index)):n_raw(ci,native_word_index(cmd_index))))$fatal(1,"FAIL_NLONG raw vs EXP/mask ci%0d op%0d word%0d got%032h",ci,cop,native_word_index(cmd_index),cd);
      if(cop==5&&ca!==n_gamma(ci,native_word_index(cmd_index)))$fatal(1,"FAIL_NLONG gamma replay/mask");
     end
    end
    commands=commands+1;cmd_index=cmd_index+1;
   end
   if(rv&&rr&&allow_n_rsp)responses=responses+1;
   if(service_active&&strict&&rsp_valid&&!rsp_error&&(pending||acks-a0!=n_words(ci)*(n_mode(ci)==0?5:4)))$fatal(1,"FAIL_NLONG completion before all write ACKs");
  end
 end
 task automatic mark;input [8*100-1:0] name;begin cases=cases+1;$display("CASE_PASS %0s",name);end endtask
 task automatic store;input integer address;input [127:0] data;
  begin @(negedge clk);owner=0;host_addr=address;host_data=data;host_valid=1;host_rsp_ready=0;
   while(!hr)@(negedge clk);@(posedge clk);#1;@(negedge clk);host_valid=0;
   while(!hrv)@(negedge clk);if(hrd!==data||hre)$fatal(1,"FAIL_NLONG host store ACK");host_rsp_ready=1;@(posedge clk);#1;@(negedge clk);host_rsp_ready=0;
  end
 endtask
 task automatic prepare;input integer index;integer k;reg [127:0] raw,g;
  begin ci=index;service_active=0;strict=1;
   for(k=0;k<n_words(ci);k=k+1)begin
    raw=n_raw(ci,k);g=n_gamma(ci,k);
    // Nonzero inactive source/gamma lanes must be masked, not included.
    if(k==n_words(ci)-1&&n_count(ci)%8)begin raw=raw|(128'hffffffffffffffffffffffffffffffff<<(16*(n_count(ci)%8)));g=g|(128'h0123456789abcdeffedcba9876543210<<(16*(n_count(ci)%8)));end
    store(src_base+k,raw);if(n_mode(ci)!=0)store(gamma_base+k,g);else store(exp_base+k,POISON);store(dst_base+k,POISON);
   end
   @(negedge clk);owner=1;service_active=1;r0=reads;w0=writes;a0=acks;c0=commands;p0=responses;d0=completions;mem_index=0;cmd_index=0;
  end
 endtask
 task automatic launch;
  begin @(negedge clk);req_mode=n_mode(ci);req_count=n_count(ci);req_epsilon=n_epsilon(ci);req_src_addr=src_base;req_gamma_addr=gamma_base;req_exp_addr=exp_base;req_dst_addr=dst_base;req_valid=1;rsp_ready=0;
   while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;
   req_mode=3;req_count=0;req_epsilon=0;req_src_addr=999;req_gamma_addr=998;req_exp_addr=997;req_dst_addr=996;
  end
 endtask
 task automatic finish;input error_expected,poison_expected;integer k;
  begin while(!rsp_valid)@(negedge clk);
   repeat(5)begin if(!rsp_valid||rsp_error!==error_expected||req_ready||!busy)$fatal(1,"FAIL_NLONG held completion flags");if(!error_expected&&rsp_saturated!==n_sat(ci))$fatal(1,"FAIL_NLONG saturation OR");@(negedge clk);end
   if(!error_expected)begin
    if(reads-r0!=3*n_words(ci)||writes-w0!=(n_mode(ci)==0?2:1)*n_words(ci)||acks-a0!=(n_mode(ci)==0?5:4)*n_words(ci)||commands-c0!=(n_mode(ci)==0?3+3*n_words(ci):2+2*n_words(ci))||responses-p0!=commands-c0||pending)$fatal(1,"FAIL_NLONG conservation ci%0d R%0d W%0d ACK%0d C%0d P%0d",ci,reads-r0,writes-w0,acks-a0,commands-c0,responses-p0);
    for(k=0;k<n_words(ci);k=k+1)begin if(ram(dst_base+k)!==n_output(ci,k))$fatal(1,"FAIL_NLONG stored output");if(n_mode(ci)==0&&ram(exp_base+k)!==n_expword(ci,k))$fatal(1,"FAIL_NLONG exact EXP stored/replayed");end
   end
   rsp_ready=1;@(posedge clk);#1;@(negedge clk);rsp_ready=0;service_active=0;owner=0;repeat(3)@(negedge clk);
   if(completions!=d0+1||rsp_valid||req_ready===poison_expected||busy!==poison_expected)$fatal(1,"FAIL_NLONG completion/reuse/poison");
  end
 endtask
 task automatic hard_reset;
  begin @(negedge clk);reset=1;req_valid=0;host_valid=0;rsp_ready=0;host_rsp_ready=0;service_active=0;owner=0;corrupt_n=0;inject_mem_error=0;
   allow_mem_req=1;allow_mem_rsp=1;allow_s_ack=1;allow_n_cmd=1;allow_n_rsp=1;
   repeat(3)@(negedge clk);reset=0;repeat(3)@(negedge clk);if(rsp_valid||busy||!req_ready||s_valid||rv)$fatal(1,"FAIL_NLONG reset recovery");
  end
 endtask
 task automatic run;input integer index,stall;
  begin prepare(index);if(stall==1)allow_n_cmd=0;if(stall==2)allow_n_rsp=0;if(stall==4)allow_mem_req=0;
   launch();
   if(stall==1)begin while(!cv)@(negedge clk);repeat(5)@(negedge clk);if(commands!=c0)$fatal(1,"FAIL_NLONG command stall accepted");allow_n_cmd=1;end
   if(stall==2)begin while(!rv)@(negedge clk);repeat(5)@(negedge clk);if(responses!=p0||rsp_valid)$fatal(1,"FAIL_NLONG response stall retired");allow_n_rsp=1;end
   if(stall==3)begin wait(mv&&mw&&ma==dst_base+n_words(ci)-1);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(rsp_valid)$fatal(1,"FAIL_NLONG destination write before ACK");end allow_s_ack=1;end
   if(stall==4)begin repeat(5)@(negedge clk);allow_mem_req=1;allow_mem_rsp=0;while(!hrv)@(negedge clk);repeat(5)@(negedge clk);allow_mem_rsp=1;end
   finish(0,0);
  end
 endtask
 task automatic guard;input integer kind;
  begin prepare(0);strict=0;@(negedge clk);req_mode=1;req_count=8;req_epsilon=1;req_src_addr=src_base;req_gamma_addr=gamma_base;req_exp_addr=exp_base;req_dst_addr=dst_base;
   case(kind)0:req_count=0;1:req_count=1025;2:req_mode=3;3:req_epsilon=0;4:req_src_addr=1023;5:req_dst_addr=src_base;6:req_dst_addr=gamma_base;7:begin req_mode=0;req_exp_addr=src_base;end 8:req_gamma_addr=src_base;9:begin req_count=1024;req_src_addr=897;end endcase
   // kind4 requires two words to exceed S, not one legal word at1023.
   if(kind==4)req_count=9;
   req_valid=1;while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;finish(1,0);
   if(reads!=r0||writes!=w0||commands!=c0)$fatal(1,"FAIL_NLONG guard touched native or S");
  end
 endtask
 integer i;
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
