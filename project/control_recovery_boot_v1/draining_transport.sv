`timescale 1ns/1ps
module draining_transport #(parameter bit SOURCE=0,J_SOURCE=0)(
 input wire clk_i,rst_ni,halt_i,link_busy_i,input wire svc_valid,output wire svc_ready,
 input wire [1023:0] descriptor,input wire [127:0] service_identity,
 output wire rsp_valid,input wire rsp_ready,output reg [15:0] status,output reg [31:0] read_bytes,write_bytes,
 output wire mem_req_valid,mem_req_write,output wire [9:0] mem_req_address,output wire [127:0] mem_req_data,
 input wire mem_req_ready,mem_rsp_valid,input wire [127:0] mem_rsp_data,output wire mem_rsp_ready,
 input wire committed_valid,input wire [511:0] committed_packet,output wire committed_take,
 output wire tx_valid,input wire tx_ready,output wire [9:0] tx_address,output wire [127:0] tx_data,tx_identity,
 input wire ack_valid,output wire ack_ready,input wire [127:0] ack_identity,input wire ack_abort,ack_committed,
 output wire reserved,output wire [9:0] reserved_address,output wire [127:0] reserved_identity,
 input wire rx_valid,output wire rx_ready,input wire [9:0] rx_address,input wire [127:0] rx_data,
 output wire rx_ack,input wire rx_ack_ready,commit_valid,output wire busy,ack_rejected
);
 localparam [2:0] IDLE=0,READ=1,OFFER=2,ACK=3,RECEIVE=4,REPLY=5;
 reg [2:0] state;reg [9:0] source_address,destination_address,reservation_address;
 reg [127:0] identity,expect_identity;reg reservation,stored,rx_pending,confirmed;
 wire [15:0] op=descriptor[47:32];wire [31:0] n0=descriptor[543:512],n1=descriptor[575:544],n2=descriptor[607:576],n3=descriptor[639:608];
 wire available=J_SOURCE ? committed_valid : mem_rsp_valid;
 wire j_ok=committed_packet[202:171]==identity[127:96] && committed_packet[234:203]==identity[95:64] &&
           committed_packet[266:235]==identity[63:32] && committed_packet[169:160]==source_address;
 wire drop_source=SOURCE && halt_i && state==OFFER && !link_busy_i && available;
 wire take_ack=ack_valid && ack_ready;
 assign svc_ready=rst_ni && state==IDLE;assign rsp_valid=rst_ni && state==REPLY;
 assign reserved=rst_ni && reservation && !stored;assign reserved_address=reservation_address;assign reserved_identity=expect_identity;
 assign busy=state!=IDLE || reservation || rx_pending;
 assign mem_req_valid=rst_ni && (SOURCE ? !J_SOURCE && state==READ : rx_valid && reserved && !rx_pending);
 assign mem_req_write=!SOURCE;assign mem_req_address=SOURCE ? source_address : rx_address;assign mem_req_data=SOURCE ? 128'b0 : rx_data;
 assign rx_ready=rst_ni && !SOURCE && reserved && !rx_pending && mem_req_ready;
 assign rx_ack=rst_ni && !SOURCE && rx_pending && mem_rsp_valid;
 assign tx_valid=rst_ni && SOURCE && !halt_i && state==OFFER && available && (!J_SOURCE || j_ok);
 assign tx_address=destination_address;assign tx_data=J_SOURCE ? committed_packet[127:0] : mem_rsp_data;assign tx_identity=identity;
 assign ack_ready=rst_ni && SOURCE && state==ACK && ack_identity==identity &&
                  (ack_abort ? halt_i && (!ack_committed || confirmed) : confirmed);
 assign ack_rejected=rst_ni && SOURCE && state==ACK && ack_valid && !ack_ready;
 assign committed_take=rst_ni && J_SOURCE && (take_ack || drop_source);
 assign mem_rsp_ready=rst_ni && (SOURCE ? !J_SOURCE && (take_ack || drop_source) : rx_ack && rx_ack_ready);
 always @(posedge clk_i)begin
  if(!rst_ni)begin state<=IDLE;source_address<=0;destination_address<=0;reservation_address<=0;
   identity<=0;expect_identity<=0;reservation<=0;stored<=0;rx_pending<=0;confirmed<=0;status<=0;read_bytes<=0;write_bytes<=0;end
  else begin
   if(commit_valid)confirmed<=1;
   if(!SOURCE && rx_valid && rx_ready)rx_pending<=1;
   if(rx_ack && rx_ack_ready)begin rx_pending<=0;stored<=1;end
   if(!SOURCE && halt_i && !link_busy_i && !rx_pending && state!=RECEIVE)begin reservation<=0;stored<=0;end
   case(state)
    IDLE:if(svc_valid)begin
     status<=0;read_bytes<=0;write_bytes<=0;state<=REPLY;
     if(halt_i)status<=11;
     else if(descriptor[1023:640]!=0 || n3!=0)status<=5;
     else if(SOURCE && op==16'h101)begin
      if(n0[31:20]!=0 || {n2,n1}!=0 || J_SOURCE && n0[9:0]>=4)status<=5;
      else begin source_address<=n0[9:0];destination_address<=n0[19:10];identity<=service_identity;confirmed<=0;state<=J_SOURCE ? OFFER : READ;end
     end else if(!SOURCE && op==16'h103)begin
      if(n0[31:10]!=0 || n2!=0 || reservation)status<=5;
      else begin reservation<=1;stored<=0;reservation_address<=n0[9:0];expect_identity<={service_identity[127:32],n1};end
     end else if(!SOURCE && op==16'h102)begin
      if({n2,n1,n0}!=0 || !reservation)status<=5;else state<=RECEIVE;
     end else status<=4;
    end
    READ:if(mem_req_ready)state<=OFFER;
    OFFER:if(drop_source)begin status<=11;read_bytes<=16;state<=REPLY;end
          else if(tx_valid && tx_ready)state<=ACK;
    ACK:if(take_ack)begin status<=ack_abort ? 16'd11 : 16'd0;read_bytes<=16;state<=REPLY;end
    RECEIVE:if(stored || halt_i && !link_busy_i && !rx_pending)begin
     status<=halt_i ? 16'd11 : 16'd0;write_bytes<=stored ? 32'd16 : 32'd0;reservation<=0;stored<=0;state<=REPLY;end
    REPLY:if(rsp_ready)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
