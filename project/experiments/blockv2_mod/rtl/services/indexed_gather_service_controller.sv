// Index read determines the address; payload uses bounded DDR/SRAM overlap.
module indexed_gather_service_controller #(parameter logic [31:0] TOPOLOGY=0)(
 input wire clk,
 input wire reset,
 input wire service_valid,
 output wire service_ready,
 input wire [127:0] service_owner,
 input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,
 output wire service_cancel_ready,
 output wire service_done_valid,
 input wire service_done_ready,
 output reg [127:0] service_done_owner,
 output reg [31:0] service_done_ticket,
 output reg [15:0] service_done_status,
 output reg [31:0] service_done_read_bytes,
 output reg [31:0] service_done_write_bytes,
 output wire rd_valid,
 input wire rd_ready,
 output wire [63:0] rd_address,
 output wire [63:0] rd_tag,
 input wire rd_rsp_valid,
 output wire rd_rsp_ready,
 input wire [63:0] rd_rsp_tag,
 input wire [511:0] rd_rsp_data,
 input wire rd_rsp_error,
 output wire s_req_valid,
 output wire s_req_write,
 input wire s_req_ready,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 input wire s_rsp_error
);
 localparam [2:0] IDLE=0,READ_REQ=1,READ_WAIT=2,DECODE_INDEX=3,LOAD_LAUNCH=4,LOAD_WAIT=5,REPORT=6;
 localparam [15:0] BAD_DESC=16'h0360,ABORTED=16'h0361,DDR_FAULT=16'h0362,
 BAD_INDEX=16'h0363,SRAM_FAULT=16'h0364;
 reg [2:0] state;reg cancelled,index_read,index_held,index_fault;
 reg [31:0] session,sequence_number,rows,offset;
 reg [63:0] table_address,read_address;reg [511:0] line;
 reg [7:0] row_shift,index_bytes;reg [5:0] index_offset;
 reg [15:0] remaining;reg [9:0] destination;reg [1:0] lane;
 wire [63:0] dt=service_descriptor[128+:64],di=service_descriptor[192+:64];
 wire [31:0] dn=service_descriptor[256+:32],dof=service_descriptor[288+:32];
 wire [15:0] db=service_descriptor[320+:16],ds=service_descriptor[336+:16];
 wire [7:0] dl=service_descriptor[352+:8],dw=service_descriptor[360+:8];
 wire [63:0] row_bytes=64'd1<<dl;
 wire [63:0] table_end=dt+({32'd0,dn}<<dl);
 wire legal=TOPOLOGY!=0&&service_descriptor[0+:32]==32'h32485447&&
 service_descriptor[32+:16]==128&&service_descriptor[48+:16]==1&&
 service_descriptor[64+:32]==32'h02504402&&service_descriptor[96+:32]==TOPOLOGY&&
 service_descriptor[991:368]==0&&dl>=6&&dl<=24&&dn!=0&&dt[63:48]==0&&dt[5:0]==0&&
 table_end>dt&&table_end<=64'h1000000000000&&
 di[63:48]==0&&((dw==4&&di[1:0]==0)||(dw==8&&di[2:0]==0))&&
 db!=0&&db<=16384&&db[5:0]==0&&dof[5:0]==0&&({32'd0,dof}+{48'd0,db})<=row_bytes&&
 ({1'b0,ds}+({1'b0,db}>>4))<=1024&&session!=32'hffffffff;
 wire cancel_now=cancelled||(service_cancel_valid&&service_cancel_ready);
 wire [511:0] shifted=line>>(index_offset*8);
 wire signed [63:0] signed_index=index_bytes==4?{{32{shifted[31]}},shifted[31:0]}:shifted[63:0];
 wire signed [64:0] normalized={signed_index[63],signed_index}+
 (signed_index[63]?$signed({33'd0,rows}):65'sd0);
 assign service_ready=!reset&&state==IDLE;
 assign service_cancel_ready=!reset&&state!=IDLE&&state!=REPORT&&!cancelled;
 assign service_done_valid=!reset&&state==REPORT;

 wire load_ready,load_done,load_error,load_rd_valid,load_rd_ready,load_rsp_ready,load_s_valid,load_s_ready;
 wire [63:0] load_address,load_tag;wire [9:0] load_s_address;wire [127:0] load_s_data;
 wire [31:0] load_s_tag;wire load_s_rsp_ready;
 reg [10:0] write_acks;reg payload_sram_error;
 wire payload_active=state==LOAD_LAUNCH||state==LOAD_WAIT;
 wire payload_match=rd_rsp_tag[63:8]=={session,24'd1};
 assign rd_valid=!reset&&((state==READ_REQ&&(!cancel_now||index_held))||(payload_active&&load_rd_valid));
 assign rd_address=payload_active?load_address:read_address;
 assign rd_tag=payload_active?{session,24'd1,load_tag[7:0]}:{session,32'd0};
 assign rd_rsp_ready=!reset&&((state==READ_WAIT)||(payload_active&&load_rsp_ready));
 assign s_req_valid=payload_active&&load_s_valid;assign s_req_write=1;
 assign s_req_address=load_s_address;assign s_req_data=load_s_data;
 assign s_rsp_ready=payload_active&&load_s_rsp_ready;
 wire [9:0] ack_address=destination+write_acks[9:0];
 s128_ddr_range_load payload_loader(
 .clk,.reset,.cancel(cancel_now),.launch_valid(state==LOAD_LAUNCH),.launch_ready(load_ready),
 .launch_base(read_address),.launch_s_base(destination),.launch_bursts(remaining[14:6]),
 .launch_pair(1'b0),.launch_pair_beat(1'b0),.launch_pair_high(1'b0),
 .done_valid(load_done),.done_error(load_error),.done_ready(state==LOAD_WAIT),
 .rd_valid(load_rd_valid),.rd_ready(payload_active&&rd_ready),.rd_address(load_address),.rd_tag(load_tag),
 .rd_rsp_valid(payload_active&&rd_rsp_valid),.rd_rsp_ready(load_rsp_ready),
 .rd_rsp_tag(payload_match?{56'd0,rd_rsp_tag[7:0]}:64'hffffffffffffffff),
 .rd_rsp_data,.rd_rsp_error,
 .s_valid(load_s_valid),.s_ready(payload_active&&s_req_ready),.s_address(load_s_address),
 .s_data(load_s_data),.s_tag(load_s_tag),.s_rsp_valid(payload_active&&s_rsp_valid),
 .s_rsp_ready(load_s_rsp_ready),.s_rsp_error,.s_rsp_tag({22'h12a000,ack_address}));
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;cancelled<=0;index_held<=0;index_fault<=0;index_read<=0;session<=0;sequence_number<=0;rows<=0;offset<=0;
   table_address<=0;read_address<=0;line<=0;row_shift<=0;index_bytes<=0;index_offset<=0;
   remaining<=0;destination<=0;lane<=0;service_done_owner<=0;service_done_ticket<=0;
   service_done_status<=0;service_done_read_bytes<=0;service_done_write_bytes<=0;
   write_acks<=0;payload_sram_error<=0;
  end else begin
   if(service_cancel_valid&&service_cancel_ready)cancelled<=1;
   if(state==READ_REQ&&rd_valid)index_held<=!rd_ready;
   if(payload_active&&rd_rsp_valid&&rd_rsp_ready&&payload_match&&!rd_rsp_error)
    service_done_read_bytes<=service_done_read_bytes+64;
   if(payload_active&&s_rsp_valid&&s_rsp_ready)begin
    write_acks<=write_acks+1;
    if(s_rsp_error)payload_sram_error<=1;
    else service_done_write_bytes<=service_done_write_bytes+16;
   end
   case(state)
    IDLE:if(service_valid&&service_ready)begin
     service_done_owner<=service_owner;service_done_ticket<=service_ticket;
     service_done_status<=legal?0:BAD_DESC;service_done_read_bytes<=0;service_done_write_bytes<=0;
     cancelled<=0;index_held<=0;index_fault<=0;index_read<=1;session<=session+1;sequence_number<=0;
     table_address<=dt;read_address<={di[63:6],6'd0};rows<=dn;offset<=dof;
     row_shift<=dl;index_bytes<=dw;index_offset<=di[5:0];
     remaining<=db;destination<=ds[9:0];lane<=0;write_acks<=0;payload_sram_error<=0;
     state<=legal?READ_REQ:REPORT;
    end
    READ_REQ:if(cancel_now&&!index_held)begin service_done_status<=ABORTED;state<=REPORT;end
     else if(rd_ready)state<=READ_WAIT;
    READ_WAIT:if(rd_rsp_valid)begin
     if(rd_rsp_tag!=rd_tag)index_fault<=1;
     else if(rd_rsp_error||index_fault)begin service_done_status<=DDR_FAULT;state<=REPORT;end
     else begin
      service_done_read_bytes<=service_done_read_bytes+64;
      if(cancel_now)begin service_done_status<=ABORTED;state<=REPORT;end
      else begin line<=rd_rsp_data;state<=DECODE_INDEX;end
     end
    end
    DECODE_INDEX:begin
     if(normalized<0||normalized>=$signed({33'd0,rows}))begin service_done_status<=BAD_INDEX;state<=REPORT;end
     else if(cancel_now)begin service_done_status<=ABORTED;state<=REPORT;end
     else begin read_address<=table_address+($unsigned(normalized[63:0])<<row_shift)+offset;state<=LOAD_LAUNCH;end
    end
    LOAD_LAUNCH:if(load_ready)state<=LOAD_WAIT;
    LOAD_WAIT:if(load_done)begin
     if(load_error)service_done_status<=payload_sram_error?SRAM_FAULT:DDR_FAULT;
     else if(cancel_now)service_done_status<=ABORTED;
     state<=REPORT;
    end
    REPORT:if(service_done_ready)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
