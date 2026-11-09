// Isolated Issue247 candidate. Same transaction interface as the production
// arbiter. Priority is a local-client class, NOT a DMA or address inference.
module popt_s_policy_arbiter #(
    parameter integer CLIENTS = 4,
    parameter integer OWNER_BITS = CLIENTS > 1 ? $clog2(CLIENTS) : 1,
    parameter bit POLICY_ENABLE = 1'b0,
    parameter [CLIENTS-1:0] CONSUMER_MASK = CLIENTS'(12),
    parameter integer MAX_CONSUMER_BURST = 2
) (
    input wire clk, reset,
    input wire [CLIENTS-1:0] req_valid, req_write,
    input wire [CLIENTS*10-1:0] req_addr,
    input wire [CLIENTS*128-1:0] req_data,
    output wire [CLIENTS-1:0] req_ready, rsp_valid,
    input wire [CLIENTS-1:0] rsp_ready,
    output wire [CLIENTS*128-1:0] rsp_data,
    output wire mem_req, mem_write,
    output wire [9:0] mem_addr,
    output wire [127:0] mem_data,
    input wire mem_ready, mem_valid,
    input wire [127:0] mem_result,
    output wire mem_take, busy
);
    generate if (!POLICY_ENABLE) begin: legacy
        // Preserve the old default including the exact ready/response cycles.
        block_local_s_arbiter #(.CLIENTS(CLIENTS), .OWNER_BITS(OWNER_BITS)) arbiter(
            .clk, .reset, .req_valid, .req_write, .req_addr, .req_data,
            .req_ready, .rsp_valid, .rsp_ready, .rsp_data,
            .mem_req, .mem_write, .mem_addr, .mem_data,
            .mem_ready, .mem_valid, .mem_result, .mem_take, .busy
        );
    end else begin: preferred
        localparam integer BURST_BITS = MAX_CONSUMER_BURST > 1 ?
                                         $clog2(MAX_CONSUMER_BURST+1) : 1;
        localparam [1:0] IDLE=0, SEND=1, RETURN=2;
        reg [1:0] state;
        reg [OWNER_BITS-1:0] owner, consumer_next, external_next;
        reg [BURST_BITS-1:0] consumer_streak;
        reg saved_write;
        reg [9:0] saved_addr;
        reg [127:0] saved_data;
        reg have_consumer, have_external, selected_consumer, found;
        reg [OWNER_BITS-1:0] selected, consumer_choice, external_choice;
        reg [CLIENTS-1:0] ready_bits, response_bits;
        reg [CLIENTS*128-1:0] response_data;
        integer consumer_index, external_index;

        // Separate round-robin cursors are necessary: sharing a cursor between
        // the two classes can starve one consumer after every forced IO grant.
        always @* begin
            have_consumer=0; have_external=0;
            consumer_choice=0; external_choice=0;
            consumer_index=0; external_index=0;
            for (integer offset=0; offset<CLIENTS; offset=offset+1) begin
                consumer_index=int'(consumer_next)+offset;
                external_index=int'(external_next)+offset;
                if (consumer_index>=CLIENTS) consumer_index=consumer_index-CLIENTS;
                if (external_index>=CLIENTS) external_index=external_index-CLIENTS;
                if (!have_consumer && CONSUMER_MASK[consumer_index] && req_valid[consumer_index]) begin
                    have_consumer=1;
                    consumer_choice=OWNER_BITS'(consumer_index);
                end
                if (!have_external && !CONSUMER_MASK[external_index] && req_valid[external_index]) begin
                    have_external=1;
                    external_choice=OWNER_BITS'(external_index);
                end
            end
            selected_consumer=have_consumer &&
                (!have_external || consumer_streak<BURST_BITS'(MAX_CONSUMER_BURST));
            selected=selected_consumer ? consumer_choice : external_choice;
            found=have_consumer || have_external;
            ready_bits=0; response_bits=0; response_data=0;
            if (!reset) begin
                if (state==IDLE && found) ready_bits[selected]=1;
                if (state==RETURN) begin
                    response_bits[owner]=mem_valid;
                    response_data[128*int'(owner)+:128]=mem_result;
                end
            end
        end
        assign req_ready=ready_bits;
        assign rsp_valid=response_bits;
        assign rsp_data=response_data;
        assign mem_req=!reset && state==SEND;
        assign mem_write=saved_write;
        assign mem_addr=saved_addr;
        assign mem_data=saved_data;
        assign mem_take=!reset && state==RETURN && rsp_ready[owner];
        assign busy=state!=IDLE;

        always @(posedge clk) begin
            if (reset) begin
                state<=IDLE; owner<=0; consumer_next<=0; external_next<=0;
                consumer_streak<=0; saved_write<=0; saved_addr<=0; saved_data<=0;
            end else case (state)
                IDLE: if (found) begin
                    owner<=selected;
                    saved_write<=req_write[selected];
                    saved_addr<=req_addr[10*int'(selected)+:10];
                    saved_data<=req_data[128*int'(selected)+:128];
                    if (selected_consumer) begin
                        consumer_next<=selected==OWNER_BITS'(CLIENTS-1) ? OWNER_BITS'(0) : selected+1'b1;
                        // Count only a consumer grant that bypasses pending IO.
                        if (have_external) consumer_streak<=consumer_streak+1'b1;
                        else consumer_streak<=0;
                    end else begin
                        external_next<=selected==OWNER_BITS'(CLIENTS-1) ? OWNER_BITS'(0) : selected+1'b1;
                        consumer_streak<=0;
                    end
                    state<=SEND;
                end
                SEND: if (mem_ready) state<=RETURN;
                RETURN: if (mem_valid && rsp_ready[owner]) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
        initial begin
            if (CLIENTS<1 || MAX_CONSUMER_BURST<1)
                $fatal(1,"invalid policy arbiter parameters");
        end
    end endgenerate
endmodule
