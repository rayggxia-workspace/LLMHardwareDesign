module tb_pj_endpoint #(parameter bit JOIN_BLOCK=0)(
    input wire clk, reset, svc_valid, output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid, input wire rsp_ready,
    output wire [15:0] status, output wire saturated,
    output wire [31:0] read_bytes, write_bytes,
    input wire seed_valid, input wire [9:0] seed_addr, input wire [127:0] seed_data,
    output wire seed_ready, seed_ack,
    input wire check_read, input wire [9:0] check_addr, input wire check_take,
    output wire check_valid, output wire [127:0] check_data
);
    wire load_valid,load_take,cmd_valid,cmd_take,gate_valid,gate_take,start,done_take,release_valid;
    wire load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated;
    wire gate_ready,gate_done,gate_error,gate_saturated,start_ready,done_valid,done_error,release_ready;
    wire [31:0] load_fields,cmd_fields,join_tag;
    wire [63:0] cmd_data;
    wire [29:0] gate_fields;
    wire [20:0] join_fields;
    wire [1:0] io_req_ready,io_rsp_valid;
    wire [255:0] io_rsp_data;
    wire [1:0] io_req_valid={check_read && !JOIN_BLOCK,seed_valid};
    wire [1:0] io_req_write=2'b01;
    wire [19:0] io_req_addr={check_addr,seed_addr};
    wire [255:0] io_req_data={128'd0,seed_data};
    wire [1:0] io_rsp_ready={check_take,1'b1};
    assign seed_ready=io_req_ready[0];
    assign seed_ack=io_rsp_valid[0];

    pj_native_service #(.JOIN_BLOCK(JOIN_BLOCK)) adapter(.*);
    if (!JOIN_BLOCK) begin: p
        assign {start_ready,done_valid,done_error,release_ready}=0;
        assign check_valid=io_rsp_valid[1];
        assign check_data=io_rsp_data[255:128];
        block_p16 block(.clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,
            .io_req_ready,.io_rsp_valid,.io_rsp_ready,.io_rsp_data,
            .load_valid,.load_ready,.load_done,.load_take,.load_error,
            .load_bank(load_fields[0]),.load_rows(load_fields[4:1]),.load_tiles(load_fields[7:5]),
            .load_a_wide(load_fields[8]),.load_b_wide(load_fields[9]),.load_reuse_b(load_fields[10]),
            .load_a_base(load_fields[20:11]),.load_b_base(load_fields[30:21]),
            .cmd_valid,.cmd_ready,.cmd_op(cmd_fields[3:0]),.cmd_index(cmd_fields[9:4]),.cmd_data,
            .cmd_store(cmd_fields[10]),.cmd_route(1'b0),.cmd_pack16(cmd_fields[11]),.cmd_dst(cmd_fields[21:12]),
            .cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_result(),
            .gate_valid,.gate_route(1'b0),.gate_ready,.gate_a(gate_fields[9:0]),
            .gate_b(gate_fields[19:10]),.gate_dst(gate_fields[29:20]),
            .gate_done,.gate_take,.gate_error,.gate_saturated,
            .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b0),
            .g_from_m_valid(1'b0),.g_from_m_data(32'b0),.g_from_m_take());
    end else begin: j
        assign {load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated,
                gate_ready,gate_done,gate_error,gate_saturated}=0;
        wire out_valid,out_last,rx_error;
        wire [31:0] out_tag;
        wire [9:0] out_index;
        wire [127:0] out_data;
        reg [127:0] committed;
        reg observed;
        reg [2:0] hold_age;
        wire out_take=hold_age==3;
        assign check_valid=observed;
        assign check_data=committed;
        block_j16 block(.clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,
            .io_req_ready,.io_rsp_valid,.io_rsp_ready,.io_rsp_data,.active_epoch(8'd1),
            .rx_tag(32'h01000007),.rx_slot({1'b0,seed_addr[3]}),.rx_last(1'b1),.rx_error,
            .start,.start_ready,.join_tag,.join_three(join_fields[20]),
            .result_addr(join_fields[9:0]),.words(join_fields[19:10]),
            .done_valid,.done_take,.done_error,.out_valid,.out_take,.out_data,.out_tag,.out_index,
            .out_last,.release_valid,.release_ready);
        always @(posedge clk) begin
            if (reset) begin committed<=0; observed<=0; hold_age<=0; end
            else begin
                if (seed_ack && rx_error) $fatal(1,"unexpected J RX error");
                if (out_valid && !out_take) hold_age<=hold_age+1'b1;
                if (out_valid && out_take) begin
                    if (out_tag!=32'h01000007 || out_index!=0 || !out_last)
                        $fatal(1,"incorrect J output identity");
                    committed<=out_data; observed<=1; hold_age<=0;
                end
                if (check_take) observed<=0;
            end
        end
    end
endmodule
