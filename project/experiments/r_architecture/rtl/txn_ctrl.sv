// Global transaction publication, shared by every explored architecture.
// Outstanding writes must drain before commit, abort completion, or reset reuse.
module txn_ctrl #(parameter CONTEXTS=24)(
 input wire clk,reset,dma_idle,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,input wire [4:0] cmd_context,
 input wire [31:0] cmd_owner,cmd_epoch,cmd_position,cmd_next,
 output reg rsp_valid,input wire rsp_ready,output reg rsp_error,output reg [127:0] rsp_data,
 output wire pending,output wire [31:0] outstanding,output wire published_role
);
 reg [CONTEXTS-1:0] valid,version;
 reg [31:0] owner[0:CONTEXTS-1],epoch[0:CONTEXTS-1],position[0:CONTEXTS-1];
 reg active,aborting,failed,computed;reg [4:0] active_context;
 reg [31:0] writes;
 assign cmd_ready=!reset&&(!rsp_valid||rsp_ready);
 assign pending=active;assign outstanding=writes;assign published_role=active_context<CONTEXTS?version[active_context]:1'b0;
 wire identity=cmd_context<CONTEXTS&&valid[cmd_context]&&owner[cmd_context]==cmd_owner&&epoch[cmd_context]==cmd_epoch&&position[cmd_context]==cmd_position;
 always @(posedge clk)begin
  if(reset)begin valid<=0;version<=0;active<=0;aborting<=0;failed<=0;computed<=0;active_context<=0;writes<=0;rsp_valid<=0;rsp_error<=0;rsp_data<=0;end
  else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    rsp_valid<=1;rsp_error<=0;rsp_data<=0;
    if(cmd_context>=CONTEXTS)rsp_error<=1;
    else case(cmd_op)
     0:if(active||!dma_idle||cmd_owner==0)rsp_error<=1;else begin valid[cmd_context]<=1;version[cmd_context]<=0;owner[cmd_context]<=cmd_owner;epoch[cmd_context]<=cmd_epoch;position[cmd_context]<=cmd_position;end
     1:if(active||!dma_idle||!identity)rsp_error<=1;else begin active<=1;active_context<=cmd_context;aborting<=0;failed<=0;computed<=0;writes<=0;end
     2:if(!active||aborting||active_context!=cmd_context||writes==32'hffffffff)rsp_error<=1;else writes<=writes+1'b1;
     3:if(!active||active_context!=cmd_context||writes==0)rsp_error<=1;else begin writes<=writes-1'b1;if(aborting&&writes==1)begin active<=0;aborting<=0;end end
     4:if(!active||aborting||active_context!=cmd_context)rsp_error<=1;else begin computed<=1;failed<=failed||cmd_next[0];end
     5:if(!active||active_context!=cmd_context)rsp_error<=1;else if(writes==0)begin active<=0;aborting<=0;end else aborting<=1;
     6:if(!active||aborting||failed||!computed||writes!=0||!identity||active_context!=cmd_context||epoch[active_context]==32'hffffffff)rsp_error<=1;
       else begin version[active_context]<=!version[active_context];epoch[active_context]<=epoch[active_context]+1'b1;position[active_context]<=cmd_next;active<=0;end
     7:if(!valid[cmd_context])rsp_error<=1;else rsp_data<={owner[cmd_context],position[cmd_context],epoch[cmd_context],31'd0,version[cmd_context]};
     default:rsp_error<=1;
    endcase
   end
  end
 end
endmodule
