`timescale 1ns/1ps

module native_sram_replay_tb;
  reg clk = 0;
  always #5 clk = ~clk;

  reg reset = 1;
  reg req = 0;
  reg wr = 1;
  reg [9:0] addr = 0;
  reg [127:0] din = 0;
  reg take = 1;
  reg wide_req = 0;
  reg wide_take = 1;
  wire ready, valid, wide_ready, wide_valid;
  wire [127:0] dout;
  wire [511:0] wide_dout;

  block_feed_s16k_sram dut (
    .clk(clk), .reset(reset), .req(req), .wr(wr), .addr(addr), .din(din),
    .ready(ready), .valid(valid), .take(take), .dout(dout),
    .wide_req(wide_req), .wide_addr(8'd0), .wide_ready(wide_ready),
    .wide_valid(wide_valid), .wide_take(wide_take), .wide_dout(wide_dout)
  );

  integer mode, tick, n_sent, w_sent, n_done, w_done;
  integer narrow_count, wide_count, narrow_unstall, wide_unstall;
  initial begin
    if (!$value$plusargs("mode=%d", mode) || mode < 0 || mode > 7)
      $fatal(1, "expected +mode=0..7");
    narrow_count = (mode == 5 || mode == 7) ? 7 : 3;
    wide_count = 0;
    if (mode >= 1 && mode <= 3) wide_count = 3;
    if (mode == 4 || mode == 6) wide_count = 1;
    narrow_unstall = (mode == 3) ? 9 : 0;
    wide_unstall = 0;
    if (mode == 2 || mode == 3) wide_unstall = 6;
    if (mode == 6 || mode == 7) wide_unstall = 9;
    n_sent = 0;
    w_sent = 0;
    n_done = 0;
    w_done = 0;

    // Initialize a different physical bank on each write. The measured
    // writes use another row so a wide response checks all four banks.
    repeat (2) @(negedge clk);
    reset = 0;
    for (integer bank = 0; bank < 4; bank = bank + 1) begin
      req = 1;
      addr = 10'(bank);
      din = 128'(bank + 1);
      @(posedge clk);
      if (!ready) $fatal(1, "seed write stalled");
      @(negedge clk);
    end
    req = 0;
    repeat (3) @(negedge clk);

    for (tick = 0; tick < 20; tick = tick + 1) begin
      req = n_sent < narrow_count;
      wr = n_sent < 3;
      addr = wr ? 10'(16 + n_sent) : 10'(n_sent - 3);
      din = 128'(32 + n_sent);
      wide_req = w_sent < wide_count;
      take = tick >= narrow_unstall;
      wide_take = tick >= wide_unstall;
      @(posedge clk);
      if (valid && take) begin
        if (n_done >= n_sent || dout !== ((n_done < 3) ? 128'(32 + n_done) : 128'(n_done - 2)))
          $fatal(1, "unexpected narrow response at %0d", tick);
        $display("TRACE narrow %0d ack %0d", n_done, tick);
        n_done = n_done + 1;
      end
      if (wide_valid && wide_take) begin
        if (w_done >= w_sent || wide_dout !== {128'd4, 128'd3, 128'd2, 128'd1})
          $fatal(1, "unexpected wide response at %0d", tick);
        $display("TRACE wide %0d ack %0d", w_done, tick);
        w_done = w_done + 1;
      end
      if (req && ready) begin
        $display("TRACE narrow %0d issue %0d", n_sent, tick);
        n_sent = n_sent + 1;
      end
      if (wide_req && wide_ready) begin
        $display("TRACE wide %0d issue %0d", w_sent, tick);
        w_sent = w_sent + 1;
      end
      @(negedge clk);
    end
    if (n_done != narrow_count || w_done != wide_count) $fatal(1, "missing responses");
    $display("PASS mode=%0d", mode);
    $finish;
  end
endmodule
