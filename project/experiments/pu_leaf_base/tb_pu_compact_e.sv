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
    integer writes=0;
    always @(posedge clk)
        if (run && s_req && s_write && ready) writes <= writes+1;

    local_s_base store(
        .clk, .reset, .req_valid(run ? s_req : host_req),
        .req_write(run ? s_write : host_write), .req_addr(run ? s_addr : host_addr),
        .req_data(run ? s_data : host_data), .req_ready(ready), .rsp_valid(valid),
        .rsp_ready(run ? s_take && allow_ack : 1'b1), .rsp_data(result)
    );
    pu_compact_e_service service(
        .clk, .reset, .cmd_valid, .cmd_store(1'b1), .cmd_direct_a(1'b0), .cmd_ready,
        .cmd_op(4'd3), .cmd_shift(5'd0), .cmd_src({10'd2,10'd1,10'd0}),
        .cmd_dst(10'd3), .done_valid, .done_ready, .done_error, .done_saturated, .done_data,
        .s_req_valid(s_req), .s_req_write(s_write), .s_req_ready(ready),
        .s_req_addr(s_addr), .s_req_data(s_data), .s_rsp_valid(valid && allow_ack),
        .s_rsp_ready(s_take), .s_rsp_data(result),
        .direct_a_abort(1'b0), .direct_a_valid(1'b0), .direct_a_ready(), .direct_a_data(128'b0),
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
        $display("PASS U compact E three operand beats and native S write acknowledgement");
        $finish;
    end
    initial begin
        #10000;
        $fatal(1, "timeout");
    end
endmodule
