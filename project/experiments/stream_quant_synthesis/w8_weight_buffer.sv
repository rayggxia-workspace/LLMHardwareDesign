// Two finite packet slots. Each B bank receives two actual 512-bit DMA beats.
// One single-port bank cannot be written while its packet is being consumed.
// Metadata/A are accepted before DMA; FIFO order defines ownership and tags.
module w8_weight_buffer #(parameter integer ABITS=8)(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire [2:0] cmd_ctx,input wire cmd_first,cmd_last,
 input wire [4:0] cmd_k,input wire [3:0] cmd_n,input wire [15:0] cmd_offset,
 input wire [16*ABITS-1:0] cmd_a,
 input wire dma_valid,output wire dma_ready,input wire [511:0] dma_data,
 output wire fill_ack,
 output wire m_valid,input wire m_ready,
 output wire [2:0] m_ctx,output wire m_first,m_last,
 output wire [4:0] m_k,output wire [3:0] m_n,output wire [15:0] m_offset,
 output wire [16*ABITS-1:0] m_a,output wire [1023:0] m_b
);
 reg head,tail,fill_slot,filling,half;
 reg [1:0] count;
 reg [1:0] full;
 reg [16*ABITS-1:0] av[0:1];reg [1023:0] bv[0:1];
 reg [2:0] cv[0:1];reg fv[0:1],lv[0:1];
 reg [4:0] kv[0:1];reg [3:0] nv[0:1];reg [15:0] ov[0:1];
 assign cmd_ready=!reset&&!filling&&count<2;
 assign dma_ready=!reset&&filling;
 assign fill_ack=dma_valid&&dma_ready&&half;
 assign m_valid=!reset&&count!=0&&full[head];
 assign m_ctx=cv[head];assign m_first=fv[head];assign m_last=lv[head];
 assign m_k=kv[head];assign m_n=nv[head];assign m_offset=ov[head];
 assign m_a=av[head];assign m_b=bv[head];
 wire push=cmd_valid&&cmd_ready,pop=m_valid&&m_ready;
 always @(posedge clk)begin
  if(reset)begin head<=0;tail<=0;count<=0;full<=0;filling<=0;half<=0;fill_slot<=0;end
  else begin
   case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
   if(push)begin
    cv[tail]<=cmd_ctx;fv[tail]<=cmd_first;lv[tail]<=cmd_last;kv[tail]<=cmd_k;nv[tail]<=cmd_n;ov[tail]<=cmd_offset;av[tail]<=cmd_a;
    fill_slot<=tail;filling<=1;half<=0;tail<=!tail;
   end
   if(dma_valid&&dma_ready)begin
    if(!half)begin bv[fill_slot][511:0]<=dma_data;half<=1;end
    else begin bv[fill_slot][1023:512]<=dma_data;full[fill_slot]<=1;filling<=0;half<=0;end
   end
   if(pop)begin full[head]<=0;head<=!head;end
  end
 end
endmodule
