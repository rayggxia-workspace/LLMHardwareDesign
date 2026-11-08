`timescale 1ns/1ps
module test_compact_s;
    reg clk = 0;
    always #10 clk = !clk;

    reg reset = 1;
    reg req_valid = 0, req_write = 0, rsp_ready = 0;
    reg [9:0] req_addr = 0;
    reg [127:0] req_data = 0;
    wire req_ready, rsp_valid;
    wire [127:0] rsp_data;

    reg load_valid = 0, done_take = 0, a_ready = 0, b_ready = 0;
    wire load_ready, done_valid, done_error, a_valid, b_valid;
    wire [127:0] a_data;
    wire [511:0] b_data;
    wire base_req_ready, base_rsp_valid;
    wire [127:0] base_rsp_data;
    reg base_enable = 1;

    local_s_base base (
        .clk, .reset, .req_valid(req_valid && base_enable), .req_write,
        .req_addr, .req_data, .req_ready(base_req_ready), .rsp_ready,
        .rsp_valid(base_rsp_valid), .rsp_data(base_rsp_data)
    );
    local_s_p p (
        .clk, .reset, .req_valid, .req_write, .req_addr, .req_data,
        .req_ready, .rsp_ready, .rsp_valid, .rsp_data,
        .load_valid, .load_ready, .load_bank(1'b0), .load_rows(4'd1), .load_tiles(3'd1),
        .load_a_wide(1'b0), .load_b_wide(1'b0), .load_reuse_b(1'b0),
        .load_a_base(10'd0), .load_b_base(10'd0), .done_valid, .done_take, .done_error,
        .a_valid, .a_ready, .a_bank(), .a_row(), .a_tile(), .a_wide(), .a_data,
        .b_valid, .b_ready, .b_bank(), .b_tile(), .b_wide(), .b_half(), .b_data
    );

    task automatic issue(input bit wr, input logic [9:0] addr, input logic [127:0] data);
        @(negedge clk);
        req_valid = 1;
        req_write = wr;
        req_addr = addr;
        req_data = data;
        @(posedge clk);
        if (!(req_ready && base_req_ready)) $fatal(1, "ordinary request blocked");
        @(negedge clk);
        req_valid = 0;
    endtask

    task automatic wait_response(input logic [127:0] expected);
        do @(negedge clk); while (!rsp_valid || !base_rsp_valid);
        repeat (3) begin
            if (!rsp_valid || !base_rsp_valid || rsp_data !== expected || base_rsp_data !== expected)
                $fatal(1, "ordinary response not preserved while stalled");
            @(negedge clk);
        end
    endtask

    task automatic retire;
        rsp_ready = 1;
        @(negedge clk);
        rsp_ready = 0;
    endtask

    initial begin
        repeat (2) @(negedge clk);
        reset = 0;
        for (int i = 0; i < 4; i++) begin
            issue(1, 10'(i), 128'(i + 10));
            wait_response(0);
            retire();
        end
        issue(0, 10'd3, 0);
        wait_response(128'd13);
        load_valid = 1;
        repeat (2) begin
            @(negedge clk);
            if (load_ready) $fatal(1, "load bypassed a stalled response");
        end
        retire();
        do @(posedge clk); while (!load_ready);
        @(negedge clk);
        load_valid = 0;
        base_enable = 0;
        req_valid = 1;
        do @(negedge clk); while (!a_valid || !b_valid);
        repeat (3) begin
            if (req_ready || !a_valid || !b_valid ||
                a_data !== 128'd10 || b_data !== {128'd13,128'd12,128'd11,128'd10})
                $fatal(1, "feeder data, ordering, or phase exclusion");
            @(negedge clk);
        end
        a_ready = 1;
        b_ready = 1;
        do @(negedge clk); while (!done_valid);
        if (req_ready || load_ready || done_error) $fatal(1, "stalled done released phase");
        req_valid = 0;
        done_take = 1;
        @(negedge clk);
        done_take = 0;
        if (!req_ready || done_valid) $fatal(1, "ordinary phase did not reopen");
        $display("PASS compact S bank data, ACK, backpressure, feeder and phase isolation");
        $finish;
    end

    initial begin
        #5000;
        $fatal(1, "test timeout");
    end
endmodule
