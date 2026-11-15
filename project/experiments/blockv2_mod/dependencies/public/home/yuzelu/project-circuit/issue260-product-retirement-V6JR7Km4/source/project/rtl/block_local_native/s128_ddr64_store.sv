// Gather one 64-byte write from four consecutive words of a private S128.
module s128_ddr64_store (
    input  wire         clk, reset,

    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire [9:0]   cmd_source_word,
    input  wire [63:0]  cmd_ddr_address, cmd_tag,
    output wire         done_valid,
    input  wire         done_ready,
    output reg  [63:0]  done_tag,
    output reg          done_error,

    output wire         s_req_valid,
    input  wire         s_req_ready,
    output wire [9:0]   s_req_address,
    input  wire         s_rsp_valid,
    output wire         s_rsp_ready,
    input  wire [127:0] s_rsp_data,
    input  wire         s_rsp_error,

    output wire         wr_valid,
    input  wire         wr_ready,
    output reg  [63:0]  wr_address, wr_tag,
    output reg  [511:0] wr_data,
    input  wire         wr_done_valid,
    output wire         wr_done_ready,
    input  wire [63:0]  wr_done_tag,
    input  wire         wr_done_error
);
    localparam [2:0] IDLE = 0, READ_WORD = 1, WAIT_WORD = 2, SEND = 3, WAIT_WRITE = 4, REPORT = 5;
    reg [2:0] state;
    reg [9:0] source_word;
    reg [1:0] word_index;

    assign cmd_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == REPORT;
    assign s_req_valid = !reset && state == READ_WORD;
    assign s_req_address = source_word + {8'd0, word_index};
    assign s_rsp_ready = !reset && state == WAIT_WORD;
    assign wr_valid = !reset && state == SEND;
    assign wr_done_ready = !reset && state == WAIT_WRITE;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            source_word <= 0;
            word_index <= 0;
            wr_address <= 0;
            wr_tag <= 0;
            wr_data <= 0;
            done_tag <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    done_tag <= cmd_tag;
                    done_error <= cmd_ddr_address[5:0] != 0 || cmd_source_word > 10'd1020;
                    if (cmd_ddr_address[5:0] != 0 || cmd_source_word > 10'd1020) begin
                        state <= REPORT;
                    end else begin
                        source_word <= cmd_source_word;
                        word_index <= 0;
                        wr_address <= cmd_ddr_address;
                        wr_tag <= cmd_tag;
                        state <= READ_WORD;
                    end
                end
                READ_WORD: if (s_req_valid && s_req_ready)
                    state <= WAIT_WORD;
                WAIT_WORD: if (s_rsp_valid && s_rsp_ready) begin
                    if (s_rsp_error) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else begin
                        wr_data[128*word_index +: 128] <= s_rsp_data;
                        word_index <= word_index + 2'd1;
                        state <= word_index == 2'd3 ? SEND : READ_WORD;
                    end
                end
                SEND: if (wr_valid && wr_ready)
                    state <= WAIT_WRITE;
                WAIT_WRITE: if (wr_done_valid && wr_done_ready) begin
                    // The fabric drives this input only for committed or failed writes.
                    done_error <= wr_done_error || wr_done_tag != wr_tag;
                    state <= REPORT;
                end
                REPORT: if (done_valid && done_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
