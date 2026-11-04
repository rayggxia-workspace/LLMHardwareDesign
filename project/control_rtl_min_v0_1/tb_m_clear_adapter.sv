`timescale 1ns/1ps
module tb_m_clear_adapter;
reg  clk_i;
reg  rst_ni;
reg  provider_released_i;
wire  poison_o;
wire  m_cmd_valid_o;
reg  m_cmd_ready_i;
wire [3:0] m_cmd_op_o;
wire [5:0] m_cmd_index_o;
wire [63:0] m_cmd_data_o;
reg  m_rsp_valid_i;
wire  m_rsp_ready_o;
reg [127:0] m_rsp_data_i;
reg  m_rsp_error_i;
reg  m_rsp_saturated_i;
wire  svc_req_ready_o;
wire  svc_rsp_valid_o;
wire [1:0] svc_rsp_kind_o;
wire [2:0] svc_rsp_token_o;
wire [31:0] svc_rsp_sequence_o;
wire [31:0] svc_rsp_job_o;
wire [31:0] svc_rsp_epoch_o;
wire [31:0] svc_rsp_task_sequence_o;
wire [15:0] svc_rsp_status_o;
wire [31:0] svc_rsp_read_bytes_o;
wire [31:0] svc_rsp_write_bytes_o;
wire  svc_rsp_saturated_o;
reg  svc_req_valid_i;
reg [1:0] svc_req_kind_i;
reg [2:0] svc_req_resource_i;
reg [2:0] svc_req_token_i;
reg [31:0] svc_req_sequence_i;
reg [31:0] svc_req_job_i;
reg [31:0] svc_req_epoch_i;
reg [31:0] svc_req_task_sequence_i;
reg [1023:0] svc_req_descriptor_i;
reg [63:0] svc_req_object_base_i;
reg [31:0] svc_req_object_length_i;
reg [31:0] svc_req_object_version_i;
reg  svc_rsp_ready_i;
  lc_m_clear_adapter dut(.*);
  integer cycle=0, mode=0,n,commands=0,responses=0,returns=0,wait_count=0;
  reg pending=0;
  reg [1023:0] canonical;
  reg [2047:0] descriptor_path;
  reg [1023:0] descriptor_input[0:0];
  initial clk_i=0;
  always #5 clk_i=~clk_i;
  always @(posedge clk_i) begin
    $display("A %0d %h",cycle,{clk_i,rst_ni,provider_released_i,poison_o,m_cmd_valid_o,m_cmd_ready_i,m_cmd_op_o,m_cmd_index_o,m_cmd_data_o,m_rsp_valid_i,m_rsp_ready_o,m_rsp_data_i,m_rsp_error_i,m_rsp_saturated_i,svc_req_ready_o,svc_rsp_valid_o,svc_rsp_kind_o,svc_rsp_token_o,svc_rsp_sequence_o,svc_rsp_job_o,svc_rsp_epoch_o,svc_rsp_task_sequence_o,svc_rsp_status_o,svc_rsp_read_bytes_o,svc_rsp_write_bytes_o,svc_rsp_saturated_o,svc_req_valid_i,svc_req_kind_i,svc_req_resource_i,svc_req_token_i,svc_req_sequence_i,svc_req_job_i,svc_req_epoch_i,svc_req_task_sequence_i,svc_req_descriptor_i,svc_req_object_base_i,svc_req_object_length_i,svc_req_object_version_i,svc_rsp_ready_i});
    cycle<=cycle+1;
    if (!rst_ni) begin pending<=0; m_rsp_valid_i<=0; end
    else begin
      if(m_cmd_valid_o && m_cmd_ready_i) begin
        if (commands!=0 || m_cmd_op_o!=6 || m_cmd_index_o!=0 || m_cmd_data_o!=0) $fatal(1,"native command tuple/count");
        commands<=commands+1; pending<=1; wait_count<=6;
      end
      if (pending && mode!=8 && mode!=9) begin
        if(wait_count==0) begin
          pending<=0; m_rsp_valid_i<=1; m_rsp_error_i<=mode==5; m_rsp_data_i<=mode==6 ? 128'd1 : 128'd0;
        end else wait_count<=wait_count-1;
      end
      if(m_rsp_valid_i && m_rsp_ready_o) begin m_rsp_valid_i<=0; responses<=responses+1; end
      if(svc_rsp_valid_o && svc_rsp_ready_i) returns<=returns+1;
    end
  end
  always @(negedge clk_i) m_cmd_ready_i=rst_ni && mode!=8 && mode!=9 && cycle%5==0;
  initial begin
    rst_ni=0;
    provider_released_i=0;
    m_cmd_ready_i=0;
    m_rsp_valid_i=0;
    m_rsp_data_i=0;
    m_rsp_error_i=0;
    m_rsp_saturated_i=0;
    svc_req_valid_i=0;
    svc_req_kind_i=0;
    svc_req_resource_i=0;
    svc_req_token_i=0;
    svc_req_sequence_i=0;
    svc_req_job_i=0;
    svc_req_epoch_i=0;
    svc_req_task_sequence_i=0;
    svc_req_descriptor_i=0;
    svc_req_object_base_i=0;
    svc_req_object_length_i=0;
    svc_req_object_version_i=0;
    svc_rsp_ready_i=0;
    n=$value$plusargs("MODE=%d",mode);
    if (!$value$plusargs("DESCRIPTOR=%s",descriptor_path)) $fatal(1,"descriptor path");
    $readmemh(descriptor_path,descriptor_input,0,0); canonical=descriptor_input[0];
    repeat(2) @(negedge clk_i); rst_ni=1;
    repeat(2) @(negedge clk_i);
    if (svc_req_ready_o) $fatal(1,"provider not released");
    provider_released_i=1;
    if (mode==7) begin
      m_rsp_valid_i=1;
      repeat(3) @(negedge clk_i);
      if (!poison_o || svc_req_ready_o || svc_rsp_valid_o || m_rsp_ready_o) $fatal(1,"stale native response retagged");
    end else begin
      svc_req_descriptor_i=canonical; svc_req_token_i=3; svc_req_sequence_i=29;
      svc_req_job_i=7; svc_req_epoch_i=2; svc_req_task_sequence_i=13;
      case(mode)
        1: svc_req_descriptor_i[448+:32]=65538;
        2: svc_req_resource_i=1;
        3: svc_req_descriptor_i[32+:16]=4;
        4: svc_req_object_base_i=16;
      endcase
      svc_req_valid_i=1;
      @(posedge clk_i); while(!svc_req_ready_o) @(posedge clk_i);
      @(negedge clk_i); svc_req_valid_i=0;
      // Change the inactive source bus; an accepted request owns its snapshot.
      svc_req_token_i=0; svc_req_sequence_i=999; svc_req_job_i=99;
      svc_req_epoch_i=99; svc_req_task_sequence_i=99; svc_req_descriptor_i=0;
      if(mode==8 || mode==9) begin
        while(!m_cmd_valid_o) @(negedge clk_i);
        @(posedge clk_i); @(negedge clk_i);
        if(mode==8) provider_released_i=0; else m_rsp_valid_i=1;
        repeat(5) @(negedge clk_i);
        if (!poison_o || svc_req_ready_o || svc_rsp_valid_o || !m_cmd_valid_o || m_rsp_ready_o)
          $fatal(1,"poison withdrew native offer or fabricated completion");
      end else begin
        while(!svc_rsp_valid_o) @(negedge clk_i);
        repeat(5) begin
          @(negedge clk_i);
          if (!svc_rsp_valid_o || svc_req_ready_o || svc_rsp_kind_o!=0 || svc_rsp_token_o!=3 ||
            svc_rsp_sequence_o!=29 || svc_rsp_job_o!=7 || svc_rsp_epoch_o!=2 || svc_rsp_task_sequence_o!=13 ||
            svc_rsp_read_bytes_o!=0 || svc_rsp_write_bytes_o!=0 || svc_rsp_saturated_o ||
            svc_rsp_status_o!=(mode==2 ? 4 : mode>=1 && mode<=4 ? 5 : mode==5 || mode==6 ? 9 : 0))
              $fatal(1,"service response snapshot/backpressure/status");
        end
        svc_rsp_ready_i=1; @(negedge clk_i); svc_rsp_ready_i=0;
        repeat(2) @(negedge clk_i);
        if (returns!=1 || poison_o || !svc_req_ready_o || commands!=(mode>=1 && mode<=4 ? 0 : 1) || responses!=commands)
          $fatal(1,"unit obligations/counts");
      end
    end
    $display("PASS adapter mode=%0d commands=%0d responses=%0d returns=%0d",mode,commands,responses,returns);
    $finish;
  end
  initial begin #10000; $fatal(1,"watchdog"); end
endmodule
