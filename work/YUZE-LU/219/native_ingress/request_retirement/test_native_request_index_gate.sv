`timescale 1ns/1ps
module test_native_request_index_gate;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic page_valid=0, page_ready, page_uses_index;
    logic [31:0] page_generation, page_input_token;
    logic [9:0] page_index_word=512;
    logic launch_valid, launch_ready=0, reservation_valid=0;
    logic [9:0] reservation_word=512;
    logic executor_done_valid=0, executor_done_ready, executor_done_error=0;
    logic [31:0] executor_done_generation;
    logic page_done_valid, page_done_ready=0, page_done_error, index_fault;
    logic [31:0] page_done_generation;
    logic s_valid,s_ready=0,ack_valid=0,ack_ready,ack_error=0;
    logic [9:0] s_word;
    logic [127:0] s_data;
    logic [31:0] s_tag,ack_tag;
    native_request_index_gate dut(.*);

    task automatic offer(input int generation, token, input bit index);
        page_valid=1; page_generation=generation; page_input_token=token; page_uses_index=index;
        #1;
        repeat(3) begin
            assert(launch_valid && !page_ready && !s_valid);
            @(negedge clk);
        end
        launch_ready=1;
        #1 assert(page_ready && launch_valid);
        @(negedge clk);
        launch_ready=0; page_valid=0; page_input_token='1;
    endtask

    task automatic terminal(input int generation,input bit failure);
        executor_done_generation=generation; executor_done_valid=1; page_done_ready=1;
        #1 assert(page_done_valid && page_done_generation==generation && page_done_error==failure);
        @(negedge clk); executor_done_valid=0; page_done_ready=0;
    endtask

    task automatic reserve_and_write(input int generation, token);
        reservation_valid=1;
        @(negedge clk);
        #1 assert(s_valid && s_word==512 && s_data=={32'd0,32'(token),64'd0} && s_tag==generation);
        repeat(3) begin
            assert(s_valid && !ack_ready && !page_done_valid && s_tag==generation);
            @(negedge clk);
        end
        s_ready=1;
        @(negedge clk); s_ready=0; reservation_valid=0;
        assert(!s_valid && ack_ready);
    endtask

    initial begin
        repeat(2) @(negedge clk);
        reset=0;
        offer(1,0,0);
        terminal(1,0);
        offer(2,81917,1);
        repeat(2) begin
            assert(!s_valid && !page_done_valid);
            @(negedge clk);
        end
        reserve_and_write(2,81917);
        repeat(5) begin
            assert(ack_ready && !page_done_valid);
            @(negedge clk);
        end
        ack_tag=2; ack_valid=1;
        @(negedge clk); ack_valid=0;
        terminal(2,0);
        offer(3,3758,1);
        reserve_and_write(3,3758);
        ack_tag=2; ack_valid=1; // Stale ACK terminates this request, with no downstream work.
        @(negedge clk); ack_valid=0;
        repeat(2) @(negedge clk);
        assert(index_fault && page_done_valid && page_done_error && page_done_generation==3);
        page_done_ready=1; page_valid=1; launch_ready=1;
        @(negedge clk);
        assert(!launch_valid && !page_ready && !s_valid);
        reset=1; page_valid=0; launch_ready=0; page_done_ready=0;
        @(negedge clk);
        reset=0; offer(4,21,1); terminal(4,1);
        assert(index_fault && !launch_valid);
        reset=1;
        @(negedge clk);
        reset=0; offer(5,99,1);
        terminal(4,0); // The sequencer will ignore this stale executor generation.
        reservation_valid=1; reservation_word=511;
        @(negedge clk);
        assert(index_fault && page_done_valid && page_done_error && page_done_generation==5 && !s_valid);
        $display("PASS native request Gather gate normal, delayed ACK, stale ACK, premature terminal, wrong reservation");
        $finish;
    end

    initial begin
        #10000;
        $fatal(1,"request index gate timeout");
    end
endmodule
