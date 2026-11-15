`timescale 1ns/1ps
// Fetch one 8 KiB activation into U.S using actual reads and write ACKs.
module ffn_x_ddr_load #(
    parameter bit RELEASE_ON_ERROR = 1'b0
) (
    input  logic clk, reset,
    input  logic launch_valid,
    output logic launch_ready,
    input  logic [63:0] launch_base,
    output logic done_valid, done_error,
    input  logic done_ready,
    output logic rd_valid,
    input  logic rd_ready,
    output logic [63:0] rd_address, rd_tag,
    input  logic rd_rsp_valid,
    output logic rd_rsp_ready,
    input  logic [63:0] rd_rsp_tag,
    input  logic [511:0] rd_rsp_data,
    output logic s_valid,
    input  logic s_ready,
    output logic [8:0] s_address,
    output logic [127:0] s_data,
    output logic [31:0] s_tag,
    input  logic s_rsp_valid,
    output logic s_rsp_ready,
    input  logic [31:0] s_rsp_tag
);
    typedef enum logic [2:0] {IDLE, READ, READ_WAIT, STORE, STORE_WAIT, DONE} state_t;
    state_t state;
    logic [63:0] base;
    logic [6:0] burst;
    logic [1:0] word;
    logic [511:0] data;

    assign launch_ready = !reset && state == IDLE;
    assign done_valid = !reset && state == DONE;
    assign rd_valid = !reset && state == READ;
    assign rd_address = base + {51'd0, burst, 6'd0};
    assign rd_tag = {57'd0, burst};
    assign rd_rsp_ready = !reset && state == READ_WAIT;
    assign s_valid = !reset && state == STORE;
    assign s_address = {burst, word};
    assign s_data = data[word*128+:128];
    assign s_tag = {23'h254000, s_address};
    assign s_rsp_ready = !reset && state == STORE_WAIT;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            base <= 0;
            burst <= 0;
            word <= 0;
            data <= 0;
            done_error <= 0;
        end else begin
            case (state)
                IDLE: if (launch_valid && launch_ready) begin
                    base <= launch_base;
                    burst <= 0;
                    word <= 0;
                    done_error <= launch_base[5:0] != 0 || launch_base > 64'hffff_ffff_ffff_e000;
                    state <= launch_base[5:0] != 0 || launch_base > 64'hffff_ffff_ffff_e000 ? DONE : READ;
                end
                READ: if (rd_ready) state <= READ_WAIT;
                READ_WAIT: if (rd_rsp_valid && rd_rsp_ready) begin
                    data <= rd_rsp_data;
                    done_error <= rd_rsp_tag != rd_tag;
                    state <= rd_rsp_tag == rd_tag ? STORE : DONE;
                end
                STORE: if (s_valid && s_ready) state <= STORE_WAIT;
                STORE_WAIT: if (s_rsp_valid && s_rsp_ready) begin
                    if (s_rsp_tag != s_tag) begin
                        done_error <= 1;
                        state <= DONE;
                    end else if (&word) begin
                        word <= 0;
                        if (&burst) state <= DONE;
                        else begin
                            burst <= burst + 1'b1;
                            state <= READ;
                        end
                    end else begin
                        word <= word + 1'b1;
                        state <= STORE;
                    end
                end
                DONE: if (done_ready && (!done_error || RELEASE_ON_ERROR)) state <= IDLE;
                default: begin
                    done_error <= 1;
                    state <= DONE;
                end
            endcase
        end
    end
endmodule
