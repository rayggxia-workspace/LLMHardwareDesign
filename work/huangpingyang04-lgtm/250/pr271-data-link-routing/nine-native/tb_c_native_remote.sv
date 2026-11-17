module tb_c_native_remote;
    logic clk=0, reset=1;
    always #5 clk=!clk;
    logic cmd_valid=0, cmd_ready, done_valid, done_ready=0;
    logic [63:0] cmd_meta;
    logic [1:0] cmd_sources;
    logic [29:0] cmd_addresses={10'd8,10'd7,10'd999};
    logic cmd_store=0;
    logic [9:0] cmd_dst=0;
    logic [127:0] done_data;
    logic done_error, done_saturated;
    logic s_req_valid, s_req_ready=1, s_req_write, s_rsp_valid=0, s_rsp_ready;
    logic [9:0] s_req_addr;
    logic [127:0] s_req_data, s_rsp_data;
    logic exec_valid, exec_ready;
    logic [63:0] exec_meta;
    logic [127:0] exec_a, exec_b, exec_c;
    logic result_valid, result_ready, result_error, result_saturated;
    logic [127:0] result_data;
    logic remote_valid, remote_ready=0, remote_rsp_valid=0, remote_rsp_ready;
    logic [9:0] remote_address;
    logic [31:0] remote_tag, remote_rsp_tag=0;
    logic [127:0] remote_rsp_data=0;
    ucf_s_compute_client #(.REMOTE_A(1)) client (.*);
    cfj_e32_port aperture (
        .clk, .reset, .request(exec_valid), .ready(exec_ready), .meta(exec_meta[18:0]),
        .a(exec_a), .b(exec_b), .c(exec_c), .response(result_valid), .take(result_ready),
        .data(result_data), .error(result_error), .saturated(result_saturated)
    );
    int requests=0;
    int remote_requests=0;
    logic remote_mode;
    always @(posedge clk) begin
        if (!reset) begin
            if(remote_valid && remote_ready) remote_requests <= remote_requests+1;
            if (s_req_valid && s_req_ready) begin
                if (s_req_write || (remote_mode && s_req_addr==999))
                    $fatal(1,"remote A traveled through C SRAM");
                s_rsp_valid <= 1;
                s_rsp_data <= s_req_addr==7 ? {4{32'd20}} :
                              s_req_addr==8 ? {4{32'd5}} : {32'd9,32'd7,-32'd2,32'd3};
                requests <= requests+1;
            end else if (s_rsp_valid && s_rsp_ready) s_rsp_valid <= 0;
        end
    end
    task automatic run(input logic rem, input logic [3:0] op, input logic [1:0] arity,
                        input logic [127:0] expected);
        int before_count, before_remote;
        logic [31:0] expected_tag;
        @(negedge clk);
        before_count=requests; before_remote=remote_requests; remote_mode=rem;
        cmd_valid=1; cmd_sources=arity;
        cmd_meta=(64'd1<<62)|(64'(rem)<<61)|{56'd0,4'hf,op};
        @(negedge clk);
        cmd_valid=0;
        if(rem) begin
            wait(remote_valid);
            expected_tag=remote_tag;
            repeat(4) begin
                @(negedge clk);
                if(!remote_valid || remote_address!=999 || remote_tag!=expected_tag || s_req_valid)
                    $fatal(1,"unstable or duplicated remote request");
            end
            remote_ready=1;
            @(negedge clk); remote_ready=0;
            wait(remote_rsp_ready);
            // A stale response must not execute or advance the A read.
            remote_rsp_tag=expected_tag+1; remote_rsp_data='1; remote_rsp_valid=1;
            @(negedge clk); remote_rsp_valid=0;
            repeat(3) @(negedge clk);
            if(exec_valid || done_valid || s_req_valid) $fatal(1,"accepted stale tag");
            remote_rsp_tag=expected_tag;
            remote_rsp_data={32'd9,32'd7,-32'd2,32'd3}; remote_rsp_valid=1;
            @(negedge clk); remote_rsp_valid=0; remote_rsp_data='1;
        end
        wait(done_valid);
        repeat(3) begin
            @(negedge clk);
            if(!done_valid || done_data!==expected) $fatal(1,"unstable result under backpressure");
        end
        if(done_error || done_saturated || requests-before_count!=int'(arity)-int'(rem) ||
           remote_requests-before_remote!=int'(rem)) $fatal(1,"read accounting mismatch");
        done_ready=1;
        @(negedge clk); done_ready=0;
    endtask
    initial begin
        repeat(3) @(negedge clk); reset=0;
        run(1,0,2,{32'd29,32'd27,32'd18,32'd23});
        run(1,1,3,{32'd34,32'd32,32'd23,32'd28});
        run(1,2,2,{32'd180,32'd140,-32'd40,32'd60});
        run(0,0,2,{32'd29,32'd27,32'd18,32'd23});
        $display("PASS: C native remote A -> real E32 ADD2/ADD3/PRODUCT; local fallback; stalls and stale tag rejection");
        $finish;
    end
    initial begin repeat(1600) @(posedge clk); $fatal(1,"timeout"); end
endmodule
