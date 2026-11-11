// U groups independent N, compact E and S_base leaves under local services.
module pu_u_group #(parameter integer NEXP_BATCH=0, NEXP_DIRECT=0, NEXP_DIRECT_LANES=2, NEXP_S16=0, E_PIPELINE=0, E_QUEUE_DEPTH=0, E_S32=0) (
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
    input wire [1:0] e_cmd_sources,
    input wire [3:0] e_cmd_op,
    input wire [(E_S32!=0?7:5)-1:0] e_cmd_shift,
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
    wire n_complete,n_service_ready;
    wire [127:0] n_service_data;
    wire n_service_error,n_service_saturated;
    reg n_rejected;
    wire n_is_batch=NEXP_BATCH!=0&&n_cmd_meta[3:0]==15;
    wire n_is_32=n_cmd_meta[39:8]==32'h4e583332;
    wire n_is_s16=NEXP_S16!=0 && NEXP_DIRECT!=0 && n_cmd_meta[39:8]==32'h4e583136;
    wire n_batch_bad=n_is_batch&&(
        (n_cmd_meta[39:8]!=32'h4e455850&&!n_is_32&&!n_is_s16)||n_cmd_meta[7:4]==0||
        n_cmd_meta[7:4]>(n_is_32?4:8)||n_cmd_sources!=1||n_cmd_src[19:10]!=0||n_cmd_direct||
        (n_is_s16 && n_cmd_meta[7:4]>4 && (!n_cmd_store || n_cmd_dst==1023)));
    assign n_cmd_ready=n_service_ready&&!n_rejected;
    assign n_done_data=n_rejected?128'd0:n_service_data;
    assign n_done_error=n_rejected||n_service_error;
    assign n_done_saturated=!n_rejected&&n_service_saturated;
    always @(posedge clk)begin
        if(reset)n_rejected<=0;
        else begin
            if(n_rejected&&n_done_ready)n_rejected<=0;
            if(n_cmd_valid&&n_cmd_ready&&n_batch_bad)n_rejected<=1;
        end
    end
    reg n_direct, n_sent;
    assign n_to_e_valid = n_complete && n_direct && !n_done_error && !n_sent;
    assign n_to_e_data = n_done_data;
    assign n_done_valid = !reset && (n_rejected || (n_complete && (!n_direct || n_done_error || n_sent)));
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
    ucf_s_compute_client #(.NEXP_S16(NEXP_BATCH!=0 && NEXP_DIRECT!=0 && NEXP_S16!=0)) n_service(
        .clk, .reset, .cmd_valid(n_cmd_valid&&!n_rejected&&!n_batch_bad), .cmd_ready(n_service_ready), .cmd_meta({24'b0,n_cmd_meta}),
        .cmd_sources(n_cmd_sources), .cmd_addresses({10'b0,n_cmd_src}), .cmd_store(n_cmd_store), .cmd_dst(n_cmd_dst),
        .done_valid(n_complete), .done_ready(n_done_ready && n_done_valid), .done_data(n_service_data),
        .done_error(n_service_error), .done_saturated(n_service_saturated),
        .s_req_valid(request[0]), .s_req_ready(accept[0]), .s_req_write(write[0]),
        .s_req_addr(addr[9:0]), .s_req_data(data[127:0]), .s_rsp_valid(response[0]),
        .s_rsp_ready(take[0]), .s_rsp_data(result[127:0]), .exec_valid(n_valid), .exec_ready(n_ready),
        .exec_meta(n_meta), .exec_a(na), .exec_b(nb), .exec_c(),
        .result_valid(nr_valid), .result_ready(nr_ready), .result_data(nr),
        .result_error(nr_error), .result_saturated(nr_sat)
    );
    wire core_valid,core_ready,core_result_valid,core_result_ready,core_error,core_saturated;
    wire [63:0] core_meta;
    wire [127:0] core_a,core_b,core_result;
    generate if(NEXP_BATCH!=0)begin: batch_route
        pu_nexp_shared #(.NEXP_DIRECT(NEXP_DIRECT)) dispatch(
            .clk,.reset,.exec_valid(n_valid),.exec_ready(n_ready),.exec_meta(n_meta),.exec_a(na),.exec_b(nb),
            .result_valid(nr_valid),.result_ready(nr_ready),.result_data(nr),.result_error(nr_error),.result_saturated(nr_sat),
            .n_valid(core_valid),.n_ready(core_ready),.n_meta(core_meta),.n_a(core_a),.n_b(core_b),
            .n_result_valid(core_result_valid),.n_result_ready(core_result_ready),.n_result(core_result),
            .n_error(core_error),.n_saturated(core_saturated)
        );
    end else begin: legacy_route
        assign core_valid=n_valid;assign n_ready=core_ready;assign core_meta=n_meta;assign core_a=na;assign core_b=nb;
        assign nr_valid=core_result_valid;assign core_result_ready=nr_ready;assign nr=core_result;
        assign nr_error=core_error;assign nr_sat=core_saturated;
    end endgenerate
    // Exactly one native N; optional direct EXP widening is explicit below.
    // DIRECT without BATCH does not expose a new ordinary native ABI.
    block_v2_n #(.NEXP_DIRECT((NEXP_BATCH!=0)&&(NEXP_DIRECT!=0)),
        .NEXP_DIRECT_LANES((NEXP_BATCH!=0&&NEXP_DIRECT!=0)?NEXP_DIRECT_LANES:2)) normalize(
        .clk, .reset, .cmd_valid(core_valid), .cmd_ready(core_ready),
        .cmd_op(core_meta[3:0]), .cmd_count(core_meta[7:4]), .cmd_param(core_meta[39:8]),
        .cmd_data(core_a), .cmd_aux(core_b), .rsp_valid(core_result_valid), .rsp_ready(core_result_ready),
        .rsp_data(core_result), .rsp_error(core_error), .rsp_saturated(core_saturated), .busy()
    );

    wire e_valid, e_ready, er_valid, er_ready, er_error, er_sat;
    wire [3:0] op;
    wire [(E_S32!=0?7:5)-1:0] shift;
    wire [127:0] ea, er;
    generate if(E_QUEUE_DEPTH==0)begin: serial_e
    pu_compact_e_service #(.SHIFT_WIDTH(E_S32!=0?7:5)) e_service(
        .clk, .reset, .cmd_valid(e_cmd_valid), .cmd_store(e_cmd_store), .cmd_direct_a(e_cmd_direct_a),
        .cmd_sources(e_cmd_sources), .cmd_ready(e_cmd_ready), .cmd_op(e_cmd_op), .cmd_shift(e_cmd_shift), .cmd_src(e_cmd_src), .cmd_dst(e_cmd_dst),
        .done_valid(e_done_valid), .done_ready(e_done_ready), .done_error(e_done_error),
        .done_saturated(e_done_saturated), .done_data(e_done_data),
        .s_req_valid(request[1]), .s_req_write(write[1]), .s_req_ready(accept[1]),
        .s_req_addr(addr[19:10]), .s_req_data(data[255:128]), .s_rsp_valid(response[1]),
        .s_rsp_ready(take[1]), .s_rsp_data(result[255:128]),
        .direct_a_valid(e_direct_a_valid), .direct_a_abort(e_direct_a_abort), .direct_a_ready(e_direct_a_ready), .direct_a_data(e_direct_a_data),
        .e_in_valid(e_valid), .e_in_ready(e_ready), .e_in_op(op), .e_in_shift(shift), .e_in_data(ea),
        .e_out_valid(er_valid), .e_out_ready(er_ready), .e_out_data(er), .e_out_error(er_error), .e_out_saturated(er_sat)
    );
    end else begin: queued_e
    pu_queued_e_service #(.DEPTH(E_QUEUE_DEPTH),.SHIFT_WIDTH(E_S32!=0?7:5)) e_service(
        .clk, .reset, .cmd_valid(e_cmd_valid), .cmd_store(e_cmd_store), .cmd_direct_a(e_cmd_direct_a),
        .cmd_sources(e_cmd_sources), .cmd_ready(e_cmd_ready), .cmd_op(e_cmd_op), .cmd_shift(e_cmd_shift), .cmd_src(e_cmd_src), .cmd_dst(e_cmd_dst),
        .done_valid(e_done_valid), .done_ready(e_done_ready), .done_error(e_done_error),
        .done_saturated(e_done_saturated), .done_data(e_done_data),
        .s_req_valid(request[1]), .s_req_write(write[1]), .s_req_ready(accept[1]),
        .s_req_addr(addr[19:10]), .s_req_data(data[255:128]), .s_rsp_valid(response[1]),
        .s_rsp_ready(take[1]), .s_rsp_data(result[255:128]),
        .direct_a_valid(e_direct_a_valid), .direct_a_abort(e_direct_a_abort), .direct_a_ready(e_direct_a_ready), .direct_a_data(e_direct_a_data),
        .e_in_valid(e_valid), .e_in_ready(e_ready), .e_in_op(op), .e_in_shift(shift), .e_in_data(ea),
        .e_out_valid(er_valid), .e_out_ready(er_ready), .e_out_data(er), .e_out_error(er_error), .e_out_saturated(er_sat)
    );
    end endgenerate
    block_v2_e_compact #(.PIPELINED(E_PIPELINE),.S32(E_S32)) elementwise(
        .clk, .reset, .in_valid(e_valid), .in_ready(e_ready), .in_op(op), .in_shift(shift), .in_data(ea),
        .out_valid(er_valid), .out_ready(er_ready), .out_data(er), .out_error(er_error), .out_saturated(er_sat)
    );
    initial begin
        if(E_QUEUE_DEPTH!=0&&E_QUEUE_DEPTH!=2&&E_QUEUE_DEPTH!=4)
            $fatal(1,"E_QUEUE_DEPTH must be 0, 2 or 4");
        if(NEXP_DIRECT_LANES!=2&&NEXP_DIRECT_LANES!=4)
            $fatal(1,"NEXP_DIRECT_LANES must be exactly 2 or 4");
    end
endmodule
