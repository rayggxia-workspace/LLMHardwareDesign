`timescale 1ns/1ps
module test_s128_ddr_range_load_pipeline;
    logic clk=0, reset=1, launch=0, inject_error=0;
    always #5 clk=~clk;
    wire done, error, rd_valid, rd_ready, s_valid, s_ready, s_take;
    wire [63:0] rd_tag;
    wire [9:0] address;
    wire [127:0] data;
    wire [31:0] tag;
    logic rd_return=0;
    logic [31:0] tags[4];
    int sent=0, acked=0, cycle=0, last_issue=-10;
    logic consecutive=0;
    assign s_ready=cycle%5!=0;
    wire s_response=sent>acked && cycle%4!=0;
    s128_ddr_range_load #(.PIPELINE_WRITES(1'b1)) dut(
        .clk,.reset,.launch_valid(launch),.launch_ready(),.launch_base(64'd0),
        .launch_s_base(10'd16),.launch_bursts(8'd1),.launch_pair(1'b0),
        .launch_pair_beat(1'b0),.launch_pair_high(1'b0),.done_valid(done),
        .done_error(error),.done_ready(1'b0),.rd_valid,.rd_ready(1'b1),.rd_address(),
        .rd_tag,.rd_rsp_valid(rd_return),.rd_rsp_ready(rd_ready),.rd_rsp_tag(64'd0),
        .rd_rsp_data({128'd4,128'd3,128'd2,128'd1}),
        .s_valid,.s_ready,.s_address(address),.s_data(data),.s_tag(tag),
        .s_rsp_valid(s_response),.s_rsp_ready(s_take),
        .s_rsp_tag(tags[acked%4] ^ (inject_error && acked==0 ? 32'd1 : 32'd0)));
    always @(posedge clk) begin
        if (reset) begin
            cycle<=0; sent<=0; acked<=0; rd_return<=0;
            consecutive<=0; last_issue<=-10;
        end else begin
            cycle<=cycle+1;
            if (rd_valid) rd_return<=1;
            if (rd_ready&&rd_return) rd_return<=0;
            if (s_valid&&s_ready) begin
                assert(address == 10'(16+sent) && data==128'(sent+1));
                tags[sent]<=tag;
                sent<=sent+1;
                if (last_issue==cycle-1) consecutive<=1;
                last_issue<=cycle;
            end
            if (s_response&&s_take) acked<=acked+1;
            assert(sent-acked<=2);
        end
    end
    task automatic run(input bit fault);
        @(negedge clk); reset=1;
        @(negedge clk); reset=0; launch=1; inject_error=fault;
        @(negedge clk); launch=0;
        wait(done);
        assert(sent==4 && acked==4 && consecutive && error==fault)
            else $fatal(1,"write pipeline failed to retire or drain");
    endtask
    initial begin
        run(0);
        run(1);
        $display("PASS bounded write pipeline, stalls and error drain");
        $finish;
    end
    initial begin
        #2000;
        $fatal(1,"timeout");
    end
endmodule
