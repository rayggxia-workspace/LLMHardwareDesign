`timescale 1ns/1ps
module test_feeder_trace;
    reg clk = 0;
    always #10 clk = !clk;
    reg reset = 1, req_valid = 0, req_write = 0, rsp_ready = 0;
    reg [9:0] req_addr = 0;
    reg [127:0] req_data = 0;
    wire req_ready, rsp_valid;
    wire [127:0] rsp_data;
    reg load_valid = 0;
    wire load_ready, done_valid, done_error, a_valid, b_valid;
    wire [127:0] a_data;
    wire [511:0] b_data;
    wire [2:0] a_row;
    wire [1:0] a_tile;
    integer cycle = 0, a_count = 0, wide_count = 0;
    local_s_p dut(.clk, .reset, .req_valid, .req_write, .req_addr, .req_data,
        .req_ready, .rsp_ready, .rsp_valid, .rsp_data,
        .load_valid, .load_ready, .load_bank(1'b0), .load_rows(4'd8), .load_tiles(3'd4),
        .load_a_wide(1'b1), .load_b_wide(1'b0), .load_reuse_b(1'b1),
        .load_a_base(10'd0), .load_b_base(10'd0), .done_valid, .done_take(1'b0), .done_error,
        .a_valid, .a_ready(1'b1), .a_bank(), .a_row, .a_tile, .a_wide(), .a_data,
        .b_valid, .b_ready(1'b1), .b_bank(), .b_tile(), .b_wide(), .b_half(), .b_data);

    task automatic write_word(input integer address);
        @(negedge clk);
        req_valid = 1;
        req_write = 1;
        req_addr = 10'(address);
        req_data = {4{32'(address+1)}};
        do @(posedge clk); while (!req_ready);
        @(negedge clk);
        req_valid = 0;
        while (!rsp_valid) @(negedge clk);
        if (rsp_data !== 128'd0) $fatal(1, "write response must contain zero");
        rsp_ready = 1;
        @(negedge clk);
        rsp_ready = 0;
    endtask

    initial begin
        repeat (4) @(negedge clk);
        reset = 0;
        for (integer i = 0; i < 32; i = i+1) write_word(i);
        @(negedge clk);
        load_valid = 1;
        do @(posedge clk); while (!load_ready);
        @(negedge clk);
        load_valid = 0;
        while (!done_valid) begin
            @(negedge clk);
            if (cycle > 1000) $fatal(1, "feeder progress watchdog");
        end
        if (done_error || a_count != 32 || wide_count != 8) $fatal(1, "unexpected feeder completion");
        $display("FEEDER_TRACE_PASS A_beats=%0d A_bytes_per_beat=16 wide_reads=%0d", a_count, wide_count);
        $finish;
    end
    always @(posedge clk) begin
        cycle = cycle+1;
        if (!reset) begin
            if (dut.wide_req && dut.wide_ready) begin
                $display("WIDE_REQ,%0d,%0d", cycle, dut.wide_addr);
                wide_count = wide_count+1;
            end
            if (a_valid) begin
                if (a_data !== {4{32'(8*int'(a_tile)+int'(a_row)+1)}}) $fatal(1, "feeder address/word order mismatch");
                $display("A_BEAT,%0d,%0d,%0d", cycle, a_tile, a_row);
                a_count = a_count+1;
            end
            if (b_valid) $fatal(1, "reuse_B trace must not produce B data");
        end
    end
endmodule
