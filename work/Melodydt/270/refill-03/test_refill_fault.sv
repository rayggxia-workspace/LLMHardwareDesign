`timescale 1ns/1ps
module test_refill_fault;
    localparam int BURSTS = 40;
    localparam int BAD_BEAT = 17;
    logic clk, reset = 1, launch_valid = 0;
    initial clk = 0;
    always #5 clk = ~clk;
    logic launch_ready, done_valid, done_error, rd_valid, rd_rsp_ready;
    logic s_valid, s_rsp_ready;
    logic [63:0] rd_address, rd_rsp_tag;
    logic [9:0] s_address;
    logic [127:0] s_data;
    logic [31:0] s_tag, s_rsp_tag;
    int mode, issued, returned, offers, acks, cycle;
    int expected_slot, expected_lane;
    logic [31:0] s_history[2*BURSTS];
    wire rd_ready = cycle % 3 != 0;
    wire rd_rsp_valid = issued > returned && cycle % 5 != 0;
    wire s_ready = cycle % 4 != 0;
    wire s_rsp_valid = offers > acks && cycle % 7 == 0;
    function automatic logic [127:0] word_at(input int slot, lane);
        int unsigned value;
        value = slot * 4 + lane + 1;
        return {96'd0, value};
    endfunction
    wire [511:0] payload = {word_at(returned, 3), word_at(returned, 2),
                           word_at(returned, 1), word_at(returned, 0)};
    assign rd_rsp_tag = 64'(returned) ^ (mode == 1 && returned == BAD_BEAT ? 64'h100 : 64'd0);
    assign s_rsp_tag = s_history[acks] ^ (mode == 2 && acks == 15 ? 32'h1 : 32'd0);
    s128_ddr_response_load #(.OVERLAP(1'b1)) dut(
        .clk,.reset,.launch_valid,.launch_ready,.launch_base(64'h4000),
        .launch_s_base(10'd64),.launch_bursts(8'(BURSTS)),.launch_pair(1'b1),.launch_pair_high(1'b1),
        .done_valid,.done_error,.done_ready(1'b1),.rd_valid,.rd_ready,.rd_address,
        .rd_rsp_valid,.rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data(payload),.s_valid,.s_ready,
        .s_address,.s_data,.s_tag,.s_rsp_valid,.s_rsp_ready,.s_rsp_tag);

    always @(posedge clk) if (!reset) begin
        cycle <= cycle + 1;
        if (rd_valid && rd_ready) begin
            assert(rd_address == 64'h4000 + 64'(issued) * 512);
            issued <= issued + 1;
        end
        if (rd_rsp_valid && rd_rsp_ready) returned <= returned + 1;
        if (s_valid && s_ready) begin
            assert(s_address == 10'(64 + 2*expected_slot + expected_lane));
            assert(s_data == word_at(expected_slot, 2 + expected_lane));
            assert(s_tag == {22'h12a000,s_address});
            s_history[offers] <= s_tag;
            offers <= offers + 1;
            expected_lane <= 1 - expected_lane;
            if (expected_lane == 1)
                expected_slot <= expected_slot + (mode == 1 && expected_slot == BAD_BEAT-1 ? 2 : 1);
        end
        if (s_rsp_valid && s_rsp_ready) acks <= acks + 1;
        if (done_valid) begin
            assert(done_error == (mode != 0));
            assert(issued == BURSTS && returned == BURSTS && offers == acks);
            assert(acks == 2*(BURSTS - (mode == 1 ? 1 : 0)));
            $display("PASS refill fault=%0d DDR=%0d SRAM=%0d cycles=%0d", mode, returned, acks, cycle);
            $finish;
        end
    end

    initial begin
        assert($value$plusargs("MODE=%d", mode));
        repeat (3) @(negedge clk);
        reset = 0;
        @(negedge clk);
        assert(launch_ready);
        launch_valid = 1;
        @(negedge clk);
        launch_valid = 0;
    end

    initial begin
        #500000;
        $fatal(1, "refill did not drain");
    end
endmodule

