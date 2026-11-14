"""Exercise the resident Gather through the native four-flit command port."""
from pathlib import Path

def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'unexpected program fixture anchor: {old}')
    return source.replace(old, new)

source = Path('tb_u_gather_program.sv').read_text()
source = source.replace('tb_u_gather_program', 'tb_u_gather_frame')
start = source.index('  control_pm #')
end = source.index('    .block_id_i',start)
source = source[:start]+'''  wire frame_ready,tx_valid,tx_sop,tx_eop,link_fault,link_drained;
  logic tx_ready=0;
  logic [2:0] tx_words=0;
  logic [1:0] flit=0;
  localparam logic [31:0] NATIVE_IMAGE=32'hbeef17, NATIVE_TOPOLOGY=32'hadcafe;
  u_n32_native_frame_64 #(.ENABLE_INDEXED_GATHER(1)) dut (
'''+source[end:]
source = once(source,'    .block_id_i(8\'d0),.topology_id_i(TOPOLOGY),.clk_i(clk),.rst_ni(!reset),',
              '    .clk_i(clk),.rst_ni(!reset),')
start = source.index('    .pm_req_ready_i')
end = source.index('    .score_valid',start)
source=source[:start]+'''    .native_rx_valid_i(task_valid),.native_rx_sop_i(flit==0),.native_rx_eop_i(flit==3),
    .native_rx_credit_i(1'b1),.native_rx_data_i(task_packet[128*flit+:128]),
    .native_rx_target_i(8'd3),.native_rx_ready_o(frame_ready),
    .native_tx_valid_o(tx_valid),.native_tx_sop_o(tx_sop),.native_tx_eop_o(tx_eop),
    .native_tx_data_o(tx_data),.native_tx_ready_i(tx_ready),
    .native_image_i(NATIVE_IMAGE),.native_topology_i(NATIVE_TOPOLOGY),.legacy_image_i(image[3][96+:32]),
    .native_link_drained_o(link_drained),.native_link_fault_o(link_fault),.life_o(life),
'''+source[end:]
source=once(source,'  integer backend_count', '''  wire [127:0] tx_data;
  logic [511:0] returned=0;
  assign event_packet=returned;
  assign event_valid=tx_words==4;
  always @(posedge clk) if (!reset && tx_valid && tx_ready) begin
    assert(tx_words<4 && tx_sop==(tx_words==0) && tx_eop==(tx_words==3));
    returned[128*tx_words+:128]<=tx_data;
    tx_words<=tx_words+1;
  end
  integer backend_count''')
source=source.replace('dut.', 'dut.local_group.')
source=once(source,'assert(!dma_fault && !poison);','assert(!dma_fault && !poison && !link_fault);')
source=once(source,"event_packet[0+:16]==1 && event_packet[16+:8]==2 &&",
            "event_packet[0+:16]==2 && event_packet[16+:8]==2 && event_packet[24+:8]==3 &&")
source=once(source,'event_packet[192+:32]==8208 && event_packet[224+:32]==8192);',
            'event_packet[192+:32]==8208 && event_packet[224+:32]==8192 &&\n             event_packet[128+:8]==9 && event_packet[352+:32]==1 && event_packet[384+:32]==NATIVE_TOPOLOGY);')
i=source.index('    while(!task_ready)')
j=source.index('    $finish;',i)
source=source[:i]+'''    while(life!=5) @(negedge clk);
    task_packet[0+:16]=2; task_packet[24+:8]=3; task_packet[32+:32]=7;
    task_packet[64+:32]=1; task_packet[96+:32]=1; task_packet[136+:8]=9;
    task_packet[160+:32]=NATIVE_IMAGE; task_packet[192+:32]=NATIVE_TOPOLOGY;
    task_packet[224+:32]=1;
    task_valid=1;
    for(integer i=0;i<4;i++) begin
      flit=2'(i);
      do @(posedge clk); while(!frame_ready);
      @(negedge clk);
    end
    task_valid=0;
    while(!tx_valid) @(negedge clk);
    repeat(7) begin @(negedge clk); assert(tx_valid && tx_sop && commits==512); end
    tx_ready=1;
    while(!event_valid) @(negedge clk);
    event_take=1;
    @(negedge clk); event_take=0;
    assert(life==5 && link_drained && !link_fault);
    $display("PASS generated Gather framed CALL read_back=352 ddr_beats=%0d sram_writes=%0d last_commit=%0d",
             response_count,commits,last_commit);
'''+source[j:]
Path('tb_u_gather_frame.sv').write_text(source)

