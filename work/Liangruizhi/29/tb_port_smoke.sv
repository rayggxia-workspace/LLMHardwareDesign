`timescale 1ns/1ps
module tb_port_smoke;
    parameter integer MODE = 0;
    parameter integer DEPTH = 2;
    logic clk = 0, rst = 1;
    logic [2:0] req_valid = 0, req_ready, req_bank = 0, req_write = 0;
    logic [29:0] req_addr = 0;
    logic [1535:0] req_wdata = 0;
    logic [191:0] req_wstrb = 0;
    logic [95:0] req_tag = 0;
    logic [2:0] rsp_valid, rsp_ready = 0, rsp_write;
    logic [1535:0] rsp_data;
    logic [95:0] rsp_tag;
    integer counts [0:2];
    integer req_sequence [0:2];
    integer wait_cycles [0:2];
    integer max_wait_cycles [0:2];
    logic [2:0] accepted;
    logic [511:0] expected;

    initial begin
        #1000000;
        $fatal(1, "smoke simulation watchdog expired");
    end

    bank_port_fabric #(.PORT_MODE(MODE), .RESP_DEPTH(DEPTH), .LINK_MASK(6'b011111)) dut (.*);

    function automatic logic [511:0] pattern(input logic [31:0] value);
        pattern = {16{value}};
    endfunction

    task automatic tick;
        #5 clk = 1;
        #1 clk = 0;
        #4;
    endtask

    task automatic set_req(input integer ep, input logic bank, input logic wr,
                           input logic [9:0] address, input logic [511:0] data,
                           input logic [63:0] strb, input logic [31:0] tag);
        req_valid[ep] = 1;
        req_bank[ep] = bank;
        req_write[ep] = wr;
        req_addr[ep*10 +: 10] = address;
        req_wdata[ep*512 +: 512] = data;
        req_wstrb[ep*64 +: 64] = strb;
        req_tag[ep*32 +: 32] = tag;
    endtask

    task automatic issue(input integer ep, input logic bank, input logic wr,
                         input logic [9:0] address, input logic [511:0] data,
                         input logic [63:0] strb, input logic [31:0] tag);
        integer waits;
        set_req(ep, bank, wr, address, data, strb, tag);
        #1;
        waits = 0;
        while (!req_ready[ep] && waits < 100) begin
            tick;
            #1;
            waits = waits + 1;
        end
        if (!req_ready[ep]) $fatal(1, "issue timeout");
        tick;
        req_valid[ep] = 0;
        #1;
    endtask

    task automatic check_rsp(input integer ep, input logic wr, input logic [31:0] tag,
                             input logic [511:0] data);
        if (!rsp_valid[ep] || rsp_write[ep] !== wr || rsp_tag[ep*32 +: 32] !== tag ||
            rsp_data[ep*512 +: 512] !== data)
            $fatal(1, "unexpected response ep=%0d wanted tag=%0d", ep, tag);
    endtask

    initial begin
        tick;
        if (req_ready != 0 || rsp_valid != 0) $fatal(1, "reset handshake");
        rst = 0;
        // Fill the finite write-ack FIFO without consuming any response.
        for (int i = 1; i <= DEPTH; i = i + 1)
            issue(0, 0, 1, 10'(6+i), pattern(32'(i)), '1, 32'(i));
        check_rsp(0, 1, 1, '0);
        set_req(0, 0, 1, 10'(7+DEPTH), pattern(32'(DEPTH+1)), '1, 32'(DEPTH+1));
        #1;
        repeat (2) begin
            if (req_ready[0]) $fatal(1, "accepted into full response FIFO");
            check_rsp(0, 1, 1, '0);
            tick;
        end
        // Full + pop permits a simultaneous push (including DEPTH=1).
        rsp_ready[0] = 1;
        #1;
        if (!req_ready[0]) $fatal(1, "missing full pop+push credit");
        check_rsp(0, 1, 1, '0);
        tick;
        req_valid[0] = 0;
        #1;
        for (int i = 2; i <= DEPTH+1; i = i + 1) begin
            check_rsp(0, 1, 32'(i), '0);
            tick;
        end
        if (rsp_valid[0]) $fatal(1, "response FIFO did not drain");
        // Initialize the second row explicitly before fairness/read tests.
        issue(0, 0, 1, 8, pattern(8), '1, 20);
        check_rsp(0, 1, 20, '0);
        tick;

        // Read is registered, and a stalled read response blocks write data.
        rsp_ready[0] = 0;
        set_req(0, 0, 0, 7, '0, '0, 100);
        #1;
        if (rsp_valid[0]) $fatal(1, "zero-cycle read bypass");
        if (!req_ready[0]) $fatal(1, "read should be eligible");
        tick;
        req_valid[0] = 0;
        #1;
        check_rsp(0, 0, 100, pattern(1));
        set_req(0, 0, 1, 20, pattern(20), '1, 101);
        #1;
        repeat (2) begin
            if (req_ready[0]) $fatal(1, "write data overlaps stalled read response");
            check_rsp(0, 0, 100, pattern(1));
            tick;
        end
        rsp_ready[0] = 1;
        #1;
        if (req_ready[0]) $fatal(1, "write must be blocked even on read response pop edge");
        tick;
        #1;
        if (!req_ready[0]) $fatal(1, "write did not resume after read response");
        tick;
        req_valid[0] = 0;
        #1;
        check_rsp(0, 1, 101, '0);
        tick;

        // Read control can overlap a valid read response and same-edge pop.
        issue(0, 0, 0, 7, '0, '0, 200);
        check_rsp(0, 0, 200, pattern(1));
        set_req(0, 0, 0, 7, '0, '0, 201);
        #1;
        if (!req_ready[0]) $fatal(1, "read control incorrectly blocked by read response");
        tick;
        req_valid[0] = 0;
        #1;
        check_rsp(0, 0, 201, pattern(1));
        tick;

        // Same bank+row R/R is serialized, even with two read-capable ports.
        rsp_ready = '1;
        set_req(0, 0, 0, 7, '0, '0, 300);
        set_req(1, 0, 0, 7, '0, '0, 301);
        #1;
        if ((req_ready & 3'b011) == 0 || (req_ready & 3'b011) == 3'b011)
            $fatal(1, "same-row R/R was not serialized");
        accepted = req_ready & req_valid;
        tick;
        req_valid = req_valid & ~accepted;
        #1;
        if ((req_ready & req_valid) == 0) $fatal(1, "same-row loser did not resume");
        accepted = req_ready & req_valid;
        tick;
        req_valid = req_valid & ~accepted;
        tick;
        tick;

        // Persistent R0/R1/W2 tests the first-winner RR update: all three
        // continuously eligible endpoints must receive service.
        for (int ep = 0; ep < 3; ep = ep + 1) begin
            counts[ep] = 0;
            req_sequence[ep] = 400 + ep*100;
            wait_cycles[ep] = 0;
            max_wait_cycles[ep] = 0;
            set_req(ep, 0, ep == 2, (ep == 2) ? 10'd20 : 10'(7+ep),
                    pattern(32'(req_sequence[ep])), '1, 32'(req_sequence[ep]));
        end
        for (int cycle = 0; cycle < 12; cycle = cycle + 1) begin
            #1;
            accepted = req_ready & req_valid;
            tick;
            for (int ep = 0; ep < 3; ep = ep + 1) begin
                if (accepted[ep]) begin
                    counts[ep] = counts[ep] + 1;
                    wait_cycles[ep] = 0;
                    req_sequence[ep] = req_sequence[ep] + 1;
                    req_tag[ep*32 +: 32] = 32'(req_sequence[ep]);
                    req_wdata[ep*512 +: 512] = pattern(32'(req_sequence[ep]));
                end else begin
                    wait_cycles[ep] = wait_cycles[ep] + 1;
                    if (wait_cycles[ep] > max_wait_cycles[ep])
                        max_wait_cycles[ep] = wait_cycles[ep];
                end
            end
        end
        for (int ep = 0; ep < 3; ep = ep + 1)
            if (counts[ep] == 0 || max_wait_cycles[ep] > 2)
                $fatal(1, "persistent endpoint service bound failed ep=%0d", ep);
        // Stop producing only after each outstanding request is accepted.
        while (req_valid != 0) begin
            #1;
            accepted = req_ready & req_valid;
            tick;
            req_valid = req_valid & ~accepted;
        end
        tick;
        tick;

        // Different banks can grant the same row index at the same edge.
        set_req(0, 0, 1, 30, pattern(30), '1, 700);
        set_req(1, 1, 1, 30, pattern(31), '1, 701);
        #1;
        if ((req_ready & 3'b011) != 3'b011) $fatal(1, "independent banks serialized");
        tick;
        req_valid = 0;
        tick;

        // Byte strobe and no-op write, then reset without clearing SRAM.
        issue(0, 0, 1, 7, 512'haa, 64'd1, 800);
        tick;
        issue(0, 0, 1, 7, '1, '0, 801);
        tick;
        rst = 1;
        req_valid = 0;
        tick;
        rst = 0;
        expected = pattern(1);
        expected[7:0] = 8'haa;
        issue(0, 0, 0, 7, '0, '0, 802);
        check_rsp(0, 0, 802, expected);
        tick;

        // The disabled D->bank1 link must never handshake.
        set_req(2, 1, 1, 40, pattern(40), '1, 900);
        #1;
        repeat (3) begin
            if (req_ready[2]) $fatal(1, "masked link was accepted");
            tick;
        end
        rst = 1; // reset explicitly aborts this permanently blocked request
        req_valid = 0;
        tick;
        $display("PORT_SMOKE_PASS MODE=%0d DEPTH=%0d RR_GRANTS=%0d,%0d,%0d", MODE, DEPTH,
                 counts[0], counts[1], counts[2]);
        $display("MAX_UNGRANTED_CYCLES=%0d,%0d,%0d", max_wait_cycles[0],
                 max_wait_cycles[1], max_wait_cycles[2]);
        $finish;
    end
endmodule
