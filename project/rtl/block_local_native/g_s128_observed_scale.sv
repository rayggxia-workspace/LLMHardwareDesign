// LC-owned probe on actual accepted G outputs. The G leaf and data path are
// unchanged; max logic and metadata registers are real adapter area/load.
// Successful done is inherited only after the original frontend's true S ACK.
// Thus a subsequent A16 pack can reuse the observed shift without a scan pass.
module g_s128_observed_scale (
    input wire clk, reset,
    input wire [127:0] cmd_key, input wire [15:0] cmd_kk,
    output reg [127:0] done_key, output reg [15:0] done_kk,
    output wire [5:0] done_a_shift,
    input wire cmd_valid, output wire cmd_ready,
    input wire [9:0] cmd_gate_base, cmd_up_base, cmd_mid_base,
    input wire [5:0] cmd_words, input wire cmd_gated,
    output reg done_valid, input wire done_take,
    output reg done_error, output reg [5:0] done_words,
    output reg s_req_valid, output reg s_req_write,
    output reg [9:0] s_req_addr, output reg [127:0] s_req_data,
    input wire s_req_ready, s_rsp_valid,
    output wire s_rsp_ready, input wire [127:0] s_rsp_data,
    output wire g_in_valid, input wire g_in_ready,
    output wire [63:0] g_in_gate, g_in_up,
    output wire g_in_gated, output wire [1:0] g_in_mask,
    input wire g_out_valid, output wire g_out_ready,
    input wire [63:0] g_out_data, input wire [1:0] g_out_mask,
    input wire g_out_error
);
    g_s128_frontend stream(.*);
    reg [31:0] maximum;
    reg [31:0] next_maximum, sample;
    always @* begin
        next_maximum=maximum;sample=0;
        for(integer lane=0;lane<2;lane=lane+1) begin
            sample=g_out_data[32*lane+31] ? (~g_out_data[32*lane+:32]+32'd1) : g_out_data[32*lane+:32];
            if(g_out_mask[lane] && sample>next_maximum)next_maximum=sample;
        end
    end
    function automatic [5:0] choose_shift(input [31:0] largest);
        reg found;
        begin
            choose_shift=17;found=0;
            for(integer s=0;s<18;s=s+1)begin
                if(!found && {32'd0,largest}<=(64'd32767<<s))begin choose_shift=6'(s);found=1;end
            end
        end
    endfunction
    assign done_a_shift=done_valid && !done_error ? choose_shift(maximum) : 6'd0;
    always @(posedge clk)begin
        if(reset)begin maximum<=0;done_key<=0;done_kk<=0;end
        else begin
            if(cmd_valid && cmd_ready)begin maximum<=0;done_key<=cmd_key;done_kk<=cmd_kk;end
            if(g_out_valid && g_out_ready && !g_out_error)maximum<=next_maximum;
        end
    end
endmodule
