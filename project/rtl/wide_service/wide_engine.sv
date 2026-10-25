// Entire instruction/address/control sequencing is RTL. Program memory is explicit.
module wide_engine #(parameter LOCAL=1)(
 input wire clk,reset,input wire cmd_valid,output wire cmd_ready,
 input wire [31:0] cmd_pc,cmd_limit,input wire [2:0] cmd_lane,input wire [15:0] cmd_tag,
 output wire busy,output wire done,input wire done_ready,output reg [7:0] status,output reg [15:0] tag,
 output wire mem_req,mem_write,output wire [31:0] mem_addr,output wire [127:0] mem_wdata,
 input wire mem_ready,mem_valid,output wire mem_take,input wire [127:0] mem_rdata,
 output wire f_req,f_write,output wire [4:0] f_addr,output wire [127:0] f_wdata,
 input wire f_ready,f_valid,output wire f_take,input wire [127:0] f_rdata,
 output wire lut_req,output wire [14:0] lut_addr,input wire lut_valid,input wire [31:0] lut_data,
 output reg [63:0] cycles,output reg [31:0] actions,fetches,frame_reads,frame_writes,rom_reads,
 output wire [7:0] debug_state);
 localparam IDLE=0,FETCH=1,ICACHE=2,DECODE=3,READOP=4,OPRET=5,EXEC=6,ALUWAIT=7,
 WPREP=8,RMW=9,WNEXT=10,ADVANCE=11,REQ=12,WAITR=13,TABLE=14,ROMWAIT=15,DONE=16;
 reg [7:0] state,continuation;
 reg [31:0] pc,limit,cache_line,table_word,stack[0:3]; reg [2:0] sp,lane;
 reg [63:0] inst;reg [127:0] cache,reply;reg cache_valid;
 reg [1:0] phase;reg [9:0] spec;reg [8:0] byte_addr,write_addr;reg [7:0] write_byte;
 reg [63:0] ar,br,cr;reg [31:0] opcodes;
 wire [7:0] alu_response;wire [63:0] alu_lo,alu_hi;
 reg [7:0] result_lo,result_hi;reg write_high;reg [2:0] lut_offset;reg lut_store;reg [31:0] lut_word;
 reg req_is_frame,req_wr;reg [31:0] req_addr;reg [127:0] req_data;
 wire [3:0] op=inst[3:0];wire waiting_local=(LOCAL!=0)&&req_is_frame;
 wire rready=waiting_local ? f_ready:mem_ready;
 wire rval=waiting_local ? f_valid:mem_valid;
 wire [127:0] rdata=waiting_local ? f_rdata:mem_rdata;
 wire [63:0] table_entry=table_word[0]?reply[127:64]:reply[63:0];
 wire [31:0] call_index=inst[45:14]+{24'b0,ar[8*lane+:8]};
 assign debug_state=state;assign cmd_ready=state==IDLE;assign busy=state!=IDLE;assign done=state==DONE;
 assign mem_req=state==REQ&&!waiting_local;assign mem_write=req_wr;
 assign mem_addr=req_is_frame ? (32'h10000000|req_addr) : req_addr;assign mem_wdata=req_data;
 assign mem_take=state==WAITR&&!waiting_local;
 assign f_req=state==REQ&&waiting_local;assign f_write=req_wr;assign f_addr=req_addr[8:4];assign f_wdata=req_data;
 assign f_take=state==WAITR&&waiting_local;
 assign lut_req=state==EXEC&&op==13&&br[8*lane+:8]<128;
 assign lut_addr={br[8*lane+:7],ar[8*lane+:8]};
 byte_alu alu(clk,reset,(state==EXEC&&op<=11&&!(inst[54]&&ar[8*lane+:8]!=1))?(8'b1<<lane):8'b0,
 opcodes,ar,br,cr,alu_response,alu_lo,alu_hi);
 task access(input isframe,input wr,input [31:0] addr,input [127:0] dat,input [7:0] nextstate);
 begin req_is_frame<=isframe;req_wr<=wr;req_addr<=addr;req_data<=dat;continuation<=nextstate;state<=REQ;end endtask
 task fail(input [7:0] code);begin status<=code;state<=DONE;end endtask
 always @* begin
  if(phase==0)spec=inst[13:4];else if(phase==1)spec=inst[23:14];else spec=inst[33:24];
  if(op==12&&phase!=0)spec=10'h200;
  if(op==13&&phase==2)spec=10'h200;
  byte_addr=spec[8:0];
  if(lut_store)begin write_addr=inst[42:34]+lut_offset;write_byte=lut_word[8*lut_offset+:8];end
  else begin write_addr=write_high?inst[51:43]:inst[42:34];write_byte=write_high?result_hi:result_lo;end
 end
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;status<=0;tag<=0;pc<=0;limit<=0;lane<=0;sp<=0;cache_valid<=0;cache<=0;cache_line<=0;
   inst<=0;phase<=0;ar<=0;br<=0;cr<=0;opcodes<=0;reply<=0;cycles<=0;actions<=0;fetches<=0;frame_reads<=0;frame_writes<=0;rom_reads<=0;
   req_is_frame<=0;req_wr<=0;req_addr<=0;req_data<=0;continuation<=0;result_lo<=0;result_hi<=0;write_high<=0;lut_store<=0;lut_offset<=0;lut_word<=0;table_word<=0;
  end else begin
   if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
   if(state!=IDLE&&state!=DONE&&cycles>=64'd64000000)fail(8);
   else case(state)
   IDLE:if(cmd_valid)begin pc<=cmd_pc;limit<=cmd_limit;lane<=cmd_lane;tag<=cmd_tag;status<=0;sp<=0;cache_valid<=0;cycles<=0;actions<=0;fetches<=0;frame_reads<=0;frame_writes<=0;rom_reads<=0;
    if(cmd_limit==0||cmd_limit>32'h1000000||cmd_pc>=cmd_limit)fail(1);else state<=FETCH;end
   FETCH:if(pc>=limit)fail(1);else if(cache_valid&&cache_line=={pc[31:1],1'b0})begin inst<=pc[0]?cache[127:64]:cache[63:0];state<=DECODE;end
    else begin fetches<=fetches+1;access(0,0,{pc[28:1],4'b0},0,ICACHE);end
   ICACHE:begin cache<=reply;cache_line<={pc[31:1],1'b0};cache_valid<=1;inst<=pc[0]?reply[127:64]:reply[63:0];state<=DECODE;end
   DECODE:begin phase<=0;lut_store<=0;write_high<=0;lut_offset<=0;
    if(op<=11)begin if(inst[63:55]!=0||((op!=11)&&inst[54]))fail(2);else state<=READOP;end
    else if(op==12)begin if(inst[63:54]!=0)fail(2);else state<=READOP;end
    else if(op==13)begin if(inst[63:43]!=0||inst[42:34]>508)fail(2);else state<=READOP;end
    else if((op==14&&inst!=64'd14)||(op==15&&inst!=64'd15))fail(2);
    else state<=EXEC;
   end
   READOP:if(phase==3)begin opcodes[4*lane+:4]<=op;state<=EXEC;end
    else if(spec[9])begin
     if(spec[8])fail(2);else begin
      if(phase==0)ar[8*lane+:8]<=spec[7:0];else if(phase==1)br[8*lane+:8]<=spec[7:0];else cr[8*lane+:8]<=spec[7:0];phase<=phase+1;
     end
    end else begin frame_reads<=frame_reads+1;access(1,0,{23'b0,byte_addr[8:4],4'b0},0,OPRET);end
   OPRET:begin if(phase==0)ar[8*lane+:8]<=reply[8*byte_addr[3:0]+:8];else if(phase==1)br[8*lane+:8]<=reply[8*byte_addr[3:0]+:8];else cr[8*lane+:8]<=reply[8*byte_addr[3:0]+:8];phase<=phase+1;state<=READOP;end
   EXEC:if(op<=11)begin if(inst[54]&&ar[8*lane+:8]!=1)fail(7);else begin actions<=actions+1;state<=ALUWAIT;end end
    else if(op==12)begin
     if(sp>=4)fail(3);else if(ar[8*lane+:8]>inst[53:46])fail(4);
     else if(inst[45:14]>=limit||{24'b0,ar[8*lane+:8]}>=limit-inst[45:14])fail(1);
     else begin table_word<=call_index;access(0,0,(call_index&32'hfffffffe)<<3,0,TABLE);end
    end else if(op==14)begin if(sp==0)fail(3);else begin sp<=sp-1;pc<=stack[sp-1];state<=FETCH;end end
    else if(op==15)begin if(sp!=0)fail(3);else state<=DONE;end
    else if(op==13)begin if(br[8*lane+:8]>=128)fail(5);else begin rom_reads<=rom_reads+1;state<=ROMWAIT;end end
    else fail(2);
   ALUWAIT:if(alu_response[lane])begin result_lo<=alu_lo[8*lane+:8];result_hi<=alu_hi[8*lane+:8];write_high<=0;if(inst[53])state<=WPREP;else if(inst[52])begin write_high<=1;state<=WPREP;end else state<=ADVANCE;end
   WPREP:begin frame_reads<=frame_reads+1;access(1,0,{23'b0,write_addr[8:4],4'b0},0,RMW);end
   RMW:begin req_data<=reply;req_data[8*write_addr[3:0]+:8]<=write_byte;req_is_frame<=1;req_wr<=1;req_addr<={23'b0,write_addr[8:4],4'b0};continuation<=WNEXT;frame_writes<=frame_writes+1;state<=REQ;end
   WNEXT:if(lut_store)begin if(lut_offset==3)state<=ADVANCE;else begin lut_offset<=lut_offset+1;state<=WPREP;end end
    else if(!write_high&&inst[52])begin write_high<=1;state<=WPREP;end else state<=ADVANCE;
   ADVANCE:begin pc<=pc+1;state<=FETCH;end
   REQ:if(rready)state<=WAITR;
   WAITR:if(rval)begin reply<=rdata;state<=continuation;end
   TABLE:if(table_word>=limit||table_entry[63:32]!=0||table_entry[31:0]>=limit)fail(1);else begin stack[sp]<=pc+1;sp<=sp+1;pc<=table_entry[31:0];state<=FETCH;end
   ROMWAIT:if(lut_valid)begin lut_word<=lut_data;lut_store<=1;lut_offset<=0;state<=WPREP;end
   DONE:if(done_ready)state<=IDLE;
   default:fail(2);
   endcase
  end
 end
endmodule
