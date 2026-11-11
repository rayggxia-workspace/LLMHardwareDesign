// Finite S512 -> A128/B512 loader. This is real synthesizable active logic,
// included in the fixed S macro below, not assumed to exist in M11/M12.
// Two512-bit A entries plus one512-bit B entry; one memory read outstanding.
// A/B may retire together. Four A containers share a wide read. No serialized
// B128 path and no unbounded software FIFO.
module block_feed_loader #(parameter integer ENABLE_REUSE_A = 0,
 parameter integer ENABLE_SKIP_A = 0) (
 input wire clk,reset,
 input wire load_valid,output wire load_ready,
 input wire load_bank,input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,load_reuse_b,
 input wire load_skip_a,
 input wire [9:0] load_a_base,load_b_base,
 output reg done_valid,input wire done_take,output reg done_error,
 output reg busy,
 output wire mem_req,output wire [7:0] mem_addr,input wire mem_ready,
 input wire mem_valid,output wire mem_take,input wire [511:0] mem_data,
 output wire a_valid,input wire a_ready,output wire a_bank,
 output wire [2:0] a_row,output wire [1:0] a_tile,
 output wire a_wide,output wire [127:0] a_data,
 output wire b_valid,input wire b_ready,output wire b_bank,
 output wire [1:0] b_tile,output wire b_wide,b_half,
 output wire [511:0] b_data
);
 reg bank,aw,bw,reuse_b,skip_a;reg [3:0] rows;reg [2:0] tiles;
 wire requested_skip_a=ENABLE_SKIP_A!=0 && load_skip_a;
 reg [7:0] abase,bbase;
 reg [1:0] tile;reg phase_a,group_a,half_b,requests_done,pending;
 reg p_is_b,p_half;reg [1:0] p_tile;reg [2:0] p_row;
 reg [511:0] queue_data[0:1];reg [511:0] weight_data;reg weight_valid,weight_half;
 reg [1:0] weight_tile;
 reg [1:0] queue_tile[0:1];reg [2:0] queue_row[0:1];
 reg head,tail;reg [1:0] count;reg [1:0] a_word;
 assign load_ready=!reset&&!busy&&!done_valid;
 assign a_valid=!reset&&busy&&count!=0;
 assign b_valid=!reset&&busy&&weight_valid;
 assign a_bank=bank;assign a_row=queue_row[head]+{1'b0,a_word};
 assign a_tile=queue_tile[head];assign a_wide=aw;
 assign a_data=queue_data[head][128*int'(a_word)+:128];
 assign b_bank=bank;assign b_tile=weight_tile;assign b_wide=bw;
 assign b_half=weight_half;assign b_data=weight_data;
 wire a_fire=a_valid&&a_ready;
 wire b_fire=b_valid&&b_ready;
 wire pop=a_fire&&(a_word==3||{1'b0,a_row}+1==rows);
 wire space=count<2||pop;
 wire weight_space=!weight_valid||b_fire;
 wire received;
 // Retire a read response and issue its successor on the same edge. The
 // synchronous S response register remains the sole outstanding read slot.
 assign mem_req=!reset&&busy&&!requests_done&&(!pending||received)&&(phase_a?space:weight_space);
 // Byte ordering: a tile stores ceil(rows/4) complete 512-bit groups, each
 // containing four 128-bit A containers. B stores 64B (S8) or128B (S16).
 wire [7:0] a_line=abase+({6'b0,tile}<<(rows>4?1:0))+{7'b0,group_a};
 wire [7:0] b_line=bbase+({6'b0,tile}<<(bw?1:0))+{7'b0,half_b};
 assign mem_addr=phase_a?a_line:b_line;
 assign mem_take=!reset&&busy&&pending&&(p_is_b?weight_space:space);
 assign received=mem_valid&&mem_take;
 wire push=received&&!p_is_b;
 // Optional rows=0 is an explicit B-only transfer. It never invents A validity;
 // the M command still checks the retained operand bank and format.
 wire b_only=ENABLE_REUSE_A!=0 && load_rows==0 && !load_reuse_b;
 wire legal=((load_rows>0&&load_rows<=8)||b_only)&&load_tiles>0&&load_tiles<=4&&
     (requested_skip_a||load_a_base[1:0]==0)&&load_b_base[1:0]==0&&
     (requested_skip_a||b_only||int'(load_a_base)+int'(load_tiles)*(load_rows>4?8:4)<=1024)&&
     (load_reuse_b||int'(load_b_base)+int'(load_tiles)*(load_b_wide?8:4)<=1024);
 always @(posedge clk)begin
  if(reset)begin
   busy<=0;done_valid<=0;done_error<=0;bank<=0;aw<=0;bw<=0;reuse_b<=0;
   rows<=0;tiles<=0;abase<=0;bbase<=0;tile<=0;phase_a<=0;group_a<=0;half_b<=0;skip_a<=0;
   requests_done<=0;pending<=0;head<=0;tail<=0;count<=0;a_word<=0;
   p_is_b<=0;p_half<=0;p_tile<=0;p_row<=0;weight_valid<=0;weight_half<=0;weight_tile<=0;
  end else begin
   if(done_valid&&done_take)done_valid<=0;
   if(load_valid&&load_ready)begin
    done_error<=!legal;
    if(!legal)done_valid<=1;
    else begin
     busy<=1;bank<=load_bank;rows<=load_rows;tiles<=load_tiles;
     aw<=load_a_wide;bw<=load_b_wide;reuse_b<=load_reuse_b;skip_a<=requested_skip_a;
     abase<=load_a_base[9:2];bbase<=load_b_base[9:2];
     tile<=0;phase_a<=load_reuse_b&&!requested_skip_a;group_a<=0;half_b<=0;
     requests_done<=requested_skip_a&&load_reuse_b;pending<=0;head<=0;tail<=0;count<=0;a_word<=0;weight_valid<=0;
    end
   end
   if(received)pending<=0;
   if(mem_req&&mem_ready)begin
    pending<=1;p_is_b<=!phase_a;p_half<=half_b;p_tile<=tile;p_row<=group_a?4:0;
    if(!phase_a)begin
     if(bw&&!half_b)half_b<=1;
     else begin
      half_b<=0;
      if(rows==0||skip_a)begin
       if({1'b0,tile}+1==tiles)requests_done<=1;
       else tile<=tile+1'b1;
      end else phase_a<=1;
     end
    end else if(rows>4&&!group_a)group_a<=1;
    else begin
     group_a<=0;
     if({1'b0,tile}+1==tiles)requests_done<=1;
     else begin tile<=tile+1'b1;phase_a<=reuse_b;end
    end
   end
   if(b_fire)weight_valid<=0;
   if(received&&p_is_b)begin
    weight_data<=mem_data;weight_valid<=1;weight_half<=p_half;weight_tile<=p_tile;
   end
   if(push)begin
    queue_data[tail]<=mem_data;queue_tile[tail]<=p_tile;queue_row[tail]<=p_row;
    tail<=!tail;
   end
   if(a_fire&&!pop)a_word<=a_word+1'b1;
   if(pop)begin head<=!head;a_word<=0;end
   case({push,pop})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:begin end
   endcase
   if(busy&&requests_done&&!pending&&count==0&&!weight_valid)begin
    busy<=0;done_valid<=1;done_error<=0;
   end
  end
 end
endmodule
