"""Reuse the retired-token Gather fixture with the real native MC and switch."""
import argparse
from pathlib import Path


def add_mother(text):
    def swap(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f'fixture does not uniquely contain {old}')
        text = text.replace(old, new)

    swap('logic [511:0] task_packet=0;', 'wire task_valid;')
    swap('cfg_valid=0,cfg_take=0,task_valid=0,event_take=0;', 'cfg_valid=0,cfg_take=0,event_take=0;')
    swap('logic [1:0] flit=0;', '''  localparam int MOTHER_WORDS=10;
  reg [127:0] mother_image[0:MOTHER_WORDS-1];
  string mother_path;
  logic mc_cfg_valid=0,mc_cfg_take=0,mc_start_request=0;
  logic [2:0] mc_cfg_op=0;
  logic [13:0] mc_cfg_address=0;
  logic [127:0] mc_cfg_data=0;
  wire mc_cfg_ready,mc_cfg_rsp,mc_start_ready,mc_result,mc_poison;
  wire [15:0] mc_cfg_status,mc_result_status;
  wire [3:0] mc_life;
  wire [127:0] mc_cfg_result;
  wire [31:0] mc_result_job,mc_result_reads,mc_result_writes,mc_frame_fault,mc_protocol_faults;
  wire mc_valid,mc_ready,mc_sop,mc_eop,mc_credit;
  wire [7:0] mc_target,mc_source;
  wire [127:0] mc_data,mc_rx_data;
  wire mc_rx_valid,mc_rx_ready,mc_rx_sop,mc_rx_eop,switch_idle;
  wire [8:0] switch_valid,switch_ready;
  wire [71:0] switch_target;
  integer call_at=-1, terminal_at=-1, output_flits=0;
  // The trace drives the vocabulary reduction. The MC alone executes the
  // linked Gather page. A request manager must only assert start on ownership.
  wire mc_start_valid=mc_start_request && retired_valid && !retired_error &&
                      retired_tag==TOKEN_GENERATION;
  assign task_valid=switch_valid[3];
  mother_control_native64_transport128 mc (
    .clk_i(clk),.rst_ni(!reset),.release_valid_i(release_valid),
    .release_sequence_i(32'd1),.release_epoch_i(32'd1),
    .deploy_valid_i(deploy),.deploy_generation_i(32'd1),.poison_o(mc_poison),
    .cfg_req_valid_i(mc_cfg_valid),.cfg_req_op_i(mc_cfg_op),.cfg_req_generation_i(32'd1),
    .cfg_req_address_i(mc_cfg_address),.cfg_req_data_i(mc_cfg_data),
    .cfg_req_total_bytes_i(16'd160),.cfg_req_image_id_i(NATIVE_IMAGE),
    .cfg_req_topology_id_i(NATIVE_TOPOLOGY),.cfg_req_abi_id_i(32'h02500002),
    .cfg_req_capacity_id_i(32'h02590003),.cfg_req_proof_i(1'b1),
    .cfg_rsp_ready_i(mc_cfg_take),.cfg_req_ready_o(mc_cfg_ready),.cfg_rsp_valid_o(mc_cfg_rsp),
    .cfg_rsp_status_o(mc_cfg_status),.cfg_rsp_data_o(mc_cfg_result),.life_o(mc_life),
    .start_valid_i(mc_start_valid),.start_credit_i(1'b1),.start_job_i(32'd7),
    .start_epoch_i(32'd1),.start_sequence_i(32'd1),.start_generation_i(32'd1),
    .local_image_ids_i(288'(NATIVE_IMAGE)<<96),.local_enabled_i(9'b000001000),
    .start_ready_o(mc_start_ready),.tx_valid(mc_valid),.tx_ready(mc_ready),
    .tx_data(mc_data),.tx_target(mc_target),.tx_sop(mc_sop),.tx_eop(mc_eop),.tx_credit(mc_credit),
    .rx_valid(mc_rx_valid),.rx_ready(mc_rx_ready),.rx_data(mc_rx_data),
    .rx_source(mc_source),.rx_sop(mc_rx_sop),.rx_eop(mc_rx_eop),
    .transport_drained_i(switch_idle && link_drained),.frame_fault_count(mc_frame_fault),
    .result_valid_o(mc_result),.result_ready_i(1'b1),.result_job_o(mc_result_job),
    .result_status_o(mc_result_status),.result_confirmed_read_bytes_o(mc_result_reads),
    .result_confirmed_write_bytes_o(mc_result_writes),.recover_valid_i(1'b0),
    .protocol_fault_count_o(mc_protocol_faults)
  );
  mc_lc_packet128_switch #(.ENDPOINTS(9)) switch (
    .clk,.reset,.tx_valid(mc_valid),.tx_sop(mc_sop),.tx_ready(mc_ready),
    .tx_target(mc_target),.tx_header_target(mc_data[24+:8]),.lc_rx_valid(switch_valid),
    .lc_rx_ready({5'b0,frame_ready,3'b0}),.lc_rx_target(switch_target),.lc_rx_header_target(),
    .lc_tx_valid({5'b0,tx_valid && allow_return,3'b0}),.lc_tx_ready(switch_ready),
    .lc_tx_data({640'b0,tx_data,384'b0}),.lc_tx_sop({5'b0,tx_sop,3'b0}),
    .lc_tx_eop({5'b0,tx_eop,3'b0}),.rx_valid(mc_rx_valid),.rx_ready(mc_rx_ready),
    .rx_data(mc_rx_data),.rx_source(mc_source),.rx_sop(mc_rx_sop),.rx_eop(mc_rx_eop),
    .transport_idle(switch_idle)
  );
  logic allow_return=0;
  assign tx_ready=allow_return && switch_ready[3];
  always @(posedge clk) if(!reset) begin
    if(mc_valid && mc_ready) begin
      assert(mc_target==3 && switch_valid==9'b000001000 && mc_credit);
      assert(mc_sop==(output_flits==0) && mc_eop==(output_flits==3) && output_flits<4);
      if(mc_sop) begin
        assert(retired_valid && !retired_error && retired_tag==TOKEN_GENERATION);
        call_at<=cycle;
      end
      output_flits<=output_flits+1;
    end
    if(mc_rx_valid && mc_rx_ready && mc_rx_eop) terminal_at<=cycle;
    if(mc_result) begin
      assert(output_flits==4 && terminal_at>last_commit && terminal_at<cycle);
      assert(mc_result_status==0 && mc_result_job==7 && mc_result_reads==8208 && mc_result_writes==8208);
      assert(!mc_poison && mc_frame_fault==0 && mc_protocol_faults==0);
    end
  end''')
    swap('logic tx_ready=0;', 'wire tx_ready;')
    swap("localparam logic [31:0] NATIVE_IMAGE=32'hbeef17, NATIVE_TOPOLOGY=32'hadcafe;",
         "wire [31:0] NATIVE_IMAGE=mother_image[3][96+:32], NATIVE_TOPOLOGY=mother_image[4][0+:32];")
    swap('''    .native_rx_valid_i(task_valid),.native_rx_sop_i(flit==0),.native_rx_eop_i(flit==3),
    .native_rx_credit_i(1'b1),.native_rx_data_i(task_packet[128*flit+:128]),
    .native_rx_target_i(8'd3),.native_rx_ready_o(frame_ready),''',
         '''    .native_rx_valid_i(task_valid),.native_rx_sop_i(mc_sop),.native_rx_eop_i(mc_eop),
    .native_rx_credit_i(mc_credit),.native_rx_data_i(mc_data),
    .native_rx_target_i(switch_target[24+:8]),.native_rx_ready_o(frame_ready),''')
    swap('  initial begin\n    #1000000;', '''  task automatic configure_mother(input logic [2:0] op, input integer word);
    @(negedge clk);
    mc_cfg_valid=1; mc_cfg_op=op; mc_cfg_address=14'(word*16); mc_cfg_data=mother_image[word];
    do @(posedge clk); while(!mc_cfg_ready);
    @(negedge clk); mc_cfg_valid=0;
    while(!mc_cfg_rsp) @(negedge clk);
    assert(mc_cfg_status==0 && (op!=2 || mc_cfg_result===mother_image[word]))
      else $fatal(1,"MC configuration op=%0d word=%0d status=%0d",op,word,mc_cfg_status);
    mc_cfg_take=1; @(negedge clk); mc_cfg_take=0;
  endtask

  initial begin
    #1000000;''')
    swap('    $readmemh(image_path,image);', '''    assert($value$plusargs("mother=%s",mother_path));
    $readmemh(mother_path,mother_image);
    assert(mother_image[4][0+:32]==TOPOLOGY);
    $readmemh(image_path,image);''')
    swap('''    configure(4,0);
    @(negedge clk); deploy=1;
    while(life!=5) @(negedge clk);''', '''    configure(4,0);
    configure_mother(0,0);
    for(integer i=0;i<MOTHER_WORDS;i++) configure_mother(1,i);
    for(integer i=0;i<MOTHER_WORDS;i++) configure_mother(2,i);
    configure_mother(3,0);
    configure_mother(4,0);
    @(negedge clk); deploy=1;
    while(life!=5 || mc_life!=5) @(negedge clk);''')
    start = text.index('    // The request sequencer')
    stop = text.index('    while(!tx_valid)', start)
    text = text[:start] + '''    // Offer the page before the retirement is available. Its start can
    // handshake only after the previous token's actual reduction completes.
    mc_start_request=1;
    do @(posedge clk); while(!(mc_start_valid && mc_start_ready));
    @(negedge clk); mc_start_request=0;
''' + text[stop:]
    swap('    tx_ready=1;', '    allow_return=1;')
    swap('''    @(negedge clk); event_take=0;
    assert(life==5 && link_drained && !link_fault);''', '''    @(negedge clk); event_take=0;
    while(!mc_result) @(negedge clk);
    @(posedge clk); @(negedge clk);
    assert(life==5 && link_drained && !link_fault && switch_idle);
    $display("PASS mother-to-U0 Gather call=%0d token_writer_accept=%0d index_commit=%0d row_commit=%0d terminal=%0d reads=%0d writes=%0d",
             call_at,retire_at,index_commit_at,last_commit,terminal_at,mc_result_reads,mc_result_writes);''')
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(add_mother(args.fixture.read_text()))
