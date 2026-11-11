// Optional finite descriptor queue. One unchanged local-S request port, one
// compact E core, ordered writes/completions; independent reads may overlap E.
// Cross-client N/IO dependencies remain the caller's synchronization contract.
module pu_queued_e_service #(parameter integer DEPTH=2, SHIFT_WIDTH=5)(
 input wire clk,reset,cmd_valid,cmd_store,cmd_direct_a,output wire cmd_ready,
 input wire [1:0] cmd_sources,input wire [3:0] cmd_op,input wire [SHIFT_WIDTH-1:0] cmd_shift,
 input wire [29:0] cmd_src,input wire [9:0] cmd_dst,
 output wire done_valid,input wire done_ready,output wire done_error,done_saturated,
 output wire [127:0] done_data,
 output wire s_req_valid,s_req_write,input wire s_req_ready,
 output wire [9:0] s_req_addr,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,
 input wire direct_a_valid,direct_a_abort,output wire direct_a_ready,input wire [127:0] direct_a_data,
 output wire e_in_valid,input wire e_in_ready,output wire [3:0] e_in_op,
 output wire [SHIFT_WIDTH-1:0] e_in_shift,output wire [127:0] e_in_data,
 input wire e_out_valid,output wire e_out_ready,input wire [127:0] e_out_data,
 input wire e_out_error,e_out_saturated
);
 localparam integer PTR=$clog2(DEPTH), CNT=$clog2(DEPTH+1);
 localparam [2:0] FREE=0,READING=1,READY=2,EXECUTING=3,RESULT=4,DONE=5;
 reg [2:0] state[0:DEPTH-1];
 reg [PTR-1:0] head,tail;
 reg [CNT-1:0] count;
 reg [3:0] ops[0:DEPTH-1];reg [SHIFT_WIDTH-1:0] shifts[0:DEPTH-1];
 reg stores[0:DEPTH-1],directs[0:DEPTH-1],errors[0:DEPTH-1],saturated[0:DEPTH-1];
 reg [1:0] sources[0:DEPTH-1],read_count[0:DEPTH-1],sent_count[0:DEPTH-1];
 reg [29:0] addresses[0:DEPTH-1];reg [9:0] destinations[0:DEPTH-1];
 reg [127:0] operands_a[0:DEPTH-1],operands_b[0:DEPTH-1],operands_c[0:DEPTH-1],results[0:DEPTH-1];
 reg memory_busy,memory_write;
 reg [PTR-1:0] memory_slot;reg [1:0] memory_operand;
 reg read_found,issue_found,issue_blocked,response_found,hazard;
 reg [PTR-1:0] read_slot,issue_slot,response_slot;
 reg [9:0] read_address;
 reg [1:0] last_beat;
 integer idx,older;
 function automatic [PTR-1:0] next_slot(input [PTR-1:0] p);
  next_slot=p==PTR'(DEPTH-1)?PTR'(0):p+1'b1;
 endfunction
 always @* begin
  read_found=0;issue_found=0;issue_blocked=0;response_found=0;
  read_slot=0;issue_slot=0;response_slot=0;read_address=0;hazard=0;idx=0;older=0;
  for(integer n=0;n<DEPTH;n=n+1)begin
   idx=(int'(head)+n)%DEPTH;
   if(n<int'(count))begin
    if(!read_found && state[idx]==READING)begin read_found=1;read_slot=PTR'(idx);end
    if(!issue_blocked && (state[idx]==READING || state[idx]==READY))begin
     issue_blocked=1;
     if(state[idx]==READY)begin issue_found=1;issue_slot=PTR'(idx);end
    end
    if(!response_found && state[idx]==EXECUTING)begin response_found=1;response_slot=PTR'(idx);end
   end
  end
  if(read_found)begin
   read_address=addresses[read_slot][10*int'(read_count[read_slot])+:10];
   // Read-order plus in-order writes also preserve WAR/WAW. RAW waits for
   // every earlier destination's actual write ACK (state DONE), not E result.
   for(integer n=0;n<DEPTH;n=n+1)begin
    older=(int'(head)+n)%DEPTH;
    if(n<int'(count) && n<((int'(read_slot)-int'(head)+DEPTH)%DEPTH) &&
       stores[older] && state[older]!=DONE && destinations[older]==read_address)hazard=1;
   end
  end
  last_beat=(ops[issue_slot]==3||ops[issue_slot]==6)?2:
            (ops[issue_slot]==7||ops[issue_slot]==8||ops[issue_slot]>=10)?0:1;
 end
 wire writing=count!=0 && state[head]==RESULT && stores[head] && !errors[head];
 wire direct_wait=read_found && directs[read_slot] && read_count[read_slot]==0;
 wire reading=read_found && !direct_wait && !hazard;
 assign cmd_ready=!reset && count<CNT'(DEPTH);
 assign done_valid=!reset && count!=0 && state[head]==DONE;
 assign done_data=results[head];assign done_error=errors[head];assign done_saturated=saturated[head];
 assign s_req_valid=!reset && !memory_busy && (writing||reading);
 assign s_req_write=writing;
 assign s_req_addr=writing?destinations[head]:read_address;
 assign s_req_data=results[head];
 assign s_rsp_ready=!reset && memory_busy;
 assign direct_a_ready=!reset && !memory_busy && direct_wait;
 assign e_in_valid=!reset && issue_found;
 assign e_in_op=ops[issue_slot];assign e_in_shift=shifts[issue_slot];
 assign e_in_data=sent_count[issue_slot]==0?operands_a[issue_slot]:
                  sent_count[issue_slot]==1?operands_b[issue_slot]:operands_c[issue_slot];
 assign e_out_ready=!reset && response_found;
 always @(posedge clk)begin
  if(reset)begin
   head<=0;tail<=0;count<=0;memory_busy<=0;memory_slot<=0;memory_operand<=0;memory_write<=0;
   for(integer n=0;n<DEPTH;n=n+1)state[n]<=FREE;
  end else begin
   case({cmd_valid&&cmd_ready,done_valid&&done_ready})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:;
   endcase
   if(done_valid&&done_ready)begin state[head]<=FREE;head<=next_slot(head);end
   if(cmd_valid&&cmd_ready)begin
    state[tail]<=cmd_sources==0?READY:READING;tail<=next_slot(tail);
    ops[tail]<=cmd_op;shifts[tail]<=cmd_shift;stores[tail]<=cmd_store;directs[tail]<=cmd_direct_a;
    sources[tail]<=cmd_sources;addresses[tail]<=cmd_src;destinations[tail]<=cmd_dst;
    read_count[tail]<=0;sent_count[tail]<=0;errors[tail]<=0;saturated[tail]<=0;results[tail]<=0;
    operands_a[tail]<=0;operands_b[tail]<=0;operands_c[tail]<=0;
   end
   if(s_req_valid&&s_req_ready)begin
    memory_busy<=1;memory_write<=writing;memory_slot<=writing?head:read_slot;memory_operand<=read_count[read_slot];
   end
   if(s_rsp_valid&&s_rsp_ready)begin
    memory_busy<=0;
    if(memory_write)state[memory_slot]<=DONE;
    else begin
     case(memory_operand)
      0:operands_a[memory_slot]<=s_rsp_data;
      1:operands_b[memory_slot]<=s_rsp_data;
      2:operands_c[memory_slot]<=s_rsp_data;
      default:;
     endcase
     read_count[memory_slot]<=read_count[memory_slot]+1'b1;
     if(read_count[memory_slot]+1'b1==sources[memory_slot])state[memory_slot]<=READY;
    end
   end
   if(direct_a_ready)begin
    if(direct_a_abort)begin state[read_slot]<=RESULT;errors[read_slot]<=1;end
    else if(direct_a_valid)begin
     operands_a[read_slot]<=direct_a_data;read_count[read_slot]<=1;
     if(sources[read_slot]==1)state[read_slot]<=READY;
    end
   end
   if(e_in_valid&&e_in_ready)begin
    if(sent_count[issue_slot]==last_beat)state[issue_slot]<=EXECUTING;
    else sent_count[issue_slot]<=sent_count[issue_slot]+1'b1;
   end
   if(e_out_valid&&e_out_ready)begin
    results[response_slot]<=e_out_data;errors[response_slot]<=e_out_error;saturated[response_slot]<=e_out_saturated;
    state[response_slot]<=RESULT;
   end
   if(count!=0 && state[head]==RESULT && (!stores[head]||errors[head]))state[head]<=DONE;
  end
 end
 initial if(DEPTH!=2 && DEPTH!=4)$fatal(1,"E queue depth must be 2 or 4");
endmodule
