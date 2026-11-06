// U groups independent N, compact E and S_base leaves under local services.
module pu_u_group (
    input wire clk, reset,
    input wire n_cmd_valid, n_cmd_store, n_cmd_direct, n_done_ready,
    output wire n_cmd_ready, n_done_valid, n_done_error, n_done_saturated,
    input wire [39:0] n_cmd_meta,
    input wire [1:0] n_cmd_sources,
    input wire [19:0] n_cmd_src,
    input wire [9:0] n_cmd_dst,
    output wire [127:0] n_done_data,
    output wire n_to_e_valid,
    input wire n_to_e_ready,
    output wire [127:0] n_to_e_data,
    input wire e_cmd_valid, e_cmd_store, e_cmd_direct_a, e_done_ready,
    output wire e_cmd_ready, e_done_valid, e_done_error, e_done_saturated,
    input wire [3:0] e_cmd_op,
    input wire [4:0] e_cmd_shift,
    input wire [29:0] e_cmd_src,
    input wire [9:0] e_cmd_dst,
    output wire [127:0] e_done_data,
    input wire e_direct_a_valid, e_direct_a_abort,
    output wire e_direct_a_ready,
    input wire [127:0] e_direct_a_data,
    input wire [1:0] io_req_valid, io_req_write, io_rsp_ready,
    input wire [19:0] io_req_addr,
    input wire [255:0] io_req_data,
    output wire [1:0] io_req_ready, io_rsp_valid,
    output wire [255:0] io_rsp_data
);
    wire [3:0] request, write, accept, response, take;
    wire [39:0] addr;
    wire [511:0] data, result;
    assign request[3:2] = io_req_valid;
    assign write[3:2] = io_req_write;
    assign take[3:2] = io_rsp_ready;
    assign addr[39:20] = io_req_addr;
    assign data[511:256] = io_req_data;
    assign io_req_ready = accept[3:2];
    assign io_rsp_valid = response[3:2];
    assign io_rsp_data = result[511:256];

    wire mem_req, mem_write, mem_ready, mem_valid, mem_take;
    wire [9:0] mem_addr;
    wire [127:0] mem_data, mem_result;
    block_local_s_arbiter #(.CLIENTS(4)) arbiter(
        .clk, .reset, .req_valid(request), .req_write(write), .req_addr(addr), .req_data(data),
        .req_ready(accept), .rsp_valid(response), .rsp_ready(take), .rsp_data(result),
        .mem_req, .mem_write, .mem_addr, .mem_data, .mem_ready, .mem_valid, .mem_result, .mem_take, .busy()
    );
    local_s_base store(
        .clk, .reset, .req_valid(mem_req), .req_write(mem_write), .req_addr(mem_addr), .req_data(mem_data),
        .req_ready(mem_ready), .rsp_valid(mem_valid), .rsp_ready(mem_take), .rsp_data(mem_result)
    );

    wire n_valid, n_ready, nr_valid, nr_ready, nr_error, nr_sat;
    wire [63:0] n_meta;
    wire [127:0] na, nb, nr;
    wire n_complete;
    reg n_direct, n_sent;
    assign n_to_e_valid = n_complete && n_direct && !n_done_error && !n_sent;
    assign n_to_e_data = n_done_data;
    assign n_done_valid = n_complete && (!n_direct || n_done_error || n_sent);
    always @(posedge clk) begin
        if (reset) begin
            n_direct <= 1'b0;
            n_sent <= 1'b0;
        end else if (n_cmd_valid && n_cmd_ready) begin
            n_direct <= n_cmd_direct;
            n_sent <= 1'b0;
        end else if (n_to_e_valid && n_to_e_ready) begin
            n_sent <= 1'b1;
        end
    end
    ucf_s_compute_client n_service(
        .clk, .reset, .cmd_valid(n_cmd_valid), .cmd_ready(n_cmd_ready), .cmd_meta({24'b0,n_cmd_meta}),
        .cmd_sources(n_cmd_sources), .cmd_addresses({10'b0,n_cmd_src}), .cmd_store(n_cmd_store), .cmd_dst(n_cmd_dst),
        .done_valid(n_complete), .done_ready(n_done_ready && n_done_valid), .done_data(n_done_data),
        .done_error(n_done_error), .done_saturated(n_done_saturated),
        .s_req_valid(request[0]), .s_req_ready(accept[0]), .s_req_write(write[0]),
        .s_req_addr(addr[9:0]), .s_req_data(data[127:0]), .s_rsp_valid(response[0]),
        .s_rsp_ready(take[0]), .s_rsp_data(result[127:0]), .exec_valid(n_valid), .exec_ready(n_ready),
        .exec_meta(n_meta), .exec_a(na), .exec_b(nb), .exec_c(),
        .result_valid(nr_valid), .result_ready(nr_ready), .result_data(nr),
        .result_error(nr_error), .result_saturated(nr_sat)
    );
    block_v2_n normalize(
        .clk, .reset, .cmd_valid(n_valid), .cmd_ready(n_ready),
        .cmd_op(n_meta[3:0]), .cmd_count(n_meta[7:4]), .cmd_param(n_meta[39:8]),
        .cmd_data(na), .cmd_aux(nb), .rsp_valid(nr_valid), .rsp_ready(nr_ready),
        .rsp_data(nr), .rsp_error(nr_error), .rsp_saturated(nr_sat), .busy()
    );

    wire e_valid, e_ready, er_valid, er_ready, er_error, er_sat;
    wire [3:0] op;
    wire [4:0] shift;
    wire [127:0] ea, er;
    pu_compact_e_service e_service(
        .clk, .reset, .cmd_valid(e_cmd_valid), .cmd_store(e_cmd_store), .cmd_direct_a(e_cmd_direct_a),
        .cmd_ready(e_cmd_ready), .cmd_op(e_cmd_op), .cmd_shift(e_cmd_shift), .cmd_src(e_cmd_src), .cmd_dst(e_cmd_dst),
        .done_valid(e_done_valid), .done_ready(e_done_ready), .done_error(e_done_error),
        .done_saturated(e_done_saturated), .done_data(e_done_data),
        .s_req_valid(request[1]), .s_req_write(write[1]), .s_req_ready(accept[1]),
        .s_req_addr(addr[19:10]), .s_req_data(data[255:128]), .s_rsp_valid(response[1]),
        .s_rsp_ready(take[1]), .s_rsp_data(result[255:128]),
        .direct_a_valid(e_direct_a_valid), .direct_a_abort(e_direct_a_abort), .direct_a_ready(e_direct_a_ready), .direct_a_data(e_direct_a_data),
        .e_in_valid(e_valid), .e_in_ready(e_ready), .e_in_op(op), .e_in_shift(shift), .e_in_data(ea),
        .e_out_valid(er_valid), .e_out_ready(er_ready), .e_out_data(er), .e_out_error(er_error), .e_out_saturated(er_sat)
    );
    block_v2_e_compact elementwise(
        .clk, .reset, .in_valid(e_valid), .in_ready(e_ready), .in_op(op), .in_shift(shift), .in_data(ea),
        .out_valid(er_valid), .out_ready(er_ready), .out_data(er), .out_error(er_error), .out_saturated(er_sat)
    );
endmodule
