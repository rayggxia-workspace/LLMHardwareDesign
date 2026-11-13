    // The N32 row lease, E and the stored link share the same private S.
    localparam [15:0] LINK_SEND=16'h0101, LINK_RECEIVE=16'h0102, LINK_RESERVE=16'h0103;
    reg legacy_active;
    reg link_reservation, incoming_pending;
    reg [15:0] active_operation;
    wire legacy_available, e_ready, e_rsp, e_sat, n_ready, n_rsp;
    wire [15:0] e_status, n_status;
    wire [31:0] e_reads, e_writes, n_reads, n_writes;
    wire [1:0] n_kind;
    wire [2:0] n_token;
    wire [31:0] n_sequence,n_job,n_epoch,n_task;
    reg [1:0] e_kind;
    reg [2:0] e_token;
    reg [31:0] e_sequence,e_job,e_epoch,e_task;
    wire [15:0] operation = svc_req_descriptor_o[32+:16];
    wire link_command = operation==LINK_SEND || operation==LINK_RECEIVE || operation==LINK_RESERVE;
    wire legacy_command = svc_req_kind_o==0 && svc_req_resource_o==0 &&
        (link_command || (operation==16'h0100 && svc_req_descriptor_o[513:512]==0));
    wire legacy_offer = legacy_available && (legacy_command || link_reservation);
    wire [1023:0] legacy_descriptor = link_reservation &&
        (operation!=LINK_RECEIVE || !legacy_command) ?
        {svc_req_descriptor_o[1023:48],16'hffff,svc_req_descriptor_o[31:0]} : svc_req_descriptor_o;
    wire sending = legacy_active && active_operation==LINK_SEND;
    wire incoming_admitted = !reset && legacy_available && !sending &&
        ((!deploy_valid_i && !legacy_active) || (link_rx_reserved && incoming_addr==link_rx_addr));
    wire receiving = incoming_pending || (incoming_admitted && incoming_valid);
    wire preload_busy = receiving && !(link_reservation || link_rx_reserved);
    assign svc_req_ready_i = !legacy_active && !preload_busy && (legacy_offer ? e_ready : n_ready);
    assign svc_rsp_valid_i = legacy_active ? e_rsp : n_rsp;
    assign svc_rsp_kind_i = legacy_active ? e_kind : n_kind;
    assign svc_rsp_token_i = legacy_active ? e_token : n_token;
    assign svc_rsp_sequence_i = legacy_active ? e_sequence : n_sequence;
    assign svc_rsp_job_i = legacy_active ? e_job : n_job;
    assign svc_rsp_epoch_i = legacy_active ? e_epoch : n_epoch;
    assign svc_rsp_task_sequence_i = legacy_active ? e_task : n_task;
    assign svc_rsp_status_i = legacy_active ? e_status : n_status;
    assign svc_rsp_read_bytes_i = legacy_active ? e_reads : n_reads;
    assign svc_rsp_write_bytes_i = legacy_active ? e_writes : n_writes;
    assign svc_rsp_saturated_i = legacy_active && e_sat;
    always @(posedge clk_i) begin
        if (reset) begin
            legacy_active<=0;
            link_reservation<=0;
            incoming_pending<=0;
            active_operation<=0;
        end else begin
            if (incoming_ack && incoming_ack_ready) incoming_pending<=0;
            else if (incoming_valid && incoming_ready) incoming_pending<=1;
            if (legacy_active && e_rsp && svc_rsp_ready_o) begin
                legacy_active<=0;
                if (e_status==0 && active_operation==LINK_RESERVE) link_reservation<=1;
                if (e_status==0 && active_operation==LINK_RECEIVE) link_reservation<=0;
            end else if (legacy_offer && svc_req_valid_o && svc_req_ready_i) begin
                legacy_active<=1;
                active_operation<=legacy_descriptor[32+:16];
                e_kind<=svc_req_kind_o; e_token<=svc_req_token_o; e_sequence<=svc_req_sequence_o;
                e_job<=svc_req_job_o; e_epoch<=svc_req_epoch_o; e_task<=svc_req_task_sequence_o;
            end
        end
    end

    wire l_req,l_wr,l_ready,l_rsp,l_take;
    wire [9:0] l_addr;
    wire [127:0] l_data,l_result;
    wire e_req,e_wr,e_take;
    wire [9:0] e_addr;
    wire [127:0] e_data;
    wire send_start,send_ready,send_done,tx_req,tx_take;
    wire [9:0] source_addr,destination_addr,tx_addr;
    assign incoming_ready = incoming_admitted && !incoming_pending && l_ready;
    assign incoming_ack = incoming_pending && l_rsp;
    assign l_req = receiving ? !incoming_pending && incoming_valid : sending ? tx_req : e_req;
    assign l_wr = receiving || (!sending && e_wr);
    assign l_addr = receiving ? incoming_addr : sending ? tx_addr : e_addr;
    assign l_data = receiving ? incoming_data : sending ? 128'b0 : e_data;
    assign l_take = receiving ? incoming_pending && incoming_ack_ready : sending ? tx_take : e_take;

    // Keep the S read response live until the destination write is confirmed.
    // A link reservation excludes a concurrent send from this private S.
    stored_link transport(
        .clk(clk_i),.reset,.start(send_start),.ready(send_ready),.done(send_done),
        .source_addr,.destination_addr,.tx_req,.tx_ready(sending && l_ready),
        .tx_addr,.tx_valid(sending && l_rsp),.tx_take,.tx_data(l_result),
        .rx_valid(outgoing_valid),.rx_ready(outgoing_ready),.rx_addr(outgoing_addr),
        .rx_data(outgoing_data),.rx_stored(outgoing_ack),.rx_stored_ready(outgoing_ack_ready),
        .sink_reserved(peer_rx_reserved && peer_rx_addr==outgoing_addr)
    );
    u_n32_s128_group datapath(
        .clk(clk_i),.reset,.svc_valid(svc_req_valid_o&&!legacy_offer&&!legacy_active&&!preload_busy),.svc_ready(n_ready),
        .svc_kind(svc_req_kind_o),.svc_resource(svc_req_resource_o),.svc_token(svc_req_token_o),
        .svc_sequence(svc_req_sequence_o),.svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),
        .svc_task_sequence(svc_req_task_sequence_o),.descriptor(svc_req_descriptor_o),
        .rsp_valid(n_rsp),.rsp_ready(svc_rsp_ready_o&&!legacy_active),.rsp_kind(n_kind),
        .rsp_token(n_token),.rsp_sequence(n_sequence),.rsp_job(n_job),.rsp_epoch(n_epoch),.rsp_task_sequence(n_task),
        .status(n_status),.read_bytes(n_reads),.write_bytes(n_writes),
        .score_valid,.score_ready,.score_data,.score_tag,.score_word,.score_source,.score_slot,
        .score_ack_valid,.score_ack_ready,.score_ack_tag,.score_ack_word,.score_ack_source,.score_ack_slot,
        .probability_valid,.probability_ready,.probability_data,.probability_tag,.probability_word,
        .probability_head,.probability_sequence,.probability_ack_valid,.probability_ack_ready,.probability_ack_sequence,
        .legacy_available,.legacy_active(legacy_active || link_reservation || receiving),
        .legacy_req_valid(l_req),.legacy_req_write(l_wr),
        .legacy_req_address(l_addr),.legacy_req_data(l_data),.legacy_req_ready(l_ready),
        .legacy_rsp_valid(l_rsp),.legacy_rsp_ready(l_take),.legacy_rsp_data(l_result)
    );

    wire [1:0] cmd_valid,cmd_store,done_ready;
    wire [127:0] cmd_meta;
    wire [3:0] cmd_sources;
    wire [59:0] cmd_addresses;
    wire [19:0] cmd_dst;
    wire cmd_ready,done_valid,done_error,done_saturated;
    ucf_native_service #(.LANES(2)) legacy_frontend(
        .clk(clk_i),.reset,.svc_valid(svc_req_valid_o&&legacy_offer&&!legacy_active&&!preload_busy),
        .svc_ready(e_ready),.descriptor(legacy_descriptor),.rsp_valid(e_rsp),
        .rsp_ready(svc_rsp_ready_o&&legacy_active),.status(e_status),.saturated(e_sat),
        .read_bytes(e_reads),.write_bytes(e_writes),.cmd_valid,.cmd_store,.done_ready,
        .cmd_meta,.cmd_sources,.cmd_addresses,.cmd_dst,.cmd_ready({1'b0,cmd_ready}),
        .done_valid({1'b0,done_valid}),.done_error({1'b0,done_error}),.done_saturated({1'b0,done_saturated}),
        .send_start,.send_ready,.send_done,.source_addr,.destination_addr,
        .receive_commit(incoming_ack && incoming_ack_ready),
        .receive_reserved(link_rx_reserved),.receive_address(link_rx_addr)
    );
    wire e_in_valid,e_in_ready,e_out_valid,e_out_ready,e_out_error,e_out_saturated;
    wire [3:0] e_in_op;
    wire [4:0] e_in_shift;
    wire [127:0] e_in_data,e_out_data;
    pu_compact_e_service legacy_e(
        .clk(clk_i),.reset,.cmd_valid(cmd_valid[0]),.cmd_store(cmd_store[0]),.cmd_direct_a(1'b0),
        .cmd_ready,.cmd_sources(cmd_sources[1:0]),.cmd_op(cmd_meta[3:0]),.cmd_shift(cmd_meta[8:4]),
        .cmd_src(cmd_addresses[29:0]),.cmd_dst(cmd_dst[9:0]),.done_valid,.done_ready(done_ready[0]),
        .done_error,.done_saturated,.done_data(),.s_req_valid(e_req),.s_req_write(e_wr),
        .s_req_ready(!receiving && !sending && l_ready),.s_req_addr(e_addr),.s_req_data(e_data),
        .s_rsp_valid(!receiving && !sending && l_rsp),.s_rsp_ready(e_take),.s_rsp_data(l_result),
        .direct_a_valid(1'b0),.direct_a_abort(1'b0),
        .direct_a_ready(),.direct_a_data(128'b0),.e_in_valid,.e_in_ready,.e_in_op,.e_in_shift,.e_in_data,
        .e_out_valid,.e_out_ready,.e_out_data,.e_out_error,.e_out_saturated
    );
    block_v2_e_compact elementwise(
        .clk(clk_i),.reset,.in_valid(e_in_valid),.in_ready(e_in_ready),.in_op(e_in_op),.in_shift(e_in_shift),
        .in_data(e_in_data),.out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),
        .out_error(e_out_error),.out_saturated(e_out_saturated)
    );
