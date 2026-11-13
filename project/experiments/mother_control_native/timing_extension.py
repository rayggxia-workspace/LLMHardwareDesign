"""Text-only bounded trace points for calibrated PM/packet control costs."""

def extend(s):
    s=s.replace('  integer check_ptr=', '  integer timing_file=0;\n  string timing_path;\n  integer check_ptr=')
    marker='    check_targets=$value$plusargs("TARGETS_FILE=%s",targets_path);'
    assert marker in s
    s=s.replace(marker,'''    if($value$plusargs("TIMING_TRACE=%s",timing_path)) begin
      timing_file=$fopen(timing_path,"w");assert(timing_file!=0);
      $fwrite(timing_file,"cycle,event,target,detail,value\\n");
    end
'''+marker)
    marker='  initial begin #5000000;'
    assert marker in s
    s=s.replace(marker,'''`ifdef MC_TRANSPORT128
  wire timing_PM_req=dut.mother.pm_req_valid_o&&dut.mother.pm_req_ready_i&&!dut.mother.pm_req_write_o;
  wire timing_PM_rsp=dut.mother.pm_rsp_valid_i&&dut.mother.pm_rsp_ready_o;
  wire [13:0] timing_PM_address=dut.mother.pm_req_address_o;
`else
  wire timing_PM_req=dut.pm_req_valid_o&&dut.pm_req_ready_i&&!dut.pm_req_write_o;
  wire timing_PM_rsp=dut.pm_rsp_valid_i&&dut.pm_rsp_ready_o;
  wire [13:0] timing_PM_address=dut.pm_req_address_o;
`endif
  always @(posedge clk_i) if(runtime_active&&timing_file!=0) begin
    if(timing_PM_req)$fwrite(timing_file,"%0d,PMREQ,0,%0d,0\\n",cycle,timing_PM_address);
    if(timing_PM_rsp)$fwrite(timing_file,"%0d,PMRSP,0,0,0\\n",cycle);
    if(task_valid_o&&task_ready_i)$fwrite(timing_file,"%0d,TASK,%0d,%0d,%016x\\n",cycle,task_target_o,task_packet_o[16+:8],task_packet_o[256+:64]);
    if(return_valid_i&&return_ready_o)$fwrite(timing_file,"%0d,RETURN,%0d,%0d,%0d\\n",cycle,return_packet_i[24+:8],return_packet_i[16+:8],return_packet_i[96+:32]);
`ifdef MC_TRANSPORT128
    if(tx_valid&&tx_ready)$fwrite(timing_file,"%0d,TX,%0d,%0d,%0d\\n",cycle,tx_target,tx_sop,tx_eop);
    if(rx_valid&&rx_ready)$fwrite(timing_file,"%0d,RX,%0d,%0d,%0d\\n",cycle,rx_source,rx_sop,rx_eop);
`endif
  end
'''+marker)
    return s
