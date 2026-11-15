// Execute RMSNorm over two leased halves of U0's existing 16 KiB private SRAM.
module u_resident_rms_core (
    input wire clk, reset, svc_valid,
    output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid,
    input wire rsp_ready,
    output reg [15:0] status,
    output reg [31:0] read_bytes, write_bytes,
    output wire s_req_valid, s_req_write,
    input wire s_req_ready,
    output wire [9:0] s_req_address,
    output wire [127:0] s_req_data,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data
);
    localparam [2:0] IDLE=0, FACTOR=1, WAIT_FACTOR=2, APPLY=3, WAIT_APPLY=4, REPORT=5;
    reg [2:0] state;
    reg x_high, in_gamma, request_write;
    reg [31:0] epsilon;
    reg signed [5:0] baseline;
    reg signed [7:0] epsilon_shift, factor_shift, gamma_shift;
    wire [31:0] row_layout = descriptor[512+:32];
    wire valid_layout = (row_layout & 32'hfffffff8)==0 && row_layout[0]!=row_layout[1];
    wire valid_descriptor = valid_layout && descriptor[1023:608]==0 &&
        descriptor[583:582]=={2{descriptor[581]}} && descriptor[575:544]!=0;
    wire factor_ready, factor_done, factor_error, factor_req, factor_take;
    wire apply_ready, apply_done, apply_error, apply_req, apply_write, apply_take;
    wire [9:0] factor_address, apply_address;
    wire [31:0] factor_value;
    wire applying = state==WAIT_APPLY;
    assign svc_ready = !reset && state==IDLE;
    assign rsp_valid = !reset && state==REPORT;
    assign s_req_valid = applying ? apply_req : state==WAIT_FACTOR && factor_req;
    assign s_req_write = applying && apply_write;
    assign s_req_address = applying ?
        {apply_address[9] ^ (apply_write && !in_gamma), apply_address[8:0]} : factor_address;
    assign s_rsp_ready = applying ? apply_take : state==WAIT_FACTOR && factor_take;

    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            status<=0;
            read_bytes<=0;
            write_bytes<=0;
            request_write<=0;
        end else begin
            if (s_req_valid && s_req_ready) request_write<=s_req_write;
            if (s_rsp_valid && s_rsp_ready) begin
                if (request_write) write_bytes<=write_bytes+16;
                else read_bytes<=read_bytes+16;
            end
            case (state)
                IDLE: if (svc_valid) begin
                    x_high<=row_layout[0];
                    in_gamma<=row_layout[2]==row_layout[1];
                    epsilon<=descriptor[544+:32];
                    baseline<=descriptor[576+:6];
                    epsilon_shift<=descriptor[584+:8];
                    factor_shift<=descriptor[592+:8];
                    gamma_shift<=descriptor[600+:8];
                    read_bytes<=0;
                    write_bytes<=0;
                    status<=valid_descriptor ? 16'd0 : 16'h0220;
                    state<=valid_descriptor ? FACTOR : REPORT;
                end
                FACTOR: if (factor_ready) state<=WAIT_FACTOR;
                WAIT_FACTOR: if (factor_done) begin
                    status<=factor_error ? 16'h0222 : 16'd0;
                    state<=factor_error ? REPORT : APPLY;
                end
                APPLY: if (apply_ready) state<=WAIT_APPLY;
                WAIT_APPLY: if (apply_done) begin
                    status<=apply_error ? 16'h0222 : 16'd0;
                    state<=REPORT;
                end
                REPORT: if (rsp_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end

    wire n_valid, n_ready, n_rsp, n_take, n_error, n_sat;
    wire [3:0] n_op, n_count;
    wire [31:0] n_param;
    wire [127:0] n_data, n_result;
    s32_rms_factor_s128 factor_path (
        .clk,.reset,.cmd_valid(state==FACTOR),.cmd_ready(factor_ready),
        .cmd_base({x_high,9'b0}),.cmd_length(13'd2048),.cmd_baseline_shift(baseline),
        .cmd_epsilon_mantissa(epsilon),.cmd_epsilon_shift(epsilon_shift),.cmd_tag(32'd0),
        .done_valid(factor_done),.done_ready(state==WAIT_FACTOR),.done_factor(factor_value),
        .done_tag(),.done_shift(),.done_extra_shift(),.done_error(factor_error),
        .s_req_valid(factor_req),.s_req_ready(state==WAIT_FACTOR && s_req_ready),
        .s_req_address(factor_address),.s_rsp_valid(state==WAIT_FACTOR && s_rsp_valid),
        .s_rsp_ready(factor_take),.s_rsp_data,.s_rsp_error(1'b0),
        .n_cmd_valid(n_valid),.n_cmd_ready(n_ready),.n_cmd_op(n_op),.n_cmd_count(n_count),
        .n_cmd_param(n_param),.n_cmd_data(n_data),.n_rsp_valid(n_rsp),.n_rsp_ready(n_take),
        .n_rsp_factor(n_result[31:0]),.n_rsp_error(n_error),.n_rsp_saturated(n_sat)
    );
    block_v2_n norm (
        .clk,.reset,.cmd_valid(n_valid),.cmd_ready(n_ready),.cmd_op(n_op),.cmd_count(n_count),
        .cmd_param(n_param),.cmd_data(n_data),.cmd_aux(128'b0),.rsp_valid(n_rsp),
        .rsp_ready(n_take),.rsp_data(n_result),.rsp_error(n_error),.rsp_saturated(n_sat),.busy()
    );

    wire e_valid, e_ready, e_rsp, e_take, e_error;
    wire [63:0] e_data, e_result;
    wire [3:0] e_op, e_mask, e_clipped;
    wire [7:0] e_shift;
    wire [2:0] e_minus;
    s32_rms_apply_s128 #(.RESULT_IN_GAMMA(1'b1)) apply_path (
        .clk,.reset,.cmd_valid(state==APPLY),.cmd_ready(apply_ready),
        .cmd_x({x_high,9'b0}),.cmd_gamma({!x_high,9'b0}),.cmd_words(10'd512),
        .cmd_factor(factor_value),.cmd_factor_shift(factor_shift),.cmd_gamma_shift(gamma_shift),
        .done_valid(apply_done),.done_error(apply_error),.done_ready(applying),
        .s_req_valid(apply_req),.s_req_write(apply_write),.s_req_ready(applying && s_req_ready),
        .s_req_address(apply_address),.s_req_data,.s_rsp_valid(applying && s_rsp_valid),
        .s_rsp_error(1'b0),.s_rsp_ready(apply_take),.s_rsp_data,
        .e_in_valid(e_valid),.e_in_ready(e_ready),.e_in_data(e_data),.e_in_op(e_op),
        .e_in_mask(e_mask),.e_in_shift(e_shift),.e_in_minus(e_minus),
        .e_out_valid(e_rsp),.e_out_ready(e_take),.e_out_error(e_error),
        .e_out_data(e_result),.e_out_clipped(e_clipped)
    );
    e_s32_ap64 arithmetic (
        .clk,.reset,.in_valid(e_valid),.in_ready(e_ready),.in_data(e_data),.in_op(e_op),
        .in_mask(e_mask),.in_shift(e_shift),.in_minus(e_minus),.out_valid(e_rsp),
        .out_ready(e_take),.out_data(e_result),.out_clipped(e_clipped),.out_error(e_error)
    );
endmodule
