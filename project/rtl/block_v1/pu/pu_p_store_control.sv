// A pending feeder job closes ordinary admission, then waits for the current
// ordinary response to retire. The actual SRAM feeder completion reopens it.
module pu_p_store_control #(
    parameter integer CLIENTS = 4
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
    output wire mem_take,
    input wire load_valid,
    output wire load_ready,
    output wire store_load_valid,
    input wire store_load_ready,
    input wire store_done_valid, store_done_error,
    output wire store_done_take,
    output wire load_done_valid, load_done_error,
    input wire load_done_take
);
    reg feeder_active;
    wire ordinary_busy;
    wire ordinary_admit = !load_valid && !feeder_active;

    block_local_s_arbiter #(.CLIENTS(CLIENTS)) ordinary (
        .clk(clk), .reset(reset),
        .req_valid(req_valid & {CLIENTS{ordinary_admit}}),
        .req_write(req_write), .req_addr(req_addr), .req_data(req_data),
        .req_ready(req_ready), .rsp_valid(rsp_valid),
        .rsp_ready(rsp_ready), .rsp_data(rsp_data),
        .mem_req(mem_req), .mem_write(mem_write), .mem_addr(mem_addr),
        .mem_data(mem_data), .mem_ready(mem_ready), .mem_valid(mem_valid),
        .mem_result(mem_result), .mem_take(mem_take), .busy(ordinary_busy)
    );

    wire can_load = !reset && !ordinary_busy && !feeder_active;
    assign load_ready = can_load && store_load_ready;
    assign store_load_valid = can_load && load_valid;
    assign load_done_valid = !reset && feeder_active && store_done_valid;
    assign load_done_error = load_done_valid && store_done_error;
    assign store_done_take = !reset && feeder_active && load_done_take;

    always @(posedge clk) begin
        if (reset)
            feeder_active <= 1'b0;
        else if (load_valid && load_ready)
            feeder_active <= 1'b1;
        else if (load_done_valid && load_done_take)
            feeder_active <= 1'b0;
    end
endmodule
