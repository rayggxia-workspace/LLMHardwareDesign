// Issue162 C v1. All program/descriptor contents are loadable while idle.
// Control traffic is 32-bit framed; bulk tensor payload never traverses C.
// Configuration is an internal request/response port; AXI-Lite wrapper separate.
module control_c(
 input wire clk,reset,
 input wire cfg_valid,output wire cfg_ready,input wire cfg_write,
 input wire [15:0] cfg_addr,input wire [31:0] cfg_wdata,input wire [3:0] cfg_wstrb,
 output reg cfg_rsp_valid,input wire cfg_rsp_ready,output reg [31:0] cfg_rdata,output reg cfg_error,
 output reg task_valid,input wire task_ready,output reg [31:0] task_data,
 output reg [3:0] task_endpoint,output reg task_last,
 input wire done_valid,output wire done_ready,input wire [31:0] done_data,input wire done_last,
 output wire busy,output reg ended,output reg [3:0] fault,output reg [7:0] error_pc
);
 localparam IDLE=0,FETCH=1,EXEC=2,TX_READ=3,TX_SEND=4;
 reg [2:0] state;reg running;
 reg [7:0] pc;reg [63:0] instruction;
 reg [31:0] code_lo[0:255],code_hi[0:255];reg [255:0] code_lv,code_hv;
 reg [31:0] desc[0:127];reg [127:0] desc_valid;
 reg [31:0] r[0:15];reg [39:0] address_reg[0:7];
 reg [7:0] loop_pc[0:3];reg [31:0] loop_left[0:3];reg [2:0] loop_depth;
 reg [31:0] event_used,event_done;reg [10:0] generation[0:31];
 reg [3:0] event_ep[0:31],event_lease[0:31];reg [31:0] event_result[0:31];
 reg [31:0] event_leased;reg [15:0] lease_used;
 reg [31:0] done_header,last_done_header;reg done_half;
 reg [3:0] tx_desc;reg [2:0] tx_word;reg [15:0] tx_tag;
 reg [31:0] submitted,completed,stalls;
 wire [7:0] op=instruction[63:56];wire [3:0] rd=instruction[55:52],ra=instruction[51:48],rb=instruction[47:44];
 wire [3:0] flags=instruction[43:40];wire [7:0] aux=instruction[39:32];wire [31:0] imm=instruction[31:0];
 wire [4:0] wait_slot=r[ra][4:0];
 wire [6:0] desc_index={ra,3'b000};
 wire [3:0] desc_ep=desc[desc_index][11:8];
 reg free_valid;reg [4:0] free_slot;
 integer j;
 always @* begin
  free_valid=0;free_slot=0;
  for(integer k=31;k>=0;k=k-1) if(!event_used[k]) begin free_valid=1;free_slot=k[4:0];end
 end
 wire no_pending=(event_used & ~event_done)==0;
 wire quiet=!running && state==IDLE && !task_valid && no_pending;
 assign cfg_ready=!cfg_rsp_valid;
 assign done_ready=1'b1; // completion path never waits on the instruction decoder
 assign busy=running || state==TX_READ || state==TX_SEND || task_valid || !no_pending;
 wire [4:0] done_slot=done_header[4:0];
 wire done_match=event_used[done_slot] && !event_done[done_slot] &&
  generation[done_slot]==done_header[15:5] && event_ep[done_slot]==done_header[19:16];
 // Signed 42-bit address sum catches negative values and carry out of bit39.
 wire signed [41:0] addr_sum=$signed({2'b00,address_reg[ra[2:0]]})+$signed({{10{imm[31]}},imm});
 task fail;
  input [3:0] reason;
  begin if(fault==0) begin fault<=reason;error_pc<=pc;end running<=0;state<=IDLE;end
 endtask
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;running<=0;pc<=0;instruction<=0;loop_depth<=0;
   code_lv<=0;code_hv<=0;desc_valid<=0;event_used<=0;event_done<=0;
   event_leased<=0;lease_used<=0;done_half<=0;done_header<=0;last_done_header<=0;
   task_valid<=0;task_data<=0;task_endpoint<=0;task_last<=0;
   cfg_rsp_valid<=0;cfg_error<=0;cfg_rdata<=0;ended<=0;fault<=0;error_pc<=0;
   tx_desc<=0;tx_word<=0;tx_tag<=0;submitted<=0;completed<=0;stalls<=0;
   for(j=0;j<16;j=j+1) r[j]<=0;
   for(j=0;j<8;j=j+1) address_reg[j]<=0;
   for(j=0;j<32;j=j+1) begin generation[j]<=0;event_ep[j]<=0;event_lease[j]<=0;event_result[j]<=0;end
   for(j=0;j<4;j=j+1) begin loop_pc[j]<=0;loop_left[j]<=0;end
  end else begin
   if(cfg_rsp_valid && cfg_rsp_ready) cfg_rsp_valid<=0;
   if(cfg_valid && cfg_ready) begin
    cfg_rsp_valid<=1;cfg_rdata<=0;cfg_error<=0;
    if(cfg_addr[1:0]!=0) cfg_error<=1;
    else if(cfg_write) begin
     if(!quiet || cfg_wstrb!=4'hf) cfg_error<=1;
     else if(cfg_addr==16'h0004) begin
      if(cfg_wdata[1]) begin
       event_used<=0;event_done<=0;event_leased<=0;lease_used<=0;loop_depth<=0;
       fault<=0;ended<=0;state<=IDLE;done_half<=0;
       for(j=0;j<16;j=j+1) r[j]<=0;
       for(j=0;j<8;j=j+1) address_reg[j]<=0;
      end else if(cfg_wdata[0]) begin
       if(event_used!=0 || !code_lv[cfg_wdata[15:8]] || !code_hv[cfg_wdata[15:8]]) cfg_error<=1;
       else begin pc<=cfg_wdata[15:8];running<=1;ended<=0;fault<=0;loop_depth<=0;state<=FETCH;end
      end
     end else if(cfg_addr>=16'h0040 && cfg_addr<16'h0080) r[cfg_addr[5:2]]<=cfg_wdata;
     else if(cfg_addr>=16'h0080 && cfg_addr<16'h00c0) begin
      if(!cfg_addr[2]) address_reg[cfg_addr[5:3]][31:0]<=cfg_wdata;
      else if(cfg_wdata[31:8]!=0) cfg_error<=1;
      else address_reg[cfg_addr[5:3]][39:32]<=cfg_wdata[7:0];
     end else if(cfg_addr>=16'h1000 && cfg_addr<16'h1800) begin
      if(cfg_addr[2]) begin code_hi[cfg_addr[10:3]]<=cfg_wdata;code_hv[cfg_addr[10:3]]<=1;end
      else begin code_lo[cfg_addr[10:3]]<=cfg_wdata;code_lv[cfg_addr[10:3]]<=1;end
     end else if(cfg_addr>=16'h2000 && cfg_addr<16'h2200) begin desc[cfg_addr[8:2]]<=cfg_wdata;desc_valid[cfg_addr[8:2]]<=1;end
     else cfg_error<=1;
    end else begin
     case(cfg_addr)
      16'h0000:cfg_rdata<=32'h43310001;
      16'h0008:cfg_rdata<={24'b0,fault,ended,2'b0,busy};
      16'h000c:cfg_rdata<={16'b0,error_pc,pc};
      16'h0010:cfg_rdata<=submitted;
      16'h0014:cfg_rdata<=completed;
      16'h0018:cfg_rdata<=stalls;
      16'h001c:cfg_rdata<=last_done_header;
      default:begin
       if(cfg_addr>=16'h0040 && cfg_addr<16'h0080) cfg_rdata<=r[cfg_addr[5:2]];
       else if(cfg_addr>=16'h0080 && cfg_addr<16'h00c0)
        cfg_rdata<=cfg_addr[2]?{24'b0,address_reg[cfg_addr[5:3]][39:32]}:address_reg[cfg_addr[5:3]][31:0];
       else cfg_error<=1;
      end
     endcase
    end
   end
   // Running program and transport use separate phases. The whole task is
   // emitted before another instruction may edit its descriptor.
   case(state)
    IDLE:begin end
    FETCH:if(running && fault==0) begin
     if(!code_lv[pc] || !code_hv[pc]) fail(2);
     else begin instruction<={code_hi[pc],code_lo[pc]};state<=EXEC;end
    end
    EXEC:if(running && fault==0) begin
     state<=FETCH;
     // Sequential execution past the finite program end is an error, never a wrap.
     if(pc==255 && op!=11 && op!=18) fail(2);
     else begin
      pc<=pc+1;
      case(op)
       0:begin end
       1:r[rd]<=imm;
       2:r[rd]<=r[ra]+r[rb];
       3:r[rd]<=r[ra]-r[rb];
       4:r[rd]<=r[ra]&r[rb];
       5:r[rd]<=r[ra]|r[rb];
       6:r[rd]<=flags[0]?r[ra]>>imm[4:0]:r[ra]<<imm[4:0];
       7:if(rd[3]) fail(2);else address_reg[rd[2:0]]<={aux,imm};
       8:if(rd[3] || ra[3] || addr_sum[41:40]!=0) fail(2);else address_reg[rd[2:0]]<=addr_sum[39:0];
       9:if(loop_depth==4 || r[ra]==0) fail(2);else begin
        loop_pc[loop_depth[1:0]]<=pc+1;loop_left[loop_depth[1:0]]<=r[ra];loop_depth<=loop_depth+1;
       end
       10:if(loop_depth==0) fail(1);else if(loop_left[loop_depth-1]==1) loop_depth<=loop_depth-1;
        else begin loop_left[loop_depth-1]<=loop_left[loop_depth-1]-1;pc<=loop_pc[loop_depth-1];end
       11:if(imm>=256) fail(2);else if(flags==0 || r[ra]!=0) pc<=imm[7:0];
       12:if(aux>=8) fail(2);else begin desc[{rd,aux[2:0]}]<=r[ra];desc_valid[{rd,aux[2:0]}]<=1;end
       13:if(!desc_valid[desc_index] || desc_ep>=7) fail(5);
        else if(!free_valid || (flags[0] && lease_used[aux[3:0]])) begin pc<=pc;state<=EXEC;stalls<=stalls+1;end
        else begin
         event_used[free_slot]<=1;event_done[free_slot]<=0;generation[free_slot]<=generation[free_slot]+1;
         event_ep[free_slot]<=desc_ep;event_leased[free_slot]<=flags[0];event_lease[free_slot]<=aux[3:0];
         if(flags[0]) lease_used[aux[3:0]]<=1;
         tx_tag<={generation[free_slot]+11'd1,free_slot};r[rd]<={16'b0,generation[free_slot]+11'd1,free_slot};
         tx_desc<=ra;tx_word<=0;task_endpoint<=desc_ep;state<=TX_READ;submitted<=submitted+1;
        end
       14:if(r[ra][31:16]!=0 || !event_used[wait_slot] || generation[wait_slot]!=r[ra][15:5]) fail(3);
        else if(!event_done[wait_slot]) begin pc<=pc;state<=EXEC;stalls<=stalls+1;end
        else begin
         r[rd]<=event_result[wait_slot];event_used[wait_slot]<=0;event_done[wait_slot]<=0;
         if(event_leased[wait_slot]) lease_used[event_lease[wait_slot]]<=0;event_leased[wait_slot]<=0;
        end
       15,17,18:if(!no_pending) begin pc<=pc;state<=EXEC;stalls<=stalls+1;end
        else begin event_used<=0;event_done<=0;event_leased<=0;lease_used<=0;
         if(op==18) begin running<=0;ended<=1;state<=IDLE;end
        end
       default:fail(1); // LOAD_META is reserved until the real metadata endpoint exists
      endcase
     end
    end
    TX_READ:begin
     task_valid<=1;task_last<=tx_word==7;
     if(tx_word==0) task_data<={tx_tag,desc[{tx_desc,3'b000}][15:0]};
     else task_data<=desc_valid[{tx_desc,tx_word}]?desc[{tx_desc,tx_word}]:32'b0;
     state<=TX_SEND;
    end
    TX_SEND:if(task_valid && task_ready) begin
     task_valid<=0;
     if(tx_word==7) state<=running?FETCH:IDLE;
     else begin tx_word<=tx_word+1;state<=TX_READ;end
    end
    default:fail(1);
   endcase
   // Last assignment wins over execution on error. Already launched task
   // packets finish transmission; accepted endpoints are drained on the link.
   if(done_valid) begin
    if(!done_half) begin
     if(done_last) begin
      if(fault==0) begin fault<=3;error_pc<=pc;end running<=0;
      if(state!=TX_READ && state!=TX_SEND) state<=IDLE;
     end else begin done_header<=done_data;done_half<=1;end
    end else begin
     done_half<=0;
     if(!done_last || !done_match) begin
      if(fault==0) begin fault<=3;error_pc<=pc;end running<=0;
      if(state!=TX_READ && state!=TX_SEND) state<=IDLE;
     end else begin
      event_done[done_slot]<=1;event_result[done_slot]<=done_data;last_done_header<=done_header;completed<=completed+1;
      if(done_header[23:20]!=0) begin
       if(fault==0) begin fault<=4;error_pc<=pc;end running<=0;
       if(state!=TX_READ && state!=TX_SEND) state<=IDLE;
      end
     end
    end
   end
  end
 end
endmodule
