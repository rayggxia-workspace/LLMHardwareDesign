// Joint base transport admission. Status inputs are synchronous to clk.
module native_joint_drain #(
    parameter integer LOCAL_LINKS = 6,
    parameter integer P_CONTROLLERS = 3,
    parameter integer DDR_LANES = 4,
    parameter integer GENERATION_WIDTH = 32
) (
    input wire clk, reset,
    input wire admission_closed,
    input wire switch_idle, dma_transport_quiescent,
    input wire [P_CONTROLLERS-1:0] p_idle, p_window_idle, p_copy_ack_drained,
    input wire [LOCAL_LINKS-1:0] local_link_drained,
    input wire relay_queues_empty,
    input wire [DDR_LANES-1:0] ddr_queues_empty,
    input wire ddr_request_pending, ddr_response_pending,
    input wire purge_request_fire, purge_response_fire,
    input wire [GENERATION_WIDTH-1:0] purge_request_generation, purge_response_generation,
    input wire [GENERATION_WIDTH-1:0] current_dma_generation,
    output wire transport_drained
);
    reg purge_pending, verified_generation;
    reg [GENERATION_WIDTH-1:0] expected_generation, last_verified_generation;

    // The DMA contract holds a single accepted purge until the corresponding
    // backend response. Match its generation during cold boot and re-arm.
    always @(posedge clk) begin
        if (reset) begin
            purge_pending <= 1'b0;
            verified_generation <= 1'b0;
            expected_generation <= '0;
            last_verified_generation <= '0;
        end else if (purge_request_fire) begin
            purge_pending <= 1'b1;
            verified_generation <= 1'b0;
            expected_generation <= purge_request_generation;
        end else if (purge_response_fire && purge_pending &&
                     purge_response_generation == expected_generation) begin
            purge_pending <= 1'b0;
            verified_generation <= 1'b1;
            last_verified_generation <= purge_response_generation;
        end
    end

    // DMA p_mode_client_drained and local COPY use separate ownership proofs.
    assign transport_drained = !reset && admission_closed &&
        switch_idle && dma_transport_quiescent && (&p_idle) &&
        (&p_window_idle) && (&p_copy_ack_drained) && (&local_link_drained) &&
        relay_queues_empty && (&ddr_queues_empty) &&
        !ddr_request_pending && !ddr_response_pending &&
        !purge_pending && !purge_request_fire && !purge_response_fire &&
        verified_generation && current_dma_generation == last_verified_generation;
endmodule
