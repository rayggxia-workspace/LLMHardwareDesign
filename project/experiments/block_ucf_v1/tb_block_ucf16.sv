module ucf_case #(parameter integer KIND=0)(input wire clk, output reg passed=0);
    localparam integer K = KIND == 2 ? 3 : 2;
    reg reset=1;
    reg [K-1:0] cmd_valid=0, cmd_store=0, done_ready=0;
    reg [K*64-1:0] cmd_meta=0;
    reg [K*2-1:0] cmd_sources=0;
    reg [K*30-1:0] cmd_addresses=0;
    reg [K*10-1:0] cmd_dst=0;
    wire [K-1:0] cmd_ready, done_valid, done_error, done_saturated;
    wire [K*128-1:0] done_data;
    reg rx_valid=0, rx_stored_ready=0, tx_req=0, tx_take=0;
    reg [9:0] rx_addr=0, tx_addr=0;
    reg [127:0] rx_data=0;
    wire rx_ready, rx_stored, tx_ready, tx_valid;
    wire [127:0] tx_data;
    reg [127:0] answer;
`ifdef UCF_FINAL_NETLIST
    if (KIND == 0) begin: u_gate
        block_u16 dut (.*);
    end else if (KIND == 1) begin: f_gate
        block_f16 dut (.*);
    end else begin: c_gate
        block_c16 dut (.*);
    end
`else
    block_ucf16 #(.KIND(KIND)) dut (.*);
`endif

    task automatic tick;
        @(posedge clk);
        @(negedge clk);
    endtask
    task automatic write_word(input [9:0] addr, input [127:0] data);
        rx_addr=addr;
        rx_data=data;
        rx_valid=1;
        do @(posedge clk); while (!rx_ready);
        @(negedge clk);
        rx_valid=0;
        while (!rx_stored) tick();
        repeat (2) begin
            tick();
            if (!rx_stored) $fatal(1, "KIND=%d lost write acknowledgement", KIND);
        end
        rx_stored_ready=1;
        tick();
        rx_stored_ready=0;
    endtask
    task automatic start_read(input [9:0] addr, input [127:0] want);
        tx_addr=addr;
        tx_req=1;
        do @(posedge clk); while (!tx_ready);
        @(negedge clk);
        tx_req=0;
        while (!tx_valid) tick();
        if (tx_data !== want) $fatal(1,"KIND=%d address=%d got=%h expected=%h",KIND,addr,tx_data,want);
    endtask
    task automatic release_read(input [127:0] want);
        if (!tx_valid || tx_data !== want) $fatal(1,"KIND=%d source released before ACK",KIND);
        tx_take=1;
        tick();
        tx_take=0;
    endtask
    task automatic expect_word(input [9:0] addr, input [127:0] want);
        start_read(addr,want);
        release_read(want);
    endtask
    task automatic execute(input integer lane, input [63:0] meta,
                           input [1:0] n, input [29:0] addr, input bit store,
                           input [9:0] dst, output [127:0] value);
        cmd_meta[64*lane+:64]=meta;
        cmd_sources[2*lane+:2]=n;
        cmd_addresses[30*lane+:30]=addr;
        cmd_store[lane]=store;
        cmd_dst[10*lane+:10]=dst;
        cmd_valid[lane]=1;
        do @(posedge clk); while (!cmd_ready[lane]);
        @(negedge clk);
        cmd_valid[lane]=0;
        while (!done_valid[lane]) tick();
        if (done_error[lane]) $fatal(1,"KIND=%d lane=%d meta=%h command failed",KIND,lane,meta);
        value=done_data[128*lane+:128];
        done_ready[lane]=1;
        tick();
        done_ready[lane]=0;
    endtask

    initial begin
        repeat (2) tick();
        reset=0;
        write_word(5, {8{16'd17}});
        write_word(6, {8{16'd25}});
        execute(0,0,2,{10'd0,10'd6,10'd5},1,1023,answer);
        expect_word(1023,{8{16'd42}});
        if (KIND == 0) begin
            write_word(12,0);
            execute(1,0,0,0,0,0,answer);
            execute(1,64'h21,1,30'd12,0,0,answer);
            execute(1,2,0,0,0,0,answer);
            execute(1,64'h23,1,30'd12,1,13,answer);
            expect_word(13,128'h80008000);
            execute(1,4,0,0,0,0,answer);
            execute(1,64'h26,1,30'd13,1,14,answer);
            expect_word(14,128'h20002000);
            write_word(20,{8{16'd1024}});
            write_word(21,128'd1);
            execute(1,64'h100,1,30'd21,0,0,answer);
            execute(1,64'h81,1,30'd20,0,0,answer);
            execute(1,2,0,0,0,0,answer);
            execute(1,64'h85,2,{10'd0,10'd20,10'd20},1,22,answer);
            expect_word(22,{8{16'd1024}});
            write_word(23,{4{32'h00000400}});
            execute(0,64'ha9,2,{10'd0,10'd23,10'd22},1,24,answer);
            expect_word(24,{8{16'd1024}});
            // Four expert (id,score) pairs; equal scores choose smaller id.
            write_word(50,{16'd2,16'd25,16'd1,16'hffff,16'd7,16'd25,16'd5,16'd10});
            execute(1,64'h308,0,0,0,0,answer);
            execute(1,64'h49,1,30'd50,0,0,answer);
            execute(1,64'ha,0,0,1,51,answer);
            expect_word(51,{80'd0,16'd5,16'd7,16'd2});
        end else begin
            write_word(12,0);
            write_word(13,128'h04000400);
            execute(1,9,2,{10'd0,10'd13,10'd12},1,14,answer);
            expect_word(14,128'h02000200);
            write_word(17,128'h04000400);
            execute(1,0,1,30'd17,1,18,answer);
            expect_word(18,128'h02ed02ed);
            // Reformat the already committed activation via the distinct E lane.
            execute(0,64'h1a,1,30'd18,1,19,answer);
            expect_word(19,128'h01760176);
            if (KIND == 2) begin
                write_word(15,{32'd100,32'd200,32'd300,32'd400});
                execute(2,0,1,30'd15,0,0,answer);
                execute(2,2,0,0,1,16,answer);
                expect_word(16,{32'd100,32'd200,32'd300,32'd400});
                // R next = 0.5*old. Check both state banks and all four
                // 128-bit slices of the retained 512-bit native response.
                write_word(25,{32'd60,32'd40,32'd20,32'd10});
                write_word(26,128'h40000000);
                execute(2,32,1,30'd25,0,0,answer);
                execute(2,20,1,30'd26,0,0,answer);
                execute(2,33,0,0,0,0,answer);
                execute(2,3,0,0,1,30,answer);
                execute(2,7,0,0,1,31,answer);
                execute(2,11,0,0,1,32,answer);
                execute(2,15,0,0,1,33,answer);
                expect_word(30,{64'd150,64'd200});
                expect_word(31,{64'd50,64'd100});
                expect_word(32,{64'd10,64'd5});
                expect_word(33,{64'd30,64'd20});
                execute(2,6,0,0,1,34,answer);
                expect_word(34,{32'd50,32'd100,32'd150,32'd200});
                execute(2,2,0,0,1,35,answer);
                expect_word(35,{32'd100,32'd200,32'd300,32'd400});
                execute(2,64'd29,0,0,0,0,answer);
            end
        end
        $display("PASS KIND=%0d real-SRAM compute and writeback",KIND);
        passed=1;
    end
endmodule

module tb_block_ucf16;
    reg clk=0;
    always #5 clk=!clk;
    wire u, c, f;
    ucf_case #(.KIND(0)) u_case(clk,u);
    ucf_case #(.KIND(1)) f_case(clk,f);
    ucf_case #(.KIND(2)) c_case(clk,c);
    reg [127:0] loop_result;
    initial begin
        wait (u && c && f);
        @(negedge clk);
        // The test driver supplies transport and destination addresses. Neither
        // source is released until the opposite physical SRAM acknowledges.
        c_case.write_word(40,{8{16'd1024}});
        c_case.start_read(40,{8{16'd1024}});
        u_case.write_word(40,c_case.tx_data);
        c_case.release_read({8{16'd1024}});
        u_case.execute(1,64'h100,1,30'd21,0,0,loop_result);
        u_case.execute(1,64'h81,1,30'd40,0,0,loop_result);
        u_case.execute(1,2,0,0,0,0,loop_result);
        u_case.execute(1,64'h85,2,{10'd0,10'd40,10'd20},1,41,loop_result);
        u_case.start_read(41,{8{16'd1024}});
        c_case.write_word(41,u_case.tx_data);
        u_case.release_read({8{16'd1024}});
        c_case.execute(0,0,2,{10'd0,10'd41,10'd40},1,42,loop_result);
        c_case.expect_word(42,{8{16'd2048}});
        $display("PASS C-U-C held-source SRAM handoff");
        $finish;
    end
    initial begin
        #50000;
        $fatal(1,"integration timed out");
    end
endmodule
