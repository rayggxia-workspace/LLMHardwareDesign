// Native P16 operand, command, and SRAM response exercise. The test driver
// is an integration fixture. It does not stand in for the programmable MC/LC.
module native_p(
    input logic clk, reset,
    input wire net_req, net_write, net_take,
    input wire [9:0] net_addr,
    input wire [127:0] net_data,
    output wire net_ready, net_rsp,
    output wire [127:0] net_result
);
  logic req=0, wr=0, rsp_take=0;
  semaphore port_lock=new(1);
  logic [9:0] address=0;
  logic [127:0] data=0;
  wire [1:0] ready, rsp;
  wire [255:0] result;
  logic load=0, cmd=0, store=0, gated=0;
  logic [9:0] cmd_dst=0;
  logic [3:0] op=0;
  logic [63:0] arg=0;
  wire load_ready, load_done, load_error, cmd_ready, cmd_done, cmd_error;
  wire gate_ready, gate_done, gate_error;

  assign net_ready=ready[1];
  assign net_rsp=rsp[1];
  assign net_result=result[255:128];
  block_p16 dut (
    .clk(clk), .reset(reset),
    .io_req_valid({net_req,req}), .io_req_write({net_write,wr}),
    .io_req_addr({net_addr,address}), .io_req_data({net_data,data}),
    .io_req_ready(ready), .io_rsp_valid(rsp), .io_rsp_ready({net_take,rsp_take}),
    .io_rsp_data(result),
    .load_valid(load), .load_ready(load_ready), .load_bank(1'b0),
    .load_rows(4'd1), .load_tiles(3'd4), .load_a_wide(1'b0), .load_b_wide(1'b0),
    .load_reuse_b(1'b0), .load_a_base(10'd0), .load_b_base(10'd16),
    .load_done(load_done), .load_take(1'b1), .load_error(load_error),
    .cmd_valid(cmd), .cmd_ready(cmd_ready), .cmd_op(op), .cmd_index(6'b0),
    .cmd_data(arg), .cmd_store(store), .cmd_route(1'b0), .cmd_pack16(store),
    .cmd_dst(cmd_dst), .cmd_done(cmd_done), .cmd_take(1'b1), .cmd_error(cmd_error),
    .cmd_saturated(), .cmd_result(),
    .gate_valid(gated), .gate_route(1'b0), .gate_ready(gate_ready),
    .gate_a(10'd32), .gate_b(10'd33), .gate_dst(10'd34),
    .gate_done(gate_done), .gate_take(1'b1), .gate_error(gate_error),
    .gate_saturated(), .m_to_g_valid(), .m_to_g_data(), .m_to_g_take(1'b0),
    .g_from_m_valid(1'b0), .g_from_m_data(32'b0), .g_from_m_take());

  task automatic access(input bit write, input int addr,
    input logic [127:0] value, input int stall, output logic [127:0] got);
    port_lock.get();
    @(negedge clk);
    req=1; wr=write; address=10'(addr); data=value;
    do @(posedge clk); while(!ready[0]);
    @(negedge clk); req=0;
    if(stall != 0) begin
      wait(rsp[0]);
      repeat(stall) begin
        @(negedge clk);
        if(!rsp[0]) $fatal(1, "SRAM response dropped under backpressure");
      end
    end
    rsp_take=1;
    do @(posedge clk); while(!rsp[0]);
    got=result[127:0];
    @(negedge clk); rsp_take=0;
    port_lock.put();
  endtask

  task automatic command(input int code, input logic [63:0] argument,
    input bit write, input int dest, input bit expected_error);
    @(negedge clk);
    cmd=1; op=4'(code); arg=argument; store=write; cmd_dst=10'(dest);
    do @(posedge clk); while(!cmd_ready);
    @(negedge clk); cmd=0;
    do @(posedge clk); while(!cmd_done);
    if(cmd_error!==expected_error) $fatal(1,"native M command %0d unexpected status", code);
  endtask

  task automatic project(input logic [127:0] words[0:2559], input int dest);
    logic [127:0] ignored;
    command(4,64'd1,0,0,0);
    for(int seg=0;seg<80;seg++) begin
      for(int i=0;i<32;i++) access(1,i,words[32*seg+i],0,ignored);
      @(negedge clk); load=1;
      do @(posedge clk); while(!load_ready);
      @(negedge clk); load=0;
      do @(posedge clk); while(!load_done);
      if(load_error) $fatal(1,"native feeder failed");
      command(10,seg==0?64'hc284:64'hc280,0,0,0);
    end
    command(5,64'h102,1,dest,0);
  endtask

  task automatic gate;
    @(negedge clk); gated=1;
    do @(posedge clk); while(!gate_ready);
    @(negedge clk); gated=0;
    do @(posedge clk); while(!gate_done);
    if(gate_error) $fatal(1,"native G failed");
  endtask
endmodule

module tb_ffn;
  logic clk=0, reset=1;
  always #5 clk=~clk;
  wire src_req, src_ready, src_rsp, src_take;
  wire dst_req, dst_ready, dst_rsp, dst_take;
  wire [9:0] src_addr, dst_addr;
  wire [127:0] src_data, dst_data;
  logic copy_start=0, allow_ack=0;
  logic [9:0] copy_src=0, copy_dst=0;
  wire copy_ready, copy_done;
  native_p p0(clk,reset,dst_req,1'b1,dst_take,dst_addr,dst_data,dst_ready,dst_rsp,);
  native_p p1(clk,reset,src_req,1'b0,src_take,src_addr,128'b0,src_ready,src_rsp,src_data);
  ffn_copy copier(
    .clk(clk), .reset(reset), .start(copy_start), .source_word(copy_src), .dest_word(copy_dst),
    .ready(copy_ready), .done(copy_done), .source_req(src_req), .source_ready(src_ready),
    .source_addr(src_addr), .source_rsp(src_rsp), .source_take(src_take), .source_data(src_data),
    .dest_req(dst_req), .dest_ready(dst_ready), .dest_addr(dst_addr), .dest_data(dst_data),
    .dest_rsp(dst_rsp), .dest_take(dst_take), .allow_ack(allow_ack));
  logic [127:0] g[0:2559], u[0:2559], expected[0:2];
  logic [32:0] mc[0:7], lc0[0:11], lc1[0:11];
  wire finished, failed, reserve_up;
  wire [1:0] service_valid;
  wire [65:0] service_word;
  logic [1:0] service_ready=0, service_done=0, service_error=0;
  logic load_image=0, start_program=0;
  logic [1:0] load_target=0;
  logic [3:0] load_address=0;
  logic [32:0] load_word=0;
  int stall;
  bit fail_test;
  localparam logic [127:0] SENTINEL=128'h0123456789abcdeffedcba9876543210;
  string vectors, images;
  logic [127:0] result;

  ffn_program_ctrl controller(
    .clk(clk), .reset(reset), .load(load_image), .load_target(load_target),
    .load_address(load_address), .load_data(load_word), .start(start_program),
    .finished(finished), .failed(failed), .reserve_up(reserve_up),
    .service_valid(service_valid), .service_word(service_word),
    .service_ready(service_ready), .service_done(service_done), .service_error(service_error));

  task automatic local_run(input int block, input logic [32:0] ins);
    logic [127:0] got;
    int a,b,c;
      a=int'(ins[29:20]); b=int'(ins[19:10]); c=int'(ins[9:0]);
      case(ins[32:30])
        4: begin
          if(a>1 || b!=(a==0?32:33) || c!=a) $fatal(1,"invalid project descriptor");
          if(block==0) begin
            if(a==0) p0.project(g,b); else p0.project(u,b);
            p0.access(0,b,0,0,got);
          end else begin
            if(a!=1) $fatal(1,"P1 projection must be up");
            p1.project(u,b);
            p1.access(0,b,0,0,got);
          end
          if(got!==expected[a]) $fatal(1,"native projection %0d got %h expected %h",a,got,expected[a]);
          $display("TRACE projection %0d %h",a,got);
        end
        5: begin
          if(block!=1 || a!=33 || b!=33 || !reserve_up)
            $fatal(1,"invalid copy descriptor or unready destination");
          @(negedge clk);
          if(!copy_ready) $fatal(1,"transport busy");
          copy_src=10'(a); copy_dst=10'(b); copy_start=1;
          @(negedge clk); copy_start=0;
          $display("TRACE up_in_flight");
          wait(dst_rsp);
          repeat(stall) begin
            @(negedge clk);
            if(!dst_rsp || !src_rsp || src_take || src_data!==expected[1])
              $fatal(1,"early release or corrupted held data");
          end
          @(negedge clk); allow_ack=1;
          do @(posedge clk); while(!(dst_rsp && dst_take));
          $display("TRACE up_rx_stored");
          do @(posedge clk); while(!copy_done);
          @(negedge clk); allow_ack=0;
          $display("TRACE up_source_release");
        end
        6: begin
          if(block!=0 || a!=32 || b!=33 || c!=34 || reserve_up)
            $fatal(1,"invalid gate descriptor or missing operands");
          p0.gate();
          p0.access(0,c,0,0,got);
          if(got!==expected[2]) $fatal(1,"native mid mismatch got %h expected %h",got,expected[2]);
          $display("TRACE mid_stored %h",got);
        end
        default: $fatal(1,"unknown local opcode");
      endcase
  endtask

  task automatic worker(input int block);
    logic [32:0] ins;
    forever begin
      @(negedge clk); service_ready[block]=1;
      do @(posedge clk); while(!service_valid[block]);
      ins=service_word[33*block+:33];
      @(negedge clk); service_ready[block]=0;
      if(fail_test) begin
        if(block!=0 || ins[32:30]!=4 || ins[19:10]!=32)
          $fatal(1,"unexpected service during failure test");
        p0.command(15,0,1,32,1);
      end else local_run(block,ins);
      @(negedge clk);
      service_done[block]=1; service_error[block]=fail_test;
      @(negedge clk);
      service_done[block]=0; service_error[block]=0;
    end
  endtask

  initial worker(0);
  initial worker(1);

  task automatic write_image(input int target, input int addr, input logic [32:0] word);
    @(negedge clk);
    load_image=1;
    load_target=2'(target);
    load_address=4'(addr);
    load_word=word;
  endtask

  initial begin
    if(!$value$plusargs("vectors=%s",vectors) || !$value$plusargs("images=%s",images) ||
       !$value$plusargs("stall=%d",stall)) $fatal(1,"missing test input");
    $readmemh({vectors,"/gate.hex"},g);
    $readmemh({vectors,"/up.hex"},u);
    $readmemh({vectors,"/expected.hex"},expected);
    $readmemh({images,"/mc.hex"},mc);
    $readmemh({images,"/lc0.hex"},lc0);
    $readmemh({images,"/lc1.hex"},lc1);
    repeat(4) @(negedge clk);
    reset=0;
    fail_test=$test$plusargs("fail_test");
    if(fail_test) p0.access(1,32,SENTINEL,0,result);
    for(int i=0;i<8;i++) write_image(0,i,mc[i]);
    for(int i=0;i<12;i++) write_image(1,i,lc0[i]);
    for(int i=0;i<12;i++) write_image(2,i,lc1[i]);
    @(negedge clk); load_image=0; start_program=1;
    @(negedge clk); start_program=0;
    wait(finished || failed);
    if(fail_test) begin
      if(!failed || finished || src_req || dst_req) $fatal(1,"controller exposed failed service");
      p0.access(0,32,0,0,result);
      if(result!==SENTINEL) $fatal(1,"failed service wrote SRAM");
      $display("PASS native P16 error suppresses program advancement");
    end else begin
      if(failed) $fatal(1,"program controller rejected image");
    p0.command(15,0,1,34,1);
    p0.access(0,34,0,0,result);
    if(result!==expected[2]) $fatal(1,"failed command modified SRAM");
      $display("PASS native P16 FFN image stall=%0d",stall);
    end
    $finish;
  end
  initial begin
    repeat(200000) @(posedge clk);
    $fatal(1,"watchdog");
  end
endmodule
