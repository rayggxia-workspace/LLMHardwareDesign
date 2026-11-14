`timescale 1ns/1ps
module tb_u_gather_program;
  logic clk=0,reset=1;
  always #5 clk=~clk;
  integer cycle=0, issued=0, commits=0, index_reads=0;
  reg [127:0] expected_row[0:511];
  reg [127:0] image[0:21];
  reg [31:0] index_asset[0:0];
  localparam logic [63:0] TABLE=64'd3298373632;
  logic [63:0] row_address;
  localparam logic [31:0] TOPOLOGY=32'h02500031;
  logic release_valid=0,deploy=0,cfg_valid=0,cfg_take=0,task_valid=0,event_take=0;
  logic incoming_valid=0;
  logic [2:0] cfg_op=0;
  logic [13:0] cfg_addr=0;
  logic [127:0] cfg_data=0;
  logic [511:0] task_packet=0;
  wire cfg_ready,cfg_rsp,event_valid,task_ready,incoming_ready,incoming_ack,poison;
  wire [15:0] cfg_status;
  wire [127:0] cfg_result,pm_wdata,pm_rdata;
  wire [511:0] event_packet;
  wire [13:0] pm_addr;
  wire pm_req,pm_ready,pm_write,pm_rsp,pm_take,pm_error;
  wire [3:0] life;
  integer last_commit=-1;
  string image_path, row_path, index_path;
  control_pm #(.BYTES(4096)) pm (
    .clk_i(clk),.rst_ni(!reset),.req_valid_i(pm_req),.req_write_i(pm_write),
    .req_address_i(pm_addr),.req_data_i(pm_wdata),.req_ready_o(pm_ready),
    .rsp_valid_o(pm_rsp),.rsp_ready_i(pm_take),.rsp_data_o(pm_rdata),.rsp_error_o(pm_error)
  );
  u_n32_controlled_64 #(.ENABLE_INDEXED_GATHER(1)) dut (
    .block_id_i(8'd0),.topology_id_i(TOPOLOGY),.clk_i(clk),.rst_ni(!reset),
    .release_valid_i(release_valid),.release_sequence_i(32'd1),.release_epoch_i(32'd1),
    .deploy_valid_i(deploy),.deploy_generation_i(32'd1),.poison_o(poison),
    .cfg_req_valid_i(cfg_valid),.cfg_req_op_i(cfg_op),.cfg_req_generation_i(32'd1),
    .cfg_req_address_i(cfg_addr),.cfg_req_data_i(cfg_data),.cfg_req_total_bytes_i(16'd352),
    .cfg_req_image_id_i(image[3][96+:32]),.cfg_req_topology_id_i(TOPOLOGY),
    .cfg_req_abi_id_i(32'h01930001),.cfg_req_capacity_id_i(32'h17630001),
    .cfg_req_proof_i(1'b1),.cfg_rsp_ready_i(cfg_take),.cfg_req_ready_o(cfg_ready),
    .cfg_rsp_valid_o(cfg_rsp),.cfg_rsp_status_o(cfg_status),.cfg_rsp_data_o(cfg_result),
    .pm_req_ready_i(pm_ready),.pm_rsp_valid_i(pm_rsp),.pm_rsp_data_i(pm_rdata),.pm_rsp_error_i(pm_error),
    .pm_req_valid_o(pm_req),.pm_req_write_o(pm_write),.pm_req_address_o(pm_addr),
    .pm_req_data_o(pm_wdata),.pm_rsp_ready_o(pm_take),
    .task_valid_i(task_valid),.task_packet_i(task_packet),.task_credit_i(1'b1),.task_ready_o(task_ready),
    .event_ready_i(event_take),.event_valid_o(event_valid),.event_packet_o(event_packet),.life_o(life),
    .close_req_ready_i(1'b0),.close_rsp_valid_i(1'b0),.close_rsp_sequence_i('0),
    .close_rsp_job_i('0),.close_rsp_epoch_i('0),.close_rsp_task_sequence_i('0),
    .close_rsp_token_i('0),.close_rsp_status_i('0),
    .score_valid(1'b0),.score_data('0),.score_tag('0),.score_word('0),.score_source('0),
    .score_slot(1'b0),.score_ack_ready(1'b1),.probability_ready(1'b0),.probability_ack_valid(1'b0),
    .probability_ack_sequence('0),
    .dma_req_valid,.dma_req_ready,.dma_req_address,.dma_req_tag,.dma_req_channel,.dma_req_record_beats,
    .dma_rsp_valid,.dma_rsp_ready,.dma_rsp_tag,.dma_rsp_data,
    .incoming_valid,.incoming_ready,.incoming_addr(10'd512),.incoming_data({96'b0,index_asset[0]}),
    .incoming_ack,.incoming_ack_ready(1'b1),.peer_rx_reserved(1'b0),.peer_rx_addr('0),
    .outgoing_ready(1'b0),.outgoing_ack(1'b0)
  );
  wire dma_req_valid,dma_req_ready,dma_req_channel,dma_rsp_ready;
  wire [63:0] dma_req_address;
  wire [31:0] dma_req_tag;
  wire [4:0] dma_req_record_beats;
  wire dma_rsp_valid;
  wire [31:0] dma_rsp_tag;
  wire [511:0] dma_rsp_data;
  wire [11:0] req_ready,rsp_valids;
  wire [383:0] rsp_tags;
  wire [6143:0] rsp_payload;
  wire [3:0] backend_valid, backend_rsp_ready;
  wire [255:0] backend_addr,backend_tags;
  wire backend_fence,backend_fence_done_ready,dma_fault;
  wire [31:0] backend_generation;
  logic purge_done=0;
  logic [3:0] backend_rsp_valid=0;
  logic [255:0] backend_rsp_tags=0;
  logic [2047:0] backend_rsp_data=0;
  wire [3:0] backend_ready = {4{cycle%5!=2}};
  assign dma_req_ready=req_ready[3];
  assign dma_rsp_valid=rsp_valids[3];
  assign dma_rsp_tag=rsp_tags[96+:32];
  assign dma_rsp_data=rsp_payload[1536+:512];
  mc_dma_fabric_typed_p_elastic fabric (
    .clk,.reset,.p_mode_valid('0),.p_mode_native64('0),.p_mode_client_drained('1),
    .c_req_valid({8'b0,dma_req_valid,3'b0}),.c_req_ready(req_ready),
    .c_req_address({512'b0,dma_req_address,192'b0}),.c_req_tag({256'b0,dma_req_tag,96'b0}),
    .c_req_channel({8'b0,dma_req_channel,3'b0}),.c_req_record_beats({40'b0,dma_req_record_beats,15'b0}),
    .c_rsp_valid(rsp_valids),.c_rsp_ready({8'b0,dma_rsp_ready,3'b0}),
    .c_rsp_tag(rsp_tags),.c_rsp_data(rsp_payload),
    .c_close_valid('0),.c_close_tag_base('0),
    .c_cancel_valid('0),.c_cancel_tag('0),.c_cancel_ack_ready('1),
    .c_fence_valid('0),.c_fence_cookie('0),.c_fence_epoch('0),.c_fence_done_ready('1),
    .d_req_valid(backend_valid),.d_req_ready(backend_ready),
    .d_req_address(backend_addr),.d_req_tag(backend_tags),
    .d_rsp_valid(backend_rsp_valid),.d_rsp_ready(backend_rsp_ready),
    .d_rsp_tag(backend_rsp_tags),.d_rsp_data(backend_rsp_data),
    .d_fence_valid(backend_fence),.d_fence_ready(1'b1),.d_fence_generation(backend_generation),
    .d_fence_done_valid(purge_done),.d_fence_done_ready(backend_fence_done_ready),
    .d_fence_done_generation(backend_generation),.fault_valid(dma_fault),.fault_ready(1'b1)
  );
  integer backend_count=0, response_count=0;
  logic [1:0] backend_have=0;
  logic [63:0] backend_tag[2];

  always @(posedge clk) if (!reset) begin
    cycle<=cycle+1;
    assert(!dma_fault && !poison);
      if (backend_fence) purge_done<=1;
      else if (purge_done && backend_fence_done_ready) purge_done<=0;
      begin
        int n, sent, phase;
        logic [1:0] arrived;
        n=0;
        sent=0;
        arrived=backend_have;
        for (int lane=0;lane<4;lane++) begin
          if (backend_valid[lane] && backend_ready[lane]) begin
            int beat;
            beat=int'((backend_addr[64*lane+:64]-row_address)/64);
            assert (beat>=0 && beat<128 && beat/2==backend_count/2);
            assert (lane/2==int'(backend_addr[64*lane+11]));
            assert (!arrived[beat%2]);
            arrived[beat%2]=1;
            backend_tag[beat%2]<=backend_tags[64*lane+:64];
            n++;
          end
          if (backend_rsp_valid[lane] && backend_rsp_ready[lane]) begin
            backend_rsp_valid[lane]<=0;
            sent++;
          end
        end
        backend_count<=backend_count+n;
        response_count<=response_count+sent;
        if (backend_rsp_valid==0 && backend_have==2'b11 && cycle%3==1) begin
          int first_lane;
          phase=1-(response_count%2);
          first_lane=int'(backend_tag[phase][15])*2;
          backend_rsp_valid[first_lane]<=1;
          backend_rsp_tags[64*first_lane+:64]<=backend_tag[phase];
          for (int i=0;i<4;i++)
            backend_rsp_data[512*first_lane+128*i+:128]<=expected_row[8*(response_count/2)+4*phase+i];
          if (phase==0) arrived=0;
        end
        backend_have<=arrived;
      end
    if (dma_req_valid && dma_req_ready) begin
      assert(dma_req_address==row_address+64*issued && dma_req_tag==32'(issued));
      assert(dma_req_channel==dma_req_address[11] && dma_req_record_beats==2);
      issued<=issued+1;
    end
    if (dut.gather_active && dut.l_req && dut.l_ready) begin
      if (dut.l_wr) begin
        assert(dut.l_addr==10'(commits) && dut.l_data==expected_row[commits]);
      end else begin
        assert(dut.l_addr==512);
        index_reads<=index_reads+1;
      end
    end
    if (dut.gather_active && dut.l_rsp && dut.l_take && issued!=0) begin
      commits<=commits+1;
      last_commit<=cycle;
    end
    if (event_valid) begin
      assert(commits==512 && issued==128 && backend_count==128 && response_count==128 && index_reads==1);
      assert(cycle>last_commit && event_packet[0+:16]==1 && event_packet[16+:8]==2 &&
             event_packet[32+:32]==7 && event_packet[64+:32]==1 &&
             event_packet[96+:32]==1 && event_packet[144+:16]==0 &&
             event_packet[192+:32]==8208 && event_packet[224+:32]==8192);
    end
  end

  for (genvar i=0;i<4;i++) begin: verify_bank
    // Observe the actual stored words after the completion packet.
    always @(posedge clk) if (event_valid && event_take)
      for (integer j=0;j<128;j++)
        assert(dut.datapath.store.storage.banks[i].memory.mem[j]===expected_row[j*4+i]);
  end

  task automatic configure(input logic [2:0] op, input integer word_index);
    @(negedge clk);
    cfg_valid=1; cfg_op=op; cfg_addr=14'(word_index*16); cfg_data=image[word_index];
    do @(posedge clk); while(!cfg_ready);
    @(negedge clk); cfg_valid=0;
    while(!cfg_rsp) @(negedge clk);
    if(cfg_status!=0 || (op==2 && cfg_result!==image[word_index]))
      $fatal(1,"configure op %0d word %0d status %0d",op,word_index,cfg_status);
    cfg_take=1; @(negedge clk); cfg_take=0;
  endtask
  initial begin
    #200000;
    $fatal(1,"timeout life=%0d seq=%0d pc=%0d commits=%0d issued=%0d fault=%0d",life,dut.seq_o,dut.trace_pc_o,commits,issued,dma_fault);
  end
  initial begin
    assert($value$plusargs("image=%s",image_path) && $value$plusargs("row=%s",row_path)
            && $value$plusargs("index=%s",index_path));
    $readmemh(image_path,image);
    $readmemh(row_path,expected_row);
    $readmemh(index_path,index_asset);
    row_address=TABLE+64'(index_asset[0])*8192;
    repeat(5) @(negedge clk);
    reset=0;
    repeat(5) @(negedge clk);
    release_valid=1; @(negedge clk); release_valid=0;
    configure(0,0);
    for(integer i=0;i<22;i++) configure(1,i);
    for(integer i=0;i<22;i++) configure(2,i);
    configure(3,0);
    configure(4,0);
    incoming_valid=1;
    do @(posedge clk); while(!incoming_ready);
    @(negedge clk); incoming_valid=0;
    while(!incoming_ack) @(negedge clk);
    @(negedge clk); deploy=1;
    while(!task_ready) @(negedge clk);
    task_packet[0+:16]=1; task_packet[32+:32]=7; task_packet[64+:32]=1;
    task_packet[96+:32]=1; task_packet[160+:32]=image[3][96+:32]; task_packet[192+:32]=TOPOLOGY;
    task_valid=1;
    do @(posedge clk); while(!task_ready);
    @(negedge clk); task_valid=0;
    while(!event_valid) @(negedge clk);
    repeat(7) begin @(negedge clk); assert(event_valid); end
    event_take=1;
    @(negedge clk); event_take=0;
    assert(life==5 && !event_valid);
    $display("PASS generated Gather PM read_back=352 ddr_beats=%0d sram_writes=%0d last_commit=%0d",response_count,commits,last_commit);
    $finish;
  end
endmodule

