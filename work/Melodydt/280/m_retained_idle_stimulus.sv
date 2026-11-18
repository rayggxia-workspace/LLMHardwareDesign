localparam logic [127:0] ScopeKey = 128'h9ac1_7574_1306_427a_67a5_653c_aca1_4ec8;
localparam logic [127:0] ScopeOwner = 128'h73a5_2fe8_f672_7e14_5f66_97b5_8e62_168f;
localparam logic [255:0] ScopeBias = 256'h0102_0304_0506_0708_090a_0b0c_0d0e_0f10_ffe1_fd22_04d2_fffe_0080_0037_00fe_018b;
logic acknowledged = 0;

task automatic send_scope_word(input logic [127:0] word, input int index);
    lc_data = word;
    lc_valid = 1;
    lc_sop = index == 0;
    lc_eop = index == 7;
    do @(posedge clk); while (!lc_ready);
    @(negedge clk);
endtask

always @(posedge clk) begin
    if ($time >= 1000 && !reset) begin
        if (lc_valid || lr_valid || a_valid || mc_req_valid || mc_rsp_valid ||
            mc_close_valid || mc_fence_req_valid || mc_fence_done_valid || fault_interrupt)
            $fatal(1, "traffic during the retained-scope idle window");
        if (!dut.scope_valid[1] || dut.scope_key[1] !== ScopeKey ||
            dut.scope_owner[1] !== ScopeOwner || dut.scope_bias[1] !== ScopeBias)
            $fatal(1, "scope payload did not remain resident");
    end
    if (!reset && lr_valid && lr_ready && lr_sop) begin
        if (lr_data[39:32] != 8'd10 || lr_data[47:40] != 0 || lr_data[79:48] != 32'd1)
            $fatal(1, "expected successful BEGIN_SCOPE acknowledgment: %h", lr_data);
        acknowledged <= 1;
    end
    if ($time > 82930)
        $fatal(1, "retained-scope capture timed out");
end

initial begin
    $dumpfile("idle.vcd");
    $dumpvars(1, dut);
    repeat (5) @(negedge clk);
    reset = 0;
    // Generation 1, session 1, scope handle 1, eight beats and BEGIN_SCOPE opcode.
    send_scope_word(128'h0000_0001_0000_0000_0000_0001_0181_4d02, 0);
    send_scope_word(ScopeKey, 1);
    send_scope_word(ScopeOwner, 2);
    send_scope_word(128'h0001_0080, 3);
    send_scope_word(128'd0, 4);
    send_scope_word(ScopeBias[127:0], 5);
    send_scope_word(ScopeBias[255:128], 6);
    send_scope_word(128'h0000_0000_0000_0000_4b31_3633_5333_3251, 7);
    lc_valid = 0;
    lc_sop = 0;
    lc_eop = 0;
    lc_data = 0;
    repeat (8279) @(negedge clk);
    if (!acknowledged)
        $fatal(1, "BEGIN_SCOPE acknowledgment missing");
    $display("PASS old M retained scope with no traffic during the power window");
    $finish;
end
