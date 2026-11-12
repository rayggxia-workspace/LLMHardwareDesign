`timescale 1ns/1ps
module tb_transport_quiescent;
    logic clk = 0;
    always #5 clk = ~clk;
    logic reset = 1;
    logic [11:0] c_req_valid = 0, c_req_ready;
    logic [383:0] c_req_tag = 0;
    logic [59:0] c_req_record_beats = 0;
    logic [11:0] c_rsp_valid, c_rsp_ready = 0;
    logic [383:0] c_rsp_tag;
    logic [11:0] c_close_valid = 0, c_close_ready;
    logic [383:0] c_close_tag_base = 0;
    logic [11:0] c_fence_valid = 0, c_fence_ready, c_fence_done_valid, c_fence_done_ready = 0;
    logic [383:0] c_fence_cookie = 0, c_fence_done_cookie;
    logic [107:0] c_fence_epoch = 0, c_fence_done_epoch;
    logic [11:0] c_cancel_valid = 0, c_cancel_ready;
    logic [11:0] c_cancel_ack_valid, c_cancel_ack_ready = 0;
    logic [2:0] p_mode_valid = 0, p_mode_ready;
    logic transport_quiescent;
    logic [3:0] d_req_valid, d_req_ready = 0, d_rsp_valid = 0, d_rsp_ready;
    logic [255:0] d_req_tag, d_rsp_tag = 0;
    logic d_fence_valid, d_fence_ready = 0, d_fence_done_valid = 0, d_fence_done_ready;
    logic [31:0] d_fence_generation, d_fence_done_generation = 0;
    logic fault_valid, fault_ready = 0;
    logic [7:0] fault_kind;
    logic [11:0] debug_beats, debug_descriptors;
    logic [31:0] debug_generation;

    // The backend holds ownership until a real d_rsp handshake and accepts only a matching purge.
    logic backend_pending = 0, fence_pending = 0, boot_purge_completed = 0;
    logic [31:0] accepted_fence = 0;
    always @(posedge clk) begin
        if (reset) begin
            backend_pending <= 0;
            fence_pending <= 0;
            boot_purge_completed <= 0;
            accepted_fence <= 0;
        end else begin
            if (|(d_req_valid & d_req_ready)) backend_pending <= 1;
            if (backend_pending && |(d_rsp_valid & d_rsp_ready)) backend_pending <= 0;
            if (d_fence_valid && d_fence_ready) begin
                accepted_fence <= d_fence_generation;
                fence_pending <= 1;
            end
            if (d_fence_done_valid && d_fence_done_ready &&
                fence_pending && d_fence_done_generation == accepted_fence) begin
                fence_pending <= 0;
                boot_purge_completed <= 1;
            end
        end
    end
    mc_dma_fabric_typed_p dut(
        .clk, .reset, .p_mode_valid, .p_mode_native64(3'b0), .p_mode_client_drained(3'b111), .p_mode_ready,
        .c_req_valid, .c_req_ready, .c_req_address(768'b0), .c_req_tag, .c_req_channel(12'b0), .c_req_record_beats,
        .c_rsp_valid, .c_rsp_ready, .c_rsp_tag, .c_close_valid, .c_close_ready, .c_close_tag_base,
        .c_cancel_valid, .c_cancel_ready, .c_cancel_tag(384'b0), .c_cancel_ack_valid, .c_cancel_ack_ready,
        .c_fence_valid, .c_fence_ready, .c_fence_cookie, .c_fence_epoch,
        .c_fence_done_valid, .c_fence_done_ready, .c_fence_done_cookie, .c_fence_done_epoch,
        .d_req_valid, .d_req_ready, .d_req_tag, .d_rsp_valid, .d_rsp_ready, .d_rsp_tag, .d_rsp_data(2048'b0),
        .d_fence_valid, .d_fence_ready, .d_fence_generation, .d_fence_done_valid,
        .d_fence_done_ready, .d_fence_done_generation, .fault_valid, .fault_ready, .fault_kind,
        .debug_beats, .debug_descriptors, .debug_generation, .transport_quiescent
    );

    task automatic tick;
        @(posedge clk);
        @(negedge clk);
    endtask
    task automatic check_idle(input string label, input logic expected);
        #1;
        $display("%-34s quiescent=%0b generation=%0d beats=%0d descriptors=%0d held_fault=%0b",
                 label, transport_quiescent, debug_generation, debug_beats, debug_descriptors, fault_valid);
        assert (transport_quiescent === expected) else $fatal(1, "bad drain at %s", label);
    endtask
    initial begin
        #1500;
        $fatal(1, "typed DMA drain regression timed out");
    end

    initial begin
        int lane;
        logic [63:0] read_tag;
        repeat (2) tick();
        reset = 0;
        check_idle("cold after reset before purge", 0);
        assert (dut.fence_state == 1 && debug_generation == 1);
        tick();
        check_idle("cold purge offer stalled", 0);
        assert (d_fence_valid && d_fence_generation == 2);
        d_fence_ready = 1;
        tick();
        d_fence_ready = 0;
        check_idle("cold purge accepted in wait", 0);
        assert (fence_pending && !boot_purge_completed);
        d_fence_done_valid = 1;
        d_fence_done_generation = 1;
        check_idle("wrong purge completion", 0);
        assert (dut.new_fault && d_fence_done_ready);
        tick();
        d_fence_done_valid = 0;
        check_idle("wrong purge held fault", 0);
        assert (fault_valid && fault_kind == 2 && debug_generation == 1);
        fault_ready = 1;
        tick();
        fault_ready = 0;
        d_fence_done_generation = 2;
        d_fence_done_valid = 1;
        #1;
        assert (d_fence_done_ready);
        tick();
        d_fence_done_valid = 0;
        check_idle("matched cold purge consumed", 1);
        assert (debug_generation == 2 && boot_purge_completed);

        d_rsp_valid[0] = 1;
        d_rsp_tag[63:0] = 64'h100000000;
        check_idle("same-cycle stale DDR response", 0);
        assert (dut.new_fault && d_rsp_ready[0]);
        tick();
        d_rsp_valid = 0;
        check_idle("held fault backpressure", 0);
        assert (fault_valid && fault_kind == 1);
        fault_ready = 1;
        tick();
        fault_ready = 0;
        check_idle("fault consumed", 1);

        c_req_valid[0] = 1;
        c_req_tag[31:0] = 32'h100;
        c_req_record_beats[4:0] = 5'd2;
        check_idle("same-cycle new client request", 0);
        assert (c_req_ready[0]);
        tick();
        c_req_valid = 0;
        check_idle("descriptor and beat reserved", 0);
        assert (debug_beats == 1 && debug_descriptors == 1);
        do begin
            tick();
            #1;
        end while (d_req_valid == 0);
        for (lane = 0; !d_req_valid[lane]; lane++);
        read_tag = d_req_tag[64*lane+:64];
        check_idle("registered backend offer held", 0);
        d_req_ready[lane] = 1;
        tick();
        d_req_ready = 0;
        d_rsp_valid[lane] = 1;
        d_rsp_tag[64*lane+:64] = read_tag;
        #1;
        assert (d_rsp_ready[lane]);
        tick();
        d_rsp_valid = 0;
        check_idle("client return skid held", 0);
        assert (!backend_pending && c_rsp_valid[0] && c_rsp_tag[31:0] == 32'h100);
        c_rsp_ready[0] = 1;
        tick();
        c_rsp_ready = 0;
        check_idle("beats empty descriptor open", 0);
        assert (dut.empty_transport && debug_beats == 0 && debug_descriptors == 1);
        c_close_valid[0] = 1;
        c_close_tag_base[31:0] = 32'h100;
        #1;
        assert (c_close_ready[0]);
        tick();
        c_close_valid = 0;
        tick();
        check_idle("real CLOSE returned idle", 1);
        assert (debug_descriptors == 0);

        c_fence_valid[9] = 1;
        c_fence_cookie[9*32+:32] = 32'h12345678;
        c_fence_epoch[9*9+:9] = 9'h155;
        check_idle("same-cycle new P FENCE", 0);
        assert (c_fence_ready[9] && dut.begin_fence);
        tick();
        c_fence_valid = 0;
        tick();
        check_idle("P FENCE backend offer held", 0);
        assert (d_fence_valid && d_fence_generation == 3);
        d_fence_ready = 1;
        tick();
        d_fence_ready = 0;
        d_fence_done_valid = 1;
        d_fence_done_generation = 3;
        #1;
        assert (d_fence_done_ready);
        tick();
        d_fence_done_valid = 0;
        check_idle("P FENCE held client reply", 0);
        assert (c_fence_done_valid[9] && c_fence_done_cookie[9*32+:32] == 32'h12345678 &&
                c_fence_done_epoch[9*9+:9] == 9'h155);
        c_fence_done_ready[9] = 1;
        tick();
        c_fence_done_ready = 0;
        check_idle("P FENCE client reply consumed", 1);
        assert (debug_generation == 3);

        // An unowned cancel still has a real acknowledgement to consume.
        c_cancel_valid[0] = 1;
        check_idle("same-cycle cancel offer", 0);
        assert (c_cancel_ready[0]);
        tick();
        c_cancel_valid = 0;
        check_idle("held cancel acknowledgement", 0);
        assert (c_cancel_ack_valid[0]);
        c_cancel_ack_ready[0] = 1;
        tick();
        c_cancel_ack_ready = 0;
        check_idle("cancel acknowledgement consumed", 1);

        p_mode_valid[0] = 1;
        check_idle("same-cycle mode change offer", 0);
        assert (p_mode_ready[0]);
        tick();
        p_mode_valid = 0;
        check_idle("mode change consumed", 1);
        $display("PASS typed DMA transport_quiescent");
        $finish;
    end
endmodule
