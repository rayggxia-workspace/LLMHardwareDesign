`timescale 1ns/1ps
// Actual three P typed scopes -> M2 -> scratch S -> scatter -> G -> Mid.
module test_ffn_three_p_native #(
 parameter integer COLS=384,
 parameter bit WITH_DOWN=1'b0,FOUR_BANK_LOOKAHEAD=1'b0,WITH_SHARED_DMA=1'b0,WITH_PROGRAM=1'b0,
 parameter bit SPLIT_UP_CHANNEL=1'b0,EARLY_EXEC=1'b0
);
 localparam integer TILES=COLS/128,STRIPES=(COLS+191)/192;
 localparam [63:0] JOB=64'h250_ff01;
 reg clk;initial clk=0;always #5 clk=!clk;
 reg reset=1;
 wire start_valid,done_ready;
 wire stripe_ready,stripe_commit_valid,stripe_commit_error;
 wire [63:0] stripe_commit_owner;
 wire [15:0] stripe_commit_first;
 wire start_ready,stripe_valid,stripe_commit_ready,mid_valid,mid_ready,done_valid,done_error;
 wire [63:0] stripe_owner,mid_owner;
 wire [15:0] stripe_first,mid_first;
 wire [7:0] stripe_width;
 wire [1:0] mid_destination;
 wire [9:0] mid_destination_base;
 wire [5:0] mid_shift;
 wire [31:0] rejected_commits;
 wire [2:0] fs_valid,fs_write,fs_ready,fs_rsp_valid,fs_rsp_ready;
 wire [29:0] fs_address;
 wire [383:0] fs_data,fs_rsp_data;
 wire [95:0] fs_tag,fs_rsp_tag;
 bit zero_peer_ack_payload,poison_peer_ack_payload;
 wire [255:0] peer_ack_payload=zero_peer_ack_payload?'0:
     poison_peer_ack_payload?'1:fs_rsp_data[383:128];
 wire [383:0] ffn_rsp_data={peer_ack_payload,fs_rsp_data[127:0]};
 ffn_gate_up_mid #(.TOTAL_COLUMNS(COLS)) dut(.clk,.reset,.start_valid,.start_ready,.start_owner(JOB),
  .stripe_valid,.stripe_ready,.stripe_owner,.stripe_first,.stripe_width,
  .stripe_commit_valid,.stripe_commit_ready,.stripe_commit_owner,.stripe_commit_first,.stripe_commit_error,
  .s_valid(fs_valid),.s_write(fs_write),.s_ready(fs_ready),.s_address(fs_address),.s_data(fs_data),.s_tag(fs_tag),
  .s_rsp_valid(fs_rsp_valid),.s_rsp_ready(fs_rsp_ready),.s_rsp_data(ffn_rsp_data),.s_rsp_tag(fs_rsp_tag),
  .mid_valid,.mid_ready,.mid_owner,.mid_first,.mid_destination,.mid_destination_base,.mid_shift,
  .done_valid,.done_ready,.done_error,.rejected_commits);

 wire copy_stage,copy_start,copy_take;
 wire [1:0] source_p;
 wire [15:0] copy_generation;
 wire [31:0] copy_first;
 wire [9:0] copy_src,copy_ring;
 wire [4:0] copy_words;
 wire copy_ready,copy_done,copy_error,copy_drained;
 wire [10:0] copy_prefix;
 wire [127:0] copy_key,copy_word;
 wire [31:0] copy_faults,copy_committed;
 wire cs_valid,cs_ready,cs_rsp_valid,cs_rsp_ready,cd_valid,cd_ready,cd_rsp_valid,cd_rsp_ready;
 wire [9:0] cs_address,cd_address;
 wire [31:0] cs_tag,cs_rsp_tag,cd_tag,cd_rsp_tag;
 wire [127:0] cs_rsp_data;
 wire [127:0] current_key;
 wire [15:0] copy_mask=16'hffff>>(5'd16-copy_words);
 wire join_ready;
 assign stripe_ready=join_ready;
 wire [2:0] project_valid,project_done_ready;
 wire [2:0] project_ready,project_done_valid,project_done_error;
 wire [63:0] project_owner;
 wire [47:0] project_first;
 wire [11:0] project_groups;
 wire [191:0] project_done_owner;
 wire [47:0] project_done_first;
 wire [14:0] project_done_gate_words,project_done_up_words;
 wire [31:0] rejected_terminals;
 ffn_stripe_commit gather(.clk,.reset,.stripe_valid,.stripe_ready(join_ready),
  .stripe_owner,.stripe_first,.stripe_width,.project_valid,.project_ready,.project_owner,.project_first,.project_groups,
  .project_done_valid,.project_done_ready,.project_done_owner,.project_done_first,.project_done_gate_words,
  .project_done_up_words,.project_done_error,.copy_stage,.copy_valid(copy_start),.copy_ready,
  .copy_source(source_p),.copy_key(current_key),.copy_generation,.copy_first,.copy_scratch(copy_src),.copy_ring,.copy_words,
  .copy_done_valid(copy_done),.copy_done_ready(copy_take),.copy_done_key(copy_key),.copy_done_prefix(copy_prefix),
  .copy_done_error(copy_error),.commit_valid(stripe_commit_valid),.commit_ready(stripe_commit_ready),
  .commit_owner(stripe_commit_owner),.commit_first(stripe_commit_first),.commit_error(stripe_commit_error),.rejected_terminals);
 s32_stripe_copy scatter(.clk,.reset,.halt(1'b0),.start_valid(copy_start),.start_ready(copy_ready),
  .start_key(current_key),.start_generation(copy_generation),.start_first_col(copy_first),
  .start_source_base(copy_src),.start_ring_base(copy_ring),.start_words(copy_words),
  .start_written_mask(copy_mask),.start_producer_error(1'b0),.destination_window_released(1'b1),
  .source_valid(cs_valid),.source_ready(cs_ready),.source_address(cs_address),.source_tag(cs_tag),
  .source_response_valid(cs_rsp_valid),.source_response_ready(cs_rsp_ready),.source_response_tag(cs_rsp_tag),
  .source_response_data(cs_rsp_data),.source_response_error(1'b0),.destination_valid(cd_valid),.destination_ready(cd_ready),
  .destination_address(cd_address),.destination_tag(cd_tag),.destination_data(copy_word),
  .destination_ack_valid(cd_rsp_valid),.destination_ack_ready(cd_rsp_ready),.destination_ack_tag(cd_rsp_tag),
  .destination_ack_error(1'b0),.copy_key,.committed_prefix(copy_prefix),.done_valid(copy_done),.done_ready(copy_take),
  .done_error(copy_error),.quiescent(copy_drained),.fault_cycles(copy_faults),.committed_words(copy_committed));

 localparam [127:0] X_KEY={32'd1,32'd9,32'd8,32'd7};
 localparam [127:0] MID_KEY={32'd1,32'd9,32'd9,32'd1};
 wire down_phase,down_take;
 wire [2:0] down_index,down_call;
 wire [2:0] down_ready,down_terminal;
 integer mode,seed,cycle,stripe_index,mid_retired,loads,copy_writes,project_terms,w_requests,w_responses;
 bit trace_tiles,early_k_prep;
 reg [1023:0] scopes[WITH_DOWN?192:STRIPES*3];
 reg [127:0] x_raw[512],mid_words[TILES*17];
 reg [127:0] down_words[516];
 wire [127:0] active_key=down_phase?MID_KEY:X_KEY;
 wire [15:0] tile_generation,tile_k;
 wire [31:0] tile_ticket;
 wire [31:0] tile_session=32'(down_phase?STRIPES+1+int'(down_index):stripe_index+1);
 wire lease_start,lease_release;
 wire [2:0] lease_ready,release_ready,window_enabled,window_idle,window_need,proof_valid,reads_drained;
 wire [15:0] needed_k[3];
 wire [127:0] needed_key[3];
 wire [5:0] proof_shift[3];
 wire proof_take;
 wire header_start,header_take;
 wire header_start_ready,header_done,header_error,header_idle;
 wire [2:0] hf_valid,hf_ready,ha_valid,ha_ready,ha_error;
 wire [95:0] hf_tag,ha_tag;
 wire [383:0] hf_data;
 wire [31:0] header_rejected;
 wire [5:0] tile_shift;
 wire shift_valid;
 copy_scale_header_tx x_header(.clk,.reset,.halt(1'b0),.start_valid(header_start),.start_ready(header_start_ready),
  .start_key(active_key),.start_generation(tile_generation),.start_kk(tile_k),.start_written_mask(16'hffff),
  .start_session(tile_session),.start_ticket(tile_ticket),.start_shift(tile_shift),.start_mask(3'b111),
  .start_producer_error(!shift_valid),.frame_valid(hf_valid),.frame_ready(hf_ready),.frame_tag(hf_tag),.frame_data(hf_data),
  .ack_valid(ha_valid),.ack_ready(ha_ready),.ack_tag(ha_tag),.ack_error(ha_error),
  .done_valid(header_done),.done_ready(header_take),.done_error(header_error),.quiescent(header_idle),.rejected_ack(header_rejected));
 wire xcopy_start,xcopy_take;
 wire xcopy_ready,xcopy_done,xcopy_error,xcopy_idle,xcopy_identity;
 wire [15:0] xcopy_gen,xcopy_k;
 wire [31:0] xcopy_session,xcopy_ticket,xcopy_faults,xcopy_count;
 wire [127:0] xcopy_key,xcopy_u_rsp_data;
 wire [32:0] xcopy_prefix;
 wire [2:0] xp_valid,xp_ready,xp_ack_valid,xp_ack_ready;
 wire [29:0] xp_address;
 wire [95:0] xp_tag,xp_ack_tag;
 wire [383:0] xp_data;
 wire xcopy_u_valid,xcopy_u_ready,xcopy_u_rsp_valid,xcopy_u_rsp_ready;
 wire [9:0] xcopy_u_address;
 wire [31:0] xcopy_u_tag,xcopy_u_rsp_tag;
 wire [9:0] raw_base={1'b0,tile_k[10:7],5'd0};
 wire [9:0] x_base=10'd512+{2'd0,tile_k[10:7],4'd0};
 wire [6:0] mid_tile=tile_k[13:7];
 wire [1:0] mid_source=2'(mid_tile%7'd3);
 wire [9:0] mid_source_word=10'd256+(10'(mid_tile/7'd3)<<4);
 early_copy_epoch_3p xcopy(.clk,.reset,.halt(1'b0),.start_valid(xcopy_start),.start_ready(xcopy_ready),
  .start_key(active_key),.start_generation(tile_generation),.start_kk(tile_k),.start_session(tile_session),.start_ticket(tile_ticket),
  .start_U_base(down_phase?mid_source_word:x_base),.start_P_bases({3{10'd880}}),.start_words(11'd16),.start_P_mask(3'b111),
  .destination_window_released(&window_enabled),.u_valid(xcopy_u_valid),.u_ready(xcopy_u_ready),.u_address(xcopy_u_address),
  .u_tag(xcopy_u_tag),.u_response_valid(xcopy_u_rsp_valid),.u_response_ready(xcopy_u_rsp_ready),.u_response_tag(xcopy_u_rsp_tag),
  .u_response_data(xcopy_u_rsp_data),.u_response_error(1'b0),.p_valid(xp_valid),.p_ready(xp_ready),.p_address(xp_address),
  .p_tag(xp_tag),.p_data(xp_data),.p_ack_valid(xp_ack_valid),.p_ack_ready(xp_ack_ready),.p_ack_tag(xp_ack_tag),.p_ack_error(3'd0),
  .copy_key(xcopy_key),.copy_committed_prefix(xcopy_prefix),.copy_generation(xcopy_gen),.copy_kk(xcopy_k),
  .copy_identity_valid(xcopy_identity),.copy_session(xcopy_session),.copy_ticket(xcopy_ticket),
  .done_valid(xcopy_done),.done_ready(xcopy_take),.done_error(xcopy_error),.quiescent(xcopy_idle),
  .fault_cycles(xcopy_faults),.committed_words(xcopy_count));
 wire q_start,q_take;
 reg dir_cfg=0;
 wire q_start_ready,q_done,q_bad,q_cancelled,dir_cfg_ready,dir_bad,dir_pub_ready,dir_pub_bad,x_shift_valid;
 wire [127:0] q_key,q_wdata,q_rsp_data;
 wire [15:0] q_k,q_mask;
 wire [4:0] q_words;
 wire [5:0] q_shift,x_shift,mid_scales[3];
 wire [2:0] mid_scale_valid;
 wire q_req,q_wr,q_ready,q_rsp,q_rsp_ready;
 wire [9:0] q_addr;
 wire [31:0] q_tag,q_rsp_tag,q_reject,dir_reject;
 s32_a16_tile_quantizer quant(.clk,.reset,.cmd_valid(q_start),.cmd_ready(q_start_ready),
  .cmd_key(X_KEY),.cmd_generation(tile_generation),.cmd_kk(tile_k),.cmd_source(raw_base),.cmd_destination(x_base),
  .cmd_shift_known(1'b0),.cmd_shift(6'd0),.cancel_valid(1'b0),.cancel_key(128'd0),
  .s_valid(q_req),.s_ready(q_ready),.s_write(q_wr),.s_address(q_addr),.s_data(q_wdata),.s_tag(q_tag),
  .rsp_valid(q_rsp),.rsp_ready(q_rsp_ready),.rsp_tag(q_rsp_tag),.rsp_data(q_rsp_data),.rsp_error(1'b0),
  .done_valid(q_done),.done_ready(q_take),.done_key(q_key),.done_kk(q_k),.done_error(q_bad),.done_cancelled(q_cancelled),
  .done_words(q_words),.done_written_mask(q_mask),.done_shift(q_shift),.rejected_responses(q_reject));
 a_scale_directory32 x_directory(.clk,.reset,.cfg_valid(dir_cfg),.cfg_ready(dir_cfg_ready),.cfg_key(X_KEY),
  .cfg_first_kk(16'd0),.cfg_tiles(6'd16),.cfg_stride3(1'b0),.storage_released(xcopy_idle),
  .leases_drained(&window_idle),.cfg_rejected(dir_bad),.publish_valid(q_done&&q_take),.publish_ready(dir_pub_ready),
  .publish_key(q_key),.publish_kk(q_k),.publish_shift(q_shift),.publish_written_mask(q_mask),
  .publish_error(q_bad||q_cancelled),.publish_rejected(dir_pub_bad),.lookup_key(X_KEY),.lookup_kk(tile_k),
  .lookup_valid(x_shift_valid),.lookup_shift(x_shift),.rejected_publications(dir_reject));
 assign shift_valid=down_phase?mid_scale_valid[mid_source]:x_shift_valid;
 assign tile_shift=down_phase?mid_scales[mid_source]:x_shift;
 for(genvar p=0;p<3;p++)begin: mid_dir
  if(WITH_DOWN)begin: enabled
   wire cfg_ready,cfg_bad,pub_ready,pub_bad;
   wire [31:0] rejects;
   a_scale_directory32 directory(.clk,.reset,.cfg_valid(dir_cfg),.cfg_ready,.cfg_key(MID_KEY),
    .cfg_first_kk(16'(128*p)),.cfg_tiles(6'((TILES+2-p)/3)),.cfg_stride3(1'b1),
    .storage_released(!down_phase),.leases_drained(&window_idle),.cfg_rejected(cfg_bad),
    .publish_valid(mid_valid&&mid_ready&&mid_destination==2'(p)),.publish_ready(pub_ready),.publish_key(MID_KEY),
    .publish_kk(mid_first),.publish_shift(mid_shift),.publish_written_mask(16'hffff),.publish_error(1'b0),
    .publish_rejected(pub_bad),.lookup_key(MID_KEY),.lookup_kk(tile_k),
    .lookup_valid(mid_scale_valid[p]),.lookup_shift(mid_scales[p]),.rejected_publications(rejects));
   always @(posedge clk)if(!reset)begin
    assert(!cfg_bad&&!pub_bad&&rejects==0);
    if(dir_cfg)assert(cfg_ready);
    if(mid_valid&&mid_ready&&mid_destination==2'(p))assert(pub_ready);
   end
  end else begin: disabled
   assign mid_scale_valid[p]=0;assign mid_scales[p]=0;
  end
 end
 reg uboot=0,ub_take=0;
 reg [8:0] ub_addr=0;
 wire [2:0] ur,uv;
 wire [95:0] ut;
 wire [1:0] u_owners;
 wire u_req,u_write,u_ready,u_rsp,u_rsp_ready;
 wire [9:0] u_addr;
 wire [127:0] u_data,u_result,u_out;
 native_s128_mux3 umux(.clk,.reset,.c_valid({q_req,xcopy_u_valid&&!down_phase,uboot}),.c_write({q_wr,1'b0,1'b1}),
  .c_address({q_addr,xcopy_u_address,1'b0,ub_addr}),.c_data({q_wdata,128'd0,x_raw[ub_addr]}),
  .c_tag({q_tag,xcopy_u_tag,32'h42544f4f}),.c_ready(ur),.c_response_valid(uv),
  .c_response_ready({q_rsp_ready,xcopy_u_rsp_ready&&!down_phase,ub_take}),.c_response_data(u_result),.c_response_tag(ut),
  .req_valid(u_req),.req_write(u_write),.req_address(u_addr),.req_data(u_data),.req_ready(u_ready),
  .rsp_valid(u_rsp),.rsp_ready(u_rsp_ready),.rsp_data(u_out),.owners_occupied(u_owners));
 local_s_base source_x(.clk,.reset,.req_valid(u_req),.req_write(u_write),.req_addr(u_addr),.req_data(u_data),
  .req_ready(u_ready),.rsp_valid(u_rsp),.rsp_ready(u_rsp_ready),.rsp_data(u_out));
 assign q_ready=ur[2];assign q_rsp=uv[2];assign q_rsp_tag=ut[95:64];assign q_rsp_data=u_result;
 assign xcopy_u_ready=down_phase?(!inspect&&aux_ready[mid_source]):ur[1];
 assign xcopy_u_rsp_valid=down_phase?(!inspect&&aux_v[mid_source]):uv[1];
 assign xcopy_u_rsp_tag=down_phase?aux_tag[mid_source]:ut[63:32];
 assign xcopy_u_rsp_data=down_phase?aux_data[mid_source]:u_result;
 wire [2:0] mr_valid,mr_ready,mr_channel,mr_close,mr_close_ready,mrsp_valid,mrsp_ready;
 wire [63:0] mr_addr[3];
 wire [31:0] mr_tag[3],mr_close_tag[3],mrsp_tag[3];
 wire [4:0] mr_beats[3];
 wire [511:0] mrsp_data[3];
 wire [2:0] pr_q;
 wire [2:0] aux_ready,aux_v;
 wire [31:0] aux_tag[3];
 wire [127:0] aux_data[3];
 localparam integer SCOPE_COUNT=WITH_DOWN?192:STRIPES*3;
 wire ddr_idle;
 logic program_start=0,program_result_take=0;
 wire program_ready,program_result;
 wire [31:0] terminal_reads,terminal_writes;
 wire [2:0] lc_call,lc_call_ready,lc_cancel,lc_cancel_ready,lc_done,lc_done_ready;
 wire [383:0] lc_owner,lc_done_owner;
 wire [3071:0] lc_descriptor;
 wire [47:0] lc_done_status;
 wire [95:0] lc_done_reads,lc_done_writes;
 wire [2:0] dr_valid,dr_ready,dr_channel,dr_close,dr_close_ready,dr_rsp_valid,dr_rsp_ready;
 wire [191:0] dr_address;
 wire [95:0] dr_tag,dr_close_tag,dr_rsp_tag;
 wire [14:0] dr_length;
 wire [1535:0] dr_rsp_data;
 if(WITH_PROGRAM)begin: programmed
  initial assert(WITH_SHARED_DMA)else $fatal(1,"native program requires shared descriptor DMA");
  ffn_program_control_fixture control(.clk,.reset,.start(program_start),.transport_drained(ddr_idle),
   .ready(program_ready),.result_valid(program_result),.result_ready(program_result_take),.terminal_reads,.terminal_writes,
   .service_valid(lc_call),.service_ready(lc_call_ready),.service_owner(lc_owner),.service_descriptor(lc_descriptor),
   .service_cancel(lc_cancel),.service_cancel_ready(lc_cancel_ready),.service_done_valid(lc_done),.service_done_ready(lc_done_ready),
   .service_done_owner(lc_done_owner),.service_done_status(lc_done_status),.service_done_reads(lc_done_reads),
   .service_done_writes(lc_done_writes),.dr_valid,.dr_ready,.dr_address,.dr_tag,.dr_channel,.dr_length,
   .dr_close,.dr_close_ready,.dr_close_tag,.dr_rsp_valid,.dr_rsp_ready,.dr_rsp_tag,.dr_rsp_data);
 end else begin: direct_test
  assign {program_ready,program_result,terminal_reads,terminal_writes,lc_owner,lc_descriptor,lc_cancel}=0;
  assign lc_call=3'b111;
  assign lc_done_ready=3'b111;
  assign {dr_valid,dr_address,dr_tag,dr_channel,dr_length,dr_close,dr_close_tag,dr_rsp_ready}=0;
  wire _unused=^{program_start,program_result_take,lc_call_ready,lc_cancel_ready,lc_done,lc_done_owner,
      lc_done_status,lc_done_reads,lc_done_writes,dr_ready,dr_close_ready,dr_rsp_valid,dr_rsp_tag,dr_rsp_data};
 end
 reg inspect=0,inspect_rsp_take=0;
 reg [1:0] inspect_p=0;
 reg [9:0] inspect_addr=0;
 for(genvar p=0;p<3;p++)begin: ps
  wire choose_copy=copy_stage&&source_p==2'(p);
  wire destination_copy=copy_stage&&p==0;
  wire checking=inspect&&inspect_p==2'(p);
  wire reading_mid=down_phase&&mid_source==2'(p);
  wire [1023:0] descriptor=scopes[(down_phase ? 174+down_index*3:stripe_index*3)+p];
  wire [1023:0] execution_descriptor=WITH_PROGRAM?lc_descriptor[p*1024+:1024]:descriptor;
  wire [127:0] call_owner={32'd1,32'd1,32'd9,tile_session};
  wire [127:0] execution_owner=WITH_PROGRAM?lc_owner[p*128+:128]:call_owner;
  wire [127:0] returned_owner;
  wire [31:0] returned_ticket,read_bytes,write_bytes;
  wire [15:0] result_status;
  wire [5:0] gate_count,up_count;
  wire [31:0] copy_return_tag;
  wire node_ready,node_done;
  wire [2:0] _unused_flags={pr_q[p],reads_drained[p],window_idle[p]};
  wire [31:0] expected_records=down_phase?32'(descriptor[592+:5])*86:32'(project_groups[p*4+:4])*32;
  wire [31:0] expected_writes=down_phase?32'(descriptor[592+:5])*32:32'(project_groups[p*4+:4])*64;
  wire local_offer=down_phase?down_call[p]:project_valid[p];
  wire local_take=down_phase?down_take:project_done_ready[p];
  assign project_ready[p]=!down_phase&&node_ready&&lc_call[p];
  assign project_done_valid[p]=!down_phase&&node_done&&lc_done_ready[p];
  assign down_ready[p]=down_phase&&node_ready&&lc_call[p];
  assign down_terminal[p]=down_phase&&node_done&&lc_done_ready[p];
  assign lc_call_ready[p]=local_offer&&node_ready;
  assign lc_done[p]=node_done&&local_take;
  assign lc_done_owner[p*128+:128]=returned_owner;
  assign lc_done_status[p*16+:16]=result_status;
  assign lc_done_reads[p*32+:32]=read_bytes;
  assign lc_done_writes[p*32+:32]=write_bytes;
  always @(posedge clk)if(!reset&&local_offer&&lc_call[p]&&node_ready)begin
   assert(execution_owner==call_owner&&execution_descriptor==descriptor)
    else $fatal(1,"actual MC/LC scope binding p=%0d stripe=%0d Down=%0d",p,stripe_index,down_phase);
  end
  always @(posedge clk)if(!reset&&(project_done_valid[p]||down_terminal[p])&&project_done_error[p])
   $fatal(1,"P terminal p=%0d status=%0d owner=%h expected=%h ticket=%h reads=%0d/%0d writes=%0d/%0d words=%0d,%0d",
      p,result_status,returned_owner,call_owner,returned_ticket,read_bytes,expected_records*1088,
      write_bytes,expected_writes,gate_count,up_count);
  assign project_done_owner[p*64+:64]=project_owner;
  assign project_done_first[p*16+:16]=descriptor[544+:16];
  assign project_done_gate_words[p*5+:5]=gate_count[4:0];
  assign project_done_up_words[p*5+:5]=up_count[4:0];
  assign project_done_error[p]=result_status!=0||returned_owner!=call_owner||returned_ticket!=call_owner[31:0]||
      (!down_phase&&descriptor[544+:16]!=project_first[p*16+:16])||read_bytes!=expected_records*1088||write_bytes!=expected_writes||
      (down_phase?(gate_count!={descriptor[592+:5],1'b0}||up_count!=0):(gate_count[5]||up_count[5]));
  assign fs_ready[p]=!down_phase&&!copy_stage&&!checking&&aux_ready[p];
  assign fs_rsp_valid[p]=!down_phase&&!copy_stage&&!checking&&aux_v[p];
  assign fs_rsp_data[p*128+:128]=aux_data[p];
  assign fs_rsp_tag[p*32+:32]=aux_tag[p];
  if(p==0)begin: scatter_dest_port
   assign cd_rsp_tag=copy_return_tag;
  end else begin: no_scatter_dest
   wire [31:0] _unused_copy_return_tag=copy_return_tag;
  end
  test_ffn_native_p_node #(.SHARED_MID_SOURCE(WITH_DOWN),.FOUR_BANK_LOOKAHEAD(FOUR_BANK_LOOKAHEAD),.EARLY_EXEC(EARLY_EXEC)) node(
   .clk,.reset,.allow_req(mode==0||(cycle+2*p)%7>=2),
   .allow_rsp(mode==0||(cycle+3*p)%11>=4),.service_valid(local_offer&&lc_call[p]),.service_ready(node_ready),
   .service_cancel_valid(lc_cancel[p]),.service_cancel_ready(lc_cancel_ready[p]),
   .service_owner(execution_owner),.service_descriptor(execution_descriptor),.service_done_valid(node_done),
   .service_done_ready(local_take&&lc_done_ready[p]),.service_done_owner(returned_owner),.service_done_ticket(returned_ticket),
   .service_done_status(result_status),.service_done_read_bytes(read_bytes),.service_done_write_bytes(write_bytes),
   .committed_gate_words(gate_count),.committed_up_words(up_count),.window_need_valid(window_need[p]),
   .window_need_k(needed_k[p]),.window_need_key(needed_key[p]),.lease_valid(lease_start),.lease_ready(lease_ready[p]),
   .lease_key(active_key),.lease_generation(tile_generation),.lease_k(tile_k),.lease_session(tile_session),.lease_ticket(tile_ticket),
   .header_valid(hf_valid[p]),.header_ready(hf_ready[p]),.header_tag(hf_tag[p*32+:32]),.header_data(hf_data[p*128+:128]),
   .header_ack_valid(ha_valid[p]),.header_ack_ready(ha_ready[p]),.header_ack_tag(ha_tag[p*32+:32]),.header_ack_error(ha_error[p]),
   .release_window(lease_release),.release_ready(release_ready[p]),.copy_drained(xcopy_idle),
   .copy_progress_valid(xcopy_identity),.copy_key(xcopy_key),.copy_progress_generation(xcopy_gen),.copy_progress_k_elements(xcopy_k),
   .copy_progress_session(xcopy_session),.copy_progress_ticket(xcopy_ticket),.copy_committed_prefix(xcopy_prefix[p*11+:11]),
   .cp_valid(xp_valid[p]),.cp_ready(xp_ready[p]),.cp_address(xp_address[p*10+:10]),.cp_tag(xp_tag[p*32+:32]),
   .cp_data(xp_data[p*128+:128]),.cp_ack_valid(xp_ack_valid[p]),.cp_ack_ready(xp_ack_ready[p]),.cp_ack_tag(xp_ack_tag[p*32+:32]),
   .a_load_proof_valid(proof_valid[p]),.a_load_proof_ready(proof_take),.a_load_proof_shift(proof_shift[p]),
   .a_source_reads_drained(reads_drained[p]),.quiescent(pr_q[p]),.window_enabled(window_enabled[p]),.window_idle(window_idle[p]),
   .aux_valid(checking ? inspect_req:reading_mid?xcopy_u_valid:choose_copy ? cs_valid:!down_phase&&!copy_stage&&fs_valid[p]),
   .aux_write(!down_phase&&!checking&&!choose_copy&&fs_write[p]),
   .aux_address(checking ? inspect_addr:reading_mid?xcopy_u_address:choose_copy ? cs_address:fs_address[p*10+:10]),
   .aux_data(checking||choose_copy||reading_mid ? 128'd0:fs_data[p*128+:128]),
   .aux_tag(checking ? 32'h10250:reading_mid?xcopy_u_tag:choose_copy ? cs_tag:fs_tag[p*32+:32]),.aux_ready(aux_ready[p]),
   .aux_rsp_valid(aux_v[p]),.aux_rsp_ready(checking ? inspect_rsp_take:reading_mid?xcopy_u_rsp_ready:choose_copy ? cs_rsp_ready:fs_rsp_ready[p]),
   .aux_rsp_tag(aux_tag[p]),.aux_rsp_data(aux_data[p]),.aux2_valid(destination_copy&&cd_valid),.aux2_write(1'b1),
   .aux2_address(cd_address),.aux2_data(copy_word),.aux2_tag(cd_tag),.aux2_ready(aux2_r[p]),
   .aux2_rsp_valid(aux2_v[p]),.aux2_rsp_ready(destination_copy&&cd_rsp_ready),.aux2_rsp_tag(copy_return_tag),
   .mc_req_valid(mr_valid[p]),.mc_req_ready(mr_ready[p]),.mc_req_address(mr_addr[p]),.mc_req_tag(mr_tag[p]),
   .mc_req_channel(mr_channel[p]),.mc_req_record_beats(mr_beats[p]),.mc_close_valid(mr_close[p]),
   .mc_close_tag_base(mr_close_tag[p]),.mc_close_ready(mr_close_ready[p]),.mc_rsp_valid(mrsp_valid[p]),.mc_rsp_ready(mrsp_ready[p]),
   .mc_rsp_tag(mrsp_tag[p]),.mc_rsp_data(mrsp_data[p]));
 end
 wire [2:0] aux2_r,aux2_v;
 assign cs_ready=copy_stage&&aux_ready[source_p];
 assign cs_rsp_valid=copy_stage&&aux_v[source_p];
 assign cs_rsp_tag=aux_tag[source_p];
 assign cs_rsp_data=aux_data[source_p];
 assign cd_ready=copy_stage&&aux2_r[0];
 assign cd_rsp_valid=copy_stage&&aux2_v[0];
 wire [3:0] _unused_aux2={aux2_r[2:1],aux2_v[2:1]};

 wire [31:0] dma_req_count,dma_rsp_count,dma_purge_count;
 function automatic [511:0] weight_frame(input logic[63:0] address,input int sr);
  integer way,offset,rec,beat,group,ktile,t,n,i,kk,k_count;
  logic [7:0] ww;
  reg [511:0] value;
  way=address>=64'h06000000 ? 2 : int'(address>=64'h04000000);
  offset=int'(address-64'(way+1)*64'h02000000-((way==1&&SPLIT_UP_CHANNEL)?64'd2048:64'd0));
  k_count=way==2?86:16;
  rec=offset/1088;beat=(offset%1088)/64;group=rec/k_count;ktile=rec%k_count;
  value=0;
  if(beat==16)begin
   for(i=0;i<8;i++)value[i*16+:16]=way==2?16'h3c00:16'h1c00;
  end else begin
   for(i=0;i<64;i++)begin
    t=beat/2;n=(beat%2)*4+i/16;kk=ktile*128+t*16+i%16;
    ww=8'((((group*8+n+7)*(kk%31+3)+ktile*13+way*17+sr)%15)-7);
    value[i*8+:8]=ww;
   end
  end
  return value;
 endfunction
 if(WITH_SHARED_DMA)begin: actual_shared_dma
  wire [11:0] req_ready,rsp_valid,close_ready;
  wire [383:0] rsp_tag;
  wire [6143:0] rsp_data;
  wire [3:0] d_req,d_req_ready,d_rsp,d_rsp_ready;
  wire [255:0] d_addr,d_tag,d_ret_tag;
  wire [2047:0] d_ret_data;
  wire d_fence,d_fence_ready,d_fence_done_ready;
  wire [31:0] d_fence_generation;
  reg fence_pending,backend_purge_completed;
  reg [31:0] fence_generation;
  integer backend_req,backend_rsp,backend_purges;
  wire fault_valid;
  wire [7:0] fault_kind;
  wire [3:0] fault_client;
  wire [31:0] fault_local;
  wire [63:0] fault_global;
  wire [11:0] debug_beats,debug_descriptors;
  wire [3:0] backend_empty;
  wire transport_quiescent;
  wire [31:0] transport_generation;
  wire [103:0] unused_debug;
  wire [383:0] unused_cancel_tag,unused_fence_cookie;
  wire [107:0] unused_fence_epoch;
  assign dma_req_count=32'(backend_req);
  assign dma_rsp_count=32'(backend_rsp);
  assign dma_purge_count=32'(backend_purges);
  assign mr_ready=req_ready[11:9];
  assign mrsp_valid=rsp_valid[11:9];
  assign mr_close_ready=close_ready[11:9];
  assign dr_ready=req_ready[2:0];
  assign dr_rsp_valid=rsp_valid[2:0];
  assign dr_rsp_tag=rsp_tag[95:0];
  assign dr_rsp_data=rsp_data[1535:0];
  assign dr_close_ready=close_ready[2:0];
  assign ddr_idle=transport_quiescent&&(&backend_empty)&&backend_purge_completed&&!fence_pending;
  assign d_fence_ready=(&backend_empty)&&!fence_pending;
  mc_dma_fabric_typed_p dma(.clk,.reset,
   .p_mode_valid(3'd0),.p_mode_native64(3'd0),.p_mode_client_drained(3'b111),
   .p_mode_ready(unused_debug[2:0]),.p_mode_active(unused_debug[5:3]),.p_req_rejected(unused_debug[8:6]),
   .c_req_valid({mr_valid,6'd0,dr_valid}),.c_req_ready(req_ready),.c_req_address({mr_addr[2],mr_addr[1],mr_addr[0],384'd0,dr_address}),
   .c_req_tag({mr_tag[2],mr_tag[1],mr_tag[0],192'd0,dr_tag}),.c_req_channel({mr_channel,6'd0,dr_channel}),
   .c_req_record_beats({mr_beats[2],mr_beats[1],mr_beats[0],30'd0,dr_length}),
   .c_rsp_valid(rsp_valid),.c_rsp_ready({mrsp_ready,6'd0,dr_rsp_ready}),.c_rsp_tag(rsp_tag),.c_rsp_data(rsp_data),
   .c_close_valid({mr_close,6'd0,dr_close}),.c_close_ready(close_ready),
   .c_close_tag_base({mr_close_tag[2],mr_close_tag[1],mr_close_tag[0],192'd0,dr_close_tag}),
   .c_cancel_valid(12'd0),.c_cancel_ready(unused_debug[20:9]),.c_cancel_tag(384'd0),
   .c_cancel_ack_valid(unused_debug[32:21]),.c_cancel_ack_ready(12'hfff),.c_cancel_ack_tag(unused_cancel_tag),.c_cancel_ack_rejected(unused_debug[44:33]),
   .c_fence_valid(12'd0),.c_fence_ready(unused_debug[56:45]),.c_fence_cookie(384'd0),.c_fence_epoch(108'd0),
   .c_fence_done_valid(unused_debug[68:57]),.c_fence_done_ready(12'hfff),.c_fence_done_cookie(unused_fence_cookie),.c_fence_done_epoch(unused_fence_epoch),
   .d_req_valid(d_req),.d_req_ready,.d_req_address(d_addr),.d_req_tag(d_tag),
   .d_rsp_valid(d_rsp),.d_rsp_ready,.d_rsp_tag(d_ret_tag),.d_rsp_data(d_ret_data),
   .d_fence_valid(d_fence),.d_fence_ready,.d_fence_generation,
   .d_fence_done_valid(fence_pending),.d_fence_done_ready,.d_fence_done_generation(fence_generation),
   .fault_valid,.fault_ready(1'b1),.fault_kind,.fault_client,.fault_local_tag(fault_local),.fault_global_tag(fault_global),
   .debug_beats,.debug_descriptors,.debug_generation(transport_generation),.transport_quiescent);
  assign unused_debug[103:69]={req_ready[8:0],rsp_valid[8:0],close_ready[8:0],8'd0};
  wire _unused=^{unused_debug,unused_cancel_tag,unused_fence_cookie,unused_fence_epoch,rsp_tag[287:0],rsp_data[4607:0]};
  for(genvar p=0;p<3;p++)begin: weight_returns
   assign mrsp_tag[p]=rsp_tag[(9+p)*32+:32];
   assign mrsp_data[p]=rsp_data[(9+p)*512+:512];
  end
  // The backend owns at most sixteen issued beats per physical lane. It
  // retains tag and payload until accepted by the actual fabric return skid.
  for(genvar lane=0;lane<4;lane++)begin: finite_backend_lane
   reg [3:0] head,tail;
   reg [4:0] count;
   reg [63:0] tag[16];
   reg [511:0] payload[16];
   integer due[16];
   wire issue=d_req[lane]&&d_req_ready[lane];
   wire take=d_rsp[lane]&&d_rsp_ready[lane];
   assign d_req_ready[lane]=!reset&&!fence_pending&&count<16&&(mode==0||(cycle+lane)%7!=seed%7);
   assign d_rsp[lane]=!reset&&count!=0&&cycle>=due[head];
   assign d_ret_tag[lane*64+:64]=tag[head];
   assign d_ret_data[lane*512+:512]=payload[head];
   assign backend_empty[lane]=count==0;
   always @(posedge clk)begin
    if(reset)begin head<=0;tail<=0;count<=0;end
    else begin
     if(issue)begin
      assert(d_addr[lane*64+:6]==0);
      tag[tail]<=d_tag[lane*64+:64];
      if(d_tag[lane*64+6+:4]<3&&WITH_PROGRAM)begin
       assert(d_addr[lane*64+:64]>=4096&&d_addr[lane*64+:64]<64'(4096+128*SCOPE_COUNT));
       payload[tail]<=scopes[(int'(d_addr[lane*64+:64])-4096)/128][512*int'(d_addr[lane*64+6])+:512];
      end else begin
       assert(d_tag[lane*64+6+:4]>=9&&d_tag[lane*64+6+:4]<=11);
       payload[tail]<=weight_frame(d_addr[lane*64+:64],seed);
      end
      due[tail]<=cycle+7+lane/2;
      tail<=tail+1'b1;
     end
     if(take)head<=head+1'b1;
     case({issue,take})
      2'b10: count<=count+1'b1;
      2'b01: count<=count-1'b1;
      default: ;
     endcase
    end
   end
  end
  for(genvar ch=0;ch<2;ch++)begin: limit
   reg [1:0] last_one,last_two;
   wire [1:0] now=2'($countones(d_req[ch*2+:2]&d_req_ready[ch*2+:2]));
   always @(posedge clk)begin
    if(reset)begin last_one<=0;last_two<=0;end
    else begin
     assert(int'(now)+int'(last_one)+int'(last_two)<=4)else $fatal(1,"DDR channel exceeds 51.2 GB/s envelope");
     last_two<=last_one;last_one<=now;
    end
   end
  end
  always @(posedge clk)begin
   if(reset)begin
    fence_pending<=0;backend_purge_completed<=0;fence_generation<=0;
    backend_req<=0;backend_rsp<=0;backend_purges<=0;
   end
   else begin
    if(d_fence&&d_fence_ready)begin
     assert(d_req==0&&d_rsp==0&&backend_req==backend_rsp);
     fence_pending<=1;fence_generation<=d_fence_generation;backend_purges<=backend_purges+1;
    end
    if(fence_pending&&d_fence_done_ready)begin
     assert(fence_generation==transport_generation+32'd1);
     fence_pending<=0;backend_purge_completed<=1;
    end
    if(ddr_idle)assert(debug_beats==0&&debug_descriptors==0&&backend_req==backend_rsp);
    backend_req<=backend_req+$countones(d_req&d_req_ready);
    backend_rsp<=backend_rsp+$countones(d_rsp&d_rsp_ready);
    assert(!fault_valid)else $fatal(1,"real DMA fault kind=%0d client=%0d local=%h global=%h",fault_kind,fault_client,fault_local,fault_global);
   end
  end
 end else begin: legacy_single_peer
 reg [31:0] pend,pend_tag[32];
 reg [1:0] pend_p[32];
 reg [511:0] pend_data[32];
 integer pend_due[32];
 integer free_idx,rsp_choice,issue_p,rsp_idx,rsp_p;
 integer rr;
 assign {dma_req_count,dma_rsp_count,dma_purge_count}=96'd0;
 assign {dr_ready,dr_close_ready,dr_rsp_valid,dr_rsp_tag,dr_rsp_data}=0;
 wire _unused_dma=^{dr_valid,dr_address,dr_tag,dr_channel,dr_length,dr_close,dr_close_tag,dr_rsp_ready};
 assign mr_close_ready=3'b111;
 assign ddr_idle=pend==0;
 always_comb begin
  free_idx=-1;rsp_choice=-1;issue_p=-1;rsp_p=-1;
  for(integer i=0;i<32;i++)begin
   if(!pend[i]&&free_idx<0)free_idx=i;
   if(pend[i]&&pend_due[i]<=cycle&&rsp_choice<0)rsp_choice=i;
  end
  for(integer i=0;i<3;i++)
   if(mr_valid[(rr+i)%3]&&issue_p<0)issue_p=(rr+i)%3;
  if(rsp_idx>=0)rsp_p=int'(pend_p[rsp_idx]);
 end
 for(genvar p=0;p<3;p++)begin: w_port
  assign mr_ready[p]=!reset&&free_idx>=0&&issue_p==p&&(mode==0||cycle%5!=seed%5);
  assign mrsp_valid[p]=!reset&&rsp_p==p;
  assign mrsp_tag[p]=mrsp_valid[p] ? pend_tag[rsp_idx]:0;
  assign mrsp_data[p]=mrsp_valid[p] ? pend_data[rsp_idx]:0;
 end
 always @(posedge clk)begin
  if(reset)begin rr<=0;pend<=0;rsp_idx<=-1;end
  else begin
   if(|(mr_valid&mr_ready))begin
    pend[free_idx]<=1;pend_p[free_idx]<=2'(issue_p);pend_tag[free_idx]<=mr_tag[issue_p];
    pend_data[free_idx]<=weight_frame(mr_addr[issue_p],seed);pend_due[free_idx]<=cycle+7+int'(mr_channel[issue_p]);
    rr<=(issue_p+1)%3;
   end
   if(rsp_idx<0&&rsp_choice>=0)rsp_idx<=rsp_choice;
   if(|(mrsp_valid&mrsp_ready))begin pend[rsp_idx]<=0;rsp_idx<=-1;end
  end
 end
 end
 assign mid_ready=mode==0||cycle%13>=4;
 always @(posedge clk)begin
  if(reset)begin
   cycle<=0;stripe_index<=0;mid_retired<=0;loads<=0;copy_writes<=0;project_terms<=0;
   w_requests<=0;w_responses<=0;
  end else begin
   cycle<=cycle+1;
   if(cycle>6000000)$fatal(1,"three-P FFN watchdog stripe=%0d K=%0d down=%0d index=%0d",stripe_index,tile_k,down_phase,down_index);
   for(integer p=0;p<3;p++)if(mr_valid[p]&&mr_ready[p])begin
    assert(mr_beats[p]==17&&mr_tag[p][4:0]<17&&mr_addr[p][5:0]==0&&
           mr_addr[p]>=64'h02000000&&mr_addr[p]<(down_phase?64'h08000000:64'h06000000))
     else $fatal(1,"native W8 record address/beat");
   end
   w_requests<=w_requests+$countones(mr_valid&mr_ready);
   w_responses<=w_responses+$countones(mrsp_valid&mrsp_ready);
   if(stripe_commit_valid&&stripe_commit_ready)begin
    assert(!stripe_commit_error)else $fatal(1,"true projection scatter rejected");
    stripe_index<=stripe_index+1;
   end
   project_terms<=project_terms+$countones(project_done_valid&project_done_ready);
   copy_writes<=copy_writes+$countones(xp_ack_valid&xp_ack_ready);
   if(proof_take)loads<=loads+$countones(proof_valid);
   if(mid_valid&&mid_ready)begin
    assert(mid_owner==JOB&&mid_first==16'(mid_retired*128)&&mid_destination==2'(mid_retired%3)&&
        mid_destination_base==10'(256+16*(mid_retired/3))&&mid_shift==mid_words[mid_retired*17][5:0])
        else $fatal(1,"native P -> Mid owner=%h first=%0d dst=%0d base=%0d shift=%0d expected tile=%0d shift=%0d",
          mid_owner,mid_first,mid_destination,mid_destination_base,mid_shift,mid_retired,mid_words[mid_retired*17][5:0]);
    mid_retired<=mid_retired+1;
   end
   assert(xcopy_faults==0&&copy_faults==0&&header_rejected==0&&q_reject==0&&dir_reject==0&&!dir_bad&&!dir_pub_bad)
    else $fatal(1,"native source/copy error down=%0d index=%0d k=%0d inspect=%0d xcopy=%0d scatter=%0d header=%0d quant=%0d directory=%0d",
         down_phase,down_index,tile_k,inspect,xcopy_faults,copy_faults,header_rejected,q_reject,dir_reject);
   if(inspect)assert(xcopy_idle&&!xcopy_u_valid&&!copy_stage)
    else $fatal(1,"readback must acquire an idle S auxiliary client");
  end
 end
 task automatic cycle_wait;
  @(negedge clk);
 endtask
 reg scope_start=0,job_take=0;
 wire scope_ready,job_done,job_error;
 wire tile_command_valid,tile_command_ready,tile_done_valid,tile_done_ready,tile_done_error;
 wire [6:0] tile_command_tiles;
 ffn_native_job_sequencer #(.GATE_SCOPES(16'(STRIPES)),.WITH_DOWN(WITH_DOWN)) job_control(
  .clk,.reset,.job_valid(scope_start),.job_ready(scope_ready),.job_done,.job_error,.job_done_ready(job_take),
  .gate_start(start_valid),.gate_ready(start_ready),.gate_done(done_valid),.gate_error(done_error),
  .gate_take(done_ready),.gate_commits(16'(stripe_index)),
  .down_resources_ready((&pr_q)&&(&window_idle)&&copy_drained),
  .down_phase,.down_index,.down_call,.down_ready,.down_terminal,.down_error(|project_done_error),.down_take,
  .tiles_valid(tile_command_valid),.tiles_ready(tile_command_ready),.tiles_done(tile_done_valid),
  .tiles_error(tile_done_error),.tiles_count(tile_command_tiles),.tiles_take(tile_done_ready));
 wire all_need_match=&window_need&&needed_k[0]==tile_k&&needed_k[1]==tile_k&&needed_k[2]==tile_k;
 wire needed_owner_ok=needed_key[0]==active_key&&needed_key[1]==active_key&&needed_key[2]==active_key;
 wire proof_shift_ok=proof_shift[0]==tile_shift&&proof_shift[1]==tile_shift&&proof_shift[2]==tile_shift;
 ffn_k_window_sequencer tile_control(.clk,.reset,.namespace_rearm(1'b0),
  .command_valid(tile_command_valid),.command_ready(tile_command_ready),.command_tiles(tile_command_tiles),
  .command_quantize(!down_phase&&stripe_index==0),.command_early(early_k_prep),
  .need_match(all_need_match&&needed_owner_ok),.need_bad_owner(all_need_match&&!needed_owner_ok),
  .previous_drained((&window_idle)&&(&reads_drained)&&xcopy_idle&&header_idle),
  .tile_k,.tile_generation,.tile_ticket,.quant_valid(q_start),.quant_ready(q_start_ready),.quant_done(q_done),
  .quant_bad(q_bad||q_cancelled||q_key!=X_KEY||q_k!=tile_k||q_words!=16||q_mask!=16'hffff),
  .publish_ready(dir_pub_ready),.quant_take(q_take),.shift_valid,.header_idle,.source_idle(u_owners==0),
  .lease_ready,.lease_start,.header_valid(header_start),.header_ready(header_start_ready),.header_done,
  .header_bad(header_error||window_enabled!=3'b111),.header_take,
  .copy_valid(xcopy_start),.copy_ready(xcopy_ready),.copy_done(xcopy_done),
  .copy_bad(xcopy_error||xcopy_prefix!={3{11'd16}}||xcopy_key!=active_key),.copy_take(xcopy_take),
  .proof_valid,.proof_bad(!proof_shift_ok),.proof_take,.release_ready,.lease_release,
  .done_valid(tile_done_valid),.done_error(tile_done_error),.done_ready(tile_done_ready));

 integer begin_cycle,need_cycle,quant_cycle,header_cycle,copy_cycle,proof_cycle;
 integer first_weight_req,first_weight_rsp,completed_tiles;
 always @(posedge clk)if(reset)begin
  begin_cycle<=0;need_cycle<=-1;quant_cycle<=-1;header_cycle<=-1;copy_cycle<=-1;proof_cycle<=-1;
  first_weight_req<=0;first_weight_rsp<=0;completed_tiles<=0;
 end else begin
  if(tile_command_valid&&tile_command_ready)begin
   begin_cycle<=cycle+1;first_weight_req<=w_requests;first_weight_rsp<=w_responses;completed_tiles<=0;
  end
  if(need_cycle<0&&all_need_match&&!(early_k_prep&&tile_k!=0))need_cycle<=cycle;
  if(q_done&&q_take)assert(q_shift==0)else $fatal(1,"fixture source shift");
  if(lease_start)quant_cycle<=cycle;
  if(header_done&&header_take)header_cycle<=cycle;
  if(xcopy_done&&xcopy_take)copy_cycle<=cycle;
  if(proof_take)proof_cycle<=cycle;
  if(lease_release)begin
   assert(tile_k==16'(completed_tiles*128)&&quant_cycle>=0&&header_cycle>=0&&copy_cycle>=0&&proof_cycle>=0)
    else $fatal(1,"wrong RTL K-range order at phase=%0d scope=%0d k=%0d",down_phase,tile_session,tile_k);
   completed_tiles<=completed_tiles+1;
   if(trace_tiles)$display("K_PROFILE phase=%0d scope=%0d k=%0d start=%0d need=%0d quant=%0d header=%0d copy=%0d proof=%0d released=%0d W_req=%0d W_rsp=%0d",
    down_phase,tile_session,tile_k,begin_cycle,need_cycle,quant_cycle,header_cycle,copy_cycle,proof_cycle,cycle+1,
    w_requests-first_weight_req,w_responses-first_weight_rsp);
   begin_cycle<=cycle+1;first_weight_req<=w_requests;first_weight_rsp<=w_responses;
   need_cycle<=-1;quant_cycle<=-1;header_cycle<=-1;copy_cycle<=-1;proof_cycle<=-1;
  end
  if(tile_done_valid&&tile_done_ready)assert(!tile_done_error&&completed_tiles==int'(tile_command_tiles))
   else $fatal(1,"RTL K-range incomplete");
 end

 reg inspect_req=0;
 task automatic read_data(input integer p, address,input logic [127:0] expected);
  assert(p>=0&&p<3&&address>=0&&address<1024);
  inspect=1;inspect_req=1;inspect_p=2'(p);inspect_addr=10'(address);
  do @(posedge clk);while(!aux_ready[p]);cycle_wait();inspect_req=0;
  while(!aux_v[p])cycle_wait();
  assert(aux_tag[p]==32'h10250&&aux_data[p]==expected)
     else $fatal(1,"actual three-P S readback p=%0d addr=%0d want=%h got=%h",p,address,expected,aux_data[p]);
  inspect_rsp_take=1;cycle_wait();inspect_rsp_take=0;inspect=0;
 endtask
 string xfile,scopefile,midfile,downfile;
 integer start_cycle,down_start,job_launches,down_scopes,peer_acks;
 reg was_down;
 always @(posedge clk)begin
  if(reset)begin
   start_cycle<=0;down_start<=0;was_down<=0;job_launches<=0;down_scopes<=0;peer_acks<=0;
  end else begin
   was_down<=down_phase;
   if(scope_start&&scope_ready)job_launches<=job_launches+1;
   if(start_valid&&start_ready)start_cycle<=cycle;
   assert((fs_valid[2:1]&fs_ready[2:1]&~fs_write[2:1])==0)
    else $fatal(1,"Mid peers must receive only writes");
   peer_acks<=peer_acks+$countones(fs_rsp_valid[2:1]&fs_rsp_ready[2:1]);
   if(done_valid&&done_ready)begin
    assert(!done_error&&mid_retired==TILES&&loads==STRIPES*48&&copy_writes==STRIPES*768&&
        project_terms==STRIPES*3&&w_requests==COLS/8*32*17&&w_requests==w_responses&&(WITH_PROGRAM||ddr_idle)&&
        copy_drained&&rejected_commits==0&&rejected_terminals==0&&peer_acks==(TILES-(TILES+2)/3)*16)
     else $fatal(1,"native three-P scope accounting");
    $display("FFN_PROFILE cycles=%0d W64=%0d S_copy=%0d S_scatter=%0d",
        cycle-start_cycle,w_requests,copy_writes,copy_committed);
   end
   if(down_phase&&!was_down)down_start<=cycle;
   if(down_take)begin
    assert(down_index==3'(down_scopes))else $fatal(1,"RTL Down scope out of order");
    down_scopes<=down_scopes+1;
    if(down_index==5)
     $display("DOWN_PROFILE cycles=%0d W64=%0d Mid_replays=516 S_copy_words=24768 result_words=512",
         cycle-down_start,2048/8*86*17);
   end
  end
 end
 initial begin
  mode=0;seed=0;
  zero_peer_ack_payload=$test$plusargs("ZERO_PEER_ACK_PAYLOAD");
  poison_peer_ack_payload=$test$plusargs("POISON_PEER_ACK_PAYLOAD");
  assert(!(zero_peer_ack_payload&&poison_peer_ack_payload))else $fatal(1,"choose one Mid ACK payload mode");
  trace_tiles=$test$plusargs("TRACE_TILES");early_k_prep=$test$plusargs("EARLY_K_PREP");
  if(!$value$plusargs("mode=%d",mode))$fatal(1,"mode");
  if(!$value$plusargs("seed=%d",seed))$fatal(1,"seed");
  if(!$value$plusargs("X=%s",xfile)||!$value$plusargs("SCOPES=%s",scopefile)||!$value$plusargs("MID=%s",midfile))
   $fatal(1,"actual source vectors and descriptors required");
  $readmemh(xfile,x_raw);$readmemh(scopefile,scopes);$readmemh(midfile,mid_words);
  if(WITH_DOWN)begin
   assert(COLS==11008&&$value$plusargs("DOWN=%s",downfile));
   $readmemh(downfile,down_words);
  end
  repeat(4)cycle_wait();reset=0;
  for(integer j=0;j<512;j++)begin
   ub_addr=9'(j);uboot=1;do @(posedge clk);while(!ur[0]);cycle_wait();uboot=0;
   while(!uv[0])cycle_wait();assert(ut[31:0]==32'h42544f4f);
   ub_take=1;cycle_wait();ub_take=0;
  end
  assert(dir_cfg_ready);dir_cfg=1;cycle_wait();dir_cfg=0;
  if(WITH_PROGRAM)begin
   while(!program_ready)cycle_wait();
   program_start=1;cycle_wait();program_start=0;
  end
  scope_start=1;do @(posedge clk);while(!scope_ready);cycle_wait();scope_start=0;
  while(!job_done)cycle_wait();
  assert(!job_error&&job_launches==1&&down_scopes==(WITH_DOWN?6:0))
   else $fatal(1,"RTL outer scope completion");
  for(integer k=0;k<TILES;k++)
   for(integer w=0;w<16;w++)read_data(k%3,256+16*(k/3)+w,mid_words[k*17+1+w]);
  if(WITH_DOWN)begin
   assert(loads==(STRIPES*16+6*86)*3&&copy_writes==(STRIPES*16+6*86)*48&&
     w_requests==(COLS/8*32+2048/8*86)*17&&w_requests==w_responses&&ddr_idle&&window_idle==3'b111)
     else $fatal(1,"actual Down K128 replay accounting");
   for(integer p=0;p<3;p++)
    for(integer w=0;w<(p==0?172:170);w++)read_data(p,w,down_words[172*p+w]);
  end
  if(WITH_SHARED_DMA)begin
   assert(dma_req_count==32'(w_requests+(WITH_PROGRAM?SCOPE_COUNT*2:0))&&
          dma_rsp_count==32'(w_responses+(WITH_PROGRAM?SCOPE_COUNT*2:0))&&dma_purge_count>=1);
   $display("DMA_PROFILE backend_requests=%0d backend_returns=%0d purges=%0d",
      dma_req_count,dma_rsp_count,dma_purge_count);
  end
  if(WITH_PROGRAM)begin
   while(!program_result)cycle_wait();
   assert(terminal_reads==32'(w_requests*64+128*SCOPE_COUNT)&&
          terminal_writes==32'(COLS*8+(WITH_DOWN?8192:0)))else $fatal(1,"actual MC cumulative receipt mismatch");
   $display("PROGRAM_PROFILE calls=%0d confirmed_reads=%0d confirmed_writes=%0d",SCOPE_COUNT,terminal_reads,terminal_writes);
   program_result_take=1;cycle_wait();program_result_take=0;
  end
  job_take=1;cycle_wait();job_take=0;
  assert(scope_ready)else $fatal(1,"RTL outer scope failed to return ownership");
  $display("MID_ACK_PROFILE peer_acks=%0d zero_payload=%0d poison_payload=%0d",
      peer_acks,zero_peer_ack_payload,poison_peer_ack_payload);
  $display("PASS ffn_three_p_native columns=%0d stripes=%0d real_P_M=3 real_S_banks=16 Mid=%0d mode=%0d down=%0d four_w=%0d shared_dma=%0d program=%0d split_up=%0d early_exec=%0d early_k_prep=%0d rtl_k_window=1 rtl_outer_job=1",
      COLS,STRIPES,TILES,mode,WITH_DOWN,FOUR_BANK_LOOKAHEAD,WITH_SHARED_DMA,WITH_PROGRAM,SPLIT_UP_CHANNEL,EARLY_EXEC,early_k_prep);
  $finish;
 end
 wire [130:0] _unused_stats={xcopy_count,mr_close,mr_close_tag[0],mr_close_tag[1],mr_close_tag[2]};
endmodule
