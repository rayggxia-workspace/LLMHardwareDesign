`timescale 1ns/1ps
// Assign a physical native64 DMA serial independently of the issuing local
// controller's command ticket. The client permits one outstanding 64 B beat.
// An exhausted serial namespace is reused only after a matched physical fence.
module native64_dma_serial_client #(
    parameter logic [30:0] SERIAL_LIMIT = 31'h7fff_ffff
) (
    input logic clk, reset,
    input logic req_valid,
    output logic req_ready,
    input logic [63:0] req_address, req_tag,
    output logic rsp_valid,
    input logic rsp_ready,
    output logic [63:0] rsp_tag,
    output logic [511:0] rsp_data,
    output logic rsp_error,
    output logic dma_valid,
    input logic dma_ready,
    output logic [63:0] dma_address,
    output logic [31:0] dma_tag,
    input logic dma_rsp_valid,
    output logic dma_rsp_ready,
    input logic [31:0] dma_rsp_tag,
    input logic [511:0] dma_rsp_data,
    output logic fence_valid,
    input logic fence_ready,
    output logic [31:0] fence_cookie,
    output logic [8:0] fence_epoch,
    input logic fence_done_valid,
    output logic fence_done_ready,
    input logic [31:0] fence_done_cookie,
    input logic [8:0] fence_done_epoch,
    output logic idle, protocol_fault
);
    typedef enum logic [1:0] {AVAILABLE, PENDING, FENCE_OFFER, FENCE_WAIT} state_t;
    state_t state;
    logic [30:0] serial;
    logic [63:0] owner_tag;
    logic [40:0] fence_identity;
    logic exhausted;
    wire match_data = dma_rsp_tag[31:1]==serial;
    wire match_fence = {fence_done_epoch,fence_done_cookie}==fence_identity;

    assign dma_valid = !reset && state==AVAILABLE && req_valid && !exhausted;
    assign req_ready = !reset && state==AVAILABLE && dma_ready && !exhausted;
    assign dma_address = req_address;
    assign dma_tag = {serial,1'b0};
    assign rsp_valid = !reset && state==PENDING && dma_rsp_valid && match_data;
    assign rsp_tag = owner_tag;
    assign rsp_data = dma_rsp_data;
    assign rsp_error = dma_rsp_tag[0];
    // Wrong/stale responses never consume the current upstream owner.
    assign dma_rsp_ready = !reset && (state!=PENDING || !match_data || rsp_ready);
    assign fence_valid = !reset && state==FENCE_OFFER;
    assign {fence_epoch,fence_cookie} = fence_identity;
    assign fence_done_ready = !reset;
    assign idle = !reset && state==AVAILABLE;

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= AVAILABLE;
            serial <= 0;
            exhausted <= 0;
            owner_tag <= 0;
            fence_identity <= 1;
            protocol_fault <= 0;
        end else begin
            if ((dma_rsp_valid && dma_rsp_ready && (state!=PENDING || !match_data)) ||
                (fence_done_valid && (state!=FENCE_WAIT || !match_fence)))
                protocol_fault <= 1;
            case (state)
                AVAILABLE: if (req_valid) begin
                    if (exhausted) state <= FENCE_OFFER;
                    else if (dma_ready) begin
                        owner_tag <= req_tag;
                        state <= PENDING;
                    end
                end
                PENDING: if (rsp_valid && rsp_ready) begin
                    if (serial==SERIAL_LIMIT) exhausted <= 1;
                    else serial <= serial + 1'b1;
                    state <= AVAILABLE;
                end
                FENCE_OFFER: if (fence_ready) state <= FENCE_WAIT;
                FENCE_WAIT: if (fence_done_valid && match_fence) begin
                    fence_identity <= fence_identity + 1'b1;
                    serial <= 0;
                    exhausted <= 0;
                    state <= AVAILABLE;
                end
                default: state <= AVAILABLE;
            endcase
        end
    end
endmodule
