`timescale 1ns/1ps
// Rotate one leased 128-lane K head with actual SRAM operands and E32 writes.
module s128_rope_leased_row (
    input logic clk, reset,
    input logic cmd_valid,
    output logic cmd_ready, busy,
    input logic [9:0] cmd_source, cmd_cos, cmd_sin, cmd_dest,
    input logic [47:0] cmd_shifts,
    input logic [31:0] cmd_tag,
    output logic done_valid,
    input logic done_ready,
    output logic [31:0] done_tag,
    output logic done_error,
    output logic s_req_valid,
    input logic s_req_ready,
    output logic s_req_write,
    output logic [9:0] s_req_address,
    output logic [127:0] s_req_data,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [127:0] s_rsp_data,
    input logic s_rsp_error
);
    typedef enum logic [2:0] {IDLE, READ_REQ, READ_WAIT, ROTATE, ROTATE_WAIT, REPORT} state_t;
    state_t state;
    logic [9:0] source, cosine, sine, destination;
    logic [4:0] word_index;
    logic [1:0] operand;
    logic [47:0] shifts;
    logic [127:0] values[4];
    logic commit_ready, commit_valid, commit_bad;
    logic [31:0] commit_tag;
    logic commit_s_req, commit_s_take;
    logic [9:0] read_address, commit_address;
    logic [127:0] commit_data;
    wire illegal_window=cmd_source>10'd992 || cmd_cos>10'd992 || cmd_sin>10'd992 || cmd_dest>10'd992 ||
                         overlap(cmd_dest,cmd_source) || overlap(cmd_dest,cmd_cos) ||
                         overlap(cmd_dest,cmd_sin);

    function automatic logic overlap(input logic [9:0] first, second);
        return {1'b0,first} < {1'b0,second}+11'd32 && {1'b0,second} < {1'b0,first}+11'd32;
    endfunction

    always_comb begin
        case (operand)
            0: read_address=source+10'(word_index);
            1: read_address=source+10'(word_index ^ 5'd16);
            2: read_address=cosine+10'(word_index);
            default: read_address=sine+10'(word_index);
        endcase
    end

    assign cmd_ready=!reset&&state==IDLE;
    assign busy=!reset&&state!=IDLE;
    assign done_valid=!reset&&state==REPORT;
    assign s_req_valid=!reset&&(state==READ_REQ || (state==ROTATE_WAIT&&commit_s_req));
    assign s_req_write=state==ROTATE_WAIT;
    assign s_req_address=state==ROTATE_WAIT ? commit_address : read_address;
    assign s_req_data=commit_data;
    assign s_rsp_ready=!reset&&(state==READ_WAIT || (state==ROTATE_WAIT&&commit_s_take));

    rope_e32_s128_commit rotate_word(
        .clk,.reset,.cmd_valid(state==ROTATE),.cmd_ready(commit_ready),
        .cmd_dst(destination+10'(word_index)),.cmd_tag({27'd0,word_index}),
        .cmd_negate(!word_index[4]),.cmd_cos_shift(shifts[0+:8]),.cmd_neg_shift(shifts[8+:8]),
        .cmd_neg_align(shifts[16+:8]),.cmd_sin_shift(shifts[24+:8]),.cmd_sin_align(shifts[32+:8]),
        .cmd_out_shift(shifts[40+:8]),.cmd_value(values[0]),.cmd_paired(values[1]),
        .cmd_cos(values[2]),.cmd_sin(values[3]),.busy(),.done_valid(commit_valid),
        .done_ready(state==ROTATE_WAIT),.done_tag(commit_tag),.done_error(commit_bad),
        .s_req_valid(commit_s_req),.s_req_ready(s_req_ready&&state==ROTATE_WAIT),
        .s_req_address(commit_address),.s_req_data(commit_data),
        .s_rsp_valid(s_rsp_valid&&state==ROTATE_WAIT),.s_rsp_ready(commit_s_take),.s_rsp_error
    );

    always_ff @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            source<=0;
            cosine<=0;
            sine<=0;
            destination<=0;
            shifts<=0;
            word_index<=0;
            operand<=0;
            done_tag<=0;
            done_error<=0;
            for (int i=0;i<4;i++) values[i]<=0;
        end else begin
            case (state)
                IDLE: if (cmd_valid&&cmd_ready) begin
                    source<=cmd_source;
                    cosine<=cmd_cos;
                    sine<=cmd_sin;
                    destination<=cmd_dest;
                    shifts<=cmd_shifts;
                    word_index<=0;
                    operand<=0;
                    done_tag<=cmd_tag;
                    done_error<=illegal_window;
                    state<=illegal_window ? REPORT : READ_REQ;
                end
                READ_REQ: if (s_req_valid&&s_req_ready) state<=READ_WAIT;
                READ_WAIT: if (s_rsp_valid&&s_rsp_ready) begin
                    values[operand]<=s_rsp_data;
                    operand<=operand+1'b1;
                    done_error<=s_rsp_error;
                    if (s_rsp_error) state<=REPORT;
                    else state<=operand==3 ? ROTATE : READ_REQ;
                end
                ROTATE: if (commit_ready) state<=ROTATE_WAIT;
                ROTATE_WAIT: if (commit_valid) begin
                    done_error<=commit_bad || commit_tag!={27'd0,word_index};
                    word_index<=word_index+1'b1;
                    state<=(commit_bad || commit_tag!={27'd0,word_index} || word_index==31) ? REPORT : READ_REQ;
                end
                REPORT: if (done_valid&&done_ready) state<=IDLE;
                default: begin
                    done_error<=1;
                    state<=REPORT;
                end
            endcase
        end
    end
endmodule
