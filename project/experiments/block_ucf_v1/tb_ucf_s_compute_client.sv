module tb_ucf_s_compute_client;
    reg clk = 0;
    always #5 clk = !clk;
    reg reset = 1, cmd_valid = 0, cmd_store = 1, done_ready = 0;
    reg [63:0] cmd_meta = 64'h1234;
    reg [1:0] cmd_sources = 3;
    reg [29:0] cmd_addresses = {10'd1023, 10'd17, 10'd5};
    reg [9:0] cmd_dst = 5;
    wire cmd_ready, done_valid, done_error, done_saturated;
    wire [127:0] done_data;
    reg s_req_ready = 0, s_rsp_valid = 0;
    reg [127:0] s_rsp_data = 0;
    wire s_req_valid, s_req_write, s_rsp_ready;
    wire [9:0] s_req_addr;
    wire [127:0] s_req_data;
    reg exec_ready = 0, result_valid = 0, result_error = 0, result_saturated = 0;
    reg [127:0] result_data = 0;
    wire exec_valid, result_ready;
    wire [63:0] exec_meta;
    wire [127:0] exec_a, exec_b, exec_c;

    ucf_s_compute_client dut (.*);

    task automatic tick;
        @(posedge clk);
        @(negedge clk);
    endtask

    task automatic start;
        if (!cmd_ready) $fatal(1, "command not ready");
        cmd_valid = 1;
        tick();
        cmd_valid = 0;
    endtask

    task automatic deliver_read(input [9:0] address, input [127:0] data);
        tick();
        if (!s_req_valid || s_req_write || s_req_addr != address)
            $fatal(1, "read did not hold address %0d", address);
        s_req_ready = 1;
        tick();
        s_req_ready = 0;
        tick();
        if (!s_rsp_ready || exec_valid) $fatal(1, "read response bypassed");
        s_rsp_data = data;
        s_rsp_valid = 1;
        tick();
        s_rsp_valid = 0;
    endtask

    task automatic deliver_result(input bit fail, input [127:0] data);
        if (!exec_valid) $fatal(1, "execute not ready");
        exec_ready = 1;
        tick();
        exec_ready = 0;
        if (!result_ready) $fatal(1, "result not accepted");
        result_valid = 1;
        result_error = fail;
        result_data = data;
        tick();
        result_valid = 0;
    endtask

    initial begin
        tick();
        reset = 0;
        #1;
        start();
        deliver_read(5, 128'd11);
        deliver_read(17, 128'd22);
        deliver_read(1023, 128'd33);
        tick();
        if (!exec_valid || exec_meta != 64'h1234 ||
            exec_a != 11 || exec_b != 22 || exec_c != 33)
            $fatal(1, "operand capture or execution hold failed");
        result_saturated = 1;
        deliver_result(0, 128'hbeef);
        tick();
        if (!s_req_valid || !s_req_write || s_req_addr != 5 ||
            s_req_data != 128'hbeef || done_valid) $fatal(1, "write not held");
        s_req_ready = 1;
        tick();
        s_req_ready = 0;
        repeat (3) begin
            if (done_valid || !s_rsp_ready) $fatal(1, "completion before stored ACK");
            tick();
        end
        s_rsp_valid = 1;
        tick();
        s_rsp_valid = 0;
        tick();
        if (!done_valid || done_error || !done_saturated || done_data != 128'hbeef)
            $fatal(1, "stored completion not held");
        done_ready = 1;
        tick();
        done_ready = 0;

        cmd_sources = 0;
        start();
        if (exec_a != 0 || exec_b != 0 || exec_c != 0) $fatal(1, "stale operand");
        deliver_result(1, 128'd123);
        if (!done_valid || !done_error || s_req_valid) $fatal(1, "error stored");
        done_ready = 1;
        tick();
        done_ready = 0;
        start();
        deliver_result(0, 128'd123);
        s_req_ready = 1;
        tick();
        s_req_ready = 0;
        reset = 1;
        tick();
        reset = 0;
        tick();
        if (!cmd_ready || done_valid || s_rsp_ready) $fatal(1, "reset leaked completion");
        $display("PASS: reads, stalls, stored ACK, error and reset");
        $finish;
    end

    initial begin
        #2000;
        $fatal(1, "watchdog timeout");
    end
endmodule
