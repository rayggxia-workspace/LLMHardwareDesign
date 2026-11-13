module tb_native_host_program_switch;
    localparam integer TARGETS = 10, REQUEST_BITS = 322, RESPONSE_BITS = 176;
    reg clk = 0;
    always #5 clk = ~clk;
    reg reset = 1, allow_request = 0, host_req_valid = 0, host_rsp_ready = 0;
    reg [3:0] host_req_target = 0;
    reg [REQUEST_BITS-1:0] host_req_payload = '0;
    reg [TARGETS-1:0] target_req_ready = '0, target_rsp_valid = '0;
    reg [TARGETS*RESPONSE_BITS-1:0] target_rsp_payload = '0;
    wire host_req_ready, host_rsp_valid, host_rsp_bad_target, idle;
    wire [3:0] host_rsp_target;
    wire [REQUEST_BITS-1:0] target_req_payload;
    wire [RESPONSE_BITS-1:0] host_rsp_payload;
    wire [TARGETS-1:0] target_req_valid, target_rsp_ready;

    native_host_program_switch dut (.*);

    task automatic tick;
        @(posedge clk);
        #1;
    endtask

    task automatic require(input bit condition, input string message);
        if (!condition) $fatal(1, "%s", message);
    endtask

    initial begin
        reg [TARGETS-1:0] bit_mask;
        reg [RESPONSE_BITS-1:0] expected_payload;
        tick();
        require(idle && !host_req_ready && !host_rsp_valid, "reset gates requests and responses");
        reset = 0;
        host_req_valid = 1;
        host_req_payload = {1'b1, 320'h8c005511abcd0123456789, 1'b1};
        #1;
        require(target_req_valid == '0 && !host_req_ready, "admission closed");
        for (int target_index = 0; target_index < TARGETS; target_index++) begin
            bit_mask = 10'b1 << target_index;
            host_req_target = 4'(target_index);
            host_req_valid = 1;
            allow_request = 1;
            target_req_ready = ~bit_mask;
            #1;
            require(target_req_valid == bit_mask && !host_req_ready &&
                target_req_payload == host_req_payload, "only requested target sees payload under backpressure");
            tick();
            require(idle && !host_rsp_valid, "blocked request does not reserve owner");
            target_req_ready = '1;
            #1;
            require(host_req_ready, "selected target can accept");
            tick();
            allow_request = 0;
            host_req_target = 4'((target_index + 1) % TARGETS);
            target_rsp_valid = ~bit_mask;
            #1;
            require(!idle && !host_req_ready && !host_rsp_valid && target_req_valid == '0,
                "unselected responses and second request cannot be observed");
            expected_payload = {8'(~target_index), 160'h0102030405060708090a0b0c0d0e0f1020304050, 8'(target_index)};
            target_rsp_payload[target_index*RESPONSE_BITS+:RESPONSE_BITS] = expected_payload;
            target_rsp_valid = '1;
            tick();
            require(host_rsp_valid && !host_rsp_bad_target && host_rsp_target == 4'(target_index) &&
                host_rsp_payload == expected_payload && target_rsp_ready == '0,
                "selected response is held even after admission closes");
            host_rsp_ready = 1;
            #1;
            require(target_rsp_ready == bit_mask, "only selected target may retire");
            tick();
            require(idle && !host_rsp_valid && !host_req_ready, "response releases owner");
            host_rsp_ready = 0;
            target_rsp_valid = '0;
        end

        allow_request = 1;
        host_req_target = 4'd15;
        host_req_valid = 1;
        #1;
        require(host_req_ready && target_req_valid == '0, "invalid target is rejected locally");
        tick();
        require(host_rsp_valid && host_rsp_bad_target && host_rsp_target == 4'd15 &&
            host_rsp_payload == '0 && target_rsp_ready == '0, "invalid target response payload");
        reset = 1;
        tick();
        require(idle && !host_rsp_valid && !host_req_ready && target_rsp_ready == '0,
            "reset clears outstanding local response");
        $display("PASS host program switch ten owners, request and response backpressure, drain gating, invalid target, reset");
        $finish;
    end
endmodule
