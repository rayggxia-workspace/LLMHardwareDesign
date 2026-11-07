module tb_control_pm;
    parameter bit USE_SRAM=1;
    reg clk_i=0;always #5 clk_i=~clk_i;
    reg rst_ni=0,req_valid_i=0,req_write_i=0,rsp_ready_i=0;
    reg [13:0] req_address_i=0;
    reg [127:0] req_data_i=0;
    wire req_ready_o,rsp_valid_o,rsp_error_o;
    wire [127:0] rsp_data_o;
    control_pm #(.BYTES(8320),.USE_SRAM(USE_SRAM)) dut(.*);
    task automatic tick;@(negedge clk_i);endtask
    task automatic transaction(input bit wr,input [13:0] address,input [127:0] value,input bit error);
        req_valid_i=1;req_write_i=wr;req_address_i=address;req_data_i=value;
        do @(posedge clk_i);while(!req_ready_o);
        tick();req_valid_i=0;
        while(!rsp_valid_o)tick();
        if(rsp_error_o!==error || (!wr && !error && rsp_data_o!==value))$fatal(1,"PM mismatch backend=%0d address=%0d",USE_SRAM,address);
        repeat(4)begin tick();if(!rsp_valid_o || req_ready_o || rsp_error_o!==error || (!wr && !error && rsp_data_o!==value))$fatal(1,"PM response not held");end
        rsp_ready_i=1;tick();rsp_ready_i=0;tick();
    endtask
    initial begin
        repeat(4)tick();rst_ni=1;tick();
        transaction(1,0,128'h0123456789abcdef_fedcba9876543210,0);
        transaction(1,16,128'hfedcba98_76543210,0);
        transaction(1,8304,128'hbadcafe,0);
        transaction(0,0,128'h0123456789abcdef_fedcba9876543210,0);
        transaction(0,16,128'hfedcba98_76543210,0);
        transaction(0,8304,128'hbadcafe,0);
        transaction(1,1,128'hdead,1);transaction(1,8320,128'hdead,1);
        transaction(0,1,0,1);transaction(0,8320,0,1);
        transaction(0,0,128'h0123456789abcdef_fedcba9876543210,0);
        req_valid_i=1;req_write_i=0;req_address_i=16;
        do @(posedge clk_i);while(!req_ready_o);
        tick();req_valid_i=0;rst_ni=0;repeat(4)tick();
        if(rsp_valid_o || req_ready_o)$fatal(1,"PM reset protocol");
        rst_ni=1;repeat(4)tick();
        if(rsp_valid_o)$fatal(1,"PM stale response");
        transaction(0,16,128'hfedcba98_76543210,0);
        $display("PASS control-pm backend=%0d classes=6",USE_SRAM);$finish;
    end
    initial begin #100000;$fatal(1,"PM watchdog");end
endmodule
