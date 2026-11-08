// One statically connected word in flight. Release is coupled to the
// destination SRAM's commit response, not to request acceptance.
module stored_link (
    input wire clk, reset,
    input wire start,
    output wire ready,
    input wire [9:0] source_addr, destination_addr,
    output wire done,
    output wire tx_req,
    input wire tx_ready,
    output reg [9:0] tx_addr,
    input wire tx_valid,
    output wire tx_take,
    input wire [127:0] tx_data,
    output wire rx_valid,
    input wire rx_ready,
    output reg [9:0] rx_addr,
    output wire [127:0] rx_data,
    input wire rx_stored,
    output wire rx_stored_ready,
    input wire sink_reserved
);
    localparam IDLE=0, READ=1, OFFER=2, COMMIT=3;
    reg [1:0] state;
    assign ready = !reset && state==IDLE;
    assign tx_req = !reset && state==READ;
    assign rx_valid = !reset && state==OFFER && tx_valid && sink_reserved;
    assign rx_data = tx_data;
    assign rx_stored_ready = !reset && state==COMMIT && tx_valid;
    assign done = rx_stored_ready && rx_stored;
    assign tx_take = done;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            tx_addr <= 0;
            rx_addr <= 0;
        end else case (state)
            IDLE: if (start) begin
                tx_addr <= source_addr;
                rx_addr <= destination_addr;
                state <= READ;
            end
            READ: if (tx_ready) state <= OFFER;
            OFFER: if (rx_valid && rx_ready) state <= COMMIT;
            COMMIT: if (done) state <= IDLE;
        endcase
    end
endmodule
