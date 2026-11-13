`timescale 1ns/1ps

// Native MC/LC record transport for one global target. The LC consumes a
// checked task on the very edge that accepts its fourth physical flit.
module lc_packet128_bridge #(
    parameter logic [7:0] GLOBAL_TARGET = 0,
    parameter bit REGISTER_FINAL_BEAT = 1'b0
) (
    input  logic clk, reset,
    input  logic rx_valid, rx_sop, rx_eop, rx_credit,
    input  logic [127:0] rx_data,
    input  logic [7:0] rx_target,
    output logic rx_ready,
    output logic native_task_valid, native_task_credit,
    output logic [511:0] native_task,
    input  logic native_task_ready,
    input  logic native_event_valid,
    input  logic [511:0] native_event,
    output logic native_event_ready,
    output logic tx_valid, tx_sop, tx_eop,
    output logic [127:0] tx_data,
    input  logic tx_ready,
    output logic drained,
    output logic [31:0] frame_fault_count
);
    typedef enum logic [2:0] {FIRST, SECOND, THIRD, FOURTH, DROP} rx_state_t;
    rx_state_t state;
    logic [383:0] prefix;
    logic credit;
    logic tx_drained;
    logic [7:0] unused_tx_target;
    logic unused_tx_credit, unused_rx_ready, unused_return_valid;
    logic [511:0] unused_return_packet;
    logic [31:0] unused_rx_fault_count;

    wire target_ok = rx_target == GLOBAL_TARGET;
    wire first_ok = rx_sop && !rx_eop && target_ok &&
                    rx_data[24+:8] == GLOBAL_TARGET && rx_data[0+:16] == 16'd2 &&
                    rx_data[16+:8] == (rx_credit ? 8'd0 : 8'd1);
    wire continuation_ok = !rx_sop && target_ok && rx_credit == credit &&
                           rx_eop == (state == FOURTH);
    wire rx_fire = rx_valid && rx_ready;

    wire complete_frame = rx_valid && state == FOURTH && continuation_ok;
    // VALID is independent of the LC's READY. The physical EOP and the LC
    // accept the command on the same edge in both modes.
    if (REGISTER_FINAL_BEAT) begin : buffered_final
        logic captured;
        logic [127:0] suffix;

        // While EOP is stalled, its producer holds the flit stable. Register
        // the payload before acknowledging it to cut the physical input path.
        always_ff @(posedge clk) begin
            if (reset || rx_fire || !complete_frame) captured <= 1'b0;
            else if (!captured) begin
                suffix <= rx_data;
                captured <= 1'b1;
            end
        end

        assign native_task_valid = !reset && complete_frame && captured;
        assign native_task = {suffix, prefix};
        assign rx_ready = !reset && (!complete_frame || (captured && native_task_ready));
    end else begin : direct_final
        assign native_task_valid = !reset && complete_frame;
        assign native_task = {rx_data, prefix};
        assign rx_ready = !reset && (!complete_frame || native_task_ready);
    end
    assign native_task_credit = credit;
    assign drained = !reset && state == FIRST && !rx_valid && tx_drained;

    // Event serialization has the exact MC transmitter contract. Its unused
    // receiver is inactive. The physical switch provides the return source.
    mc_packet128_bridge event_tx (
        .clk, .reset,
        .core_task_valid(native_event_valid), .core_task_ready(native_event_ready),
        .core_task_packet(native_event), .core_task_target(GLOBAL_TARGET), .core_task_credit(1'b0),
        .tx_valid, .tx_ready, .tx_data, .tx_target(unused_tx_target),
        .tx_sop, .tx_eop, .tx_credit(unused_tx_credit),
        .rx_valid(1'b0), .rx_ready(unused_rx_ready), .rx_data(128'b0), .rx_source(8'b0),
        .rx_sop(1'b0), .rx_eop(1'b0),
        .core_return_valid(unused_return_valid), .core_return_ready(1'b0),
        .core_return_packet(unused_return_packet), .drained(tx_drained),
        .frame_fault_count(unused_rx_fault_count)
    );

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= FIRST;
            credit <= 0;
            frame_fault_count <= 0;
        end else if (rx_fire) begin
            if (state == DROP) begin
                if (rx_eop) state <= FIRST;
            end else if ((state == FIRST && !first_ok) ||
                         (state != FIRST && !continuation_ok)) begin
                // One diagnostic per rejected frame. No task is offered,
                // and remaining flits cannot become a new owner before EOP.
                state <= rx_eop ? FIRST : DROP;
                if (frame_fault_count != 32'hffffffff)
                    frame_fault_count <= frame_fault_count + 1'b1;
            end else begin
                case (state)
                    FIRST: begin
                        prefix[0+:128] <= rx_data;
                        credit <= rx_credit;
                        state <= SECOND;
                    end
                    SECOND: begin
                        prefix[128+:128] <= rx_data;
                        state <= THIRD;
                    end
                    THIRD: begin
                        prefix[256+:128] <= rx_data;
                        state <= FOURTH;
                    end
                    FOURTH: state <= FIRST;
                    default: state <= DROP;
                endcase
            end
        end
    end
endmodule
