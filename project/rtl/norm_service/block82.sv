module block82 #(parameter PROFILE=0)(input wire clk,reset,cmd,mem_hold,output wire mem_request,input wire [11:0] h,input wire [31:0] epsilon,
 output wire busy,done,input wire ack,output wire [7:0] status,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,
 output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output wire [63:0] cycles,output wire [31:0] reads,writes,output wire [7:0] debug_state);
 wire req,wr,ready,valid,take;wire [9:0] addr;wire [127:0] din,dout;reg pending;
 assign mem_request=req;
 wire usecfg=!busy&&cfg;assign cfg_ready=!busy&&!pending&&ready;assign cfg_valid=pending&&valid;assign cfg_dout=dout;
 always @(posedge clk)begin if(reset)pending<=0;else if(cfg&&cfg_ready)pending<=1;else if(cfg_valid&&cfg_take)pending<=0;end
 norm82 #(PROFILE) norm(clk,reset,cmd&&!pending&&!cfg,h,epsilon,busy,done,ack,status,req,wr,addr,din,ready&&!pending&&!mem_hold,valid&&!pending,take,dout,cycles,reads,writes,debug_state);
 store82 frame(clk,reset,usecfg?cfg:(req&&!mem_hold),usecfg?cfg_wr:wr,usecfg?cfg_addr:addr,usecfg?cfg_din:din,ready,valid,pending?cfg_take:take,dout);
endmodule
