// Control the native S feeder and own finite registered A/B handoff to M.
// Complete only after native done and both real operand packets are consumed.
module control_adapter_s(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg load_valid,input wire load_ready,output reg load_bank,
 output reg [3:0] load_rows,output reg [2:0] load_tiles,
 output reg load_a_wide,load_b_wide,load_reuse_b,output reg [9:0] load_a_base,load_b_base,
 input wire done_valid,output wire done_take,input wire done_error,
 input wire s_a_valid,output reg s_a_ready,input wire [134:0] s_a_packet,
 input wire s_b_valid,output reg s_b_ready,input wire [516:0] s_b_packet,
 output wire m_a_valid,input wire m_a_ready,output reg [134:0] m_a_packet,
 output wire m_b_valid,input wire m_b_ready,output reg [516:0] m_b_packet
);
 reg active,waiting,done_seen,held_error,a_full,b_full;reg [15:0] tag;
 wire invalid=task_data[15:0]!=16'h0500 || task_data[255:193]!=0 || task_data[191:128]!=0 ||
  task_data[63:42]!=0 || task_data[95:78]!=0 || task_data[67:64]!=0 ||
  task_data[127:110]!=0 || task_data[99:96]!=0 || task_data[35:32]==0 || task_data[35:32]>8 ||
  task_data[38:36]==0 || task_data[38:36]>4;
 assign task_ready=!active && !complete_valid && !a_full && !b_full;
 assign done_take=active && waiting && !done_seen;
 // No M ready feeds S ready combinationally. Each channel has one real slot.
 // Two look-ahead readiness state bits belong to this adapter. Their next
 // values equal the original state predicate after this same edge: no extra
 // handshake cycle or packet slot. S sees clock-to-Q plus the output driver.
 wire start_good=task_valid && task_ready && !invalid;
 wire finish=active && done_seen && !a_full && !b_full;
 wire next_active=!finish && (active || start_good);
 wire next_waiting=!finish && ((load_valid && load_ready) || (!start_good && waiting));
 wire next_done=!finish && ((done_valid && done_take) || (!start_good && done_seen));
 wire next_a_full=(s_a_valid && s_a_ready) || (a_full && !m_a_ready);
 wire next_b_full=(s_b_valid && s_b_ready) || (b_full && !m_b_ready);
 always @(posedge clk) begin
  if(reset) begin s_a_ready<=0;s_b_ready<=0;end
  else begin
   s_a_ready<=next_active && next_waiting && !next_done && !next_a_full;
   s_b_ready<=next_active && next_waiting && !next_done && !next_b_full;
  end
 end
 assign m_a_valid=a_full;assign m_b_valid=b_full;
 always @(posedge clk) begin
  if(reset) begin
   active<=0;waiting<=0;done_seen<=0;held_error<=0;a_full<=0;b_full<=0;m_a_packet<=0;m_b_packet<=0;
   tag<=0;complete_valid<=0;complete_data<=0;load_valid<=0;load_bank<=0;
   load_rows<=0;load_tiles<=0;load_a_wide<=0;load_b_wide<=0;load_reuse_b<=0;load_a_base<=0;load_b_base<=0;
  end else begin
   if(m_a_valid && m_a_ready) a_full<=0;
   if(m_b_valid && m_b_ready) b_full<=0;
   if(s_a_valid && s_a_ready) begin a_full<=1;m_a_packet<=s_a_packet;end
   if(s_b_valid && s_b_ready) begin b_full<=1;m_b_packet<=s_b_packet;end
   if(complete_valid && complete_ready) complete_valid<=0;
   if(task_valid && task_ready) begin
    tag<=task_data[31:16];load_bank<=task_data[192];load_rows<=task_data[35:32];load_tiles<=task_data[38:36];
    load_a_wide<=task_data[39];load_b_wide<=task_data[40];load_reuse_b<=task_data[41];
    load_a_base<=task_data[77:68];load_b_base<=task_data[109:100];
    if(invalid) begin complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd5,task_data[31:16]};end
    else begin active<=1;waiting<=0;done_seen<=0;held_error<=0;load_valid<=1;end
   end
   if(load_valid && load_ready) begin load_valid<=0;waiting<=1;end
   if(done_valid && done_take) begin
    done_seen<=1;held_error<=done_error;
   end
   if(active && done_seen && !a_full && !b_full) begin
    active<=0;waiting<=0;done_seen<=0;complete_valid<=1;
    complete_data<={32'b0,8'b0,held_error?4'd4:4'd0,4'd5,tag};
   end
  end
 end
endmodule
