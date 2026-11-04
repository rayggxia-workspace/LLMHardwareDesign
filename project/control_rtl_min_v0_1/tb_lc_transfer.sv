`timescale 1ns/1ps
module tb_lc_transfer #(parameter [7:0] BLOCK=0);
`include "tb_transfer_wires.svh"
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
  integer cancel=0, cancel_pc=1, zero_begin=-1, zero_end=-1;
  integer fault_address=-1, pm_error=0, expect_status=0, expect_pc=0;
  integer expected_commands=0, poison_case=0, recovery=0, session=1;
  integer no_response=0, hold_pm=0, hold_svc=0, reject_call=0;
  reg [127:0] fault_xor=0;
  reg inject_fault=0;
  reg [127:0] sampled_word;
  reg [127:0] sram[0:1023];
  reg [127:0] peer_sink, payload;
  reg [1:0] saved_kind;
  reg [31:0] saved_base;
  integer peer_state=0, data_delay=0, ready_reports=0, report_age=0;
  integer expected_reports=0, expected_read=0, expected_write=0, expected_scalar=1;
  integer fault_after=1, ack_count=0, store_count=0, read_count=0;
  reg ready_seen=0;
  reg [511:0] expected_transfer;
  wire ack_ready=!(mode==2 && saved_kind==2) && (stall==0 || cycle%13==0);
  function [127:0] pattern;
    input [31:0] task_seq;
    begin pattern=128'h0f0e0d0c0b0a09080706050403020100 ^ {4{task_seq}}; end
  endfunction
  task data_event;
    input integer kind;
    input [127:0] data;
    begin $display("D %0d %0d %0h %0h %0d %0d %0d %0d %0d",($time/10),kind,saved_base,data,
      saved_job,saved_epoch,saved_task,saved_seq,saved_kind); end
  endtask


  initial clk_i=0;
  always #5 clk_i=~clk_i;
`include "tb_trace.svh"

  // Registered program-memory peer. It models storage, never controller state.
  always @(posedge clk_i) begin
    if (!rst_ni) begin
      pm_pending<=0; pm_rsp_valid_i<=0; pm_rsp_data_i<=0; pm_rsp_error_i<=0;
      service_pending<=0; svc_rsp_valid_i<=0; peer_state<=0; ready_seen<=0;
    end else begin
      if (pm_req_valid_o && pm_req_ready_i) begin
        if (pm_pending || pm_rsp_valid_i) $fatal(1,"PM overlap");
        if (pm_req_address_o[3:0]!=0 || pm_req_address_o+16>8320) $fatal(1,"PM range");
        pm_pending<=1; request_wait<=stall+1;
        pending_write<=pm_req_write_o; pending_address<=pm_req_address_o; pending_data<=pm_req_data_o;
      end
      if (pm_pending && !(inject_fault && no_response==1)) begin
        if (request_wait==0) begin
          pm_pending<=0; pm_rsp_valid_i<=1;
          if (pending_write) begin memory[pending_address[13:4]]<=pending_data; pm_rsp_data_i<=0; end
          else begin
            pm_rsp_data_i<=memory[pending_address[13:4]] ^
              (inject_fault && saved_task_packet[96+:32]>=fault_after[31:0] && {18'b0,pending_address}==fault_address[31:0] ? fault_xor : 128'b0);
            pm_rsp_error_i<=inject_fault && saved_task_packet[96+:32]>=fault_after[31:0] && {18'b0,pending_address}==fault_address[31:0] && pm_error!=0;
            if (inject_fault && zero_begin>=0 && {18'b0,pending_address}>=zero_begin[31:0] &&
                {18'b0,pending_address}<zero_end[31:0]) pm_rsp_data_i<=0;
          end
        end else request_wait<=request_wait-1;
      end
      if (pm_rsp_valid_i && pm_rsp_ready_o) begin pm_rsp_valid_i<=0; pm_rsp_error_i<=0; end
      if (task_valid_i && task_ready_o && task_packet_i[16+:8]==0) begin ready_seen<=0; report_age<=0; end
      if (event_valid_o && event_packet_o[16+:8]==0) report_age<=report_age+1;
      if (event_valid_o && event_ready_i && event_packet_o[16+:8]==0) begin
        ready_seen<=1; ready_reports<=ready_reports+1;
      end
      if (svc_req_valid_o && svc_req_ready_i) begin
        if (peer_state!=0 || svc_rsp_valid_i || svc_req_kind_o==0 || svc_req_resource_o!=5 ||
            svc_req_object_length_o!=16 || svc_req_object_version_o!=1 || svc_req_object_base_o>=16384 ||
            svc_req_object_base_o[3:0]!=0 || svc_req_descriptor_o[1023:512]!=0)
          $fatal(1,"finite RAW16 service tuple/ownership");
        expected_transfer=0;
        for(n=0;n<4;n=n+1) expected_transfer[n*128+:128]=input_image[(input_image[3][0+:32]>>4)+
          (svc_req_kind_o==2 ? 4 : 0)+32'(n)];
        if (svc_req_descriptor_o[511:0]!==expected_transfer) $fatal(1,"transfer snapshot differs from resident binary");
        commands<=commands+1; peer_state<=1; data_delay<=mode==3 ? 1 : 32+stall*3;
        saved_kind<=svc_req_kind_o; saved_token<=svc_req_token_o; saved_seq<=svc_req_sequence_o;
        saved_job<=svc_req_job_o; saved_epoch<=svc_req_epoch_o; saved_task<=svc_req_task_sequence_o;
        saved_base<=svc_req_object_base_o[31:0]; payload<=pattern(svc_req_task_sequence_o);
      end
      if (peer_state==1) begin
        if(data_delay!=0) data_delay<=data_delay-1;
        else if(mode==3) peer_state<=5;
        else if(saved_kind==2 || BLOCK==0 || ready_seen) peer_state<=2;
      end
      if(peer_state==2) begin
        if(saved_kind==1) begin
          sram[saved_base[13:4]]<=payload; store_count<=store_count+1; data_event(1,payload); peer_state<=4;
        end else begin
          if(sram[saved_base[13:4]]!==payload) $fatal(1,"TX used stale/unwritten finite SRAM word");
          read_count<=read_count+1; data_event(2,sram[saved_base[13:4]]); peer_state<=3;
        end
      end
      if(peer_state==3) begin
        peer_sink<=sram[saved_base[13:4]]; data_event(4,sram[saved_base[13:4]]); peer_state<=4;
      end
      if(peer_state==4 && ack_ready) begin
        if(saved_kind==2 && peer_sink!==payload) $fatal(1,"peer ACK before actual peer store");
        ack_count<=ack_count+1; data_event(3,payload); peer_state<=5;
      end
      if(peer_state==5) begin
        peer_state<=6; svc_rsp_valid_i<=1; svc_rsp_kind_i<=saved_kind; svc_rsp_token_i<=saved_token;
        svc_rsp_sequence_i<=saved_seq; svc_rsp_job_i<=mode==1 ? saved_job+1 : saved_job;
        svc_rsp_epoch_i<=saved_epoch; svc_rsp_task_sequence_i<=saved_task;
        svc_rsp_status_i<=mode==3 || mode==5 && saved_kind==2 ? 9 : 0;
        svc_rsp_read_bytes_i<=mode!=3 && saved_kind==2 ? 16 : 0;
        svc_rsp_write_bytes_i<=mode!=3 && saved_kind==1 ? 16 : 0; svc_rsp_saturated_i<=0;
      end
      if(svc_rsp_valid_i && svc_rsp_ready_o) begin svc_rsp_valid_i<=0; peer_state<=0; end
      if (trace_retire_o) retire_count<=retire_count+1;
      if (event_valid_o && event_ready_i) begin
        if (event_packet_o[0+:16]!=1 || event_packet_o[24+:8]!=BLOCK ||
            event_packet_o[32+:32]!=saved_task_packet[32+:32] || event_packet_o[64+:64]!=saved_task_packet[64+:64])
          $fatal(1,"event identity");
        if(event_packet_o[16+:8]>=2) begin
          if(event_packet_o[128+:8]!=saved_task_packet[136+:8] || event_packet_o[136+:8]!=255 ||
             event_packet_o[144+:16]!=expect_status[15:0] || event_packet_o[320+:32]!=expect_pc[31:0] ||
             event_packet_o[192+:32]!=expected_read[31:0] || event_packet_o[224+:32]!=expected_write[31:0])
            $fatal(1,"terminal status/PC/confirmed prefix");
          returns<=returns+1;
        end else if(event_packet_o[160+:32]!=expected_scalar[31:0]) $fatal(1,"MOVI/REPORT scalar readback");
      end
      if (life_o==6 && cfg_req_ready_o) $fatal(1,"runtime config admission");
      if (poison_o && poison_case==0) $fatal(1,"unexpected poison");
    end
  end
  // Drive peers on falling edges. Trace samples are pre-rising-edge values.
  always @(negedge clk_i) begin
    pm_req_ready_i=rst_ni && !pm_pending && !pm_rsp_valid_i && !(inject_fault && hold_pm!=0) && (stall==0 || cycle%5==0);
    svc_req_ready_i=rst_ni && peer_state==0 && !svc_rsp_valid_i && !(inject_fault && hold_svc!=0) && (stall==0 || cycle%7==0);
    event_ready_i=rst_ni && !(mode==6 && event_valid_o && event_packet_o[16+:8]==0 && report_age<30) && (stall==0 || cycle%11==0);
  end

  task config_command;
    input [2:0] op;
    input integer address;
    input [127:0] data;
    input integer expect_status;
    begin
      @(negedge clk_i);
      cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=session[31:0];
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
`include "tb_init.svh"
    if (!$value$plusargs("IMAGE=%s",image_path) || !$value$plusargs("TASK=%s",task_path) ||
        !$value$plusargs("WORDS=%d",words)) $fatal(1,"missing files");
    n=$value$plusargs("STALL=%d",stall); n=$value$plusargs("MODE=%d",mode); n=$value$plusargs("CALLS=%d",calls);
    n=$value$plusargs("FAULT_ADDR=%d",fault_address); n=$value$plusargs("FAULT_XOR=%h",fault_xor);
    n=$value$plusargs("ZERO_BEGIN=%d",zero_begin); n=$value$plusargs("ZERO_END=%d",zero_end);
    n=$value$plusargs("EXPECTED=%d",expect_status); n=$value$plusargs("ERROR_PC=%d",expect_pc);
    n=$value$plusargs("COMMANDS=%d",expected_commands); n=$value$plusargs("REPORTS=%d",expected_reports);
    n=$value$plusargs("READ_BYTES=%d",expected_read); n=$value$plusargs("WRITE_BYTES=%d",expected_write);
    n=$value$plusargs("SCALAR=%d",expected_scalar); n=$value$plusargs("POISON=%d",poison_case);
    $readmemh(image_path,input_image,0,words-1); $readmemh(task_path,task_input,0,0);
    length_bytes=words*16; expected_image_id=input_image[3][96+:32]; expected_topology=input_image[4][0+:32];
    for(n=0;n<520;n=n+1) memory[n]={16{8'hcd}};
    for(n=0;n<1024;n=n+1) sram[n]={16{8'hcd}};
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0,0);
    for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n],0);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0,0);
    config_command(3,0,0,0); config_command(4,0,0,0);
    if(image_valid_o || task_ready_o) $fatal(1,"local PREPARE bypass");
    deploy_valid_i=1; deploy_generation_i=1;
    while(life_o!=5) @(negedge clk_i);
    inject_fault=1;
    for(job_index=0;job_index<calls;job_index=job_index+1) begin
      task_packet_i=task_input[0]; task_packet_i[96+:32]=job_index+1; saved_task_packet=task_packet_i;
      task_credit_i=1; task_valid_i=1;
      @(posedge clk_i); while(!task_ready_o) @(posedge clk_i);
      @(negedge clk_i); task_valid_i=0;
      if(mode==6) begin
        while(!(event_valid_o && event_packet_o[16+:8]==0 && !event_ready_i)) @(negedge clk_i);
        task_packet_i=saved_task_packet; task_packet_i[16+:8]=1; task_packet_i[256+:256]=0;
        task_credit_i=0; task_valid_i=1;
        @(posedge clk_i); while(!task_ready_o) @(posedge clk_i);
        @(negedge clk_i); task_valid_i=0;
      end
      if(poison_case!=0) begin
        while(!poison_o) @(negedge clk_i);
        repeat(10) @(negedge clk_i);
        if(returns!=0 || image_valid_o || task_ready_o || cfg_req_ready_o || event_valid_o) $fatal(1,"poison fabricated terminal/credit");
      end else begin
        while(returns!=job_index+1) @(negedge clk_i);
        repeat(3) @(negedge clk_i);
        if(life_o!=5 || !image_valid_o || trace_ireg_valid_o) $fatal(1,"transfer task not reusable");
      end
    end
    if(commands!=expected_commands || ready_reports!=expected_reports) $fatal(1,"service/report count");
    $display("PASS RAW16 block=%0d calls=%0d commands=%0d ready=%0d terminal=%0d stores=%0d reads=%0d ACK=%0d",
      BLOCK,calls,commands,ready_reports,returns,store_count,read_count,ack_count);
    $finish;
  end
  initial begin #400000; $fatal(1,"watchdog"); end
endmodule
