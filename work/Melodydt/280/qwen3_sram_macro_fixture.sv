`timescale 1ns/1ps
module qwen3_sram_macro_fixture;
    localparam int WINDOW_CYCLES = 512;
    logic clk = 0;
    always #5 clk = ~clk;

    logic reset = 1, req_valid = 0, req_write = 0, rsp_ready = 1;
    logic [9:0] req_addr = 0;
    logic [127:0] req_data = 0;
    wire req_ready, rsp_valid;
    wire [127:0] rsp_data;
`ifdef SRAM_BASE
    local_s_base dut (.clk, .reset, .req_valid, .req_write, .rsp_ready,
                      .req_addr, .req_data, .req_ready, .rsp_valid, .rsp_data);
`else
    logic load_valid = 0;
    logic [9:0] load_base = 0;
    wire load_ready, done_valid, done_error, a_valid, b_valid;
    wire [127:0] a_data;
    wire [511:0] b_data;
    local_s_p dut (.clk, .reset, .req_valid, .req_write, .rsp_ready,
                   .req_addr, .req_data, .req_ready, .rsp_valid, .rsp_data,
                   .load_valid, .load_ready, .load_bank(1'b0), .load_rows(4'd1), .load_tiles(3'd1),
                   .load_a_wide(1'b0), .load_b_wide(1'b0), .load_reuse_b(1'b0),
                   .load_a_base(load_base), .load_b_base(load_base),
                   .done_valid, .done_error, .done_take(1'b1),
                   .a_valid, .a_ready(1'b1), .a_bank(), .a_row(), .a_tile(), .a_wide(), .a_data,
                   .b_valid, .b_ready(1'b1), .b_bank(), .b_tile(), .b_wide(), .b_half(), .b_data);
`endif

    wire [3:0] bank_enabled, bank_writing;
    wire [31:0] all_addresses;
    // Spell the escaped identifiers as they appear in the archived routed netlists.
    assign bank_enabled[0] = ~dut.\storage.banks[0].memory .csb0;
    assign bank_enabled[1] = ~dut.\storage.banks[1].memory .csb0;
    assign bank_enabled[2] = ~dut.\storage.banks[2].memory .csb0;
    assign bank_enabled[3] = ~dut.\storage.banks[3].memory .csb0;
    assign bank_writing[0] = ~dut.\storage.banks[0].memory .web0;
    assign bank_writing[1] = ~dut.\storage.banks[1].memory .web0;
    assign bank_writing[2] = ~dut.\storage.banks[2].memory .web0;
    assign bank_writing[3] = ~dut.\storage.banks[3].memory .web0;
    assign all_addresses[7:0] = dut.\storage.banks[0].memory .addr0;
    assign all_addresses[15:8] = dut.\storage.banks[1].memory .addr0;
    assign all_addresses[23:16] = dut.\storage.banks[2].memory .addr0;
    assign all_addresses[31:24] = dut.\storage.banks[3].memory .addr0;

    int cycles = 0, read128 = 0, write128 = 0, wide512 = 0;
    logic armed = 0;
    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (armed) begin
            if (req_valid && req_ready) begin
                if (bank_enabled !== (4'b0001 << req_addr[1:0]) ||
                    (bank_writing & bank_enabled) !== (req_write ? bank_enabled : 4'b0) ||
                    all_addresses[8*int'(req_addr[1:0])+:8] !== req_addr[9:2])
                    $fatal(1, "ordinary request mismatch: mask, direction or address");
                if (req_write) write128 <= write128 + 1;
                else read128 <= read128 + 1;
            end else if (bank_enabled != 0) begin
                if (bank_enabled !== 4'b1111 || bank_writing !== 4'b0 ||
                    all_addresses !== {4{all_addresses[7:0]}})
                    $fatal(1, "feeder request is not a same-address four-bank read");
                wide512 <= wide512 + 1;
            end
        end
    end

    function automatic logic [127:0] payload(input int address);
        // Distinct deterministic words with nontrivial bit toggling.
        return {32'h12879abc ^ (32'(address)*32'h80390565), 32'h236ba419 ^ (32'(address)*32'h954f01d7),
                32'h3458ace2 ^ (32'(address)*32'h451636ed), 32'hba629afc ^ (32'(address)*32'h69ba8221)};
    endfunction

    task automatic ordinary(input bit write_enable, input int address, input logic [127:0] data);
        req_valid = 1;
        req_write = write_enable;
        req_addr = 10'(address);
        req_data = data;
        do @(posedge clk); while (!req_ready);
        @(negedge clk);
        req_valid = 0;
        while (!rsp_valid) @(negedge clk);
        if (rsp_data !== (write_enable ? 128'd0 : data))
            $fatal(1, "ordinary response mismatch at address %0d", address);
        @(negedge clk);
    endtask

`ifndef SRAM_BASE
    task automatic feeder(input int row);
        logic saw_a, saw_b;
        int address;
        saw_a = 0;
        saw_b = 0;
        address = 4*row;
        load_base = 10'(address);
        load_valid = 1;
        do @(posedge clk); while (!load_ready);
        @(negedge clk);
        load_valid = 0;
        while (!done_valid) begin
            if (a_valid) begin
                if (saw_a || a_data !== payload(address)) $fatal(1, "feeder A data mismatch");
                saw_a = 1;
            end
            if (b_valid) begin
                if (saw_b || b_data !== {payload(address+3), payload(address+2),
                                          payload(address+1), payload(address)})
                    $fatal(1, "feeder B data mismatch");
                saw_b = 1;
            end
            @(negedge clk);
        end
        if (done_error || !saw_a || !saw_b) $fatal(1, "feeder completion mismatch");
        @(negedge clk);
    endtask
`endif

    string mode, trace_path;
    int start_cycle, final_cycle, groups;
    initial begin
        if (!$value$plusargs("CASE=%s", mode) || !$value$plusargs("VCD=%s", trace_path))
            $fatal(1, "expected CASE and VCD arguments");
        $dumpfile(trace_path);
        $dumpvars(0, dut);
        repeat (8) @(negedge clk);
        reset = 0;
        for (int address = 0; address < 64; address++) ordinary(1, address, payload(address));
        // Common quiescent controller and preloaded memory before sampling.
        req_write = 0;
        req_addr = 0;
        req_data = 0;
        repeat (8) @(negedge clk);
        start_cycle = cycles;
        final_cycle = start_cycle + WINDOW_CYCLES;
        armed = 1;
        case (mode)
            "idle": groups = 0;
            "read128": begin
                groups = 64;
                for (int address = 0; address < groups; address++) ordinary(0, address, payload(address));
            end
            "write128", "write256", "write512": begin
                int lanes;
                groups = 16;
                lanes = mode == "write512" ? 4 : (mode == "write256" ? 2 : 1);
                for (int row = 0; row < groups; row++) begin
                    for (int bank = 0; bank < lanes; bank++) begin
                        int address;
                        address = 4*row + bank;
                        ordinary(1, address, ~payload(address));
                    end
                end
            end
`ifndef SRAM_BASE
            "read512": begin
                groups = 16;
                for (int row = 0; row < groups; row++) feeder(row);
            end
`endif
            default: $fatal(1, "unsupported case %s", mode);
        endcase
        if (cycles > final_cycle-4) $fatal(1, "active replay exceeds fixed sampling window");
        // Compare equal wall windows, including the ready/idle tail in active cases.
        repeat (final_cycle - cycles) @(negedge clk);
        armed = 0;
        $display("WINDOW %0d %0d", start_cycle*10000, final_cycle*10000);
        $display("PASS SRAM %s %0d %0d %0d %0d", mode, groups, read128, write128, wide512);
        // Validate write readback after the measured window, outside armed timestamps.
        if (write128 != 0) begin
            int lanes;
            lanes = write128 / groups;
            for (int row = 0; row < groups; row++)
                for (int bank = 0; bank < lanes; bank++)
                    ordinary(0, 4*row+bank, ~payload(4*row+bank));
        end
        $finish;
    end
    initial #20000 $fatal(1, "SRAM transaction timeout");
endmodule
