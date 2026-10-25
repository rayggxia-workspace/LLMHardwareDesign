module wide_block #(parameter LOCAL=1)(input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [31:0] cmd_pc,cmd_limit,input wire [2:0] cmd_lane,input wire [15:0] cmd_tag,
 output wire busy,done,input wire done_ready,output wire [7:0] status,output wire [15:0] tag,
 input wire cfg_valid,cfg_write,input wire [4:0] cfg_addr,input wire [127:0] cfg_data,
 output wire cfg_ready,cfg_response,input wire cfg_take,output wire [127:0] cfg_result,
 output wire ext_req,ext_write,output wire [31:0] ext_addr,output wire [127:0] ext_wdata,
 input wire ext_ready,ext_valid,output wire ext_take,input wire [127:0] ext_rdata,
 output wire wire_valid,output wire [127:0] wire_data,
 output wire [63:0] cycles,output wire [31:0] actions,fetches,frame_reads,frame_writes,rom_reads,wire_beats,transactions,
 output wire [7:0] debug_state);
 wire ecmd_ready;reg cfg_pending;
 wire m_req,m_wr,m_ready,m_valid,m_take;wire [31:0] m_addr;wire [127:0] m_din,m_dout;
 wire lf_req,lf_wr,lf_ready,lf_valid,lf_take;wire [4:0] lf_addr;wire [127:0] lf_din,lf_dout;
 wire t_req,t_wr,t_ready,t_valid,t_take;wire [31:0] t_addr;wire [127:0] t_din,t_dout;
 wire r_req,r_wr,r_ready,r_valid,r_take;wire [4:0] r_addr;wire [127:0] r_din,r_dout;
 wire lut_req,lut_valid;wire [14:0] lut_addr;wire [31:0] lut_data;
 wire target_frame=t_addr[28];
 wire use_cfg=cfg_valid&&!busy&&!cfg_pending;
 assign cmd_ready=ecmd_ready&&!cfg_pending&&!cfg_valid;
 assign cfg_ready=!busy&&!cfg_pending&&r_ready;
 assign cfg_response=cfg_pending&&r_valid;assign cfg_result=r_dout;
 always @(posedge clk)begin if(reset)cfg_pending<=0;else if(cfg_valid&&cfg_ready)cfg_pending<=1;else if(cfg_response&&cfg_take)cfg_pending<=0;end
 wide_engine #(LOCAL) engine(clk,reset,cmd_valid&&cmd_ready,ecmd_ready,cmd_pc,cmd_limit,cmd_lane,cmd_tag,busy,done,done_ready,status,tag,
 m_req,m_wr,m_addr,m_din,m_ready,m_valid,m_take,m_dout,
 lf_req,lf_wr,lf_addr,lf_din,lf_ready,lf_valid,lf_take,lf_dout,
 lut_req,lut_addr,lut_valid,lut_data,cycles,actions,fetches,frame_reads,frame_writes,rom_reads,debug_state);
 memory_link link(clk,reset,m_req,m_wr,m_addr,m_din,m_ready,m_valid,m_take,m_dout,
 t_req,t_wr,t_addr,t_din,t_ready,t_valid,t_take,t_dout,wire_valid,wire_data,wire_beats,transactions);
 assign ext_req=t_req&&!target_frame;assign ext_write=t_wr;assign ext_addr=t_addr;assign ext_wdata=t_din;assign ext_take=t_take&&!target_frame;
 assign t_ready=target_frame?(LOCAL==0&&r_ready&&!cfg_pending&&!use_cfg):ext_ready;
 assign t_valid=target_frame?(LOCAL==0&&r_valid&&!cfg_pending):ext_valid;
 assign t_dout=target_frame?r_dout:ext_rdata;
 assign r_req=use_cfg ? cfg_valid : (LOCAL!=0?lf_req:(t_req&&target_frame&&!cfg_pending));
 assign r_wr=use_cfg?cfg_write:(LOCAL!=0?lf_wr:t_wr);
 assign r_addr=use_cfg?cfg_addr:(LOCAL!=0?lf_addr:t_addr[8:4]);
 assign r_din=use_cfg?cfg_data:(LOCAL!=0?lf_din:t_din);
 assign r_take=cfg_pending?cfg_take:(LOCAL!=0?lf_take:(t_take&&target_frame));
 assign lf_ready=r_ready&&!cfg_pending&&!use_cfg;assign lf_valid=r_valid&&!cfg_pending;assign lf_dout=r_dout;
 ram128 frame(clk,reset,r_req,r_wr,r_addr,r_din,r_ready,r_valid,r_take,r_dout);
 lut32 rom(clk,reset,lut_req,lut_addr,lut_valid,lut_data);
endmodule
