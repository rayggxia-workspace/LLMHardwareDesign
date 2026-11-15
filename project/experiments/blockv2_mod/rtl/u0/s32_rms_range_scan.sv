// Select the finest S16 range that fits a committed S32 row after RNE.
// The caller retains the source lease for the subsequent normalization pass.
module s32_rms_range_scan (
    input wire clk, reset,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [9:0] cmd_base,
    input wire [12:0] cmd_length,
    input wire signed [5:0] cmd_baseline_shift,
    input wire [31:0] cmd_tag,
    output wire done_valid,
    input wire done_ready,
    output reg signed [5:0] done_shift,
    output reg [5:0] done_extra_shift,
    output reg [31:0] done_tag,
    output reg done_error,
    output wire s_req_valid,
    input wire s_req_ready,
    output reg [9:0] s_req_address,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data,
    input wire s_rsp_error
);
    localparam [2:0] IDLE = 0, REQUEST = 1, RESPONSE = 2, SELECT = 3, REPORT = 4;
    reg [2:0] state;
    reg [12:0] remaining;
    reg signed [31:0] low, high, next_low, next_high;

    assign cmd_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == REPORT;
    assign s_req_valid = !reset && state == REQUEST;
    assign s_rsp_ready = !reset && state == RESPONSE;
    wire [12:0] cmd_words = (cmd_length + 13'd3) >> 2;
    wire bad_command = cmd_length == 0 || cmd_length > 13'd4096 ||
                       {3'd0, cmd_base} + cmd_words > 13'd1024;

    always @* begin
        next_low = low;
        next_high = high;
        for (integer lane = 0; lane < 4; lane = lane + 1) begin
            if (remaining > 13'(lane)) begin
                if ($signed(s_rsp_data[32*lane +: 32]) < next_low)
                    next_low = $signed(s_rsp_data[32*lane +: 32]);
                if ($signed(s_rsp_data[32*lane +: 32]) > next_high)
                    next_high = $signed(s_rsp_data[32*lane +: 32]);
            end
        end
    end

    function automatic signed [63:0] rne(
        input signed [31:0] value, input signed [5:0] shift
    );
        reg signed [63:0] extended, floor_q;
        reg [63:0] modulus, remainder;
        begin
            extended = {{32{value[31]}}, value};
            if (shift <= 0) begin
                rne = extended <<< $unsigned(-shift);
            end else begin
                modulus = 64'd1 << $unsigned(shift);
                floor_q = extended >>> $unsigned(shift);
                remainder = $unsigned(extended) & (modulus - 64'd1);
                rne = floor_q + $signed({63'd0,
                    remainder > (modulus >> 1) ||
                    (remainder == (modulus >> 1) && floor_q[0])});
            end
        end
    endfunction

    wire fits = rne(low, done_shift) >= -64'sd32768 &&
                rne(high, done_shift) <= 64'sd32767;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            remaining <= 0;
            low <= 0;
            high <= 0;
            s_req_address <= 0;
            done_tag <= 0;
            done_shift <= 0;
            done_extra_shift <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    s_req_address <= cmd_base;
                    remaining <= cmd_length;
                    low <= 32'sh7fffffff;
                    high <= 32'sh80000000;
                    done_tag <= cmd_tag;
                    done_shift <= cmd_baseline_shift;
                    done_extra_shift <= 0;
                    done_error <= bad_command;
                    state <= bad_command ? REPORT : REQUEST;
                end
                REQUEST: if (s_req_valid && s_req_ready)
                    state <= RESPONSE;
                RESPONSE: if (s_rsp_valid && s_rsp_ready) begin
                    if (s_rsp_error) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        low <= next_low;
                        high <= next_high;
                        if (remaining <= 13'd4) begin
                            state <= SELECT;
                        end else begin
                            remaining <= remaining - 13'd4;
                            s_req_address <= s_req_address + 10'd1;
                            state <= REQUEST;
                        end
                    end
                end
                SELECT: if (fits) begin
                    state <= REPORT;
                end else begin
                    done_shift <= done_shift + 6'sd1;
                    done_extra_shift <= done_extra_shift + 6'd1;
                end
                REPORT: if (done_valid && done_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
