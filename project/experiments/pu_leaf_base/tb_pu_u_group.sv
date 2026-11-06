module tb_pu_u_group;
    reg clk=0;
    always #5 clk=~clk;
    localparam integer KIND=0;
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
    wire [127:0] rx_ignored;
    reg direct_mode=0, direct_connect=0;
    wire direct_ready, direct_source_valid;
    wire [127:0] direct_source_data;
    pu_u_group dut (
        .clk, .reset,
        .n_cmd_valid(cmd_valid[1]), .n_cmd_direct(direct_mode), .n_cmd_ready(cmd_ready[1]), .n_cmd_store(cmd_store[1]),
        .n_cmd_meta(cmd_meta[103:64]), .n_cmd_sources(cmd_sources[3:2]), .n_cmd_src(cmd_addresses[49:30]),
        .n_cmd_dst(cmd_dst[19:10]), .n_done_valid(done_valid[1]), .n_done_ready(done_ready[1]),
        .n_done_error(done_error[1]), .n_done_saturated(done_saturated[1]), .n_done_data(done_data[255:128]),
        .e_cmd_valid(cmd_valid[0]), .e_cmd_ready(cmd_ready[0]), .e_cmd_store(cmd_store[0]),
        .e_cmd_op(cmd_meta[3:0]), .e_cmd_shift(cmd_meta[8:4]), .e_cmd_src(cmd_addresses[29:0]),
        .e_cmd_dst(cmd_dst[9:0]), .e_done_valid(done_valid[0]), .e_done_ready(done_ready[0]),
        .e_done_error(done_error[0]), .e_done_saturated(done_saturated[0]), .e_done_data(done_data[127:0]),
        .n_to_e_valid(direct_source_valid), .n_to_e_ready(direct_connect && direct_ready),
        .n_to_e_data(direct_source_data),
        .e_cmd_direct_a(direct_mode), .e_direct_a_valid(direct_connect && direct_source_valid),
        .e_direct_a_ready(direct_ready), .e_direct_a_data(direct_source_data),
        .io_req_valid({tx_req,rx_valid}), .io_req_write(2'b01), .io_req_addr({tx_addr,rx_addr}),
        .io_req_data({128'b0,rx_data}), .io_req_ready({tx_ready,rx_ready}),
        .io_rsp_valid({tx_valid,rx_stored}), .io_rsp_ready({tx_take,rx_stored_ready}),
        .io_rsp_data({tx_data,rx_ignored})
    );
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
            // Two independent 8-element tiles share the same Softmax context.
            // Each uniform probability is 1/16 in signed Q1.14.
            write_word(54,0);
            write_word(55,0);
            execute(1,0,0,0,0,0,answer);
            execute(1,64'h81,1,30'd54,0,0,answer);
            execute(1,64'h81,1,30'd55,0,0,answer);
            execute(1,2,0,0,0,0,answer);
            execute(1,64'h83,1,30'd54,1,56,answer);
            execute(1,64'h83,1,30'd55,1,57,answer);
            execute(1,4,0,0,0,0,answer);
            execute(1,64'h86,1,30'd56,1,58,answer);
            execute(1,64'h86,1,30'd57,1,59,answer);
            expect_word(58,{8{16'd1024}});
            expect_word(59,{8{16'd1024}});
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
            execute(1,64'h100,1,30'd21,0,0,answer);
            execute(1,64'h81,1,30'd20,0,0,answer);
            execute(1,2,0,0,0,0,answer);
            // Hold N completion until the explicit N-to-E overlay is connected.
            cmd_meta[63:0]=0;
            cmd_addresses[29:0]={10'd0,10'd6,10'd0};
            cmd_dst[9:0]=25;
            cmd_store[0]=1; direct_mode=1; cmd_valid[0]=1;
            do @(posedge clk); while (!cmd_ready[0]);
            @(negedge clk); cmd_valid[0]=0;
            cmd_meta[127:64]=64'h85;
            cmd_addresses[59:30]={10'd0,10'd20,10'd20};
            cmd_sources[3:2]=2;
            cmd_store[1]=0; cmd_valid[1]=1;
            do @(posedge clk); while (!cmd_ready[1]);
            @(negedge clk); cmd_valid[1]=0;
            while (!direct_source_valid || !direct_ready) tick();
            if (done_valid != 0) $fatal(1, "reported completion before transfer");
            repeat (2) tick();
            if (!direct_source_valid || done_valid != 0) $fatal(1, "unbound overlay did not hold source");
            direct_connect=1;
            tick();
            direct_connect=0; direct_mode=0;
            if (direct_source_valid || !done_valid[1] || done_error[1])
                $fatal(1, "overlay handshake did not retire exactly once");
            done_ready[1]=1;
            tick();
            done_ready[1]=0;
            while (!done_valid[0]) tick();
            if (done_error[0]) $fatal(1, "direct compact E command failed");
            done_ready[0]=1;
            tick();
            done_ready[0]=0;
            expect_word(25,{8{16'd1049}});
            // Four expert (id,score) pairs; equal scores choose smaller id.
            write_word(50,{16'd2,16'd25,16'd1,16'hffff,16'd7,16'd25,16'd5,16'd10});
            execute(1,64'h308,0,0,0,0,answer);
            execute(1,64'h49,1,30'd50,0,0,answer);
            execute(1,64'ha,0,0,1,51,answer);
            expect_word(51,{80'd0,16'd5,16'd7,16'd2});
        end
        $display("PASS U native N/E/S_base, direct N-to-E and SRAM readback");
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "timeout");
    end
endmodule
