`timescale 1ns/1ps
module test_qwen3_sram_banks;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic req=0, wr=0, ready, valid, take=0;
    logic [9:0] addr;
    logic [127:0] din, dout;
    logic wide_req=0, wide_ready, wide_valid, wide_take=0;
    logic [7:0] wide_addr;
    logic [511:0] wide_dout;
    logic [3:0] bank_enable, bank_write;
    logic [31:0] bank_addresses;
    integer read128=0, read512=0, write128=0, serial_mode=0;
    string wave_file;
    localparam logic [7:0] ROW=8'd59;
    localparam logic [511:0] DATA={128'h89abcdef,128'hdeadbeef,128'hcafe1234,128'h1234ffff};
    block_feed_s16k_sram dut(.*);

    for(genvar b=0;b<4;b++) begin : observed
        assign bank_enable[b]=!dut.banks[b].memory.csb0;
        assign bank_write[b]=!dut.banks[b].memory.web0;
        assign bank_addresses[8*b+:8]=dut.banks[b].memory.addr0;
    end
    always @(posedge clk) if(!reset) begin
        if(wide_req && wide_ready) begin
            if(bank_enable!==4'b1111 || bank_write!==4'b0000 ||
               bank_addresses!=={4{wide_addr}}) $fatal(1,"wide bank binding");
            read512 <= read512+1;
        end else if(req && ready) begin
            if(bank_enable!==(4'b1<<addr[1:0]) || (bank_write & bank_enable)!=(wr?bank_enable:4'b0))
                $fatal(1,"ordinary bank binding");
            if(wr) write128<=write128+1;
            else read128<=read128+1;
        end else if(bank_enable!=0) $fatal(1,"unaccounted bank operation");
    end
    task automatic narrow(input bit write, input logic [9:0] address, input logic [127:0] expected);
        wr=write; addr=address; din=expected; req=1;
        do @(posedge clk); while(!ready);
        @(negedge clk); req=0;
        while(!valid) @(negedge clk);
        if(dout!==expected) $fatal(1,"lane data mismatch");
        take=1; @(negedge clk); take=0;
    endtask
    initial begin
        if (!$value$plusargs("WAVE=%s",wave_file)) $fatal(1,"missing waveform");
        void'($value$plusargs("SERIAL=%d",serial_mode));
        $dumpfile(wave_file);
        $dumpvars(2,dut);
        repeat(5) @(negedge clk);
        reset=0;
        if (serial_mode!=0) begin
            for(int row=0;row<16;row++) begin
                for(int bank=0;bank<2;bank++)
                    narrow(1,10'(4*row+bank),DATA[128*bank+:128] ^ 128'(32+row));
                for(int bank=0;bank<2;bank++)
                    narrow(0,10'(4*row+bank),DATA[128*bank+:128] ^ 128'(32+row));
            end
            for(int row=0;row<16;row++) begin
                for(int bank=0;bank<4;bank++)
                    narrow(1,10'(4*row+bank),DATA[128*bank+:128] ^ 128'(64+row));
                for(int bank=0;bank<4;bank++)
                    narrow(0,10'(4*row+bank),DATA[128*bank+:128] ^ 128'(64+row));
            end
            if (write128!=96 || read128!=96 || read512!=0) $fatal(1,"serialized bank count");
            $display("PASS SRAM SERIAL: 16x256-bit and 16x512-bit writes -> 96 native 128-bit writes, 96 reads");
            $finish;
        end
        for(int b=0;b<4;b++) narrow(1,{ROW,2'(b)},DATA[128*b+:128]);
        wide_addr=ROW; wide_req=1;
        do @(posedge clk); while(!wide_ready);
        @(negedge clk); wide_req=0;
        repeat(5) @(negedge clk);
        if(!wide_valid || wide_dout!==DATA) $fatal(1,"512-bit data or held response mismatch");
        wide_take=1; @(negedge clk); wide_take=0;
        for(int b=0;b<4;b++) narrow(0,{ROW,2'(b)},DATA[128*b+:128]);
        if(read128!=4 || read512!=1 || write128!=4) $fatal(1,"bank count mismatch");
        $display("PASS SRAM 512-bit read=%0d 128-bit read=%0d write=%0d",read512,read128,write128);
        $finish;
    end
    initial #30000 $fatal(1,"SRAM timeout");
endmodule
