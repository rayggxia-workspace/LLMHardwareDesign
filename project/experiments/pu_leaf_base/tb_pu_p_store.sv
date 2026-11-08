`timescale 1ns/1ps
module tb_pu_p_store;
    reg clk=0;
    always #5 clk=~clk;
    reg reset=1, req=0, take=0, load=0, load_take=0;
    wire ready, valid, mreq, mwrite, mtake, mready, mvalid;
    wire [9:0] maddr;
    wire [127:0] mdata, mrdata, result;
    wire lready, lvalid, sready, sdone, serr, stake, done, err;
    wire av, bv;
    wire [127:0] adata;
    wire [511:0] bdata;
    reg feeder_take=0;
    pu_p_store_control #(.CLIENTS(1)) control(
        .clk, .reset, .req_valid(req), .req_write(1'b1), .req_addr(10'd0),
        .req_data(128'd9), .req_ready(ready), .rsp_valid(valid), .rsp_ready(take), .rsp_data(result),
        .mem_req(mreq), .mem_write(mwrite), .mem_addr(maddr), .mem_data(mdata),
        .mem_ready(mready), .mem_valid(mvalid), .mem_result(mrdata), .mem_take(mtake),
        .load_valid(load), .load_ready(lready), .store_load_valid(lvalid), .store_load_ready(sready),
        .store_done_valid(sdone), .store_done_error(serr), .store_done_take(stake),
        .load_done_valid(done), .load_done_error(err), .load_done_take(load_take)
    );
    local_s_p store(
        .clk, .reset, .req_valid(mreq), .req_write(mwrite), .req_addr(maddr),
        .req_data(mdata), .req_ready(mready), .rsp_valid(mvalid), .rsp_ready(mtake), .rsp_data(mrdata),
        .load_valid(lvalid), .load_ready(sready), .load_bank(1'b0), .load_rows(4'd1), .load_tiles(3'd1),
        .load_a_wide(1'b0), .load_b_wide(1'b0), .load_reuse_b(1'b0),
        .load_a_base(10'd0), .load_b_base(10'd0), .done_valid(sdone), .done_error(serr), .done_take(stake),
        .a_valid(av), .a_ready(feeder_take), .a_bank(), .a_row(), .a_tile(), .a_wide(), .a_data(adata),
        .b_valid(bv), .b_ready(feeder_take), .b_bank(), .b_tile(), .b_wide(), .b_half(), .b_data(bdata)
    );
    initial begin
        repeat (2) @(negedge clk);
        reset=0; req=1;
        do @(posedge clk); while (!ready);
        @(negedge clk); load=1;
        do @(negedge clk); while (!valid);
        repeat (3) begin
            if (ready || lready || lvalid || result !== 0)
                $fatal(1, "feeder crossed pending write response");
            @(negedge clk);
        end
        take=1;
        do @(posedge clk); while (!lready);
        @(negedge clk); load=0; take=0;
        do @(negedge clk); while (!av || !bv);
        if (adata !== 128'd9 || bdata[127:0] !== 128'd9)
            $fatal(1, "feeder read did not observe retired write");
        feeder_take=1;
        do @(negedge clk); while (!done);
        repeat (3) begin
            if (ready || err || !done) $fatal(1, "phase reopened before completion consumption");
            @(negedge clk);
        end
        load_take=1;
        @(negedge clk);
        if (!ready || done) $fatal(1, "ordinary admission failed to reopen");
        $display("PASS P native S write retirement and feeder phase exclusion");
        $finish;
    end
    initial begin
        #10000;
        $fatal(1, "timeout");
    end
endmodule
