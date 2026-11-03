// Issue151 L4-A-TSP: H1024/Sq2 original-residual preservation and replay.
// Wo is an explicit external integer cut, not an implemented Attention path.
// One real S, one T, one E, one S helper; no private residual/context array.
module block_w4_atsp_top(
 input wire clk,reset,abort,
 input wire job_valid,output wire job_ready,input wire [31:0] job_generation,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 input wire [31:0] in_generation,input wire [7:0] in_index,input wire in_last,
 output wire input_stored,input wire start_valid,output wire start_ready,
 output wire busy,output wire spool_saved,
 input wire work_valid,output wire work_ready,input wire [7:0] work_addr,
 input wire [127:0] work_data,
 output wire work_rsp_valid,input wire work_rsp_ready,output wire work_rsp_error,
 input wire resume_valid,output wire resume_ready,
 input wire wo_valid,output wire wo_ready,input wire [127:0] wo_data,
 input wire [7:0] wo_index,input wire wo_last,input wire [31:0] wo_generation,
 output wire done_valid,input wire done_ready,
 output wire done_error,done_saturated,done_partial,
 output wire [8:0] done_words,output wire [31:0] done_generation,
 output wire out_valid,input wire out_ready,output wire [127:0] out_data,
 output wire [9:0] out_index,output wire out_last,output wire [31:0] out_generation
);
 localparam [5:0] WAIT_JOB=0,INPUT=1,INPUT_REQ=2,INPUT_RSP=3,STORED=4,
  RAW_BEGIN=5,RAW_READ_REQ=6,RAW_READ_RSP=7,RAW_WRITE=8,RAW_COMMIT=9,
  RAW_SAVED=10,HEAD_HOLD=11,WORK_REQ=12,WORK_RSP=13,WORK_ACK=14,
  WO_WAIT=15,WO_REQ=16,WO_RSP=17,RAW_CAPTURE=18,RAW_SAVE_REQ=19,
  RAW_SAVE_RSP=20,E_REQ=21,E_RSP=22,RAW_RELEASE=23,OUT_BEGIN=24,
  OUT_READ_REQ=25,OUT_READ_RSP=26,OUT_WRITE=27,OUT_COMMIT=28,
  OUT_DRAIN=29,OUT_RELEASE=30,DONE=31;
 localparam OWNER_LOCAL=1'b0,OWNER_E=1'b1;
 reg [5:0] state;
 reg owner,frame_active,frame_stored,running,raw_saved;
 reg error_latched,saturation_latched,internal_reset,work_error_hold;
 reg [8:0] input_index,output_index,output_count;
 reg [7:0] raw_index,work_addr_hold;
 reg [6:0] group_index;
 reg row_index,wo_slot;
 reg [31:0] job_generation_hold;
 reg [127:0] held_data;
 reg local_req_valid,local_write;
 reg [9:0] local_addr;
 wire leaf_reset,local_rsp_ready,input_fire,start_fire,wo_fire,wo_meta_ok,input_meta_ok;
 wire permit_s_req=1'b1,permit_s_rsp=1'b1;
 wire permit_e_req=1'b1,permit_e_rsp=1'b1;
 wire permit_t_begin=1'b1,permit_t_write=1'b1,permit_t_commit=1'b1;
 wire permit_t_read=1'b1,permit_t_release=1'b1;
 wire permit_work=1'b1,permit_resume=1'b1,permit_wo=1'b1;
 wire h_req_valid,h_req_ready,h_req_write,h_rsp_valid,h_rsp_ready,h_rsp_error;
 wire [9:0] h_req_addr;
 wire [127:0] h_req_data,h_rsp_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire e_req_valid,e_req_ready,e_rsp_valid,e_rsp_ready,e_rsp_error,e_rsp_saturated;
 wire e_mem_req_valid,e_mem_req_ready,e_mem_req_write,e_mem_rsp_valid,e_mem_rsp_ready;
 wire [9:0] e_mem_req_addr;
 wire [127:0] e_mem_req_data;
 wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error,e_out_saturated;
 wire [3:0] e_in_op;
 wire [4:0] e_in_shift;
 wire [127:0] e_in_a,e_in_b,e_in_c,e_out_data;
 wire [9:0] e_dst;
 wire t_begin_valid,t_begin_ready,t_write_valid,t_write_ready;
 wire t_commit_valid,t_commit_ready,t_release_valid,t_release_ready;
 wire t_read_valid,t_read_take,t_read_last,t_busy,t_sealed,t_committed,t_protocol_error;
 wire [9:0] t_write_index,t_read_index,t_word_count;
 wire [127:0] t_read_data;
 wire [1:0] t_owner;
 wire [31:0] t_generation;
 wire [2:0] t_state;
 wire raw_meta_ok,out_meta_ok;

 assign leaf_reset=reset||abort||internal_reset;
 assign job_ready=!leaf_reset&&state==WAIT_JOB;
 assign in_ready=!leaf_reset&&state==INPUT&&input_index<9'd256;
 assign input_fire=in_valid&&in_ready;
 assign input_meta_ok=in_generation==job_generation_hold&&
  in_index==input_index[7:0]&&in_last==(input_index==9'd255);
 assign input_stored=!reset&&!abort&&frame_stored;
 assign start_ready=!leaf_reset&&state==STORED&&frame_stored;
 assign start_fire=start_valid&&start_ready;
 assign busy=!reset&&(frame_active||state==DONE);
 assign spool_saved=!leaf_reset&&raw_saved;
 assign work_ready=!leaf_reset&&state==HEAD_HOLD&&permit_work;
 assign work_rsp_valid=!leaf_reset&&state==WORK_ACK;
 assign work_rsp_error=work_error_hold;
 // A work offer has priority over resume; a pending write/ACK cannot be cut.
 assign resume_ready=!leaf_reset&&state==HEAD_HOLD&&!work_valid&&permit_resume;
 assign wo_ready=!leaf_reset&&state==WO_WAIT&&permit_wo;
 assign wo_fire=wo_valid&&wo_ready;
 assign wo_meta_ok=wo_generation==job_generation_hold&&
  wo_index=={group_index,wo_slot}&&wo_last==(group_index==7'd127&&wo_slot);
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_latched;
 assign done_saturated=saturation_latched;
 assign done_partial=error_latched&&output_count!=0;
 assign done_words=output_count;
 assign done_generation=job_generation_hold;
 assign out_generation=job_generation_hold;

 // All ordinary-S clients use the same helper and actual native write ACK.
 always @* begin
  local_req_valid=1'b1;local_write=1'b0;local_addr=10'd0;
  case(state)
   INPUT_REQ:begin local_write=1'b1;local_addr={1'd0,input_index};end
   RAW_READ_REQ:local_addr={2'd0,raw_index[0],raw_index[7:1]};
   WORK_REQ:begin local_write=1'b1;local_addr={2'd0,work_addr_hold};end
   WO_REQ:begin local_write=1'b1;local_addr=10'd256+{9'd0,wo_slot};end
   RAW_SAVE_REQ:begin local_write=1'b1;local_addr=10'd258;end
   OUT_READ_REQ:local_addr=output_index[7] ?
    10'd384+{3'd0,output_index[6:0]} : {3'd0,output_index[6:0]};
   default:local_req_valid=1'b0;
  endcase
 end
 assign local_rsp_ready=state==INPUT_RSP||state==RAW_READ_RSP||state==WORK_RSP||
  state==WO_RSP||state==RAW_SAVE_RSP||state==OUT_READ_RSP;
 assign h_req_valid=!leaf_reset&&permit_s_req&&
  (owner==OWNER_E ? e_mem_req_valid : local_req_valid);
 assign h_req_write=owner==OWNER_E ? e_mem_req_write : local_write;
 assign h_req_addr=owner==OWNER_E ? e_mem_req_addr : local_addr;
 assign h_req_data=owner==OWNER_E ? e_mem_req_data : held_data;
 assign h_rsp_ready=!leaf_reset&&(owner==OWNER_E ? e_mem_rsp_ready : local_rsp_ready);
 assign e_mem_req_ready=!leaf_reset&&permit_s_req&&owner==OWNER_E&&h_req_ready;
 assign e_mem_rsp_valid=!leaf_reset&&owner==OWNER_E&&h_rsp_valid;
 assign s_take=helper_s_take&&permit_s_rsp;
 block_p2_s_ctrl u_s_ctrl(
  .clk(clk),.resetn(!leaf_reset),.req_valid(h_req_valid),.req_ready(h_req_ready),
  .req_write(h_req_write),.req_addr(h_req_addr),.req_data(h_req_data),
  .rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),.rsp_data(h_rsp_data),.rsp_error(h_rsp_error),
  .s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_ready(s_ready),
  .s_rsp_valid(s_valid&&permit_s_rsp),.s_rsp_ready(helper_s_take),.s_dout(s_dout));
 block_feed_s_macro u_s(
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'd1),.load_tiles(3'd1),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(10'd0),.load_b_base(10'd0),.done_valid(),.done_take(1'b0),
  .done_error(),.busy(),.a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),
  .a_wide(),.a_data(),.b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),
  .b_wide(),.b_half(),.b_data());

 assign e_req_valid=!leaf_reset&&state==E_REQ&&permit_e_req;
 assign e_rsp_ready=!leaf_reset&&state==E_RSP&&permit_e_rsp;
 assign e_dst=row_index ? 10'd384+{3'd0,group_index} : {3'd0,group_index};
 block_w3_e_ctrl u_e_ctrl(
  .clk(clk),.reset(leaf_reset),.req_valid(e_req_valid),.req_ready(e_req_ready),
  .req_op(4'd0),.req_shift(5'd0),.req_count(4'd8),
  .req_src_a(10'd256+{9'd0,row_index}),.req_src_b(10'd258),.req_src_c(10'd0),.req_dst(e_dst),
  .rsp_valid(e_rsp_valid),.rsp_ready(e_rsp_ready),.rsp_error(e_rsp_error),.rsp_saturated(e_rsp_saturated),
  .mem_req_valid(e_mem_req_valid),.mem_req_ready(e_mem_req_ready),.mem_req_write(e_mem_req_write),
  .mem_req_addr(e_mem_req_addr),.mem_req_data(e_mem_req_data),
  .mem_rsp_valid(e_mem_rsp_valid),.mem_rsp_ready(e_mem_rsp_ready),
  .mem_rsp_data(h_rsp_data),.mem_rsp_error(h_rsp_error),
  .e_in_valid(e_in_valid),.e_in_ready(e_in_ready),.e_in_op(e_in_op),.e_in_shift(e_in_shift),
  .e_in_a(e_in_a),.e_in_b(e_in_b),.e_in_c(e_in_c),
  .e_out_valid(e_out_valid),.e_out_ready(e_out_ready),.e_out_data(e_out_data),
  .e_out_error(e_out_error),.e_out_saturated(e_out_saturated));
 block_v2_e u_e(
  .clk(clk),.reset(leaf_reset),.in_valid(e_in_valid),.in_ready(e_in_ready),
  .in_op(e_in_op),.in_shift(e_in_shift),.in_a(e_in_a),.in_b(e_in_b),.in_c(e_in_c),
  .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),
  .out_error(e_out_error),.out_saturated(e_out_saturated));

 assign t_begin_valid=!leaf_reset&&permit_t_begin&&(state==RAW_BEGIN||state==OUT_BEGIN);
 assign t_write_valid=!leaf_reset&&permit_t_write&&(state==RAW_WRITE||state==OUT_WRITE);
 assign t_write_index=state==RAW_WRITE ? {2'd0,raw_index} : {1'd0,output_index};
 assign t_commit_valid=!leaf_reset&&permit_t_commit&&(state==RAW_COMMIT||state==OUT_COMMIT);
 assign t_release_valid=!leaf_reset&&permit_t_release&&(state==RAW_RELEASE||state==OUT_RELEASE);
 assign raw_meta_ok=t_owner==2'd1&&t_generation==job_generation_hold&&t_word_count==10'd256&&
  t_read_index=={2'd0,group_index,row_index}&&
  t_read_last==(group_index==7'd127&&row_index);
 assign out_meta_ok=t_owner==2'd2&&t_generation==job_generation_hold&&t_word_count==10'd256&&
  t_read_index=={1'd0,output_index}&&t_read_last==(output_index==9'd255);
 assign out_valid=!leaf_reset&&state==OUT_DRAIN&&t_read_valid&&out_meta_ok&&
  !t_protocol_error&&permit_t_read;
 assign out_data=t_read_data;
 assign out_index=t_read_index;
 assign out_last=out_valid&&t_read_last;
 assign t_read_take=!leaf_reset&&!t_protocol_error&&permit_t_read&&
  ((state==RAW_CAPTURE&&t_read_valid&&raw_meta_ok)||
   (state==OUT_DRAIN&&out_valid&&out_ready));
 transaction6k u_t(
  .clk(clk),.reset(leaf_reset),.begin_valid(t_begin_valid),.begin_ready(t_begin_ready),
  .begin_owner(state==RAW_BEGIN ? 2'd1 : 2'd2),.begin_generation(job_generation_hold),
  .begin_words(10'd256),.write_valid(t_write_valid),.write_ready(t_write_ready),
  .write_index(t_write_index),.write_data(held_data),
  .commit_valid(t_commit_valid),.commit_ready(t_commit_ready),.revoke_valid(1'b0),.revoke_ready(),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),
  .read_data(t_read_data),.read_last(t_read_last),.owner(t_owner),.generation(t_generation),
  .word_count(t_word_count),.release_valid(t_release_valid),.release_ready(t_release_ready),
  .busy(t_busy),.sealed(t_sealed),.committed(t_committed),
  .protocol_error(t_protocol_error),.debug_state(t_state));

 task automatic empty_job;
  begin
   state<=WAIT_JOB;owner<=OWNER_LOCAL;frame_active<=0;frame_stored<=0;running<=0;raw_saved<=0;
   error_latched<=0;saturation_latched<=0;work_error_hold<=0;
   input_index<=0;output_index<=0;output_count<=0;raw_index<=0;work_addr_hold<=0;
   group_index<=0;row_index<=0;wo_slot<=0;job_generation_hold<=0;held_data<=0;
  end
 endtask
 task automatic fail_job;
  begin
   state<=DONE;owner<=OWNER_LOCAL;frame_stored<=0;running<=0;raw_saved<=0;
   error_latched<=1;internal_reset<=1;
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin empty_job();internal_reset<=0;end
  else begin
   internal_reset<=0;
   if(abort)begin
    // An accepted admission owns a completion even before start.
    if(state==DONE)begin if(done_ready)empty_job();end
    else if(frame_active)fail_job();
    else begin empty_job();internal_reset<=1;end
   end else if(frame_active&&state!=DONE&&t_protocol_error)fail_job();
   else case(state)
    WAIT_JOB:if(job_valid&&job_ready)begin
     frame_active<=1;job_generation_hold<=job_generation;state<=INPUT;
    end
    INPUT:if(input_fire)begin
     if(!input_meta_ok)fail_job();else begin held_data<=in_data;state<=INPUT_REQ;end
    end
    INPUT_REQ:if(h_req_valid&&h_req_ready)state<=INPUT_RSP;
    INPUT_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();
     else if(input_index==9'd255)begin input_index<=9'd256;frame_stored<=1;state<=STORED;end
     else begin input_index<=input_index+1'b1;state<=INPUT;end
    end
    STORED:if(start_fire)begin
     running<=1;raw_index<=0;group_index<=0;row_index<=0;wo_slot<=0;state<=RAW_BEGIN;
    end
    RAW_BEGIN:if(t_begin_valid&&t_begin_ready)state<=RAW_READ_REQ;
    RAW_READ_REQ:if(h_req_valid&&h_req_ready)state<=RAW_READ_RSP;
    RAW_READ_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin held_data<=h_rsp_data;state<=RAW_WRITE;end
    end
    RAW_WRITE:if(t_write_valid&&t_write_ready)begin
     if(raw_index==8'd255)state<=RAW_COMMIT;
     else begin raw_index<=raw_index+1'b1;state<=RAW_READ_REQ;end
    end
    RAW_COMMIT:if(t_commit_valid&&t_commit_ready)state<=RAW_SAVED;
    RAW_SAVED:if(t_read_valid)begin
     if(!raw_meta_ok)fail_job();else begin raw_saved<=1;state<=HEAD_HOLD;end
    end
    HEAD_HOLD:begin
     if(!t_read_valid||!raw_meta_ok)fail_job();
     else if(work_valid&&work_ready)begin
      held_data<=work_data;work_addr_hold<=work_addr;work_error_hold<=0;state<=WORK_REQ;
     end else if(resume_valid&&resume_ready)begin group_index<=0;row_index<=0;wo_slot<=0;state<=WO_WAIT;end
    end
    WORK_REQ:if(h_req_valid&&h_req_ready)state<=WORK_RSP;
    WORK_RSP:if(h_rsp_valid&&h_rsp_ready)begin work_error_hold<=h_rsp_error;state<=WORK_ACK;end
    WORK_ACK:if(work_rsp_valid&&work_rsp_ready)begin
     if(work_error_hold)fail_job();else state<=HEAD_HOLD;
    end
    WO_WAIT:if(wo_fire)begin
     // Invalid cut metadata is accepted only to report failure; no S write.
     if(!wo_meta_ok)fail_job();else begin held_data<=wo_data;state<=WO_REQ;end
    end
    WO_REQ:if(h_req_valid&&h_req_ready)state<=WO_RSP;
    WO_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();
     else if(!wo_slot)begin wo_slot<=1;state<=WO_WAIT;end
     else begin wo_slot<=0;row_index<=0;state<=RAW_CAPTURE;end
    end
    RAW_CAPTURE:if(t_read_valid)begin
     if(!raw_meta_ok)fail_job();
     else if(t_read_take)begin held_data<=t_read_data;state<=RAW_SAVE_REQ;end
    end
    RAW_SAVE_REQ:if(h_req_valid&&h_req_ready)state<=RAW_SAVE_RSP;
    RAW_SAVE_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin owner<=OWNER_E;state<=E_REQ;end
    end
    E_REQ:if(e_req_valid&&e_req_ready)state<=E_RSP;
    E_RSP:if(e_rsp_valid&&e_rsp_ready)begin
     saturation_latched<=saturation_latched||e_rsp_saturated;
     if(e_rsp_error)fail_job();
     else begin
      owner<=OWNER_LOCAL;
      if(!row_index)begin row_index<=1;state<=RAW_CAPTURE;end
      else if(group_index==7'd127)state<=RAW_RELEASE;
      else begin group_index<=group_index+1'b1;row_index<=0;wo_slot<=0;state<=WO_WAIT;end
     end
    end
    RAW_RELEASE:if(t_release_valid&&t_release_ready)begin
     raw_saved<=0;output_index<=0;state<=OUT_BEGIN;
    end
    OUT_BEGIN:if(t_begin_valid&&t_begin_ready)state<=OUT_READ_REQ;
    OUT_READ_REQ:if(h_req_valid&&h_req_ready)state<=OUT_READ_RSP;
    OUT_READ_RSP:if(h_rsp_valid&&h_rsp_ready)begin
     if(h_rsp_error)fail_job();else begin held_data<=h_rsp_data;state<=OUT_WRITE;end
    end
    OUT_WRITE:if(t_write_valid&&t_write_ready)begin
     if(output_index==9'd255)state<=OUT_COMMIT;
     else begin output_index<=output_index+1'b1;state<=OUT_READ_REQ;end
    end
    OUT_COMMIT:if(t_commit_valid&&t_commit_ready)begin output_index<=0;state<=OUT_DRAIN;end
    OUT_DRAIN:if(t_read_valid)begin
     if(!out_meta_ok)fail_job();
     else if(out_valid&&out_ready)begin
      output_count<=output_count+1'b1;
      if(output_index==9'd255)state<=OUT_RELEASE;
      else output_index<=output_index+1'b1;
     end
    end
    OUT_RELEASE:if(t_release_valid&&t_release_ready)begin running<=0;state<=DONE;end
    DONE:if(done_valid&&done_ready)empty_job();
    default:begin if(frame_active)fail_job();else begin empty_job();internal_reset<=1;end end
   endcase
  end
 end
endmodule
