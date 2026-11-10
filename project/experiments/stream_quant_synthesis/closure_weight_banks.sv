// Candidate 1088/1152-byte W8+FP16-scale records; M1--M10 active storage.
// 512-bit fill, 1024-bit M read, two-bank-word gather. No timing/area claim.
module closure_weight_banks #(parameter integer BANKS=4)(
 input wire clk,reset,cmd_valid,input wire cmd_release,cmd_long,input wire [2:0] cmd_bank,
 input wire [15:0] cmd_generation,output wire cmd_ready,
 input wire fill_valid,input wire [2:0] fill_bank,input wire [15:0] fill_generation,
 input wire [4:0] fill_index,input wire [511:0] fill_data,output wire fill_ready,
 input wire read_valid,input wire [2:0] read_bank,input wire [15:0] read_generation,
 input wire [2:0] read_index,output wire read_ready,
 output reg out_valid,input wire out_ready,output reg [1023:0] out_data,
 output reg [1023:0] out_scales,output reg [2:0] out_bank,out_index,
 output reg [15:0] out_generation,output reg fault
);
 localparam integer IDBITS=$clog2(BANKS);
 wire [IDBITS-1:0] cmd_id=IDBITS'(cmd_bank),fill_id=IDBITS'(fill_bank),read_id=IDBITS'(read_bank),out_id=IDBITS'(out_bank);
 reg [511:0] data[0:BANKS-1][0:17];
 reg [BANKS-1:0] live,long_record;reg [17:0] filled[0:BANKS-1];reg [7:0] consumed[0:BANKS-1];reg [15:0] generation[0:BANKS-1];
 assign cmd_ready=!reset&&!fault;
 assign fill_ready=!reset&&!fault;
 assign read_ready=!reset&&!fault&&(!out_valid||out_ready);
 always @(posedge clk)begin
  if(reset)begin
   live<=0;long_record<=0;fault<=0;out_valid<=0;out_data<=0;out_scales<=0;out_bank<=0;out_index<=0;out_generation<=0;
   for(integer i=0;i<BANKS;i=i+1)begin filled[i]<=0;consumed[i]<=0;generation[i]<=0;end
  end else if(!fault)begin
   if(out_valid&&out_ready)begin consumed[out_id][out_index]<=1;out_valid<=0;end
   if(cmd_valid&&cmd_ready)begin
    if(int'(cmd_bank)>=BANKS)fault<=1;
    else if(cmd_release)begin
     if(!live[cmd_id]||generation[cmd_id]!=cmd_generation||consumed[cmd_id]!=8'hff)fault<=1;
     else live[cmd_id]<=0;
    end else if(live[cmd_id]||generation[cmd_id]==cmd_generation)fault<=1;
    else begin live[cmd_id]<=1;generation[cmd_id]<=cmd_generation;long_record[cmd_id]<=cmd_long;filled[cmd_id]<=0;consumed[cmd_id]<=0;end
   end
   if(fill_valid&&fill_ready)begin
    if(int'(fill_bank)>=BANKS||fill_index>17)fault<=1;
    else if(!live[fill_id]||generation[fill_id]!=fill_generation||filled[fill_id][fill_index]||(!long_record[fill_id]&&fill_index==17))fault<=1;
    else begin data[fill_id][fill_index]<=fill_data;filled[fill_id][fill_index]<=1;end
   end
   if(read_valid&&read_ready)begin
    if(int'(read_bank)>=BANKS)fault<=1;
    else if(!live[read_id]||generation[read_id]!=read_generation||filled[read_id]!=(long_record[read_id]?18'h3ffff:18'h1ffff))fault<=1;
    else begin
     out_valid<=1;out_data<={data[read_id][{1'b0,read_index,1'b1}],data[read_id][{1'b0,read_index,1'b0}]};
     out_scales<={long_record[read_id]?data[read_id][17]:512'd0,data[read_id][16]};out_bank<=read_bank;out_index<=read_index;out_generation<=read_generation;
    end
   end
  end
 end
endmodule
