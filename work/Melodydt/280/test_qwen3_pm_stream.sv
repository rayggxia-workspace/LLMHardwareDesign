`timescale 1ns/1ps
module test_qwen3_pm_stream;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic launch_valid=0, launch_ready;
    logic [47:0] launch_base=48'h100000000;
    logic [15:0] launch_image_bytes;
    logic [31:0] launch_ticket=32'd7;
    logic rd_valid, rd_ready, rd_rsp_valid=0, rd_rsp_ready;
    logic [47:0] rd_address;
    logic [63:0] rd_tag, rd_rsp_tag;
    logic [511:0] rd_rsp_data;
    logic rd_rsp_error=0;
    logic pm_valid, pm_ready, pm_ack_valid=0, pm_ack_ready;
    logic [13:0] pm_address;
    logic [127:0] pm_data;
    logic pm_ack_error=0;
    logic done_valid, done_ready=0, done_error;
    logic [31:0] done_ticket;
    logic [15:0] done_ddr_bytes, done_pm_bytes;
    logic [511:0] image [256];
    int cycles=0, requests=0, writes=0, bytes=0, mode=0, acks=0;
    int idle=0, hold_cycles=0;
    string image_file, wave_file;
    native_pm_image_stream dut(.*);
    assign rd_ready=mode==0 || cycles%5==0;
    assign pm_ready=mode==0 || cycles%7==0;

    always @(posedge clk) if (!reset) begin
        cycles <= cycles+1;
        if (rd_rsp_valid && rd_rsp_ready) rd_rsp_valid <= 0;
        if (rd_valid && rd_ready) begin
            if (rd_address != launch_base+48'(64*requests)) $fatal(1,"DDR address mismatch");
            rd_rsp_valid <= 1;
            rd_rsp_tag <= rd_tag;
            rd_rsp_data <= image[requests];
            requests <= requests+1;
        end
        if (pm_ack_valid && pm_ack_ready) begin
            pm_ack_valid <= 0;
            acks <= acks+1;
        end
        if (pm_valid && pm_ready) begin
            if (int'(pm_address)!=16*writes || pm_data!==image[writes/4][128*(writes%4)+:128])
                $fatal(1,"PM lane mapping mismatch");
            pm_ack_valid <= 1;
            writes <= writes+1;
        end
    end

    initial begin
        if (!$value$plusargs("BYTES=%d",bytes) || !$value$plusargs("IMAGE=%s",image_file) ||
            !$value$plusargs("WAVE=%s",wave_file)) $fatal(1,"missing PM arguments");
        void'($value$plusargs("MODE=%d",mode));
        void'($value$plusargs("IDLE=%d",idle));
        void'($value$plusargs("HOLD=%d",hold_cycles));
        launch_image_bytes=16'(bytes);
        $readmemh(image_file,image);
        $dumpfile(wave_file);
        $dumpvars(1,dut);
        repeat(5) @(negedge clk);
        reset=0;
        if (idle==0) begin
            @(negedge clk); launch_valid=1;
            do @(posedge clk); while(!launch_ready);
            @(negedge clk); launch_valid=0;
            do @(negedge clk); while(!done_valid);
            if (done_error || done_ticket!=launch_ticket || int'(done_pm_bytes)!=bytes ||
                int'(done_ddr_bytes)!=64*requests || requests!=(bytes+63)/64 ||
                writes!=bytes/16 || acks!=writes) $fatal(1,"PM extent or acknowledgement mismatch");
            done_ready=1;
        end
        $display("PASS PM bytes=%0d DDR512=%0d PM128=%0d acks=%0d cycles=%0d mode=%0d",
                 bytes,requests,writes,acks,cycles,mode);
        if (hold_cycles>0) begin
            if (hold_cycles<=cycles) $fatal(1,"fixed window too short");
            wait(cycles==hold_cycles);
            @(negedge clk);
        end
        if (idle!=0 && (requests!=0 || writes!=0 || acks!=0)) $fatal(1,"nonempty idle window");
        $finish;
    end
    initial #500000 $fatal(1,"PM timeout");
endmodule
