`timescale 1ns/1ps
module tb_load_bounds #(parameter integer WORDS=256);
  reg clk=0; always #5 clk=~clk;
  reg reset=1,load_valid=0,rd_valid=0,rd_rsp_ready=0,rd_bank=0;
  reg [2:0] load_target=0,cmd_op=0;
  reg [9:0] load_index=0,rd_index=0;
  reg [127:0] load_data=0;
  reg cmd_valid=0,rsp_ready=0,cmd_role=0,cmd_clear=0;
  reg [8:0] cmd_rows=0;
  wire load_ready,rd_ready,rd_rsp_valid,cmd_ready,rsp_valid,rsp_error;
  wire [127:0] rd_data;
  wire [511:0] rsp_data;
  r_stream_local #(.WORDS(WORDS)) dut(.*,.cmd_mode(2'b0));
  localparam BEATS=WORDS/4;
  reg [127:0] expected_state[0:1][0:BEATS-1];
  reg [127:0] expected_operand[0:7][0:WORDS/64+5];
  integer checks=0,rejected=0,accepted=0;
  function automatic integer limit(input integer target);
    case(target)
      0,1:limit=WORDS/4;
      2,3:limit=WORDS/64;
      4,6:limit=6;
      5:limit=1;
      7:limit=4;
      default:limit=0;
    endcase
  endfunction
  function automatic [127:0] pattern(input integer t,i,salt);
    reg [127:0] value;
    for(integer j=0;j<4;j=j+1)
      value[32*j+:32]=32'(((t+1)*101+i*17+j*3+salt)*(j%2 ? -1 : 1));
    return value;
  endfunction
  task automatic remember(input integer t,i,input [127:0] value);
    if(t<2)expected_state[t][i]=value;
    else expected_operand[t][i]=value;
  endtask
  task automatic load(input integer t,i,input [127:0] value);
    integer age;
    @(negedge clk);load_valid=1;load_target=3'(t);load_index=10'(i);load_data=value;
    age=0;#1;
    while(!load_ready)begin
      @(negedge clk);#1;age=age+1;if(age>100)$fatal(1,"legal LOAD stuck t=%0d i=%0d",t,i);
    end
    @(posedge clk);#1;
    @(negedge clk);load_valid=0;
    remember(t,i,value);accepted=accepted+1;
  endtask
  task automatic reject(input integer t,i);
    @(negedge clk);load_valid=1;load_target=3'(t);load_index=10'(i);load_data=~pattern(t,i,999);
    repeat(3)begin
      #1;checks=checks+1;
      if(load_ready)$fatal(1,"invalid LOAD accepted WORDS=%0d t=%0d i=%0d",WORDS,t,i);
      if(rsp_valid)$fatal(1,"raw LOAD created an unsolicited command response");
      @(negedge clk);
    end
    load_valid=0;rejected=rejected+1;
  endtask
  task automatic read_word(input integer bank,index,input [127:0] expected);
    integer age;
    @(negedge clk);rd_valid=1;rd_bank=1'(bank);rd_index=10'(index);age=0;#1;
    while(!rd_ready)begin @(negedge clk);#1;age=age+1;if(age>100)$fatal(1,"read admission stuck");end
    @(posedge clk);#1;@(negedge clk);rd_valid=0;age=0;
    while(!rd_rsp_valid)begin @(negedge clk);age=age+1;if(age>100)$fatal(1,"read response stuck");end
    repeat(2)begin
      checks=checks+1;
      if(!rd_rsp_valid || rd_data!==expected)$fatal(1,"state changed bank=%0d index=%0d got=%h expected=%h",bank,index,rd_data,expected);
      @(negedge clk);
    end
    rd_rsp_ready=1;@(negedge clk);rd_rsp_ready=0;
  endtask
  task automatic check_state;
    for(integer bank=0;bank<2;bank=bank+1)
      for(integer index=0;index<BEATS;index=index+1)read_word(bank,index,expected_state[bank][index]);
  endtask
  // Operand registers have no host read port. Observe their complete contents,
  // independently decoding the documented 8xS16 / 4xS32 payload layouts.
  task automatic check_operands;
    for(integer i=0;i<WORDS/8;i=i+1)begin
      checks=checks+2;
      if(dut.key[i]!==expected_operand[2][i/8][16*(i%8)+:16])$fatal(1,"key changed");
      if(dut.query[i]!==expected_operand[3][i/8][16*(i%8)+:16])$fatal(1,"query changed");
    end
    for(integer i=0;i<8;i=i+1)begin
      checks=checks+3;
      if(dut.x[i]!==expected_operand[4][i/4][32*(i%4)+:32])$fatal(1,"x changed");
      if(dut.update[i]!==expected_operand[4][2+i/4][32*(i%4)+:32])$fatal(1,"update changed");
      if(dut.skip[i]!==expected_operand[4][4+i/4][32*(i%4)+:32])$fatal(1,"skip changed");
    end
    checks=checks+2;
    if(dut.decay!==expected_operand[5][0][31:0] || dut.beta!==expected_operand[5][0][63:32])$fatal(1,"decay/beta changed");
    for(integer i=0;i<24;i=i+1)begin
      checks=checks+1;if(dut.hist[i]!==expected_operand[6][i/4][32*(i%4)+:32])$fatal(1,"history changed");
    end
    for(integer i=0;i<32;i=i+1)begin
      checks=checks+1;if(dut.taps[i]!==expected_operand[7][i/8][16*(i%8)+:16])$fatal(1,"taps changed");
    end
  endtask
  task automatic command(input [2:0] op,input bit clear_dot,input [511:0] expected);
    integer age;
    @(negedge clk);cmd_valid=1;cmd_op=op;cmd_rows=9'(WORDS/8);cmd_role=0;cmd_clear=clear_dot;#1;age=0;
    while(!cmd_ready)begin @(negedge clk);#1;age=age+1;if(age>100)$fatal(1,"command admission stuck");end
    @(posedge clk);#1;@(negedge clk);cmd_valid=0;age=0;
    while(!rsp_valid)begin @(negedge clk);age=age+1;if(age>WORDS+100)$fatal(1,"command completion stuck");end
    repeat(4)begin
      checks=checks+1;
      if(rsp_error || rsp_data!==expected)$fatal(1,"legal numeric command mismatch op=%0d got=%h expected=%h",op,rsp_data,expected);
      @(negedge clk);
    end
    rsp_ready=1;@(negedge clk);rsp_ready=0;
  endtask
  reg [511:0] expected_response;
  longint signed total;
  reg signed [31:0] state_value;
  reg signed [15:0] query_value;
  initial begin
    repeat(4)@(negedge clk);reset=0;
    for(integer t=0;t<8;t=t+1)
      for(integer i=0;i<limit(t);i=i+1)load(t,i,pattern(t,i,0));
    check_state();check_operands();
    for(integer t=0;t<8;t=t+1)begin
      // Every representable invalid index, not just the first overflowing row.
      for(integer i=limit(t);i<1024;i=i+1)reject(t,i);
      check_state();check_operands();
      load(t,limit(t)-1,pattern(t,limit(t)-1,777));
      check_state();check_operands();
    end
    // Legal R arithmetic after all invalid requests: exact unit decay copies
    // the complete source state into the other bank, then query-dot is checked
    // against an independent signed S32 x S16 sum.
    load(5,0,128'h00000000000000000000000180000000);
    expected_response=0;
    for(integer lane=0;lane<8;lane=lane+1)
      expected_response[64*lane+:64]=64'($signed(expected_state[0][BEATS-2+lane/4][32*(lane%4)+:32]));
    command(0,0,expected_response);
    for(integer i=0;i<BEATS;i=i+1)expected_state[1][i]=expected_state[0][i];
    check_state();
    expected_response=0;
    for(integer lane=0;lane<8;lane=lane+1)begin
      total=0;
      for(integer row=0;row<WORDS/8;row=row+1)begin
        state_value=expected_state[1][2*row+lane/4][32*(lane%4)+:32];
        query_value=expected_operand[3][row/8][16*(row%8)+:16];
        total=total+64'(state_value)*64'(query_value);
      end
      expected_response[64*lane+:64]=total;
    end
    command(3,1,expected_response);
    // Reset suppresses admission, preserves RAM, and permits a fresh legal LOAD.
    @(negedge clk);reset=1;load_valid=1;load_target=0;load_index=10'(BEATS);load_data='1;
    repeat(3)begin #1;if(load_ready||rd_ready||rsp_valid)$fatal(1,"reset handshake");@(negedge clk);end
    load_valid=0;reset=0;
    load(0,0,128'h55aa);check_state();
    $display("PASS raw bounds WORDS=%0d accepted=%0d rejected=%0d checks=%0d",WORDS,accepted,rejected,checks);
    $finish;
  end
  initial begin #10000000;$fatal(1,"test watchdog");end
endmodule
