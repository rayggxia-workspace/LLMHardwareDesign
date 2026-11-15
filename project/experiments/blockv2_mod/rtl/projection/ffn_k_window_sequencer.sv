`timescale 1ns/1ps
// Drive the existing three-P K-window protocol from one accepted K-range command.
module ffn_k_window_sequencer #(
    parameter logic [15:0] INITIAL_GENERATION = 0,
    parameter bit RESET_GENERATION_ON_COMMAND = 0,
    parameter bit RANGED_COMMAND = 0
)(
    input  logic clk, reset, namespace_rearm,
    input  logic command_valid,
    output logic command_ready,
    input  logic [6:0] command_tiles,
    input logic [15:0] command_first_k,
    input  logic command_quantize, command_early,
    input  logic need_match, need_bad_owner, previous_drained,
    output logic [15:0] tile_k, tile_generation,
    output logic [31:0] tile_ticket,
    output logic quant_valid,
    input  logic quant_ready, quant_done, quant_bad, publish_ready,
    output logic quant_take,
    input  logic shift_valid, header_idle, source_idle,
    input  logic [2:0] lease_ready,
    output logic lease_start,
    output logic header_valid,
    input  logic header_ready, header_done, header_bad,
    output logic header_take,
    output logic copy_valid,
    input  logic copy_ready, copy_done, copy_bad,
    output logic copy_take,
    input  logic [2:0] proof_valid,
    input  logic proof_bad,
    output logic proof_take,
    input  logic [2:0] release_ready,
    output logic lease_release,
    output logic done_valid, done_error,
    input  logic done_ready
);
    typedef enum logic [3:0] {
        IDLE, NEED, QUANT_REQ, QUANT_DONE, LEASE, HEADER_REQ, HEADER_DONE,
        COPY_REQ, COPY_DONE, PROOF, RELEASE, DONE
    } state_t;
    state_t state;
    logic quantize, early;
    logic [6:0] tiles_remaining;
    wire use_early = early && tile_k != 0;

    assign command_ready = !reset && !namespace_rearm && state == IDLE;
    assign quant_valid = !reset && state == QUANT_REQ;
    assign quant_take = !reset && state == QUANT_DONE && (quant_bad || publish_ready);
    // All three destinations accept the same lease and release on one edge.
    assign lease_start = !reset && state == LEASE && shift_valid && header_idle &&
                         source_idle && (&lease_ready);
    assign header_valid = !reset && state == HEADER_REQ;
    assign header_take = !reset && state == HEADER_DONE;
    assign copy_valid = !reset && state == COPY_REQ;
    assign copy_take = !reset && state == COPY_DONE;
    assign proof_take = !reset && state == PROOF && (&proof_valid) && !proof_bad;
    assign lease_release = !reset && state == RELEASE && (&release_ready);
    assign done_valid = !reset && state == DONE;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            tile_k <= 0;
            tile_generation <= INITIAL_GENERATION;
            tile_ticket <= 0;
            quantize <= 0;
            early <= 0;
            tiles_remaining <= 0;
            done_error <= 0;
        end else if (namespace_rearm) begin
`ifndef SYNTHESIS
            assert (state == IDLE) else $fatal(1, "K-window rearm before drain");
`endif
            tile_generation <= 0;
        end else begin
            case (state)
                IDLE: if (command_valid && command_ready) begin
                    tile_k <= RANGED_COMMAND ? command_first_k : 16'd0;
                    if (RESET_GENERATION_ON_COMMAND) begin tile_generation <= 0; tile_ticket <= 0; end
                    tiles_remaining <= command_tiles;
                    quantize <= command_quantize;
                    early <= command_early;
                    done_error <= command_tiles == 0;
                    state <= command_tiles == 0 ? DONE : NEED;
                end
                NEED: if (!use_early && need_bad_owner) begin
                    done_error <= 1;
                    state <= DONE;
                end else if (use_early ? previous_drained : need_match) begin
                    // Zero is reserved. This source must be reset/rebased before
                    // wrapping either identity instead of aliasing an old tile.
                    if ((&tile_generation) || (&tile_ticket)) begin
                        done_error <= 1;
                        state <= DONE;
                    end else begin
                        tile_generation <= tile_generation + 1'b1;
                        tile_ticket <= tile_ticket + 1'b1;
                        state <= quantize ? QUANT_REQ : LEASE;
                    end
                end
                QUANT_REQ: if (quant_valid && quant_ready) state <= QUANT_DONE;
                QUANT_DONE: if (quant_done && quant_take) begin
                    done_error <= quant_bad;
                    state <= quant_bad ? DONE : LEASE;
                end
                LEASE: if (lease_start) state <= HEADER_REQ;
                HEADER_REQ: if (header_valid && header_ready) state <= HEADER_DONE;
                HEADER_DONE: if (header_done && header_take) begin
                    done_error <= header_bad;
                    state <= header_bad ? DONE : COPY_REQ;
                end
                COPY_REQ: if (copy_valid && copy_ready) state <= COPY_DONE;
                COPY_DONE: if (copy_done && copy_take) begin
                    done_error <= copy_bad;
                    state <= copy_bad ? DONE : PROOF;
                end
                PROOF: if (&proof_valid) begin
                    done_error <= proof_bad;
                    state <= proof_bad ? DONE : RELEASE;
                end
                RELEASE: if (lease_release) begin
                    tiles_remaining <= tiles_remaining - 1'b1;
                    if (tiles_remaining == 1) state <= DONE;
                    else begin
                        tile_k <= tile_k + 16'd128;
                        state <= NEED;
                    end
                end
                // A failed live protocol keeps ownership until coordinated reset.
                DONE: if (done_ready && !done_error) state <= IDLE;
                default: begin
                    done_error <= 1;
                    state <= DONE;
                end
            endcase
        end
    end
endmodule
