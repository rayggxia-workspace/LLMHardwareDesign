`timescale 1ns/1ps
module test_s128_vocabulary_retire;
  localparam integer VOCAB=151936, WORDS=VOCAB/4, TILE_WORDS=32;
  localparam logic [9:0] WINDOW=896;
  reg clk=0;
  always #5 clk=!clk;
  reg reset=1;
  reg job_valid=0,tile_valid=0,tile_release_ready=0,token_ready=0;
  wire job_ready,tile_ready,tile_release_valid,token_valid,token_error;
  reg [31:0] tile_first=0, tile_tag=10;
  wire [31:0] tile_release_first,token_id,token_tag;
  wire signed [31:0] token_logit;
  wire s_read_valid,s_read_ready,s_rsp_ready;
  wire [9:0] s_read_address;
  wire [31:0] s_read_tag;
  reg [31:0] read_owner=0;
  reg corrupt_response=0,write_valid=0,write_ack_ready=0;
  reg [9:0] write_address=0;
  reg [127:0] write_data=0;
  reg [127:0] logits[WORDS];
  wire mem_ready,mem_valid;
  wire [127:0] mem_data;
  wire memory_request=write_valid||s_read_valid;
  wire memory_response_ready=write_ack_ready||s_rsp_ready;
  assign s_read_ready=mem_ready&&!write_valid;

  s128_vocabulary_retire dut (
    .clk,.reset,.job_valid,.job_ready,.job_length(32'(VOCAB)),.job_tag(32'd10),
    .tile_valid,.tile_ready,.tile_first,.tile_tag,.tile_count(8'd128),.tile_s_base(WINDOW),
    .tile_release_valid,.tile_release_ready,.tile_release_first,
    .s_read_valid,.s_read_ready,.s_read_address,.s_read_tag,
    .s_rsp_valid(mem_valid),.s_rsp_ready,.s_rsp_tag(read_owner^{31'd0,corrupt_response}),
    .s_rsp_data(mem_data),.s_rsp_error(1'b0),
    .token_valid,.token_ready,.token_id,.token_tag,.token_logit,.token_error
  );
  local_s_base storage (
    .clk,.reset,.req_valid(memory_request),.req_write(write_valid),
    .req_addr(write_valid?write_address:s_read_address),.req_data(write_data),.req_ready(mem_ready),
    .rsp_valid(mem_valid),.rsp_ready(memory_response_ready),.rsp_data(mem_data)
  );
  integer reads=0,writes=0;
  always @(posedge clk) if (!reset) begin
    if (write_valid&&s_read_valid) $fatal(1,"consumer overlapped producer overwrite");
    if (memory_request&&mem_ready&&write_valid) writes<=writes+1;
    if (s_read_valid&&s_read_ready) begin
      read_owner<=s_read_tag;
      reads<=reads+1;
    end
  end

  task automatic send_tile(input integer first);
    tile_first=first;
    tile_valid=1;
    do @(posedge clk); while (!tile_ready);
    @(negedge clk);
    tile_valid=0;
  endtask

  task automatic write_word(input integer address_offset,input logic [127:0] data);
    write_address=WINDOW+10'(address_offset);
    write_data=data;
    write_valid=1;
    do @(posedge clk); while (!mem_ready);
    @(negedge clk);
    write_valid=0;
    write_ack_ready=1;
    do @(posedge clk); while (!mem_valid);
    @(negedge clk);
    write_ack_ready=0;
  endtask

  task automatic begin_job;
    job_valid=1;
    do @(posedge clk); while (!job_ready);
    @(negedge clk);
    job_valid=0;
  endtask

  initial begin
    $readmemh("vocab.hex", logits);
    repeat(3) @(negedge clk);
    reset=0;
    begin_job();
    for(integer first=0;first<VOCAB;first+=128) begin
      for(integer word=0;word<TILE_WORDS;word++)
        write_word(word,logits[first/4+word]);
      send_tile(first);
      do @(negedge clk); while (!tile_release_valid);
      repeat(3) begin
        if (!tile_release_valid || tile_release_first!=32'(first) || tile_ready || token_valid)
          $fatal(1,"tile ownership lost under backpressure");
        @(negedge clk);
      end
      tile_release_ready=1;
      @(negedge clk);
      tile_release_ready=0;
    end
    repeat(3) begin
      if (!token_valid || token_error || token_id!=81917 || token_tag!=10 || token_logit!=1630078)
        $fatal(1,"wrong retirement for checkpoint logits");
      @(negedge clk);
    end
    if (reads!=WORDS || writes!=WORDS) $fatal(1,"incomplete actual SRAM traversal");
    token_ready=1;
    @(negedge clk);
    token_ready=0;
    begin_job();
    write_word(0,logits[0]);
    corrupt_response=1;
    send_tile(0);
    do @(negedge clk); while (!token_valid);
    if (!token_error || tile_release_valid) $fatal(1,"wrong SRAM owner released tile");
    token_ready=1;
    @(negedge clk);
    if (token_valid || job_ready || tile_release_valid) $fatal(1,"fault repeated or admitted work");
    $display("PASS 1187 leased tiles, 37984 real SRAM reads/writes, token81917, mismatched read tag fenced");
    $finish;
  end

  initial begin
    #10000000;
    $fatal(1,"vocabulary retirement timeout");
  end
endmodule
