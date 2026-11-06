// A lease joins up to three complete fragments committed by RX into private S.
// RX uses port zero; TX uses port one and can only read committed storage.
module block_cfj_j (
 input wire clk, reset,
 input wire [1:0] io_req_valid, io_req_write,
 input wire [19:0] io_req_addr, input wire [255:0] io_req_data,
 output wire [1:0] io_req_ready, io_rsp_valid,
 input wire [1:0] io_rsp_ready, output wire [255:0] io_rsp_data,
 input wire [7:0] active_epoch,
 input wire [31:0] rx_tag, input wire [1:0] rx_slot, input wire rx_last,
 output wire rx_error,
 input wire start, output wire start_ready,
 input wire [31:0] join_tag, input wire join_three,
 input wire [9:0] result_addr, words,
 output reg done_valid, input wire done_take, output reg done_error,
 output reg out_valid, input wire out_take, output reg [127:0] out_data,
 output reg [31:0] out_tag, output reg [9:0] out_index, output reg out_last,
 input wire release_valid, output wire release_ready
);
 reg reset_q;
 always @(posedge clk) reset_q<=reset;
 localparam IDLE=0, BEGIN_T=1, READ_A=2, READ_B=3, ADD=4, WAIT_E=5,
            STORE=6, READ_T=7, WRITE_T=8, COMMIT=9, DRAIN=10, READ_C=11, ADD_THREE=12;
 reg [3:0] state;
 reg [9:0] base_a,base_b,base_c,base_result,count,index;
 reg [31:0] tag;
 reg three;
 reg [127:0] a,b,c,result_word;
 wire e_ready,e_valid,t_begin_ready,t_write_ready,t_commit_ready;
 wire [127:0] e_data,e_s_data,t_s_data;
 wire [1:0] local_req,local_write,local_ready,local_rsp,local_take;
 wire [19:0] local_addr;
 wire [255:0] local_data;
 wire e_done,t_done;

 reg [2:0] started,complete;
 reg [31:0] branch_tag[0:2];
 reg [9:0] branch_base[0:2];
 reg [10:0] branch_next[0:2];
 reg rx_pending,rx_bad;
 reg [1:0] pending_slot;
 reg [31:0] pending_tag;
 reg [9:0] pending_addr;
 reg pending_last;
 wire [31:0] rx_link_tag;
 wire [1:0] rx_link_slot;
 wire [9:0] rx_link_addr;
 wire [127:0] rx_link_data,rx_link_rsp_data;
 wire rx_link_last,rx_link_write,rx_link_valid,rx_link_ready,rx_link_rsp_valid,rx_link_rsp_ready;
 wire rx_front_ready;
 wire rx_front_window=state==IDLE && !(start && start_ready);
 assign io_req_ready[0]=rx_front_window && rx_front_ready;
 pj_mem_port #(.REQ_WIDTH(163),.RSP_WIDTH(129)) rx_boundary(
  .clk(clk),.reset(reset_q),.req_valid(io_req_valid[0] && rx_front_window),
  .req_write(io_req_write[0]),.req_addr(io_req_addr[9:0]),
  .req_data({rx_tag,rx_slot,rx_last,io_req_data[127:0]}),.req_ready(rx_front_ready),
  .rsp_valid(io_rsp_valid[0]),.rsp_data({rx_error,io_rsp_data[127:0]}),.rsp_ready(io_rsp_ready[0]),
  .s_req_valid(rx_link_valid),.s_req_write(rx_link_write),.s_req_addr(rx_link_addr),
  .s_req_data({rx_link_tag,rx_link_slot,rx_link_last,rx_link_data}),.s_req_ready(rx_link_ready),
  .s_rsp_valid(rx_link_rsp_valid),.s_rsp_data({rx_pending && rx_bad,rx_link_rsp_data}),
  .s_rsp_ready(rx_link_rsp_ready));
 wire [10:0] rx_addr={1'b0,rx_link_addr};
 wire [10:0] end_result={1'b0,result_addr}+{1'b0,words};
 wire rx_idle=!reset_q && state==IDLE && !rx_pending && !(start && start_ready);
 reg rx_legal,join_legal;
 always @* begin
  rx_legal=0;
  if(rx_link_slot<3 && rx_link_write && rx_link_tag[31:24]==active_epoch) begin
   rx_legal=!complete[rx_link_slot] && (!started[rx_link_slot] ||
            (rx_link_tag==branch_tag[rx_link_slot] && rx_addr==branch_next[rx_link_slot]));
   for(integer j=0;j<3;j=j+1)
    if({30'b0,rx_link_slot}!=j && started[j] && rx_addr>={1'b0,branch_base[j]} && rx_addr<branch_next[j])
     rx_legal=0;
  end
  join_legal=words!=0 && words<=384 && end_result<=1024 && join_tag[31:24]==active_epoch;
  for(integer j=0;j<3;j=j+1)
   if(j<2 || join_three) begin
    if(!complete[j] || branch_tag[j]!=join_tag || branch_next[j]!={1'b0,branch_base[j]}+{1'b0,words})
     join_legal=0;
    if(result_addr!=branch_base[j] && {1'b0,result_addr}<branch_next[j] && {1'b0,branch_base[j]}<end_result)
     join_legal=0;
   end
 end
 wire rx_s_ready,rx_s_rsp,tx_s_ready,tx_s_rsp,t_release_ready;
 wire [10:0] tx_addr={1'b0,io_req_addr[19:10]};
 wire tx_front_ready,tx_link_valid,tx_link_take;
 wire [9:0] tx_link_addr;
 wire [127:0] tx_link_data;
 wire tx_window=state==DRAIN && !release_valid && !io_req_write[1] &&
                tx_addr>={1'b0,base_result} && tx_addr<({1'b0,base_result}+{1'b0,count});
 assign rx_link_ready=rx_idle && (!rx_legal || rx_s_ready);
 assign rx_link_rsp_valid=rx_pending && (rx_bad || rx_s_rsp);
 assign io_req_ready[1]=tx_window && tx_front_ready;
 pj_mem_port tx_boundary(
  .clk(clk),.reset(reset_q),.req_valid(io_req_valid[1] && tx_window),
  .req_write(1'b0),.req_addr(io_req_addr[19:10]),.req_data(128'b0),.req_ready(tx_front_ready),
  .rsp_valid(io_rsp_valid[1]),.rsp_data(io_rsp_data[255:128]),.rsp_ready(io_rsp_ready[1]),
  .s_req_valid(tx_link_valid),.s_req_write(),.s_req_addr(tx_link_addr),
  .s_req_data(),.s_req_ready(tx_s_ready),.s_rsp_valid(tx_s_rsp),.s_rsp_data(tx_link_data),
  .s_rsp_ready(tx_link_take));
 wire t_valid,t_last;
 wire [127:0] t_data;
 wire [31:0] t_tag;
 wire [9:0] t_index;
 wire t_take=!out_valid || out_take;
 assign release_ready=t_release_ready && tx_front_ready && !out_valid;
 assign start_ready=!reset_q && state==IDLE && !done_valid && !rx_pending && rx_front_ready;

 pj_sram_client e_client(
  .clk(clk),.reset(reset_q),.start(state==READ_A || state==READ_B || state==READ_C || state==STORE),
  .idle(),.write_word(state==STORE),
  .address((state==READ_A ? base_a : state==READ_B ? base_b : state==READ_C ? base_c : base_result)+index),
  .data(result_word),.req_valid(local_req[1]),.req_write(local_write[1]),
  .req_addr(local_addr[19:10]),.req_data(local_data[255:128]),.req_ready(local_ready[1]),
  .rsp_valid(local_rsp[1]),.rsp_ready(local_take[1]),.done(e_done));
 pj_sram_client t_client(
  .clk(clk),.reset(reset_q),.start(state==READ_T),.idle(),
  .write_word(1'b0),.address(base_result+index),.data(128'b0),
  .req_valid(local_req[0]),.req_write(local_write[0]),.req_addr(local_addr[9:0]),
  .req_data(local_data[127:0]),.req_ready(local_ready[0]),
  .rsp_valid(local_rsp[0]),.rsp_ready(local_take[0]),.done(t_done));
 cfj_s_port #(.CLIENTS(4)) store(
  .clk(clk),.reset(reset_q),.req_valid({local_req,tx_link_valid,rx_link_valid && rx_idle && rx_legal}),
  .req_write({local_write,1'b0,1'b1}),.req_addr({local_addr,tx_link_addr,rx_link_addr}),
  .req_data({local_data,128'b0,rx_link_data}),.req_ready({local_ready,tx_s_ready,rx_s_ready}),
  .rsp_valid({local_rsp,tx_s_rsp,rx_s_rsp}),.rsp_ready({local_take,tx_link_take,rx_link_rsp_ready && rx_pending && !rx_bad}),
  .rsp_data({e_s_data,t_s_data,tx_link_data,rx_link_rsp_data}));
 cfj_e_port arithmetic(
  .clk(clk),.reset(reset_q),.in_valid(state==ADD),.in_ready(e_ready),
  .in_op(4'd0),.in_shift(5'd0),.in_a(a),.in_b(b),.in_c(128'b0),
  .use_late_a(1'b0), .late_valid(1'b0), .late_a(128'b0), .late_take(),
  .out_valid(e_valid),.out_ready(state==WAIT_E),.out_data(e_data),
  .out_error(),.out_saturated());
 // Keep full precision until all three operands have been combined.
 wire [127:0] sum_three;
 for(genvar lane=0;lane<8;lane=lane+1) begin: widen
  wire signed [17:0] x={{2{a[16*lane+15]}},a[16*lane+:16]};
  wire signed [17:0] y={{2{b[16*lane+15]}},b[16*lane+:16]};
  wire signed [17:0] z={{2{c[16*lane+15]}},c[16*lane+:16]};
  wire signed [17:0] sum=x+y+z;
  assign sum_three[16*lane+:16]=sum>18'sd32767 ? 16'h7fff : sum< -18'sd32768 ? 16'h8000 : sum[15:0];
 end
 transaction6k lease(
  .clk(clk),.reset(reset_q),.begin_valid(state==BEGIN_T),.begin_ready(t_begin_ready),
  .begin_owner(2'b0),.begin_generation(tag),.begin_words(count),
  .write_valid(state==WRITE_T),.write_ready(t_write_ready),.write_index(index),
  .write_data(result_word),.commit_valid(state==COMMIT),.commit_ready(t_commit_ready),
  .revoke_valid(1'b0),.revoke_ready(),.read_valid(t_valid),.read_take(t_take),
  .read_index(t_index),.read_data(t_data),.read_last(t_last),
  .owner(),.generation(t_tag),.word_count(),.release_valid(release_valid && release_ready),
  .release_ready(t_release_ready),.busy(),.sealed(),.committed(),.protocol_error(),.debug_state());

 always @(posedge clk) begin
  if(reset_q) begin
   state<=IDLE; done_valid<=0; done_error<=0; out_valid<=0;
   rx_pending<=0; rx_bad<=0; started<=0; complete<=0;
  end else begin
   if(t_take) begin
    out_valid<=t_valid;
    if(t_valid) begin out_data<=t_data; out_index<=t_index; out_last<=t_last; out_tag<=t_tag; end
   end
   if(rx_link_valid && rx_link_ready) begin
    rx_pending<=1; rx_bad<=!rx_legal;
    pending_slot<=rx_link_slot; pending_addr<=rx_addr[9:0]; pending_tag<=rx_link_tag; pending_last<=rx_link_last;
   end
   if(rx_link_rsp_valid && rx_link_rsp_ready) begin
    rx_pending<=0;
    if(!rx_bad) begin
     if(!started[pending_slot]) begin
      branch_base[pending_slot]<=pending_addr;
      branch_tag[pending_slot]<=pending_tag;
     end
     started[pending_slot]<=1; complete[pending_slot]<=pending_last;
     branch_next[pending_slot]<={1'b0,pending_addr}+11'd1;
    end
   end
   if(done_valid && done_take) done_valid<=0;
   case(state)
    IDLE: if(start && start_ready) begin
     done_error<=!join_legal;
     if(!join_legal) done_valid<=1;
     else begin
      base_a<=branch_base[0]; base_b<=branch_base[1]; base_c<=branch_base[2];
      base_result<=result_addr; count<=words; tag<=join_tag; index<=0; three<=join_three;
      started<=0; complete<=0; state<=BEGIN_T;
     end
    end
    BEGIN_T: if(t_begin_ready) state<=READ_A;
    READ_A: if(e_done) begin a<=e_s_data; state<=READ_B; end
    READ_B: if(e_done) begin b<=e_s_data; state<=three ? READ_C : ADD; end
    READ_C: if(e_done) begin c<=e_s_data; state<=ADD_THREE; end
    ADD: if(e_ready) state<=WAIT_E;
    WAIT_E: if(e_valid) begin result_word<=e_data; state<=STORE; end
    ADD_THREE: begin result_word<=sum_three; state<=STORE; end
    STORE: if(e_done) state<=READ_T;
    READ_T: if(t_done) begin result_word<=t_s_data; state<=WRITE_T; end
    WRITE_T: if(t_write_ready) begin
     if(index+10'd1==count) state<=COMMIT;
     else begin index<=index+10'd1; state<=READ_A; end
    end
    COMMIT: if(t_commit_ready) begin done_valid<=1; state<=DRAIN; end
    DRAIN: if(release_valid && release_ready) state<=IDLE;
    default: state<=IDLE;
   endcase
  end
 end
endmodule
