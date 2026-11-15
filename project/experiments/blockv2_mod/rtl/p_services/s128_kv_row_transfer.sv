// Transfer one resident row through native 64-byte bursts.
// Keep the SRAM window leased through done. On failure, the destination may
// be partially written and must remain unpublished.
module s128_kv_row_transfer #(
    parameter integer TAG_WIDTH = 64,
    parameter integer TAG_STEP = 1,
    parameter integer BURSTS = 8,
    parameter bit VARIABLE_BURSTS = 1'b0
)(
    input  wire clk, reset,
    input  wire cmd_valid,
    output wire cmd_ready, busy,
    input  wire [8:0] cmd_bursts,
    input  wire [9:0] cmd_sram_word,
    input  wire [63:0] cmd_ddr_address,
    input  wire [TAG_WIDTH-1:0] cmd_tag,
    output wire done_valid,
    input  wire done_ready,
    output reg  [TAG_WIDTH-1:0] done_tag,
    output reg  done_error,
    output wire burst_valid,
    input  wire burst_ready,
    output reg  [9:0] burst_sram_word,
    output reg  [63:0] burst_ddr_address,
    output reg  [TAG_WIDTH-1:0] burst_tag,
    input  wire burst_done_valid,
    output wire burst_done_ready,
    input  wire [TAG_WIDTH-1:0] burst_done_tag,
    input  wire burst_done_error
);
    localparam [1:0] IDLE=0, ISSUE=1, WAIT_BURST=2, REPORT=3;
    localparam int INDEX_BITS = BURSTS>1 ? $clog2(BURSTS) : 1;
    wire [8:0] burst_count = VARIABLE_BURSTS ? cmd_bursts : 9'(BURSTS);
    wire [TAG_WIDTH-1:0] tag_span = (TAG_WIDTH'(burst_count)-TAG_WIDTH'(1))*TAG_WIDTH'(TAG_STEP);
    reg [1:0] state;
    reg [INDEX_BITS-1:0] remaining_after_current;
    wire invalid = burst_count==0 || burst_count>9'(BURSTS) ||
                   {1'b0,cmd_sram_word}+{burst_count,2'b00}>11'd1024 ||
                   cmd_ddr_address[5:0] != 0 || cmd_ddr_address > 64'd0-(64'(burst_count)<<6) ||
                   cmd_tag > {TAG_WIDTH{1'b1}}-tag_span ||
                   (TAG_STEP == 2 && cmd_tag[0]);
    initial assert(BURSTS>=1 && BURSTS<=256);

    assign cmd_ready = !reset && state == IDLE;
    assign busy = !reset && state != IDLE;
    assign done_valid = !reset && state == REPORT;
    assign burst_valid = !reset && state == ISSUE;
    assign burst_done_ready = !reset && state == WAIT_BURST;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            remaining_after_current <= 0;
            done_tag <= 0;
            done_error <= 0;
            burst_sram_word <= 0;
            burst_ddr_address <= 0;
            burst_tag <= 0;
        end else begin
            case (state)
                IDLE: if (cmd_valid && cmd_ready) begin
                    remaining_after_current <= INDEX_BITS'(burst_count-9'd1);
                    done_tag <= cmd_tag;
                    done_error <= invalid;
                    burst_sram_word <= cmd_sram_word;
                    burst_ddr_address <= cmd_ddr_address;
                    burst_tag <= cmd_tag;
                    state <= invalid ? REPORT : ISSUE;
                end
                ISSUE: if (burst_valid && burst_ready) state <= WAIT_BURST;
                WAIT_BURST: if (burst_done_valid && burst_done_ready) begin
                    if (burst_done_error || burst_done_tag != burst_tag) begin
                        done_error <= 1;
                        state <= REPORT;
                    end else if (remaining_after_current == 0) begin
                        state <= REPORT;
                    end else begin
                        remaining_after_current <= remaining_after_current - 1'b1;
                        burst_sram_word <= burst_sram_word + 10'd4;
                        burst_ddr_address <= burst_ddr_address + 64'd64;
                        burst_tag <= burst_tag + TAG_WIDTH'(TAG_STEP);
                        state <= ISSUE;
                    end
                end
                REPORT: if (done_valid && done_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
