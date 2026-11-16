`timescale 1ns/1ps
module test_qwen3_lc_pm;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic lc_idle=1, transport_drained=1;
    logic cfg_valid=0, cfg_ready, cfg_rsp_valid, cfg_rsp_ready=1;
    logic [1:0] cfg_op;
    logic [31:0] cfg_generation=1, cfg_abi=32'h02500002, cfg_capacity=32'h02510001;
    logic [31:0] cfg_crc, cfg_actual_crc, generation;
    logic [15:0] cfg_bytes=352, image_bytes;
    logic [13:0] cfg_address;
    logic [127:0] cfg_data;
    logic [7:0] cfg_status;
    logic certified, boot_busy, pm_valid=0, pm_ready, pm_rsp_valid, pm_rsp_ready=1, pm_error;
    logic [13:0] pm_address;
    logic [127:0] pm_data, image[22];
    integer mode=0, cycles=0, writes=0, reads=0;
    string input_path, wave_path;
    lc_program_store_1k dut(.*);

    always @(posedge clk) if(!reset) cycles<=cycles+1;

    task automatic cfg(input logic [1:0] op, input int index);
        cfg_op=op;
        cfg_address=14'(16*index);
        cfg_data=image[index];
        cfg_valid=1;
        do @(posedge clk); while(!cfg_ready);
        @(negedge clk); cfg_valid=0;
        while(!cfg_rsp_valid) @(negedge clk);
        if(cfg_status!=0) $fatal(1,"PM config status %d",cfg_status);
        @(negedge clk);
    endtask

    initial begin
        if(!$value$plusargs("IMAGE=%s",input_path) || !$value$plusargs("WAVE=%s",wave_path) ||
           !$value$plusargs("CRC=%h",cfg_crc)) $fatal(1,"missing PM arguments");
        void'($value$plusargs("MODE=%d",mode));
        $readmemh(input_path,image);
        $dumpfile(wave_path); $dumpvars(1,dut);
        repeat(5) @(negedge clk); reset=0;
        @(negedge clk);
        if(mode<2) begin
            cfg(0,0);
            for(int i=0;i<22;i++) begin cfg(1,i); writes++; end
            cfg(2,0);
            if(!certified || image_bytes!=16'd352 || cfg_actual_crc!=cfg_crc || generation!=1)
                $fatal(1,"PM certification failed");
        end
        wait(cycles==600); @(negedge clk);
        if(mode==0) begin
            for(int i=0;i<22;i++) begin
                pm_address=14'(16*i); pm_valid=1;
                do @(posedge clk); while(!pm_ready);
                @(negedge clk); pm_valid=0;
                while(!pm_rsp_valid) @(negedge clk);
                if(pm_error || pm_data!==image[i]) $fatal(1,"LC PM word %d mismatch",i);
                reads++;
                @(negedge clk);
            end
        end
        wait(cycles==1000); @(negedge clk);
        $display("PASS local PM mode=%0d writes=%0d reads=%0d",mode,writes,reads);
        $finish;
    end
    initial #15000 $fatal(1,"LC PM timeout");
endmodule

module test_qwen3_mother_pm;
    logic clk_i=0,rst_ni=0;
    always #5 clk_i=~clk_i;
    logic req_valid_i=0,req_write_i,req_ready_o,rsp_valid_o,rsp_ready_i=0,rsp_error_o;
    logic [13:0] req_address_i;
    logic [127:0] req_data_i,rsp_data_o,image[104];
    logic [3:0] cs,write_mode;
    integer bank_reads[4], bank_writes[4];
    integer bytes=1664, words;
    string input_path,wave_path;
    control_pm #(.BYTES(16384),.USE_SRAM(1'b1)) dut(.*);
    for(genvar i=0;i<4;i++) begin : bank_monitor
        assign cs[i]=!dut.sram.storage.banks[i].memory.csb0;
        assign write_mode[i]=!dut.sram.storage.banks[i].memory.web0;
    end
    always @(posedge clk_i) if(rst_ni) begin
        if(!$onehot0(cs)) $fatal(1,"PM request selected multiple banks");
        for(int i=0;i<4;i++) if(cs[i]) begin
            if(write_mode[i]) bank_writes[i]++;
            else bank_reads[i]++;
        end
    end

    task automatic access(input bit write, input int index);
        req_address_i=14'(16*index); req_data_i=image[index]; req_write_i=write; req_valid_i=1;
        do @(posedge clk_i); while(!req_ready_o);
        @(negedge clk_i); req_valid_i=0;
        while(!rsp_valid_o) @(negedge clk_i);
        repeat(2) @(negedge clk_i);
        if(!rsp_valid_o || rsp_error_o || (!write && rsp_data_o!==image[index]))
            $fatal(1,"mother PM response failed at word %d",index);
        rsp_ready_i=1; @(negedge clk_i); rsp_ready_i=0;
    endtask
    initial begin
        if(!$value$plusargs("IMAGE=%s",input_path) || !$value$plusargs("WAVE=%s",wave_path))
            $fatal(1,"missing mother PM arguments");
        void'($value$plusargs("BYTES=%d",bytes));
        if(bytes<=0 || bytes>1664 || bytes%16!=0) $fatal(1,"invalid mother PM extent");
        words=bytes/16;
        $readmemh(input_path,image);
        $dumpfile(wave_path); $dumpvars(4,dut);
        repeat(5) @(negedge clk_i); rst_ni=1;
        for(int i=0;i<words;i++) access(1,i);
        for(int i=0;i<words;i++) access(0,i);
        for(int i=0;i<4;i++)
            if(bank_reads[i]!=words/4+(i<words%4?1:0) || bank_writes[i]!=bank_reads[i])
                $fatal(1,"unreconciled PM bank %d",i);
        $display("PASS mother PM bytes=%0d reads=%0d writes=%0d bank_reads=%p bank_writes=%p",
                 bytes,words,words,bank_reads,bank_writes);
        $finish;
    end
    initial #30000 $fatal(1,"mother PM timeout");
endmodule
