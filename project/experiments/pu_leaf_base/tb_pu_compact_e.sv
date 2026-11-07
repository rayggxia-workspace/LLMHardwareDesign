`timescale 1ns/1ps
module tb_pu_compact_e;
    reg clk=0;
    always #5 clk=~clk;
    reg reset=1, run=0;
    reg host_req=0, host_write=0;
    reg [9:0] host_addr=0;
    reg [127:0] host_data=0;
    reg cmd_valid=0, done_ready=0;
    wire cmd_ready, done_valid, done_error, done_saturated;
    wire [127:0] done_data;
    wire s_req, s_write, s_take, ready, valid;
    wire [9:0] s_addr;
    wire [127:0] s_data, result;
    wire ei_valid, ei_ready, eo_valid, eo_ready, eo_error, eo_sat;
    wire [3:0] op;
    wire [4:0] shift;
    wire [127:0] ei_data, eo_data;
    reg allow_ack=1;
    integer writes=0, reads=0;
    reg [1:0] source_count=3;
    reg [3:0] command_op=3;
    reg [4:0] command_shift=0;
    reg [29:0] command_src={10'd2,10'd1,10'd0};
    reg store_result=1, direct_mode=0;
    wire direct_ready;
    reg golden_valid=0, golden_take=0;
    wire golden_ready, golden_done, golden_error, golden_sat;
    wire [127:0] golden_data;
    wire [127:0] a_value={8{16'd2}}, b_value={8{16'd3}}, c_value={8{16'd5}};
    block_v2_e legacy_core(
        .clk, .reset, .in_valid(golden_valid), .in_ready(golden_ready),
        .in_op(command_op), .in_shift(command_shift),
        .in_a(source_count>0 ? a_value : 128'b0),
        .in_b(source_count>1 ? b_value : 128'b0),
        .in_c(source_count>2 ? c_value : 128'b0),
        .out_valid(golden_done), .out_ready(golden_take), .out_data(golden_data),
        .out_error(golden_error), .out_saturated(golden_sat)
    );
    always @(posedge clk)
        if (run && s_req && !s_write && ready) reads <= reads+1;
    always @(posedge clk)
        if (run && s_req && s_write && ready) writes <= writes+1;

    local_s_base store(
        .clk, .reset, .req_valid(run ? s_req : host_req),
        .req_write(run ? s_write : host_write), .req_addr(run ? s_addr : host_addr),
        .req_data(run ? s_data : host_data), .req_ready(ready), .rsp_valid(valid),
        .rsp_ready(run ? s_take && allow_ack : 1'b1), .rsp_data(result)
    );
    pu_compact_e_service service(
        .clk, .reset, .cmd_valid, .cmd_store(store_result), .cmd_direct_a(direct_mode), .cmd_ready,
        .cmd_sources(source_count), .cmd_op(command_op), .cmd_shift(command_shift), .cmd_src(command_src),
        .cmd_dst(10'd3), .done_valid, .done_ready, .done_error, .done_saturated, .done_data,
        .s_req_valid(s_req), .s_req_write(s_write), .s_req_ready(ready),
        .s_req_addr(s_addr), .s_req_data(s_data), .s_rsp_valid(valid && allow_ack),
        .s_rsp_ready(s_take), .s_rsp_data(result),
        .direct_a_abort(1'b0), .direct_a_valid(direct_mode), .direct_a_ready(direct_ready), .direct_a_data(a_value),
        .e_in_valid(ei_valid), .e_in_ready(ei_ready), .e_in_op(op), .e_in_shift(shift),
        .e_in_data(ei_data), .e_out_valid(eo_valid), .e_out_ready(eo_ready),
        .e_out_data(eo_data), .e_out_error(eo_error), .e_out_saturated(eo_sat)
    );
    block_v2_e_compact arithmetic(
        .clk, .reset, .in_valid(ei_valid), .in_ready(ei_ready), .in_op(op), .in_shift(shift),
        .in_data(ei_data), .out_valid(eo_valid), .out_ready(eo_ready), .out_data(eo_data),
        .out_error(eo_error), .out_saturated(eo_sat)
    );

    task automatic host(input bit wr, input logic [9:0] addr, input logic [127:0] data);
        @(negedge clk);
        host_req=1; host_write=wr; host_addr=addr; host_data=data;
        do @(posedge clk); while (!ready);
        @(negedge clk); host_req=0;
        do @(negedge clk); while (!valid);
        if (result !== (wr ? 128'b0 : data)) $fatal(1, "unexpected SRAM response");
        @(negedge clk);
    endtask

    task automatic compare_legacy(input integer opcode, count, direct_input, shift_amount);
        integer before_reads, expected_reads;
        @(negedge clk);
        command_op=4'(opcode); source_count=2'(count); direct_mode=1'(direct_input);
        command_shift=5'(shift_amount); command_src={10'd0,10'd2,10'd1};
        store_result=0; before_reads=reads;
        expected_reads=count-((direct_input && count>0) ? 1 : 0);
        if (!cmd_ready || !golden_ready) $fatal(1,"cores not ready");
        cmd_valid=1; golden_valid=1;
        @(negedge clk); cmd_valid=0; golden_valid=0;
        do @(negedge clk); while (!done_valid || !golden_done);
        repeat (3) begin
            if (done_data !== golden_data || done_error !== golden_error ||
                done_saturated !== golden_sat || !done_valid || !golden_done)
                $fatal(1,"legacy mismatch op=%0d sources=%0d direct=%0d shift=%0d got=%h expected=%h",
                    opcode,count,direct_input,shift_amount,done_data,golden_data);
            @(negedge clk);
        end
        if (reads-before_reads != expected_reads)
            $fatal(1,"wrong S reads op=%0d sources=%0d direct=%0d got=%0d expected=%0d",
                opcode,count,direct_input,reads-before_reads,expected_reads);
        if (opcode==3 && count==2 && shift_amount==0 && done_data !== {8{16'd6}})
            $fatal(1,"two-operand FMA read the absent C at S[0]");
        done_ready=1; golden_take=1;
        @(negedge clk); done_ready=0; golden_take=0;
    endtask

    initial begin
        repeat (2) @(negedge clk);
        reset=0;
        host(1, 0, {8{16'd2}});
        host(1, 1, {8{16'd3}});
        host(1, 2, {8{16'd4}});
        run=1; cmd_valid=1;
        do @(posedge clk); while (!cmd_ready);
        @(negedge clk); cmd_valid=0;
        wait(writes==1);
        @(negedge clk); allow_ack=0;
        repeat (5) begin
            @(negedge clk);
            if (done_valid) $fatal(1, "completion preceded SRAM response");
        end
        if (!valid) $fatal(1, "test failed to hold write acknowledgement");
        allow_ack=1;
        do @(negedge clk); while (!done_valid);
        repeat (3) begin
            if (!done_valid || done_error || done_saturated || done_data !== {8{16'd10}})
                $fatal(1, "wrong result under completion backpressure");
            @(negedge clk);
        end
        done_ready=1;
        @(negedge clk); run=0;
        host(0, 3, {8{16'd10}});
        // Poison the default third address. Legal two-source FMA must be 6, never 11.
        host(1, 0, c_value); host(1, 1, a_value); host(1, 2, b_value);
        run=1; done_ready=0;
        compare_legacy(3,2,0,0);
        for (integer d=0; d<2; d=d+1)
            for (integer sh=0; sh<2; sh=sh+1)
                for (integer o=0; o<16; o=o+1)
                    for (integer n=0; n<4; n=n+1)
                        compare_legacy(o,n,d,sh*3);
        $display("PASS U compact E 257 legacy-core comparisons, exact descriptor S read counts, direct A, ACK and completion backpressure");
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1, "timeout");
    end
endmodule
