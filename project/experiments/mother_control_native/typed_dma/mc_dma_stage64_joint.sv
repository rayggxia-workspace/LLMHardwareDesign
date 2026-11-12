`timescale 1ns/1ps
module mc_dma_stage64_joint #(
 parameter [15:0] SERIAL_LIMIT=16'hffff,
 parameter integer SKIDS_PER_CHANNEL=3
) (
 input wire clk,reset,
 // Runtime mode has independent real local and transport drain proofs.
 // A rejected request consumes VALID for diagnosis but creates no owner.
 input wire [2:0] p_mode_valid,p_mode_native64,p_mode_client_drained,
 output wire [2:0] p_mode_ready,p_mode_active,p_req_rejected,
 input wire [11:0] c_req_valid,output wire [11:0] c_req_ready,
 input wire [767:0] c_req_address,input wire [383:0] c_req_tag,
 input wire [11:0] c_req_channel,input wire [59:0] c_req_record_beats,
 output wire [11:0] c_rsp_valid,input wire [11:0] c_rsp_ready,
 output wire [383:0] c_rsp_tag,output wire [6143:0] c_rsp_data,
 input wire [11:0] c_close_valid,output wire [11:0] c_close_ready,
 input wire [383:0] c_close_tag_base,
 input wire [11:0] c_cancel_valid,output wire [11:0] c_cancel_ready,
 input wire [383:0] c_cancel_tag,
 output wire [11:0] c_cancel_ack_valid,input wire [11:0] c_cancel_ack_ready,
 output wire [383:0] c_cancel_ack_tag,output wire [11:0] c_cancel_ack_rejected,
 input wire [11:0] c_fence_valid,output wire [11:0] c_fence_ready,
 input wire [383:0] c_fence_cookie,input wire [107:0] c_fence_epoch,
 output wire [11:0] c_fence_done_valid,input wire [11:0] c_fence_done_ready,
 output wire [383:0] c_fence_done_cookie,output wire [107:0] c_fence_done_epoch,
 output wire [3:0] d_req_valid,input wire [3:0] d_req_ready,
 output wire [255:0] d_req_address,output wire [255:0] d_req_tag,
 input wire [3:0] d_rsp_valid,output wire [3:0] d_rsp_ready,
 input wire [255:0] d_rsp_tag,input wire [2047:0] d_rsp_data,
 output wire d_fence_valid,input wire d_fence_ready,output wire [31:0] d_fence_generation,
 input wire d_fence_done_valid,output wire d_fence_done_ready,
 input wire [31:0] d_fence_done_generation,
 output wire fault_valid,input wire fault_ready,output wire [7:0] fault_kind,
 output wire [3:0] fault_client,output wire [31:0] fault_local_tag,
 output wire [63:0] fault_global_tag,
 output wire [11:0] debug_beats,debug_descriptors,
 output wire [31:0] debug_generation,
 output wire transport_quiescent
,
 input wire [2:0] dyn_cmd_valid,output wire [2:0] dyn_cmd_ready,dyn_cmd_admit,
 input wire [191:0] dyn_cmd_address,input wire [95:0] dyn_cmd_tag,input wire [29:0] dyn_cmd_dst,
 input wire [5:0] dyn_cmd_first,input wire [8:0] dyn_cmd_words,input wire [2:0] dyn_force_bad_channel,
 input wire [2:0] dyn_cancel_valid,output wire [2:0] dyn_cancel_ready,input wire [95:0] dyn_cancel_tag,
 output wire [2:0] dyn_done_valid,input wire [2:0] dyn_done_ready,
 output wire [95:0] dyn_done_tag,output wire [2:0] dyn_done_error,dyn_done_cancelled,
 output wire [11:0] dyn_done_mask,
 input wire [2:0] block_S_req,block_S_ack,
 input wire [2:0] rd_mode,rd_valid,output wire [2:0] rd_ready,rd_rsp_valid,input wire [2:0] rd_rsp_ready,
 input wire [29:0] rd_address,output wire [383:0] rd_data,
 output wire [11:0] mon_rsp_ready,output wire [2:0] mon_s_req,mon_s_ack,mon_raw_retire,
 output wire [29:0] mon_s_address,output wire [383:0] mon_s_data
);
 wire [11:0] req_valid_i,req_ready_i,req_channel_i,rsp_ready_i;
 wire [767:0] req_address_i;wire [383:0] req_tag_i;wire [59:0] req_beats_i;
 wire [2:0] local_drained;
 mc_dma_fabric_typed_p #(.SERIAL_LIMIT(SERIAL_LIMIT),.SKIDS_PER_CHANNEL(SKIDS_PER_CHANNEL)) dma(
  .c_req_valid(req_valid_i),.c_req_ready(req_ready_i),.c_req_address(req_address_i),.c_req_tag(req_tag_i),
  .c_req_channel(req_channel_i),.c_req_record_beats(req_beats_i),.c_rsp_ready(rsp_ready_i),
  .p_mode_client_drained(local_drained),.*);
 assign mon_rsp_ready=rsp_ready_i;
 assign c_req_ready=req_ready_i&{9'h1ff,~p_mode_active};
 assign req_valid_i[11:3]=c_req_valid[11:3];assign req_channel_i[11:3]=c_req_channel[11:3];
 assign req_address_i[767:192]=c_req_address[767:192];assign req_tag_i[383:96]=c_req_tag[383:96];
 assign req_beats_i[59:15]=c_req_record_beats[59:15];assign rsp_ready_i[11:3]=c_rsp_ready[11:3];
 for(genvar g=0;g<3;g=g+1)begin:P
  // VALID/parameters remain offered by the LC until the eventual fabric
  // ready. Only one phase bit tracks that S already registered this owner.
  reg stage_registered;
  reg [1:0] local_owners;
  wire mode_native=p_mode_active[g];
  wire stage_cmd_valid=mode_native&&dyn_cmd_valid[g]&&!stage_registered;
  wire stage_cmd_ready,stage_cmd_admit,stage_reject_ready,stage_raw_ready,unexpected_return;
  wire stage_s_req_valid,stage_s_rsp_ready;
  wire [9:0] stage_s_address;
  wire [127:0] stage_s_data;
  wire s_req_ready_i,s_rsp_valid_i;
  wire stage_done_take=dyn_done_valid[g]&&dyn_done_ready[g];
  wire request_registered=stage_cmd_valid&&stage_cmd_ready;
  assign local_drained[g]=p_mode_client_drained[g]&&local_owners==0&&!stage_registered&&!dyn_cmd_valid[g];
  assign dyn_cmd_admit[g]=stage_cmd_admit;
  assign dyn_cmd_ready[g]=mode_native&&((stage_registered&&req_ready_i[g])||(request_registered&&!stage_cmd_admit));
  assign req_valid_i[g]=mode_native?(stage_registered&&dyn_cmd_valid[g]):c_req_valid[g];
  assign req_address_i[g*64+:64]=mode_native?dyn_cmd_address[g*64+:64]:c_req_address[g*64+:64];
  assign req_tag_i[g*32+:32]=mode_native?dyn_cmd_tag[g*32+:32]:c_req_tag[g*32+:32];
  assign req_channel_i[g]=mode_native?(dyn_cmd_address[g*64+11]^dyn_force_bad_channel[g]):c_req_channel[g];
  assign req_beats_i[g*5+:5]=mode_native?5'd1:c_req_record_beats[g*5+:5];
  assign rsp_ready_i[g]=mode_native?stage_raw_ready:c_rsp_ready[g];
  dot_s32_stage64 stage(
   .clk,.reset,.cmd_valid(stage_cmd_valid),.cmd_ready(stage_cmd_ready),.cmd_admit(stage_cmd_admit),
   .cmd_tag(dyn_cmd_tag[g*32+:32]),.cmd_dst(dyn_cmd_dst[g*10+:10]),.cmd_first(dyn_cmd_first[g*2+:2]),.cmd_words(dyn_cmd_words[g*3+:3]),
   .cancel_valid(mode_native&&dyn_cancel_valid[g]),.cancel_ready(dyn_cancel_ready[g]),.cancel_tag(dyn_cancel_tag[g*32+:32]),
   .reject_valid(mode_native&&p_req_rejected[g]),.reject_ready(stage_reject_ready),.reject_tag(dyn_cmd_tag[g*32+:32]),
   .raw_valid(mode_native&&c_rsp_valid[g]),.raw_ready(stage_raw_ready),.raw_tag(c_rsp_tag[g*32+:32]),.raw_data(c_rsp_data[g*512+:512]),.unexpected_return,
   .s_req_valid(stage_s_req_valid),.s_req_ready(s_req_ready_i&&!block_S_req[g]&&!rd_mode[g]),
   .s_req_address(stage_s_address),.s_req_wdata(stage_s_data),.s_rsp_valid(s_rsp_valid_i&&!block_S_ack[g]&&!rd_mode[g]),.s_rsp_ready(stage_s_rsp_ready),.s_rsp_error(1'b0),
   .done_valid(dyn_done_valid[g]),.done_ready(dyn_done_ready[g]),.done_tag(dyn_done_tag[g*32+:32]),
   .done_cancelled(dyn_done_cancelled[g]),.done_error(dyn_done_error[g]),.done_written_mask(dyn_done_mask[g*4+:4]));
  local_s_base real_S(.clk,.reset,
   .req_valid(rd_mode[g]?rd_valid[g]:(stage_s_req_valid&&!block_S_req[g])),.req_write(!rd_mode[g]),
   .req_addr(rd_mode[g]?rd_address[g*10+:10]:stage_s_address),.req_data(stage_s_data),.req_ready(s_req_ready_i),
   .rsp_valid(s_rsp_valid_i),.rsp_ready(rd_mode[g]?rd_rsp_ready[g]:(stage_s_rsp_ready&&!block_S_ack[g])),.rsp_data(rd_data[g*128+:128]));
  assign rd_ready[g]=rd_mode[g]&&s_req_ready_i;assign rd_rsp_valid[g]=rd_mode[g]&&s_rsp_valid_i;
  assign mon_s_req[g]=!rd_mode[g]&&stage_s_req_valid&&s_req_ready_i&&!block_S_req[g];
  assign mon_s_ack[g]=!rd_mode[g]&&s_rsp_valid_i&&stage_s_rsp_ready&&!block_S_ack[g];
  assign mon_raw_retire[g]=mode_native&&c_rsp_valid[g]&&stage_raw_ready;
  assign mon_s_address[g*10+:10]=stage_s_address;assign mon_s_data[g*128+:128]=stage_s_data;
  always @(posedge clk)begin
   if(reset)begin stage_registered<=0;local_owners<=0;end
   else begin
    if(stage_cmd_admit)stage_registered<=1;
    if(stage_registered&&dyn_cmd_ready[g])stage_registered<=0;
    case({request_registered,stage_done_take})
     2'b10:local_owners<=local_owners+1'b1;
     2'b01:local_owners<=local_owners-1'b1;
     default:;
    endcase
    assert(local_owners<=2&&(!rd_mode[g]||local_owners==0));
    assert(!unexpected_return&&(!(mode_native&&p_req_rejected[g])||stage_reject_ready));
    assert(!stage_registered||dyn_cmd_valid[g]);
   end
  end
 end
endmodule
