// Consume committed S32 projection tiles in vocabulary order. The producer
// retains each SRAM window until the corresponding tile release is accepted.
module s128_vocabulary_retire (
    input wire clk, reset,
    input wire job_valid,
    output wire job_ready,
    input wire [31:0] job_length, job_tag,
    input wire tile_valid,
    output wire tile_ready,
    input wire [31:0] tile_first, tile_tag,
    input wire [7:0] tile_count,
    input wire [9:0] tile_s_base,
    output wire tile_release_valid,
    input wire tile_release_ready,
    output reg [31:0] tile_release_first,
    output wire s_read_valid,
    input wire s_read_ready,
    output wire [9:0] s_read_address,
    output wire [31:0] s_read_tag,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [31:0] s_rsp_tag,
    input wire [127:0] s_rsp_data,
    input wire s_rsp_error,
    output wire token_valid,
    input wire token_ready,
    output wire [31:0] token_id, token_tag,
    output wire signed [31:0] token_logit,
    output wire token_error
);
    localparam [2:0] IDLE=0, TILE=1, ISSUE=2, RESPONSE=3, RELEASE=4, REPORT=5,
                     FAULT=6, FAULT_REPORTED=7;
    reg [2:0] state;
    reg [31:0] total, tag, next_index;
    reg [7:0] remaining;
    reg [9:0] address;
    wire [32:0] tile_end={1'b0,tile_first}+{25'd0,tile_count};
    wire [10:0] s_end={1'b0,tile_s_base}+(({3'd0,tile_count}+11'd3)>>2);
    wire tile_legal=tile_tag==tag && tile_first==next_index &&
                    tile_count!=0 && tile_count<=128 && tile_end<={1'b0,total} &&
                    (tile_end=={1'b0,total} || tile_count[1:0]==0) && s_end<=1024;
    wire arg_cmd_ready, arg_input_ready, arg_done, arg_error;
    wire [31:0] arg_token, arg_tag;
    wire signed [31:0] arg_logit;
    wire valid_response=s_rsp_tag==s_read_tag && !s_rsp_error;
    wire [3:0] lane_mask=4'hf >> (remaining>=4 ? 4'd0 : 4'd4-remaining[3:0]);

    assign job_ready=!reset && state==IDLE && arg_cmd_ready;
    assign tile_ready=!reset && state==TILE;
    assign s_read_valid=!reset && state==ISSUE;
    assign s_read_address=address;
    assign s_read_tag=next_index;
    assign s_rsp_ready=!reset && state==RESPONSE && arg_input_ready;
    assign tile_release_valid=!reset && state==RELEASE;
    assign token_valid=!reset && ((state==REPORT && arg_done) || state==FAULT);
    assign token_id=state==FAULT ? 0 : arg_token;
    assign token_tag=state==FAULT ? tag : arg_tag;
    assign token_logit=state==FAULT ? 0 : arg_logit;
    assign token_error=state==FAULT || arg_error;

    s32_token_argmax argmax (
        .clk, .reset(reset || state==FAULT),
        .cmd_valid(job_valid && job_ready), .cmd_ready(arg_cmd_ready),
        .cmd_length(job_length), .cmd_tag(job_tag),
        .in_valid(s_rsp_valid && s_rsp_ready && valid_response), .in_ready(arg_input_ready),
        .in_index(next_index), .in_mask(lane_mask), .in_data(s_rsp_data),
        .done_valid(arg_done), .done_ready(token_ready && state==REPORT),
        .done_token(arg_token), .done_tag(arg_tag), .done_logit(arg_logit), .done_error(arg_error)
    );

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            total<=0;
            tag<=0;
            next_index<=0;
            remaining<=0;
            address<=0;
            tile_release_first<=0;
        end else begin
            case (state)
                IDLE: if (job_valid && job_ready) begin
                    total<=job_length;
                    tag<=job_tag;
                    next_index<=0;
                    state<=job_length==0 ? REPORT : TILE;
                end
                TILE: if (tile_valid && tile_ready) begin
                    tile_release_first<=tile_first;
                    address<=tile_s_base;
                    remaining<=tile_count;
                    state<=tile_legal ? ISSUE : FAULT;
                end
                ISSUE: if (s_read_valid && s_read_ready) state<=RESPONSE;
                RESPONSE: if (s_rsp_valid && s_rsp_ready) begin
                    if (!valid_response) state<=FAULT;
                    else if (remaining<=4) begin
                        next_index<=next_index+{24'd0,remaining};
                        state<=RELEASE;
                    end else begin
                        next_index<=next_index+32'd4;
                        remaining<=remaining-8'd4;
                        address<=address+10'd1;
                        state<=ISSUE;
                    end
                end
                RELEASE: if (tile_release_valid && tile_release_ready)
                    state<=next_index==total ? REPORT : TILE;
                REPORT: if (token_valid && token_ready) state<=IDLE;
                // The caller must recover the failed window before resetting.
                FAULT: if (token_valid && token_ready) state<=FAULT_REPORTED;
                FAULT_REPORTED: state<=FAULT_REPORTED;
                default: state<=FAULT;
            endcase
        end
    end
endmodule
