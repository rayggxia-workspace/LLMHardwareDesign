module tb_qwen_transport #(parameter bit C0_ONLY = 0);
    bit clk = 0;
    always #5 clk = !clk;
    logic reset = 1;
    logic command_valid = 0, command_ready, response_valid, response_error, response_ready = 0;
    logic [3:0] command_source, command_sink;
    logic [9:0] command_source_addr = 10'd397, command_sink_addr = 10'd803;
    logic [8:0] sink_reserved = '0;
    wire [4:0] pj_req_valid, pj_req_write, pj_rsp_ready, pj_req_ready, pj_rsp_valid;
    wire [49:0] pj_req_addr;
    wire [639:0] pj_req_data;
    logic [639:0] pj_rsp_data;
    wire [3:0] ucf_tx_req, ucf_tx_take, ucf_rx_valid, ucf_rx_stored_ready;
    wire [39:0] ucf_tx_addr, ucf_rx_addr;
    wire [3:0] ucf_tx_ready, ucf_rx_ready, ucf_rx_stored;
    logic [3:0] ucf_tx_valid = '0;
    logic [511:0] ucf_tx_data;
    wire [511:0] ucf_rx_data;
    logic [4:0] pj_pending = '0, pj_writing = '0;
    logic [3:0] ucf_pending = '0;
    bit accept_reads = 0, accept_writes = 0, return_ack = 0;
    int reads = 0, writes = 0, releases = 0;
    int want_src, want_dst;
    bit permitted;

    if (C0_ONLY) begin : c0_dut
        logic [1:0] source;
        always_comb begin
            case (command_source)
                4'd2: source = 0;
                4'd3: source = 1;
                4'd4: source = 2;
                default: source = 3;
            endcase
        end
        qwen_c0_receive dut (
            .clk, .reset, .command_valid, .command_ready, .command_source(source),
            .command_source_addr, .command_sink_addr, .response_valid, .response_error, .response_ready,
            .p2_req_valid(pj_req_valid[2]), .p2_req_write(pj_req_write[2]),
            .p2_req_addr(pj_req_addr[20+:10]), .p2_req_ready(pj_req_ready[2]),
            .p2_rsp_valid(pj_rsp_valid[2]), .p2_rsp_data(pj_rsp_data[256+:128]),
            .p2_rsp_ready(pj_rsp_ready[2]),
            .tx_req({ucf_tx_req[3], ucf_tx_req[1:0]}), .tx_take({ucf_tx_take[3], ucf_tx_take[1:0]}),
            .tx_addr({ucf_tx_addr[30+:10], ucf_tx_addr[0+:20]}),
            .tx_ready({ucf_tx_ready[3], ucf_tx_ready[1:0]}), .tx_valid({ucf_tx_valid[3], ucf_tx_valid[1:0]}),
            .tx_data({ucf_tx_data[384+:128], ucf_tx_data[0+:256]}),
            .c0_rx_valid(ucf_rx_valid[2]), .c0_rx_stored_ready(ucf_rx_stored_ready[2]),
            .c0_rx_addr(ucf_rx_addr[20+:10]), .c0_rx_data(ucf_rx_data[256+:128]),
            .c0_rx_reserved(sink_reserved[5]), .c0_rx_ready(ucf_rx_ready[2]),
            .c0_rx_stored(ucf_rx_stored[2])
        );
        assign {pj_req_valid[4:3], pj_req_valid[1:0], pj_req_write[4:3], pj_req_write[1:0],
                pj_rsp_ready[4:3], pj_rsp_ready[1:0]} = '0;
        assign {pj_req_addr[49:30], pj_req_addr[19:0], pj_req_data} = '0;
        assign {ucf_tx_req[2], ucf_tx_take[2], ucf_tx_addr[20+:10]} = '0;
        assign {ucf_rx_valid[3], ucf_rx_valid[1:0], ucf_rx_stored_ready[3], ucf_rx_stored_ready[1:0],
                ucf_rx_addr[39:30], ucf_rx_addr[19:0], ucf_rx_data[511:384], ucf_rx_data[255:0]} = '0;
    end else begin : nine_dut
        qwen_nine_transport dut (.*);
    end

    function automatic bit legal(input int s, d);
        case (s)
            0: return d inside {2,4};
            1: return d inside {0,6};
            2: return d inside {3,5,6,7,8};
            3: return d inside {0,1,2,5};
            4: return d inside {1,5};
            5: return d inside {2,3,4};
            6: return d inside {2,5};
            7: return d inside {3,8};
            8: return d == 7;
            default: return 0;
        endcase
    endfunction

    function automatic logic [127:0] payload(input int id, input logic [9:0] address);
        return 128'hbd45_f069_a19e_c327_07fb_f51e_5ad0_883a ^ {4{32'(1024*id+int'(address))}};
    endfunction

    for (genvar i=0; i<5; i++) begin : pj_model
        localparam int ID = i < 3 ? i : i+4;
        assign pj_req_ready[i] = !pj_pending[i] && (pj_req_write[i] ? accept_writes : accept_reads);
        assign pj_rsp_valid[i] = pj_pending[i] && (!pj_writing[i] || return_ack);
        always @(posedge clk) begin
            if (reset) pj_pending[i] <= 0;
            else begin
                if (pj_req_valid[i] && pj_req_ready[i]) begin
                    pj_pending[i] <= 1;
                    pj_writing[i] <= pj_req_write[i];
                    if (pj_req_write[i]) begin
                        if (!permitted || want_dst != ID || pj_req_addr[10*i+:10] != command_sink_addr ||
                            pj_req_data[128*i+:128] !== payload(want_src, command_source_addr))
                            $fatal(1, "wrong P/J write at endpoint %0d", ID);
                        writes = writes+1;
                    end else begin
                        if (!permitted || want_src != ID || pj_req_addr[10*i+:10] != command_source_addr)
                            $fatal(1, "wrong P/J read at endpoint %0d", ID);
                        pj_rsp_data[128*i+:128] <= payload(ID, pj_req_addr[10*i+:10]);
                        reads = reads+1;
                    end
                end
                if (pj_rsp_valid[i] && pj_rsp_ready[i]) begin
                    pj_pending[i] <= 0;
                    if (!pj_writing[i]) begin
                        if (!return_ack || writes != 1 || want_src != ID) $fatal(1, "early/wrong P/J release");
                        releases = releases+1;
                    end
                end
            end
        end
    end
    for (genvar i=0; i<4; i++) begin : ucf_model
        localparam int ID = i+3;
        assign ucf_tx_ready[i] = !ucf_tx_valid[i] && accept_reads;
        assign ucf_rx_ready[i] = !ucf_pending[i] && accept_writes;
        assign ucf_rx_stored[i] = ucf_pending[i] && return_ack;
        always @(posedge clk) begin
            if (reset) begin
                ucf_tx_valid[i] <= 0;
                ucf_pending[i] <= 0;
            end else begin
                if (ucf_tx_req[i] && ucf_tx_ready[i]) begin
                    if (!permitted || want_src != ID || ucf_tx_addr[10*i+:10] != command_source_addr)
                        $fatal(1, "wrong U/C/F read at endpoint %0d", ID);
                    ucf_tx_valid[i] <= 1;
                    ucf_tx_data[128*i+:128] <= payload(ID, ucf_tx_addr[10*i+:10]);
                    reads = reads+1;
                end
                if (ucf_rx_valid[i] && ucf_rx_ready[i]) begin
                    if (!permitted || want_dst != ID || ucf_rx_addr[10*i+:10] != command_sink_addr ||
                        ucf_rx_data[128*i+:128] !== payload(want_src, command_source_addr))
                        $fatal(1, "wrong U/C/F write at endpoint %0d", ID);
                    ucf_pending[i] <= 1;
                    writes = writes+1;
                end
                if (ucf_rx_stored_ready[i] && ucf_rx_stored[i]) ucf_pending[i] <= 0;
                if (ucf_tx_valid[i] && ucf_tx_take[i]) begin
                    if (!return_ack || writes != 1 || want_src != ID) $fatal(1, "early/wrong U/C/F release");
                    releases = releases+1;
                    ucf_tx_valid[i] <= 0;
                end
            end
        end
    end

    task automatic transfer(input int s, d, input bit abort_before_ack = 0);
        @(negedge clk);
        want_src=s; want_dst=d; permitted=legal(s,d);
        reads=0; writes=0; releases=0;
        sink_reserved='0; accept_reads=0; accept_writes=0; return_ack=0; response_ready=0;
        command_source=4'(s); command_sink=4'(d); command_valid=1;
        if (!command_ready) $fatal(1, "switch was not idle");
        @(negedge clk);
        command_valid=0;
        repeat (3) @(negedge clk);
        if (permitted) begin
            if (reads != 0 || response_valid) $fatal(1, "read backpressure ignored");
            accept_reads=1;
            while (reads == 0) @(negedge clk);
            repeat (3) @(negedge clk);
            accept_writes=1;
            repeat (3) @(negedge clk);
            if (writes != 0 || response_valid || releases != 0) $fatal(1, "destination reservation ignored");
            sink_reserved[d]=1;
            while (writes == 0) @(negedge clk);
            repeat (4) @(negedge clk);
            if (response_valid || releases != 0) $fatal(1, "destination commit ignored");
            if (abort_before_ack) begin
                reset=1;
                repeat (2) @(negedge clk);
                reset=0;
                @(negedge clk);
                if (!command_ready || response_valid || releases != 0) $fatal(1, "reset did not discard transfer");
                return;
            end
            return_ack=1;
        end
        while (!response_valid) @(negedge clk);
        repeat (2) @(negedge clk);
        if (!response_valid || response_error != !permitted) $fatal(1, "wrong response for %0d -> %0d",s,d);
        if (reads != int'(permitted) || writes != int'(permitted) || releases != int'(permitted))
            $fatal(1, "bad transfer count for %0d -> %0d",s,d);
        response_ready=1;
        @(negedge clk);
        response_ready=0;
    endtask

    initial begin
        repeat (2) @(negedge clk);
        reset=0;
        if (C0_ONLY) begin
            transfer(2,5); transfer(3,5); transfer(4,5); transfer(6,5);
        end else begin
            for (int s=0; s<9; s++) for (int d=0; d<9; d++) transfer(s,d);
            transfer(15,5); transfer(2,15);
        end
        transfer(2,5,1);
        transfer(6,5);
        $display("PASS Qwen transport profile C0_ONLY=%0d", C0_ONLY);
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "Qwen transport regression timed out");
    end
endmodule
