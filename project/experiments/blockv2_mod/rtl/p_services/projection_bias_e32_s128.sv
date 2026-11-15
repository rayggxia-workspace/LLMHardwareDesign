// Add four projection and bias S32 values with the same binary exponent.
// The caller retains both source leases and the destination through done.
// Bias quantization is performed when building the DDR image.
module projection_bias_e32_s128 (
    input  wire clk, reset,
    input  wire cmd_valid,
    output wire cmd_ready,
    input  wire [9:0] cmd_projection, cmd_bias, cmd_dst,
    input  wire [31:0] cmd_tag,
    output wire busy, done_valid,
    input  wire done_ready,
    output reg  [31:0] done_tag,
    output reg  [3:0] done_clipped,
    output reg  done_error,

    output wire s_req_valid,
    input  wire s_req_ready,
    output wire s_req_write,
    output wire [9:0] s_req_address,
    output reg  [127:0] s_req_data,
    input  wire s_rsp_valid,
    output wire s_rsp_ready,
    input  wire [127:0] s_rsp_data,
    input  wire s_rsp_error,

    output wire e_in_valid,
    input  wire e_in_ready,
    output wire [63:0] e_in_data,
    output wire [3:0] e_in_op, e_in_mask,
    output wire [7:0] e_in_shift,
    output wire [2:0] e_in_minus,
    input  wire e_out_valid,
    output wire e_out_ready,
    input  wire [63:0] e_out_data,
    input  wire [3:0] e_out_clipped,
    input  wire e_out_error
);
    localparam [3:0] IDLE=0, READ_PROJECTION=1, WAIT_PROJECTION=2, READ_BIAS=3,
                     WAIT_BIAS=4, SEND_E=5, WAIT_E=6, WRITE_S=7, WAIT_WRITE=8, REPORT=9;
    reg [3:0] state;
    reg [9:0] projection_address, bias_address, dst_address;
    reg [127:0] projection, bias;
    reg [1:0] input_beat;
    reg high_result;
    wire [127:0] operand = input_beat[1] ? bias : projection;

    assign cmd_ready = !reset && state==IDLE;
    assign busy = !reset && state!=IDLE;
    assign done_valid = !reset && state==REPORT;
    assign s_req_valid = !reset && (state==READ_PROJECTION || state==READ_BIAS || state==WRITE_S);
    assign s_req_write = state==WRITE_S;
    assign s_req_address = state==READ_PROJECTION ? projection_address :
                           state==READ_BIAS ? bias_address : dst_address;
    assign s_rsp_ready = !reset && (state==WAIT_PROJECTION || state==WAIT_BIAS || state==WAIT_WRITE);

    assign e_in_valid = !reset && state==SEND_E;
    assign e_out_ready = !reset && state==WAIT_E;
    assign e_in_data = input_beat[0] ? operand[127:64] : operand[63:0];
    assign e_in_op = 4'd0;  // ADD2
    assign e_in_mask = 4'hf;
    assign e_in_shift = 0;
    assign e_in_minus = 0;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            projection_address <= 0;
            bias_address <= 0;
            dst_address <= 0;
            projection <= 0;
            bias <= 0;
            input_beat <= 0;
            high_result <= 0;
            s_req_data <= 0;
            done_tag <= 0;
            done_clipped <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    projection_address <= cmd_projection;
                    bias_address <= cmd_bias;
                    dst_address <= cmd_dst;
                    done_tag <= cmd_tag;
                    done_clipped <= 0;
                    done_error <= 0;
                    state <= READ_PROJECTION;
                end
                READ_PROJECTION: if (s_req_valid && s_req_ready) state <= WAIT_PROJECTION;
                WAIT_PROJECTION: if (s_rsp_valid && s_rsp_ready) begin
                    projection <= s_rsp_data;
                    done_error <= s_rsp_error;
                    state <= s_rsp_error ? REPORT : READ_BIAS;
                end
                READ_BIAS: if (s_req_valid && s_req_ready) state <= WAIT_BIAS;
                WAIT_BIAS: if (s_rsp_valid && s_rsp_ready) begin
                    bias <= s_rsp_data;
                    input_beat <= 0;
                    high_result <= 0;
                    done_error <= s_rsp_error;
                    state <= s_rsp_error ? REPORT : SEND_E;
                end
                SEND_E: if (e_in_valid && e_in_ready) begin
                    if (input_beat==3) state <= WAIT_E;
                    else input_beat <= input_beat + 2'd1;
                end
                WAIT_E: if (e_out_valid && e_out_ready) begin
                    done_error <= done_error || e_out_error;
                    done_clipped <= done_clipped | e_out_clipped;
                    if (high_result) begin
                        s_req_data[127:64] <= e_out_data;
                        state <= (done_error || e_out_error) ? REPORT : WRITE_S;
                    end else begin
                        s_req_data[63:0] <= e_out_data;
                        high_result <= 1;
                    end
                end
                WRITE_S: if (s_req_valid && s_req_ready) state <= WAIT_WRITE;
                WAIT_WRITE: if (s_rsp_valid && s_rsp_ready) begin
                    done_error <= s_rsp_error;
                    state <= REPORT;
                end
                REPORT: if (done_valid && done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
