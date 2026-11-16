`timescale 1ns/1ps
module test_qwen3_write_span;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic service_valid=0, service_ready, service_done_valid;
    logic [1023:0] service_descriptor, desc_mem[1];
    logic [15:0] service_done_status;
    logic [31:0] service_done_read_bytes, service_done_write_bytes;
    logic s_req_valid, s_req_ready, s_rsp_valid=0, s_rsp_ready;
    logic [9:0] s_req_address;
    logic [127:0] s_rsp_data=0;
    logic wr_valid, wr_ready, wr_done_valid=0, wr_done_ready;
    logic [63:0] wr_address, wr_tag, wr_done_tag=0;
    logic [511:0] wr_data;
    integer cycles=0, requests=0, writes=0, retired=0, stalls=0, mode=0;
    integer idle=0;
    string descriptor_path, wave_path;
    s128_kv_store_scope dut(
        .clk,.reset,.service_valid,.service_ready,.service_descriptor,
        .service_owner(128'hffff),.service_ticket(32'd7),
        .service_cancel_valid(1'b0),.service_cancel_ready(),
        .service_done_valid,.service_done_ready(1'b1),
        .service_done_owner(),.service_done_ticket(),.service_done_status,
        .service_done_read_bytes,.service_done_write_bytes,
        .s_req_valid,.s_req_ready,.s_req_address,.s_rsp_valid,.s_rsp_ready,
        .s_rsp_data,.s_rsp_error(1'b0),.wr_valid,.wr_ready,.wr_address,.wr_tag,
        .wr_data,.wr_done_valid,.wr_done_ready,.wr_done_tag,.wr_done_error(1'b0)
    );

    function automatic logic [127:0] payload(input integer word_index);
        logic [31:0] x;
        x=32'h9e3779b9*(1+word_index) ^ service_descriptor[223:192];
        return {x^32'h01234567,~x,x<<3,x>>5};
    endfunction

    assign s_req_ready=!s_rsp_valid && (mode==0 || cycles%4!=0);
    assign wr_ready=!wr_done_valid && (mode==0 || cycles%11==0);

    always @(posedge clk) if (!reset) begin
        cycles <= cycles+1;
        if (s_rsp_valid && s_rsp_ready) s_rsp_valid <= 0;
        if (s_req_valid && s_req_ready) begin
            if (int'(s_req_address) != int'(service_descriptor[143:128])+requests)
                $fatal(1,"SRAM source word mismatch");
            s_rsp_data <= payload(int'(s_req_address));
            s_rsp_valid <= 1;
            requests <= requests+1;
        end
        if (wr_done_valid && wr_done_ready) begin
            wr_done_valid <= 0;
            retired <= retired+1;
        end
        if (wr_valid && !wr_ready) stalls <= stalls+1;
        if (wr_valid && wr_ready) begin
            if (wr_address != service_descriptor[255:192]+64'(writes*64) ||
                wr_tag != service_descriptor[319:256]+64'(writes))
                $fatal(1,"DDR address or tag mismatch");
            for (int lane=0;lane<4;lane++)
                if (wr_data[128*lane+:128] !== payload(int'(service_descriptor[143:128])+4*writes+lane))
                    $fatal(1,"DDR payload lane mismatch");
            wr_done_tag <= wr_tag;
            wr_done_valid <= 1;
            writes <= writes+1;
        end
    end

    initial begin
        if (!$value$plusargs("DESC=%s",descriptor_path) || !$value$plusargs("WAVE=%s",wave_path))
            $fatal(1,"missing paths");
        void'($value$plusargs("MODE=%d",mode));
        void'($value$plusargs("IDLE=%d",idle));
        $readmemh(descriptor_path,desc_mem);
        service_descriptor=desc_mem[0];
        $dumpfile(wave_path);
        $dumpvars(1,dut);
        repeat (5) @(negedge clk);
        reset=0;
        repeat (7) @(negedge clk);
        if (idle==0) begin
            service_valid=1;
            do @(posedge clk); while (!service_ready);
            @(negedge clk);
            service_valid=0;
            do @(posedge clk); while (!service_done_valid);
            if (service_done_status!=0 || service_done_read_bytes!=512 || service_done_write_bytes!=512)
                $fatal(1,"terminal receipt mismatch");
        end
        wait (cycles == 1040);
        @(negedge clk);
        if (idle!=0 ? (requests!=0 || writes!=0 || retired!=0) :
            (requests!=32 || writes!=8 || retired!=8 || (mode!=0 && stalls==0)))
            $fatal(1,"extent/coverage mismatch");
        $display("PASS span mode=%0d idle=%0d requests=%0d writes=%0d retired=%0d stalls=%0d",mode,idle,requests,writes,retired,stalls);
        $finish;
    end
    initial #15000 $fatal(1,"simulation timeout");
endmodule
