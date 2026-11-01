// Finite DMA address/credit engine, one instance per read/write direction.
// Payload remains in the paired 32-word transport buffer, never in C.
// Acknowledgement means S writes accepted (load) or AXI B received (store).
module control_dma_planner(
 input wire clk,reset,
 input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output wire burst_valid,input wire burst_ready,output wire [39:0] burst_address,
 output wire [9:0] burst_local_word,output wire [3:0] burst_s_instance,
 output wire [4:0] burst_beats,output wire burst_id,output wire burst_write,
 output wire [15:0] burst_last_strobe,
 input wire ack_valid,input wire ack_id,input wire ack_error,
 output wire complete_valid,input wire complete_ready,output wire [63:0] complete_data,
 output wire [5:0] reserved_words,output reg protocol_error
);
 localparam IDLE=0,ACTIVE=1,COMPLETE=2;
 reg [1:0] state;
 reg [255:0] queue[0:1];reg qread,qwrite;reg [1:0] count;
 wire push=task_valid && task_ready;
 wire pop=complete_valid && complete_ready;
 assign task_ready=count<2;
 reg [39:0] current_external;
 reg [13:0] current_local;
 reg [3:0] instance_id;reg direction;
 reg [23:0] row_bytes;
 reg [15:0] rows,row_index;reg [13:0] local_stride;
 reg [31:0] external_stride;
 reg [23:0] offset;
 reg [15:0] tag;reg [31:0] total_bytes;
 reg all_issued,failed;reg [3:0] failure;
 reg [1:0] flight;reg [4:0] flight_beats[0:1];
 reg offer_active,offer_id;
 wire [255:0] candidate=queue[qread];
 wire [39:0] ext={candidate[71:64],candidate[63:32]};
 wire [13:0] loc=candidate[89:76];
 wire [23:0] length=candidate[119:96];
 wire [15:0] nrows=candidate[143:128],lstride=candidate[159:144];
 wire [31:0] estride=candidate[191:160];
 wire [24:0] padded=({1'b0,length}+25'd15)&25'h1fffff0;
 wire [63:0] ext_end={24'b0,ext}+({48'b0,nrows}-64'd1)*{32'b0,estride}+{39'b0,padded};
 wire [63:0] local_end={50'b0,loc}+({48'b0,nrows}-64'd1)*{48'b0,lstride}+{39'b0,padded};
 wire invalid=candidate[255:192]!=0 || candidate[127:120]!=0 || candidate[95:90]!=0 ||
  candidate[75:72]!=0 || candidate[15:8]!=0 || candidate[7:0]>1 || length==0 || nrows==0 || ext[3:0]!=0 || loc[3:0]!=0 ||
  estride[3:0]!=0 || lstride[3:0]!=0 || ext_end>64'h10000000000 || local_end>16384 ||
  (nrows>1 && ({7'b0,padded}>estride || padded>{9'b0,lstride}));
 wire free_valid=flight!=2'b11;
 assign burst_id=offer_id;
 assign burst_valid=offer_active;
 assign burst_address=current_external+{16'b0,offset};
 wire [24:0] remaining_bytes={1'b0,row_bytes}-{1'b0,offset};
 wire [20:0] remaining_words=21'((remaining_bytes+25'd15)>>4);
 wire [8:0] boundary_words=9'((13'd4096-{1'b0,burst_address[11:0]})>>4);
 wire [4:0] capped_words=remaining_words>16?5'd16:remaining_words[4:0];
 assign burst_beats=boundary_words<{4'b0,capped_words}?boundary_words[4:0]:capped_words;
 wire [24:0] next_offset={1'b0,offset}+{16'b0,burst_beats,4'b0};
 wire row_last=next_offset>={1'b0,row_bytes};
 assign burst_local_word=10'((current_local+offset[13:0])>>4);
 assign burst_s_instance=instance_id;
 assign burst_write=direction;
 assign burst_last_strobe=row_last && row_bytes[3:0]!=0 ? (16'h1<<row_bytes[3:0])-16'd1:16'hffff;
 assign reserved_words=(flight[0]?{1'b0,flight_beats[0]}:6'b0)+(flight[1]?{1'b0,flight_beats[1]}:6'b0);
 assign complete_valid=state==COMPLETE;
 assign complete_data={failed?32'b0:total_bytes,8'b0,failure,4'b0,tag};
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;qread<=0;qwrite<=0;count<=0;current_external<=0;current_local<=0;
   instance_id<=0;direction<=0;row_bytes<=0;rows<=0;row_index<=0;local_stride<=0;external_stride<=0;offset<=0;
   tag<=0;total_bytes<=0;all_issued<=0;failed<=0;failure<=0;flight<=0;flight_beats[0]<=0;flight_beats[1]<=0;protocol_error<=0;
   offer_active<=0;offer_id<=0;
  end else begin
   if(push) begin queue[qwrite]<=task_data;qwrite<=~qwrite;end
   if(pop) begin qread<=~qread;state<=IDLE;end
   case({push,pop}) 2'b10:count<=count+1;2'b01:count<=count-1;default:begin end endcase
   case(state)
    IDLE:if(count!=0) begin
     tag<=candidate[31:16];failed<=invalid;failure<=invalid?4'd2:4'd0;
     if(invalid) state<=COMPLETE;
     else begin
      current_external<=ext;current_local<=loc;
      instance_id<=candidate[75:72];direction<=candidate[0];row_bytes<=length;rows<=nrows;
      local_stride<=lstride[13:0];external_stride<=estride;row_index<=0;offset<=0;total_bytes<=length*nrows;
      all_issued<=0;flight<=0;state<=ACTIVE;
     end
    end
    ACTIVE:begin
     if(!offer_active && !all_issued && !failed && free_valid && !(ack_valid && ack_error)) begin
      offer_active<=1;offer_id<=flight[0];
     end
     if(burst_valid && burst_ready) begin
      offer_active<=0;
      flight[burst_id]<=1;flight_beats[burst_id]<=burst_beats;
      if(row_last) begin
       offset<=0;
       if(row_index+16'd1==rows) all_issued<=1;
       else begin row_index<=row_index+1;current_external<=current_external+{8'b0,external_stride};
        current_local<=current_local+local_stride;end
      end else offset<=next_offset[23:0];
     end
     if((all_issued || failed) && flight==0 && !offer_active) state<=COMPLETE;
    end
    COMPLETE:begin end
    default:begin state<=IDLE;protocol_error<=1;end
   endcase
   if(ack_valid) begin
    if(!flight[ack_id]) begin protocol_error<=1;failed<=1;failure<=3;end
    else begin
     flight[ack_id]<=0;
     if(ack_error) begin failed<=1;failure<=4;end
    end
   end
  end
 end
endmodule
