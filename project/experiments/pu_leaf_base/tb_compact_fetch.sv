`timescale 1ns/1ps
module tb_compact_fetch;
    reg [1023:0] header;
    reg [31:0] inst_count, inst_offset, pc;
    reg [13:0] cfg_address;
    reg [127:0] pm_rsp_data_i, ireg;
    reg [31:0] registers[0:7];
    `include "instruction_fetch64.svh"
    initial begin
        header=0; inst_count=3; inst_offset=128; pc=0; cfg_address=0;
        ireg=0; pm_rsp_data_i=0;
        header[64+:16]=2;
        // L_EXEC(resource=0, token=3, descriptor=7), L_WAIT(mask=8).
        pm_rsp_data_i={64'h4400000000000008,64'h4100030700000000};
        #1;
        assert(instruction_version_ok && instruction_beats==2 && instruction_end==160);
        assert(fetch_address==128 && fetch_instruction==128'h41000003070000000000000000000000);
        pc=1; #1;
        assert(fetch_address==128 && fetch_instruction==128'h44000000000000000000000800000000);
        pc=2; pm_rsp_data_i={64'b0,64'h4f00000000000000}; cfg_address=144; #1;
        assert(fetch_address==144 && fetch_instruction==128'h4f000000000000000000000000000000);
        assert(!bad_instruction_padding);
        pm_rsp_data_i[127:64]=1; #1; assert(bad_instruction_padding);
        inst_count=4; #1; assert(!bad_instruction_padding && instruction_end==160);
        inst_count=256; pc=255; #1;
        assert(instruction_beats==128 && instruction_end==2176 && fetch_address==2160);
        header[64+:16]=1; #1;
        assert(instruction_version_ok && instruction_beats==256);
        assert(fetch_address==4208 && instruction_end==4224 && fetch_instruction==pm_rsp_data_i);
        header[64+:16]=3; #1; assert(!instruction_version_ok);
        $display("PASS compact fetch: half selection, odd/even tails, max PC, legacy, version rejection");
        $finish;
    end
endmodule
