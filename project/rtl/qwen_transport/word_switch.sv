// One reserved SRAM-to-SRAM word at a time. Keep the sender pinned until
// the selected receiver reports that its SRAM write has completed.
module qwen_word_switch #(
    parameter integer SOURCES = 4,
    parameter integer SINKS = 1,
    parameter integer SRC_BITS = SOURCES > 1 ? $clog2(SOURCES) : 1,
    parameter integer DST_BITS = SINKS > 1 ? $clog2(SINKS) : 1,
    parameter logic [SOURCES*SINKS-1:0] ALLOWED = '1
) (
    input  logic clk, reset,
    input  logic command_valid,
    output logic command_ready,
    input  logic [SRC_BITS-1:0] command_source,
    input  logic [DST_BITS-1:0] command_sink,
    input  logic [9:0] command_source_addr, command_sink_addr,
    output logic response_valid, response_error,
    input  logic response_ready,
    output logic [SOURCES-1:0] tx_req, tx_take,
    output logic [SOURCES*10-1:0] tx_addr,
    input  logic [SOURCES-1:0] tx_ready, tx_valid,
    input  logic [SOURCES*128-1:0] tx_data,
    output logic [SINKS-1:0] rx_valid, rx_stored_ready,
    output logic [SINKS*10-1:0] rx_addr,
    output logic [SINKS*128-1:0] rx_data,
    input  logic [SINKS-1:0] rx_reserved, rx_ready, rx_stored
);
    typedef enum logic [2:0] { IDLE, READ_REQ, READ_DATA, WRITE_REQ, COMMIT, RESPONSE } state_t;
    state_t state;
    logic [SRC_BITS-1:0] source;
    logic [DST_BITS-1:0] sink;
    logic [9:0] source_addr, sink_addr;
    logic [127:0] word;
    logic error_latched, legal;

    always_comb begin
        legal = 1'b0;
        for (int i = 0; i < SOURCES; i++) begin
            for (int j = 0; j < SINKS; j++) begin
                if (command_source == SRC_BITS'(i) && command_sink == DST_BITS'(j))
                    legal = ALLOWED[i*SINKS+j];
            end
        end
    end

    always_comb begin
        command_ready = !reset && state == IDLE;
        response_valid = !reset && state == RESPONSE;
        response_error = response_valid && error_latched;
        tx_req = '0;
        tx_take = '0;
        tx_addr = '0;
        rx_valid = '0;
        rx_stored_ready = '0;
        rx_addr = '0;
        rx_data = '0;
        if (!reset) begin
            if (state == READ_REQ) begin
                tx_req[source] = 1'b1;
                tx_addr[10*source+:10] = source_addr;
            end
            if (state == WRITE_REQ) begin
                rx_valid[sink] = rx_reserved[sink];
                rx_addr[10*sink+:10] = sink_addr;
                rx_data[128*sink+:128] = word;
            end
            if (state == COMMIT) begin
                rx_stored_ready[sink] = tx_valid[source];
                tx_take[source] = rx_stored[sink] && tx_valid[source];
            end
        end
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            source <= '0;
            sink <= '0;
            source_addr <= '0;
            sink_addr <= '0;
            error_latched <= 1'b0;
        end else begin
            case (state)
                IDLE: if (command_valid) begin
                    error_latched <= !legal;
                    if (legal) begin
                        source <= command_source;
                        sink <= command_sink;
                        source_addr <= command_source_addr;
                        sink_addr <= command_sink_addr;
                        state <= READ_REQ;
                    end else begin
                        state <= RESPONSE;
                    end
                end
                READ_REQ: if (tx_ready[source]) state <= READ_DATA;
                READ_DATA: if (tx_valid[source]) begin
                    word <= tx_data[128*source+:128];
                    state <= WRITE_REQ;
                end
                WRITE_REQ: if (rx_reserved[sink] && rx_ready[sink]) state <= COMMIT;
                COMMIT: if (rx_stored[sink] && tx_valid[source]) state <= RESPONSE;
                RESPONSE: if (response_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
