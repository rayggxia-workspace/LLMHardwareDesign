`timescale 1ns/1ps
module tb_lc_native;
`include "tb_wires.svh"
  integer cycle=0, mode=0, stall=0, words=0, status=0, calls=1;
  integer n, job_index, commands=0, returns=0, retire_count=0;
  integer request_wait=0, service_wait=0;
  reg [127:0] input_image [0:519];
  reg [127:0] memory [0:519];
  reg pm_pending=0, service_pending=0;
  reg pending_write;
  reg [13:0] pending_address;
  reg [127:0] pending_data;
  reg [2:0] saved_token;
  reg [31:0] saved_seq,saved_job,saved_epoch,saved_task;
  reg [511:0] saved_task_packet;
  reg [1023:0] expected_desc;
  reg [2047:0] image_path, task_path;
  reg [511:0] task_input [0:0];
  reg [31:0] expected_image_id, expected_topology;
  integer length_bytes;
  integer cancel=0, native_commands=0, native_returns=0;
  wire adapter_poison;
  wire m_cmd_valid,m_cmd_ready,m_rsp_valid,m_rsp_ready,m_rsp_error,m_rsp_saturated,m_busy;
  wire [3:0] m_cmd_op;
  wire [5:0] m_cmd_index;
  wire [63:0] m_cmd_data;
  wire [127:0] m_rsp_data;
  lc_m_clear_adapter adapter(
    .clk_i(clk_i),.rst_ni(rst_ni),.provider_released_i(deploy_valid_i),.poison_o(adapter_poison),
    .m_cmd_valid_o(m_cmd_valid),.m_cmd_ready_i(m_cmd_ready),.m_cmd_op_o(m_cmd_op),
    .m_cmd_index_o(m_cmd_index),.m_cmd_data_o(m_cmd_data),.m_rsp_valid_i(m_rsp_valid),
    .m_rsp_ready_o(m_rsp_ready),.m_rsp_data_i(m_rsp_data),.m_rsp_error_i(m_rsp_error),
    .m_rsp_saturated_i(m_rsp_saturated),
    .svc_req_ready_o(svc_req_ready_i),
    .svc_rsp_valid_o(svc_rsp_valid_i),
    .svc_rsp_kind_o(svc_rsp_kind_i),
    .svc_rsp_token_o(svc_rsp_token_i),
    .svc_rsp_sequence_o(svc_rsp_sequence_i),
    .svc_rsp_job_o(svc_rsp_job_i),
    .svc_rsp_epoch_o(svc_rsp_epoch_i),
    .svc_rsp_task_sequence_o(svc_rsp_task_sequence_i),
    .svc_rsp_status_o(svc_rsp_status_i),
    .svc_rsp_read_bytes_o(svc_rsp_read_bytes_i),
    .svc_rsp_write_bytes_o(svc_rsp_write_bytes_i),
    .svc_rsp_saturated_o(svc_rsp_saturated_i),
    .svc_req_valid_i(svc_req_valid_o),
    .svc_req_kind_i(svc_req_kind_o),
    .svc_req_resource_i(svc_req_resource_o),
    .svc_req_token_i(svc_req_token_o),
    .svc_req_sequence_i(svc_req_sequence_o),
    .svc_req_job_i(svc_req_job_o),
    .svc_req_epoch_i(svc_req_epoch_o),
    .svc_req_task_sequence_i(svc_req_task_sequence_o),
    .svc_req_descriptor_i(svc_req_descriptor_o),
    .svc_req_object_base_i(svc_req_object_base_o),
    .svc_req_object_length_i(svc_req_object_length_o),
    .svc_req_object_version_i(svc_req_object_version_o),
    .svc_rsp_ready_i(svc_rsp_ready_o)
  );
  block_v2_m macro_m(.clk(clk_i),.reset(!rst_ni),
    .a_valid(1'b0),.a_ready(),.a_bank(1'b0),.a_row(3'b0),.a_tile(2'b0),.a_wide(1'b0),.a_data(128'b0),
    .b_valid(1'b0),.b_ready(),.b_bank(1'b0),.b_tile(2'b0),.b_wide(1'b0),.b_half(1'b0),.b_data(512'b0),
    .cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),.cmd_index(m_cmd_index),.cmd_data(m_cmd_data),
    .rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_data(m_rsp_data),.rsp_error(m_rsp_error),
    .rsp_saturated(m_rsp_saturated),.busy(m_busy));
  always @(posedge clk_i) if (rst_ni) begin
    $display("N %0d %0d %0d %0d %0d %0h %0d %0d %0d %0h %0d",($time/10),
      m_cmd_valid,m_cmd_ready,m_cmd_op,m_cmd_index,m_cmd_data,m_rsp_valid,m_rsp_ready,m_rsp_error,m_rsp_data,adapter_poison);
    if (m_cmd_valid && m_cmd_ready) native_commands<=native_commands+1;
    if (m_rsp_valid && m_rsp_ready) native_returns<=native_returns+1;
    if (adapter_poison) $fatal(1,"unexpected adapter poison");
  end

  initial clk_i=0;
  always #5 clk_i=~clk_i;
`include "tb_trace.svh"

  // Registered program-memory peer. It models storage, never controller state.
  always @(posedge clk_i) begin
    if (!rst_ni) begin
      pm_pending<=0; pm_rsp_valid_i<=0; pm_rsp_data_i<=0; pm_rsp_error_i<=0;

    end else begin
      if (pm_req_valid_o && pm_req_ready_i) begin
        if (pm_pending || pm_rsp_valid_i) $fatal(1,"PM overlap");
        if (pm_req_address_o[3:0]!=0 || pm_req_address_o+16>8320) $fatal(1,"PM range");
        pm_pending<=1; request_wait<=stall+1;
        pending_write<=pm_req_write_o; pending_address<=pm_req_address_o; pending_data<=pm_req_data_o;
      end
      if (pm_pending) begin
        if (request_wait==0) begin
          pm_pending<=0; pm_rsp_valid_i<=1;
          if (pending_write) begin memory[pending_address[13:4]]<=pending_data; pm_rsp_data_i<=0; end
          else pm_rsp_data_i<=memory[pending_address[13:4]];
        end else request_wait<=request_wait-1;
      end
      if (pm_rsp_valid_i && pm_rsp_ready_o) pm_rsp_valid_i<=0;
      if (svc_req_valid_o && svc_req_ready_i) begin
        if (svc_req_descriptor_o!==expected_desc) $fatal(1,"descriptor snapshot");
        commands<=commands+1;
      end
      if (trace_retire_o) retire_count<=retire_count+1;
      if (event_valid_o && event_ready_i) begin
        if (event_packet_o[0+:16]!=1 || event_packet_o[24+:8]!=0 ||
            event_packet_o[32+:32]!=saved_task_packet[32+:32] ||
            event_packet_o[64+:64]!=saved_task_packet[64+:64] ||
            event_packet_o[128+:8]!=saved_task_packet[136+:8] ||
            event_packet_o[136+:8]!=255 || event_packet_o[144+:16]!=status[15:0] ||
            event_packet_o[16+:8]!=(status==0 ? 2 : 3)) $fatal(1,"terminal mismatch");
        returns<=returns+1;
      end
      if (life_o==6 && cfg_req_ready_o) $fatal(1,"runtime config admission");
      if (poison_o) $fatal(1,"unexpected poison");
    end
  end
  // Drive peers on falling edges. Trace samples are pre-rising-edge values.
  always @(negedge clk_i) begin
    pm_req_ready_i=rst_ni && !pm_pending && !pm_rsp_valid_i && (stall==0 || cycle%5==0);
    event_ready_i=rst_ni && (stall==0 || cycle%11==0);
  end

  task config_command;
    input [2:0] op;
    input integer address;
    input [127:0] data;
    input integer expect_status;
    begin
      @(negedge clk_i);
      cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1;
      cfg_req_address_i=address[13:0]; cfg_req_data_i=data; cfg_req_proof_i=1;
      cfg_req_total_bytes_i=length_bytes[15:0]; cfg_req_image_id_i=expected_image_id;
      cfg_req_topology_id_i=expected_topology; cfg_req_abi_id_i=65537; cfg_req_capacity_id_i=32'h17630001;
      @(posedge clk_i);
      while (!cfg_req_ready_o) @(posedge clk_i);
      @(negedge clk_i); cfg_req_valid_i=0;
      while (!cfg_rsp_valid_o) @(negedge clk_i);
      repeat (stall) @(negedge clk_i);
      if (cfg_rsp_status_o!=expect_status[15:0]) $fatal(1,"config status op=%0d got=%0d want=%0d",op,cfg_rsp_status_o,expect_status);
      if (op==2 && cfg_rsp_data_o!==input_image[address>>4]) $fatal(1,"host readback mismatch");
      cfg_rsp_ready_i=1;
      @(negedge clk_i); cfg_rsp_ready_i=0;
    end
  endtask

  initial begin
`include "tb_native_init.svh"
    if (!$value$plusargs("IMAGE=%s",image_path) || !$value$plusargs("TASK=%s",task_path) ||
        !$value$plusargs("WORDS=%d",words)) $fatal(1,"missing image/task/words");
    n=$value$plusargs("STALL=%d",stall); n=$value$plusargs("STATUS=%d",status);
    n=$value$plusargs("CANCEL=%d",cancel); n=$value$plusargs("MODE=%d",mode); n=$value$plusargs("CALLS=%d",calls);
    $readmemh(image_path,input_image,0,words-1); $readmemh(task_path,task_input,0,0);
    length_bytes=words*16; expected_image_id=input_image[3][96+:32];
    expected_topology=input_image[4][0+:32]; expected_desc=0;
    if (words==23) for (n=0;n<8;n=n+1) expected_desc[n*128+:128]=input_image[15+n];
    for (n=0;n<520;n=n+1) memory[n]={16{8'hcd}};
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0,0);
    if (mode==4) begin
      config_command(1,16,0,6);
      if (image_valid_o || life_o!=1) $fatal(1,"bad load prefix did not invalidate candidate");
      $display("PASS negative bad_load_prefix"); $finish;
    end
    if (mode==1) begin
      config_command(3,0,0,3);
      if (image_valid_o || life_o!=1) $fatal(1,"premature verification admitted");
      $display("PASS negative premature_verify"); $finish;
    end
    for (n=0;n<words;n=n+1) config_command(1,n*16,input_image[n],0);
    for (n=0;n<words;n=n+1) config_command(2,n*16,0,0);
    config_command(3,0,0,mode==2 ? 3 : 0);
    if (mode==2) begin
      if (image_valid_o || life_o!=1) $fatal(1,"bad header admitted");
      $display("PASS negative bad_header"); $finish;
    end
    config_command(4,0,0,0);
    repeat(3) @(negedge clk_i);
    if (task_ready_o || image_valid_o) $fatal(1,"local PREPARE admitted");
    deploy_valid_i=1; deploy_generation_i=2;
    repeat(3) @(negedge clk_i);
    if (task_ready_o || image_valid_o) $fatal(1,"wrong generation admitted");
    deploy_generation_i=1;
    while (life_o!=5) @(negedge clk_i);
    if (mode==3) begin
      deploy_valid_i=0;
      repeat(2) @(negedge clk_i);
      if (image_valid_o || life_o!=1 || task_ready_o || poison_o) $fatal(1,"idle revoke did not invalidate");
      $display("PASS negative idle_revoke"); $finish;
    end
    if (mode==5) begin
      config_command(0,0,0,3);
      if (!image_valid_o || life_o!=5) $fatal(1,"bad BEGIN destroyed committed image");
      $display("PASS negative bad_begin_preserves_commit"); $finish;
    end
    for (job_index=0;job_index<calls;job_index=job_index+1) begin
      task_packet_i=task_input[0]; task_packet_i[96+:32]=job_index+1;
      saved_task_packet=task_packet_i; task_valid_i=0; task_credit_i=0;
      repeat(3) @(negedge clk_i);
      if (task_ready_o) $fatal(1,"CALL without terminal credit");
      task_credit_i=1; task_valid_i=1;
      @(posedge clk_i); while (!task_ready_o) @(posedge clk_i);
      @(negedge clk_i); task_valid_i=0;
      if (cancel!=0) begin
        while (commands!=job_index+1) @(negedge clk_i);
        task_packet_i=saved_task_packet; task_packet_i[16+:8]=1; task_packet_i[256+:256]=0;
        task_credit_i=0; task_valid_i=1;
        @(posedge clk_i); while (!task_ready_o) @(posedge clk_i);
        @(negedge clk_i); task_valid_i=0;
      end
      while (returns!=job_index+1) @(negedge clk_i);
      repeat(3) @(negedge clk_i);
    end
    if (native_commands!=commands || native_returns!=commands) $fatal(1,"native obligations");
    if (commands!=(words==23 ? calls : 0)) $fatal(1,"service count");
    if (status==0 && retire_count!=(words==23 ? 3*calls : calls)) $fatal(1,"retire count");
    if (life_o!=5 || !image_valid_o || trace_ireg_valid_o) $fatal(1,"not reusable after terminal");
    $display("PASS calls=%0d commands=%0d returns=%0d retired=%0d",calls,commands,returns,retire_count);
    $finish;
  end
  initial begin #200000; $fatal(1,"watchdog"); end
endmodule
