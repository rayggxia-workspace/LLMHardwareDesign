// Read a committed S32 row twice: choose its range, then feed the resident N.
// The caller holds the S lease and supplies epsilon as an exact dyadic value
// in the baseline squared units. The returned factor uses the baseline scale.
module s32_rms_factor_s128 (
    input wire clk, reset,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [9:0] cmd_base,
    input wire [12:0] cmd_length,
    input wire signed [5:0] cmd_baseline_shift,
    input wire [31:0] cmd_epsilon_mantissa,
    input wire signed [7:0] cmd_epsilon_shift,
    input wire [31:0] cmd_tag,
    output wire done_valid,
    input wire done_ready,
    output reg [31:0] done_factor, done_tag,
    output reg signed [5:0] done_shift,
    output reg [5:0] done_extra_shift,
    output reg done_error,

    output wire s_req_valid,
    input wire s_req_ready,
    output wire [9:0] s_req_address,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data,
    input wire s_rsp_error,

    output wire n_cmd_valid,
    input wire n_cmd_ready,
    output reg [3:0] n_cmd_op, n_cmd_count,
    output wire [31:0] n_cmd_param,
    output wire [127:0] n_cmd_data,
    input wire n_rsp_valid,
    output wire n_rsp_ready,
    input wire [31:0] n_rsp_factor,
    input wire n_rsp_error, n_rsp_saturated
);
    localparam [2:0] IDLE = 0, SCAN = 1, PREPARE = 2, READ_S = 3, WAIT_S = 4,
                     ISSUE_N = 5, WAIT_N = 6, REPORT = 7;
    localparam [3:0] N_BEGIN = 0, N_STATS = 1, N_FINALIZE = 2, N_FACTOR = 11;
    reg [2:0] state;
    reg [9:0] replay_address;
    reg [12:0] remaining;
    reg [31:0] epsilon_mantissa, epsilon_word;
    reg signed [7:0] epsilon_shift;
    reg [63:0] lane_words, narrowed;
    reg bad_lane;
    wire scan_ready, scan_done, scan_error, scan_req, scan_rsp_ready;
    wire [9:0] scan_address;
    wire [31:0] scan_tag;
    wire signed [5:0] scan_shift;
    wire [5:0] scan_extra;

    assign cmd_ready = !reset && state == IDLE && scan_ready;
    assign done_valid = !reset && state == REPORT;
    assign s_req_valid = !reset && (state == SCAN ? scan_req : state == READ_S);
    assign s_req_address = state == SCAN ? scan_address : replay_address;
    assign s_rsp_ready = !reset && (state == SCAN ? scan_rsp_ready : state == WAIT_S);
    assign n_cmd_valid = !reset && state == ISSUE_N;
    assign n_rsp_ready = !reset && state == WAIT_N;
    assign n_cmd_param = n_cmd_op == N_BEGIN ? 32'd1 : 0;
    assign n_cmd_data = n_cmd_op == N_BEGIN ? {96'd0, epsilon_word} :
                        n_cmd_op == N_STATS ? {64'd0, lane_words} : 128'd0;

    s32_rms_range_scan scan (
        .clk(clk), .reset(reset),
        .cmd_valid(cmd_valid && state == IDLE && cmd_epsilon_mantissa != 0),
        .cmd_ready(scan_ready), .cmd_base(cmd_base), .cmd_length(cmd_length),
        .cmd_baseline_shift(cmd_baseline_shift), .cmd_tag(cmd_tag),
        .done_valid(scan_done), .done_ready(state == SCAN), .done_shift(scan_shift),
        .done_extra_shift(scan_extra), .done_tag(scan_tag), .done_error(scan_error),
        .s_req_valid(scan_req), .s_req_ready(state == SCAN && s_req_ready),
        .s_req_address(scan_address), .s_rsp_valid(state == SCAN && s_rsp_valid),
        .s_rsp_ready(scan_rsp_ready), .s_rsp_data(s_rsp_data), .s_rsp_error(s_rsp_error)
    );

    function automatic signed [63:0] round_scaled(
        input signed [63:0] value, input signed [9:0] shift
    );
        reg signed [63:0] floor_q;
        reg [63:0] denominator, remainder;
        begin
            if (shift <= 0) begin
                round_scaled = value <<< $unsigned(-shift);
            end else if (shift > 63) begin
                round_scaled = 0;
            end else begin
                denominator = 64'd1 << $unsigned(shift);
                floor_q = value >>> $unsigned(shift);
                remainder = $unsigned(value) & (denominator - 64'd1);
                round_scaled = floor_q + $signed({63'd0,
                    remainder > (denominator >> 1) ||
                    (remainder == (denominator >> 1) && floor_q[0])});
            end
        end
    endfunction

    wire signed [9:0] eps_div_shift = -10'(epsilon_shift) + 10'({3'd0, done_extra_shift, 1'b0});
    wire [63:0] epsilon_scaled = $unsigned(round_scaled($signed({32'd0, epsilon_mantissa}), eps_div_shift));

    always @* begin
        narrowed = 0;
        bad_lane = 0;
        for (integer lane = 0; lane < 4; lane = lane + 1) begin
            if (remaining > 13'(lane)) begin
                automatic logic signed [63:0] value = round_scaled(
                    {{32{s_rsp_data[32*lane+31]}}, s_rsp_data[32*lane +: 32]}, 10'(done_shift));
                narrowed[16*lane +: 16] = value[15:0];
                if (value < -64'sd32768 || value > 64'sd32767) bad_lane = 1;
            end
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            replay_address <= 0;
            remaining <= 0;
            epsilon_mantissa <= 0;
            epsilon_shift <= 0;
            epsilon_word <= 0;
            lane_words <= 0;
            n_cmd_op <= 0;
            n_cmd_count <= 0;
            done_tag <= 0;
            done_shift <= 0;
            done_extra_shift <= 0;
            done_factor <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    replay_address <= cmd_base;
                    remaining <= cmd_length;
                    epsilon_mantissa <= cmd_epsilon_mantissa;
                    epsilon_shift <= cmd_epsilon_shift;
                    done_tag <= cmd_tag;
                    done_factor <= 0;
                    done_shift <= cmd_baseline_shift;
                    done_extra_shift <= 0;
                    done_error <= cmd_epsilon_mantissa == 0;
                    state <= cmd_epsilon_mantissa == 0 ? REPORT : SCAN;
                end
                SCAN: if (scan_done) begin
                    done_shift <= scan_shift;
                    done_extra_shift <= scan_extra;
                    done_error <= scan_error || scan_tag != done_tag;
                    state <= scan_error || scan_tag != done_tag ? REPORT : PREPARE;
                end
                PREPARE: begin
                    if (eps_div_shift < -10'sd31 || epsilon_scaled > 64'hffffffff) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        epsilon_word <= epsilon_scaled == 0 ? 32'd1 : epsilon_scaled[31:0];
                        n_cmd_op <= N_BEGIN;
                        n_cmd_count <= 0;
                        state <= ISSUE_N;
                    end
                end
                READ_S: if (s_req_valid && s_req_ready)
                    state <= WAIT_S;
                WAIT_S: if (s_rsp_valid && s_rsp_ready) begin
                    if (s_rsp_error || bad_lane) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        lane_words <= narrowed;
                        n_cmd_count <= remaining > 13'd4 ? 4'd4 : 4'(remaining);
                        n_cmd_op <= N_STATS;
                        state <= ISSUE_N;
                    end
                end
                ISSUE_N: if (n_cmd_valid && n_cmd_ready)
                    state <= WAIT_N;
                WAIT_N: if (n_rsp_valid && n_rsp_ready) begin
                    if (n_rsp_error || n_rsp_saturated) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        case (n_cmd_op)
                            N_BEGIN: state <= READ_S;
                            N_STATS: if (remaining > 13'd4) begin
                                remaining <= remaining - 13'd4;
                                replay_address <= replay_address + 10'd1;
                                state <= READ_S;
                            end else begin
                                n_cmd_op <= N_FINALIZE;
                                n_cmd_count <= 0;
                                state <= ISSUE_N;
                            end
                            N_FINALIZE: begin n_cmd_op <= N_FACTOR; state <= ISSUE_N; end
                            N_FACTOR: begin
                                done_factor <= 32'(round_scaled($signed({32'd0, n_rsp_factor}),
                                                                10'({4'd0, done_extra_shift})));
                                state <= REPORT;
                            end
                            default: begin done_error <= 1; state <= REPORT; end
                        endcase
                    end
                end
                REPORT: if (done_valid && done_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
