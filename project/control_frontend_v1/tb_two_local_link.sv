`timescale 1ns/1ps
module tb_two_local_link;
    reg clk_i=0, rst_ni=0;
    always #5 clk_i=~clk_i;
    reg task_valid_i=0, task_credit_i=1;
    reg [7:0] task_target_i=0;
    reg [511:0] task_packet_i=0;
    reg [1:0] local_task_ready_i=2'b11, local_return_valid_i=0;
    reg [1023:0] local_return_packet_i=0;
    reg return_ready_i=0;
    wire task_ready_o, local_task_credit_o, return_valid_o;
    wire [1:0] local_task_valid_o, local_return_ready_o;
    wire [511:0] local_task_packet_o, return_packet_o;
    integer accepted=0, returned=0;
    reg [511:0] queue[0:15];
    two_local_link dut(.*);

    always @(posedge clk_i) begin
        if (rst_ni) begin
            if (return_valid_o && return_ready_i) begin
                if (returned>=accepted || return_packet_o!==queue[returned])
                    $fatal(1,"return arbiter lost, duplicated or reordered an accepted packet");
                returned=returned+1;
            end
            if (local_return_valid_i[0] && local_return_ready_o[0]) begin
                queue[accepted]=local_return_packet_i[511:0];
                accepted=accepted+1;
            end else if (local_return_valid_i[1] && local_return_ready_o[1]) begin
                queue[accepted]=local_return_packet_i[1023:512];
                accepted=accepted+1;
            end
        end
    end
    task tick;
        @(negedge clk_i);
    endtask
    initial begin
        repeat(3) tick();
        rst_ni=1;
        task_valid_i=1;
        for (int target=0;target<3;target++) begin
            task_target_i=8'(target);
            task_packet_i=512'(target+17);
            #1;
            if (local_task_valid_o!==(target<2 ? 2'(1<<target) : 2'b0) ||
                task_ready_o!==(target<2) || local_task_packet_o!==task_packet_i || !local_task_credit_o)
                $fatal(1,"task route target=%0d",target);
            tick();
        end
        task_valid_i=0;
        // Accept LC1, then let LC0 become valid while the mother is blocked.
        local_return_packet_i={512'h11,512'h22};
        local_return_valid_i=2'b10;
        tick();
        local_return_valid_i=2'b01;
        repeat(6) begin
            #1;
            if (!return_valid_o || return_packet_o!==512'h11 || |local_return_ready_o)
                $fatal(1,"return changed while blocked by the mother");
            tick();
        end
        return_ready_i=1;
        tick();
        local_return_valid_i=0;
        tick();
        if (accepted!=2 || returned!=2) $fatal(1,"stalled returns not drained");
        // Both valid at once. The non-selected source holds its packet.
        local_return_packet_i={512'h33,512'h44};
        local_return_valid_i=2'b11;
        tick();
        local_return_valid_i=2'b10;
        tick();
        local_return_valid_i=0;
        tick();
        if (accepted!=4 || returned!=4) $fatal(1,"simultaneous returns not drained");
        return_ready_i=0;
        local_return_packet_i=1024'h55;
        local_return_valid_i=2'b01;
        tick();
        local_return_valid_i=0;
        rst_ni=0;
        #1;
        if (return_valid_o || |local_return_ready_o || |local_task_valid_o || task_ready_o)
            $fatal(1,"reset exposed an old transfer");
        repeat(3) tick();
        accepted=0; returned=0;
        rst_ni=1; return_ready_i=1;
        tick();
        if (return_valid_o) $fatal(1,"stale buffered return survived reset");
        local_return_packet_i=1024'h66;
        local_return_valid_i=2'b01;
        tick();
        local_return_valid_i=0;
        tick();
        if (accepted!=1 || returned!=1) $fatal(1,"return path did not recover");
        $display("PASS two-local task routes, held return, simultaneous returns and reset recovery");
        $finish;
    end
    initial begin #10000; $fatal(1,"router watchdog"); end
endmodule
