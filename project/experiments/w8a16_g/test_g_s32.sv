`timescale 1ns/1ps
module test_g_s32;
    reg clk = 0;
    always #5 clk = !clk;
    reg reset = 1;
    reg in_valid = 0, out_ready = 0;
    wire in_ready, out_valid, out_error;
    reg [63:0] in_gate = 0, in_up = 0;
    reg in_gated = 0;
    reg [1:0] in_mask = 0;
    wire [63:0] out_data;
    wire [1:0] out_mask;
    g_s32 dut(.*);

    reg [63:0] gates[0:8191], ups[0:8191], expected[0:8191];
    reg gated[0:8191], errors[0:8191];
    reg [1:0] masks[0:8191];
    integer accepted_cycle[0:8191];
    integer count, fd, scan, bit_gated, bit_error;
    integer sent = 0, received = 0, cycle = 0, mode = 0, last_received = -1;
    integer reset_left = 0;
    integer first_input = -1, first_output = -1, frame_last_input = -1;
    reg injected_reset = 0, input_stalled = 0, held = 0;
    reg [63:0] held_data;
    reg [1:0] held_mask;
    reg held_error;
    string vector_file;

    initial begin
        if (!$value$plusargs("vectors=%s", vector_file)) $fatal(1, "vectors argument missing");
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        fd = $fopen(vector_file, "r");
        if (fd == 0) $fatal(1, "cannot open vectors");
        scan = $fscanf(fd, "%d\n", count);
        if (scan != 1 || count < 1 || count > 8192) $fatal(1, "invalid vector count");
        for (integer i = 0; i < count; i = i + 1) begin
            scan = $fscanf(fd, "%h %h %d %h %h %d\n", gates[i], ups[i], bit_gated, masks[i], expected[i], bit_error);
            if (scan != 6) $fatal(1, "invalid vector row %0d", i);
            gated[i] = (bit_gated != 0);
            errors[i] = (bit_error != 0);
        end
        $fclose(fd);
        repeat (4) @(negedge clk);
        reset = 0;
        while (received < count) begin
            @(negedge clk);
            if (cycle > 200000) $fatal(1, "progress watchdog: sent=%0d received=%0d", sent, received);
            if (mode == 2 && cycle >= 80 && !injected_reset) begin
                injected_reset = 1;
                reset_left = 3;
                reset = 1;
            end else if (reset_left > 0) begin
                reset_left = reset_left - 1;
                if (reset_left == 0) reset = 0;
            end
            if (reset) begin
                in_valid = 0;
                out_ready = 0;
            end else begin
                out_ready = mode == 0 || cycle % 13 >= 5;
                if (!input_stalled) begin
                    in_valid = sent < count && (mode == 0 || cycle % 7 != 0);
                    if (sent < count) begin
                        in_gate = gates[sent];
                        in_up = ups[sent];
                        in_gated = gated[sent];
                        in_mask = masks[sent];
                    end
                end
            end
        end
        @(negedge clk);
        in_valid = 0;
        out_ready = 1;
        repeat (8) @(negedge clk);
        if (out_valid) $fatal(1, "spurious output after complete drain");
        $display("G_S32_PASS mode=%0d packets=%0d reset_injected=%0d latency_stream=4 II_stream=1", mode, received, injected_reset);
        $finish;
    end

    always @(posedge clk) begin
        cycle = cycle + 1;
        if (reset) begin
            if (out_valid || in_ready) $fatal(1, "reset must block handshakes");
            sent = 0;
            received = 0;
            input_stalled = 0;
            held = 0;
            last_received = -1;
            first_input = -1;
            first_output = -1;
            frame_last_input = -1;
        end else begin
            if (held && (!out_valid || out_data !== held_data || out_mask !== held_mask || out_error !== held_error))
                $fatal(1, "output changed under backpressure");
            held = out_valid && !out_ready;
            held_data = out_data;
            held_mask = out_mask;
            held_error = out_error;
            input_stalled = in_valid && !in_ready;
            if (in_valid && in_ready) begin
                if (sent == 0) first_input = cycle;
                if (sent == 63) frame_last_input = cycle;
                accepted_cycle[sent] = cycle;
                sent = sent + 1;
            end
            if (out_valid && out_ready) begin
                if (received == 0) first_output = cycle;
                if (received >= sent || received >= count) $fatal(1, "spurious result");
                if (out_data !== expected[received] || out_mask !== masks[received] || out_error !== errors[received])
                    $fatal(1, "packet %0d got=%h/%h/%b expected=%h/%h/%b", received, out_data, out_mask, out_error, expected[received], masks[received], errors[received]);
                if (mode == 0) begin
                    if (cycle - accepted_cycle[received] != 4) $fatal(1, "stream latency differs from four stages");
                    if (last_received >= 0 && cycle - last_received != 1) $fatal(1, "stream II differs from one");
                    if (received == 63) begin
                        if (cycle-first_input+1 != 68) $fatal(1, "128-value frame occupied cycles differ from 68");
                        $display("G_FRAME_128 first_input=%0d last_input=%0d first_output=%0d last_output=%0d occupied_cycles=%0d", first_input, frame_last_input, first_output, cycle, cycle-first_input+1);
                    end
                end
                last_received = cycle;
                received = received + 1;
            end
        end
    end
endmodule
