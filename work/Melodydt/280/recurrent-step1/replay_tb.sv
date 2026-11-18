`timescale 1ns/1ps
module replay_tb;
    reg clk=0, reset=1, cmd_valid=0;
    always #2.5 clk=~clk;
    reg [3:0] cmd_op;
    reg [9:0] cmd_index;
    reg [127:0] cmd_data;
    wire cmd_ready, rsp_valid, rsp_error, busy;
    wire [127:0] rsp_data;
    block_v1_r dut(.rsp_ready(1'b1), .*);
    integer fd, rc, count=0, cycles=0, commands, execs=0;
    integer op, idx;
    reg [127:0] din, expected;
    string path;
    always @(posedge clk) cycles<=cycles+1;
    initial begin
        if (!$value$plusargs("vectors=%s",path) || !$value$plusargs("count=%d",commands))
            $fatal(1,"missing vector arguments");
        fd=$fopen(path,"r");
        if (!fd) $fatal(1,"cannot open vectors");
        repeat (2) @(negedge clk);
        reset=0;
        #0.001;
        while (count<commands) begin
            rc=$fscanf(fd,"%d %d %h %h",op,idx,din,expected);
            if (rc!=4 || cmd_ready!==1) $fatal(1,"invalid input at command %0d",count);
            cmd_op=op; cmd_index=idx; cmd_data=din; cmd_valid=1;
            @(negedge clk);
            cmd_valid=0;
            while (rsp_valid!==1) @(negedge clk);
            if (rsp_error!==0 || rsp_data!==expected)
                $fatal(1,"command %0d op %0d idx %0d err %b got %h expected %h",count,op,idx,rsp_error,rsp_data,expected);
            if (op==6) execs=execs+1;
            count=count+1;
        end
        $display("RTL_REPLAY_PASS commands=%0d execs=%0d cycles=%0d",count,execs,cycles);
        $finish;
    end
    initial begin
        #20000000;
        $fatal(1,"timeout at command %0d",count);
    end
endmodule
