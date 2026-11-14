`timescale 1ns/1ps
// Start the installed Gather page to obtain its LINK_RECEIVE reservation.
// Stage only the input token from the request sequencer's accepted page.
module native_request_index_gate (
    input logic clk, reset,
    input logic page_valid,
    output logic page_ready,
    input logic [31:0] page_generation, page_input_token,
    input logic page_uses_index,
    input logic [9:0] page_index_word,
    output logic launch_valid,
    input logic launch_ready,

    input logic executor_done_valid,
    output logic executor_done_ready,
    input logic [31:0] executor_done_generation,
    input logic executor_done_error,
    output logic page_done_valid,
    input logic page_done_ready,
    output logic [31:0] page_done_generation,
    output logic page_done_error,

    input logic reservation_valid,
    input logic [9:0] reservation_word,
    output logic s_valid,
    input logic s_ready,
    output logic [9:0] s_word,
    output logic [127:0] s_data,
    output logic [31:0] s_tag,
    input logic ack_valid,
    output logic ack_ready,
    input logic [31:0] ack_tag,
    input logic ack_error,
    output logic index_fault
);
    typedef enum logic [2:0] {IDLE, RESERVE, WRITE_INDEX, COMMITTED, FAILED} state_t;
    state_t state;
    logic [31:0] generation, token;
    logic [9:0] word;
    logic index_ready, index_done, index_error;
    wire matching_terminal=executor_done_generation==generation;
    wire terminal_before_commit=matching_terminal &&
                                (state==RESERVE || (state==WRITE_INDEX && !(index_done && !index_error)));
    wire index_launch=state==RESERVE && reservation_valid && reservation_word==word;

    assign launch_valid=!reset && state==IDLE && page_valid;
    assign page_ready=!reset && state==IDLE && launch_ready;
    assign page_done_valid=executor_done_valid || index_fault;
    assign executor_done_ready=page_done_ready;
    assign page_done_generation=index_fault ? generation : executor_done_generation;
    assign page_done_error=index_fault || executor_done_error || terminal_before_commit;
    assign index_fault=state==FAILED;

    native_retired_token_index writer(
        .clk,.reset,.request_valid(index_launch),.request_ready(index_ready),
        .request_generation(generation),.request_token(token),.request_word(word),
        .s_valid,.s_ready,.s_word,.s_data,.s_tag,.ack_valid,.ack_ready,.ack_tag,.ack_error,
        .done_valid(index_done),.done_ready(1'b1),.done_error(index_error));

    always_ff @(posedge clk) begin
        if(reset) begin
            state<=IDLE;
            generation<=0;
            token<=0;
            word<=0;
        end else if(executor_done_valid && executor_done_ready && matching_terminal && state!=IDLE) begin
            // A terminal from a failed or premature Gather requires fabric reset.
            state<=page_done_error ? FAILED : IDLE;
        end else begin
            case(state)
                IDLE: if(page_valid && page_ready && page_uses_index) begin
                    generation<=page_generation;
                    token<=page_input_token;
                    word<=page_index_word;
                    state<=RESERVE;
                end
                RESERVE: if(reservation_valid) begin
                    if(reservation_word!=word) state<=FAILED;
                    else if(index_ready) state<=WRITE_INDEX;
                end
                WRITE_INDEX: if(index_done) state<=index_error ? FAILED : COMMITTED;
                COMMITTED, FAILED: begin end
                default: state<=FAILED;
            endcase
        end
    end
endmodule
