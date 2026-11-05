// Adapt R256 load, native command, state-read and result-slice transactions
// to the 128-bit S client. A native result stays intact until the next command.
module ucf_r256_service (
    input wire clk, reset,
    input wire request, output reg ready,
    input wire [63:0] meta,
    input wire [127:0] operand,
    output wire response, input wire take,
    output reg [127:0] data,
    output reg error
);
    localparam [1:0] IDLE=0, WAIT_COMMAND=1, WAIT_STATE=2, RETURN=3;
    reg [1:0] phase;
    reg [511:0] native_result;
    reg native_result_valid;
    wire load_ready, cmd_ready, rd_ready, cmd_valid, rd_valid, cmd_error;
    wire [511:0] cmd_data;
    wire [127:0] rd_data;
    wire state_address_ok = meta[12:3] < 10'd64;
    wire issue = !reset && phase == IDLE && request;
    assign response = !reset && phase == RETURN;
    always @* begin
        ready = 0;
        if (!reset && phase == IDLE)
            case (meta[1:0])
                0: ready = load_ready;
                1: ready = cmd_ready;
                2: ready = !state_address_ok || rd_ready;
                3: ready = 1;
            endcase
    end

    r_stream_local #(.WORDS(256)) leaf (
        .clk(clk), .reset(reset),
        .load_valid(issue && meta[1:0] == 0), .load_ready(load_ready),
        .load_target(meta[4:2]), .load_index(meta[14:5]), .load_data(operand),
        .cmd_valid(issue && meta[1:0] == 1), .cmd_ready(cmd_ready),
        .cmd_op(meta[4:2]), .cmd_rows(meta[13:5]), .cmd_role(meta[14]),
        .cmd_clear(meta[15]), .cmd_mode(meta[17:16]),
        .rsp_valid(cmd_valid), .rsp_ready(!reset && phase == WAIT_COMMAND),
        .rsp_error(cmd_error), .rsp_data(cmd_data),
        .rd_bank(meta[2]), .rd_index(meta[12:3]), .rd_valid(issue && meta[1:0] == 2 && state_address_ok),
        .rd_ready(rd_ready), .rd_rsp_valid(rd_valid),
        .rd_rsp_ready(!reset && phase == WAIT_STATE), .rd_data(rd_data)
    );

    always @(posedge clk) begin
        if (reset) begin
            phase <= IDLE;
            native_result_valid <= 0;
        end else begin
            case (phase)
                IDLE: if (request && ready) begin
                    data <= 0;
                    error <= 0;
                    case (meta[1:0])
                        0: phase <= RETURN;
                        1: begin
                            native_result_valid <= 0;
                            phase <= WAIT_COMMAND;
                        end
                        2: begin
                            error <= !state_address_ok;
                            phase <= state_address_ok ? WAIT_STATE : RETURN;
                        end
                        3: begin
                            if (native_result_valid)
                                data <= native_result[128*int'(meta[3:2])+:128];
                            error <= !native_result_valid;
                            phase <= RETURN;
                        end
                    endcase
                end
                WAIT_COMMAND: if (cmd_valid) begin
                    native_result <= cmd_data;
                    native_result_valid <= !cmd_error;
                    data <= cmd_data[127:0];
                    error <= cmd_error;
                    phase <= RETURN;
                end
                WAIT_STATE: if (rd_valid) begin
                    data <= rd_data;
                    phase <= RETURN;
                end
                RETURN: if (take) phase <= IDLE;
            endcase
        end
    end
endmodule
