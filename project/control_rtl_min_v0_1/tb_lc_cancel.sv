`timescale 1ns/1ps
module tb_lc_cancel;
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
  integer point=0, cancel_age=0, responses=0, cancel_accepts=0, expected_status=0;
  reg cancel_sent=0, outcome_done=0;
  wire hold_pm = (point==2 || point==12 || point==19 || point==18) &&
    life_o>=6 && ((point==18 && seq_o==3 && trace_pc_o==1) ||
      (point==19 && seq_o==6) || ((point==2 || point==12) && seq_o==1)) &&
    (!cancel_sent || cancel_age<3 || point==12);
  wire hold_svc = point==6 && (!cancel_sent || cancel_age<3);
  wire no_response = point==10;
  wire wrong_response = point==22;
  wire hold_event = point==9 && (!cancel_sent || cancel_age<3);

  initial clk_i=0;
  always #5 clk_i=~clk_i;
`include "tb_trace.svh"

  // Registered program-memory peer. It models storage, never controller state.
  always @(posedge clk_i) begin
    if (!rst_ni) begin
      pm_pending<=0; pm_rsp_valid_i<=0; pm_rsp_data_i<=0; pm_rsp_error_i<=0;
      service_pending<=0; svc_rsp_valid_i<=0;
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
        if (service_pending || svc_rsp_valid_i) $fatal(1,"service overlap");
        if (svc_req_kind_o!=0 || svc_req_resource_o!=0 || svc_req_descriptor_o!==expected_desc ||
            svc_req_object_base_o!=0 || svc_req_object_length_o!=0 || svc_req_object_version_o!=0)
          $fatal(1,"M clear snapshot mismatch");
        commands<=commands+1; service_pending<=1; service_wait<=32+stall*3;
        saved_token<=svc_req_token_o; saved_seq<=svc_req_sequence_o; saved_job<=svc_req_job_o;
        saved_epoch<=svc_req_epoch_o; saved_task<=svc_req_task_sequence_o;
      end
      if (service_pending && !no_response) begin
        if (service_wait==0) begin
          service_pending<=0; svc_rsp_valid_i<=1;
          svc_rsp_kind_i<=0; svc_rsp_token_i<=saved_token; svc_rsp_sequence_i<=saved_seq;
          svc_rsp_job_i<=wrong_response ? saved_job+1 : saved_job; svc_rsp_epoch_i<=saved_epoch; svc_rsp_task_sequence_i<=saved_task;
          svc_rsp_status_i<=status[15:0]; svc_rsp_read_bytes_i<=0; svc_rsp_write_bytes_i<=0; svc_rsp_saturated_i<=0;
        end else service_wait<=service_wait-1;
      end
      if (svc_rsp_valid_i && svc_rsp_ready_o) begin
        if (svc_rsp_job_i!=saved_job) $fatal(1,"wrong response accepted");
        svc_rsp_valid_i<=0; responses<=responses+1;
      end
      if (cancel_sent) cancel_age<=cancel_age+1;
      if (task_valid_i && task_ready_o && task_packet_i[16+:8]==1) cancel_accepts<=cancel_accepts+1;
      if (trace_retire_o) retire_count<=retire_count+1;
      if (event_valid_o && event_ready_i) begin
        if (event_packet_o[0+:16]!=1 || event_packet_o[24+:8]!=0 ||
            event_packet_o[32+:32]!=saved_task_packet[32+:32] ||
            event_packet_o[64+:64]!=saved_task_packet[64+:64] ||
            event_packet_o[128+:8]!=saved_task_packet[136+:8] ||
            event_packet_o[136+:8]!=255 || event_packet_o[144+:16]!=expected_status[15:0] ||
            event_packet_o[16+:8]!=(expected_status==0 ? 2 : 3)) $fatal(1,"terminal mismatch");
        returns<=returns+1;
      end
      if ((life_o==6 || life_o==7 || life_o==8) && cfg_req_ready_o) $fatal(1,"runtime config admission");
      if (poison_o && point!=10 && point!=12 && point!=22) $fatal(1,"unexpected poison");
    end
  end
  // Drive peers on falling edges. Trace samples are pre-rising-edge values.
  always @(negedge clk_i) begin
    pm_req_ready_i=rst_ni && !pm_pending && !pm_rsp_valid_i && !hold_pm && (stall==0 || cycle%5==0);
    svc_req_ready_i=rst_ni && !service_pending && !svc_rsp_valid_i && !hold_svc && (stall==0 || cycle%7==0);
    event_ready_i=rst_ni && !hold_event && (stall==0 || cycle%11==0);
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

  initial begin : run_scenario
`include "tb_init.svh"
    if (!$value$plusargs("IMAGE=%s",image_path) || !$value$plusargs("TASK=%s",task_path) ||
        !$value$plusargs("WORDS=%d",words)) $fatal(1,"missing image/task/words");
    n=$value$plusargs("STALL=%d",stall); n=$value$plusargs("STATUS=%d",status);
    n=$value$plusargs("MODE=%d",mode); n=$value$plusargs("CALLS=%d",calls); n=$value$plusargs("POINT=%d",point);
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
    for (job_index=0;job_index<calls && !outcome_done;job_index=job_index+1) begin
      task_packet_i=task_input[0]; task_packet_i[96+:32]=job_index+1;
      saved_task_packet=task_packet_i; task_valid_i=0; task_credit_i=1;
      expected_status=job_index>0 || point==9 || point==13 ? status : status!=0 ? status : 11;
      @(negedge clk_i); task_valid_i=1;
      @(posedge clk_i); while (!task_ready_o) @(posedge clk_i);
      @(negedge clk_i); task_valid_i=0;
      if (job_index==0) begin
        case (point)
          1: begin end
          2,12: begin while (!(seq_o==1 && pm_req_valid_o && !pm_req_ready_i)) @(negedge clk_i); @(posedge clk_i); @(negedge clk_i); end
          3: while (seq_o!=2) @(negedge clk_i);
          4: while (seq_o!=4) @(negedge clk_i);
          5: while (seq_o!=7) @(negedge clk_i);
          6: begin while (!(svc_req_valid_o && !svc_req_ready_i)) @(negedge clk_i); @(posedge clk_i); @(negedge clk_i); end
          7,10,11,15,22: while (seq_o!=9) @(negedge clk_i);
          8,16: while (!svc_rsp_valid_i) @(negedge clk_i);
          9: begin while (!event_valid_o) @(negedge clk_i); @(posedge clk_i); @(negedge clk_i); end
          13: while (seq_o!=9) @(negedge clk_i);
          14: while (!(seq_o==5 && trace_opcode_o==8'h4f)) @(negedge clk_i);
          17: while (!(seq_o==9 && responses==1)) @(negedge clk_i);
          18: begin while (!(seq_o==3 && trace_pc_o==1 && pm_req_valid_o && !pm_req_ready_i)) @(negedge clk_i); @(posedge clk_i); @(negedge clk_i); end
          19: begin while (!(seq_o==6 && pm_req_valid_o && !pm_req_ready_i)) @(negedge clk_i); @(posedge clk_i); @(negedge clk_i); end
          20: while (!(seq_o==4 && pm_rsp_valid_i)) @(negedge clk_i);
          21: while (seq_o!=8) @(negedge clk_i);
          default: $fatal(1,"unknown cancellation point");
        endcase
        task_packet_i=saved_task_packet; task_packet_i[16+:8]=1;
        task_packet_i[256+:256]=0; task_credit_i=0;
        if (point==13) task_packet_i[32+:32]=task_packet_i[32+:32]+1;
        cancel_sent=1; task_valid_i=1;
        if (point==13) begin
          repeat(3) @(negedge clk_i);
          if (task_ready_o || cancel_accepts!=0) $fatal(1,"wrong CANCEL identity admitted");
          // Keep the rejected tuple offered until the source is reset below.
        end else begin
          @(posedge clk_i); while (!task_ready_o) @(posedge clk_i);
          @(negedge clk_i); task_valid_i=0;
          if (point==11) begin
            @(negedge clk_i); task_valid_i=1;
            @(posedge clk_i); while (!task_ready_o) @(posedge clk_i);
            @(negedge clk_i); task_valid_i=0;
          end
        end
        if (point==10 || point==12 || point==22) begin
          while (!poison_o) @(negedge clk_i);
          repeat(12) @(negedge clk_i);
          if (returns!=0 || image_valid_o || task_ready_o || cfg_req_ready_o || life_o!=8)
            $fatal(1,"poison lost isolation or fabricated terminal");
          $display("PASS poison point=%0d commands=%0d cancel_accepts=%0d",point,commands,cancel_accepts);
          outcome_done=1;
        end
      end
      if (!outcome_done) begin
      while (returns!=job_index+1) @(negedge clk_i);
      repeat(3) @(negedge clk_i);
      if (point==13) begin
        rst_ni=0;
        @(negedge clk_i); task_valid_i=0;
        @(negedge clk_i);
        if (image_valid_o || task_ready_o || cfg_req_ready_o) $fatal(1,"reset retained admission");
        $display("PASS wrong CANCEL ignored until source reset"); outcome_done=1;
      end
      end
    end
    if (!outcome_done) begin
    if (cancel_accepts!=(point==11 ? 2 : 1)) $fatal(1,"cancel accept count");
    if (life_o!=5 || !image_valid_o || trace_ireg_valid_o) $fatal(1,"not reusable after cancellation");
    $display("PASS point=%0d calls=%0d commands=%0d returns=%0d retired=%0d cancel_accepts=%0d",
      point,calls,commands,returns,retire_count,cancel_accepts);
    end
    $finish;
  end
  initial begin #200000; $fatal(1,"watchdog"); end
endmodule
