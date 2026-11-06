  wire t_begin,t_begin_ready,t_write,t_write_ready,t_commit,t_commit_ready,t_revoke,t_revoke_ready;
  wire t_read,t_take,t_last,t_error,t_release,t_release_ready;
  wire t_native_write_ready,t_native_release_ready;
  wire [9:0] t_index,t_read_index,t_words;
  wire [1:0] t_owner;
  wire [31:0] t_generation;
  wire [127:0] t_payload,t_data;
  integer t_write_age=0,t_release_age=0;
  wire missing=$test$plusargs("JMISSING") && t_index==1;
  wire [9:0] submitted_index=$test$plusargs("JORDER") && t_index==0 ? 10'd1 : t_index;
  wire write_gate=!missing && t_write_age>=int'(stall_i)*2;
  wire release_gate=t_release_age>=int'(stall_i)*3;
  assign t_write_ready=t_native_write_ready && write_gate;
  assign t_release_ready=t_native_release_ready && release_gate;
  assign extra_ready=0;
  assign extra_ack=0;
  assign extra_result=0;
  assign e_op=$test$plusargs("JEFAULT") ? 4'd14 : 4'd0;
  assign e_shift=0;

  lc_j_lease_adapter adapter(
    .clk(clk_i),.rst_n(rst_ni),.svc_valid(svc_req_valid_o && svc_req_kind_o==0),.svc_ready(svc_req_ready_i),
    .svc_resource(svc_req_resource_o),.svc_token(svc_req_token_o),.svc_sequence(svc_req_sequence_o),
    .svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),.svc_task_sequence(svc_req_task_sequence_o),
    .svc_desc(svc_req_descriptor_o),.rsp_valid(svc_rsp_valid_i),.rsp_ready(svc_rsp_ready_o),
    .rsp_token(svc_rsp_token_i),.rsp_sequence(svc_rsp_sequence_i),.rsp_job(svc_rsp_job_i),
    .rsp_epoch(svc_rsp_epoch_i),.rsp_task_sequence(svc_rsp_task_sequence_i),.rsp_status(svc_rsp_status_i),
    .rsp_read_bytes(svc_rsp_read_bytes_i),.rsp_write_bytes(svc_rsp_write_bytes_i),.rsp_saturated(svc_rsp_saturated_i),
    .s_valid(s_valid),.s_ready(s_ready),.s_write(s_write),.s_word(s_word),.s_data(s_data),
    .s_rsp_valid(native_s_rsp_valid),.s_rsp_ready(s_take),.s_rsp_data(native_s_rsp_data),
    .t_begin(t_begin),.t_begin_ready(t_begin_ready),.t_write(t_write),.t_write_ready(t_write_ready),
    .t_index(t_index),.t_payload(t_payload),.t_commit(t_commit),.t_commit_ready(t_commit_ready),
    .t_revoke(t_revoke),.t_revoke_ready(t_revoke_ready),.t_read(t_read),.t_take(t_take),
    .t_read_index(t_read_index),.t_data(t_data),.t_last(t_last),.t_error(t_error),
    .t_owner(t_owner),.t_generation(t_generation),.t_words(t_words),
    .t_release(t_release),.t_release_ready(t_release_ready),
    .e_valid(e_valid),.e_ready(e_ready && e_req_gate),.e_a(e_a),.e_b(e_b),
    .e_rsp_valid(e_out_valid && e_rsp_gate),.e_rsp_ready(e_take),.e_result(e_y),.e_error(e_error),.e_saturated(e_sat));

  wire t_busy,t_sealed,t_committed;
  transaction6k macro_t(.clk(clk_i),.reset(!rst_ni),
    .begin_valid(t_begin),.begin_ready(t_begin_ready),.begin_owner(2'b0),
    .begin_generation(svc_rsp_task_sequence_i),.begin_words(10'd2),
    .write_valid(t_write && write_gate),.write_ready(t_native_write_ready),
    .write_index(submitted_index),.write_data(t_payload),
    .commit_valid(t_commit),.commit_ready(t_commit_ready),.revoke_valid(t_revoke),.revoke_ready(t_revoke_ready),
    .read_valid(t_read),.read_take(t_take),.read_index(t_read_index),.read_data(t_data),.read_last(t_last),
    .owner(t_owner),.generation(t_generation),.word_count(t_words),
    .release_valid(t_release && release_gate),.release_ready(t_native_release_ready),
    .busy(t_busy),.sealed(t_sealed),.committed(t_committed),.protocol_error(t_error),.debug_state());

  always @(posedge clk_i) if(rst_ni) begin
    if(t_begin && t_begin_ready) begin
      t_write_age<=0;
      $display("JC %0d TBEGIN %0d",cycle_i,svc_rsp_task_sequence_i);
    end
    if(t_write && !write_gate) begin
      t_write_age<=t_write_age+1;
      $display("JC %0d TFILL_H %0d %032h",cycle_i,submitted_index,t_payload);
    end
    if(t_write && t_write_ready) begin
      t_write_age<=0; $display("JC %0d TFILL %0d %032h",cycle_i,submitted_index,t_payload);
    end
    if(t_commit && t_commit_ready) begin
      if(!t_sealed) $fatal(1,"T commit without sealed fragment");
      $display("JC %0d TCOMMIT %0d %0d",cycle_i,t_generation,t_words);
    end
    if(t_revoke && t_revoke_ready) $display("JC %0d TREVOKE %0d",cycle_i,t_error);
    if(t_read) begin
      if(!t_committed) $fatal(1,"read before commit");
      if(t_take) $display("JC %0d TTAKE %0d %0d %032h",cycle_i,t_read_index,t_last,t_data);
      else $display("JC %0d TTAKE_H %0d %0d %032h",cycle_i,t_read_index,t_last,t_data);
    end
    if(t_release && !release_gate) begin
      t_release_age<=t_release_age+1; $display("JC %0d TREL_H %0d",cycle_i,t_generation);
    end
    if(t_release && t_release_ready) begin
      t_release_age<=0; $display("JC %0d TREL %0d",cycle_i,t_generation);
    end
    if(svc_rsp_valid_i && t_busy) $fatal(1,"service returned while T lease still held");
  end
