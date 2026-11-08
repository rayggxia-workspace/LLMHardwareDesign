module tb_p16_local #(parameter [7:0] BLOCK=0)(
`include "tb_network_lc_ports.svh"
    ,input wire [31:0] cycle_i,
    output reg [127:0] outgoing_identity,
    output reg [31:0] image_id,
    input wire seed_valid, input wire [9:0] seed_addr, input wire [127:0] seed_data,
    output wire seed_ready, seed_ack,
    input wire check_read, input wire [9:0] check_addr, input wire check_take,
    output wire check_valid, output wire [127:0] check_data,
    output wire link_rx_reserved, output wire [9:0] link_rx_addr,
    input wire peer_rx_reserved, input wire [9:0] peer_rx_addr,
    output wire outgoing_valid, input wire outgoing_ready,
    output wire [9:0] outgoing_addr, output wire [127:0] outgoing_data,
    input wire outgoing_ack, output wire outgoing_ack_ready,
    input wire incoming_valid, output wire incoming_ready,
    input wire [9:0] incoming_addr, input wire [127:0] incoming_data,
    output wire incoming_ack, input wire incoming_ack_ready
);
`define TB_NATIVE_P16
`include "tb_network_lc_wires.svh"
`undef TB_NATIVE_P16
    localparam bit SOURCE = BLOCK==0;
    wire [15:0] op = svc_req_descriptor_o[32+:16];
    wire link_command = SOURCE ? op==16'h101 : op==16'h102 || op==16'h103;
    wire link_ready, link_rsp, native_ready, native_rsp;
    wire [15:0] link_status, native_status;
    wire [31:0] link_reads, link_writes, native_reads, native_writes;
    wire link_sat, native_sat;
    reg active_link;
    always @* begin
        svc_req_ready_i = link_command ? link_ready : native_ready;
        svc_rsp_valid_i = active_link ? link_rsp : native_rsp;
        svc_rsp_status_i = active_link ? link_status : native_status;
        svc_rsp_read_bytes_i = active_link ? link_reads : native_reads;
        svc_rsp_write_bytes_i = active_link ? link_writes : native_writes;
        svc_rsp_saturated_i = active_link ? link_sat : native_sat;
    end
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            active_link<=0;
            outgoing_identity<=0;
        end else if (svc_req_valid_o && svc_req_ready_i) begin
            if (SOURCE && link_command)
                outgoing_identity<={svc_req_job_o,svc_req_epoch_o,svc_req_task_sequence_o,svc_req_sequence_o};
            active_link<=link_command;
            svc_rsp_token_i<=svc_req_token_o;
            svc_rsp_sequence_i<=svc_req_sequence_o;
            svc_rsp_job_i<=svc_req_job_o;
            svc_rsp_epoch_i<=svc_req_epoch_o;
            svc_rsp_task_sequence_i<=svc_req_task_sequence_o;
        end
    end

    network_pm pm(.clk_i,.rst_ni,.cycle_i,.stall_i(32'd0),
        .pm_req_valid_o,.pm_req_write_o,.pm_req_address_o,.pm_req_data_o,.pm_req_ready_i,
        .pm_rsp_valid_i,.pm_rsp_data_i,.pm_rsp_error_i,.pm_rsp_ready_o,
        .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));

    wire clk = clk_i;
    wire reset = !rst_ni;
    wire load_valid,load_take,cmd_valid,cmd_take,gate_valid,gate_take;
    wire load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated;
    wire gate_ready,gate_done,gate_error,gate_saturated;
    wire [31:0] load_fields,cmd_fields;
    wire [63:0] cmd_data;
    wire [29:0] gate_fields;
    pj_native_service compute(.clk,.reset,
        .svc_valid(svc_req_valid_o && !link_command),.svc_ready(native_ready),.descriptor(svc_req_descriptor_o),
        .rsp_valid(native_rsp),.rsp_ready(svc_rsp_ready_o && !active_link),
        .status(native_status),.saturated(native_sat),.read_bytes(native_reads),.write_bytes(native_writes),
        .load_valid,.load_ready,.load_done,.load_take,.load_error,.load_fields,
        .cmd_valid,.cmd_ready,.cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_fields,.cmd_data,
        .gate_valid,.gate_ready,.gate_done,.gate_take,.gate_error,.gate_saturated,.gate_fields,
        .start(),.start_ready(1'b0),.done_take(),.done_valid(1'b0),.done_error(1'b0),
        .join_tag(),.join_fields(),.release_valid(),.release_ready(1'b0));

    wire send_start,send_ready,send_done;
    wire [9:0] source_addr,destination_addr;
    // Only the three transport commands reach this adapter. Its compute ports are idle.
    ucf_native_service #(.LANES(2)) transport_commands(.clk,.reset,
        .svc_valid(svc_req_valid_o && link_command),.svc_ready(link_ready),.descriptor(svc_req_descriptor_o),
        .rsp_valid(link_rsp),.rsp_ready(svc_rsp_ready_o && active_link),
        .status(link_status),.saturated(link_sat),.read_bytes(link_reads),.write_bytes(link_writes),
        .cmd_valid(),.cmd_store(),.done_ready(),.cmd_meta(),.cmd_sources(),.cmd_addresses(),.cmd_dst(),
        .cmd_ready(2'b0),.done_valid(2'b0),.done_error(2'b0),.done_saturated(2'b0),
        .send_start,.send_ready,.send_done,.source_addr,.destination_addr,
        .receive_commit(incoming_ack && incoming_ack_ready),
        .receive_reserved(link_rx_reserved),.receive_address(link_rx_addr));

    wire [1:0] io_req_ready,io_rsp_valid;
    wire [255:0] io_rsp_data;
    wire link_req, link_take;
    wire [9:0] link_addr;
    wire [1:0] io_req_valid={link_req, seed_valid || check_read};
    wire [1:0] io_req_write={!SOURCE,seed_valid};
    wire [19:0] io_req_addr={link_addr,seed_valid ? seed_addr : check_addr};
    wire [255:0] io_req_data={SOURCE ? 128'd0 : incoming_data,seed_data};
    reg seed_pending;
    always @(posedge clk_i) begin
        if (reset) seed_pending<=0;
        else if (seed_ack) seed_pending<=0;
        else if (seed_valid && seed_ready) seed_pending<=1;
    end
    wire [1:0] io_rsp_ready={link_take,seed_pending || check_take};
    assign seed_ready=io_req_ready[0];
    assign seed_ack=seed_pending && io_rsp_valid[0];
    assign check_valid=!seed_pending && io_rsp_valid[0];
    assign check_data=io_rsp_data[127:0];

    if (SOURCE) begin: source
        assign {incoming_ready,incoming_ack}=0;
        stored_link transfer(.clk,.reset,.start(send_start),.ready(send_ready),
            .source_addr,.destination_addr,.done(send_done),
            .tx_req(link_req),.tx_ready(io_req_ready[1]),.tx_addr(link_addr),
            .tx_valid(io_rsp_valid[1]),.tx_take(link_take),.tx_data(io_rsp_data[255:128]),
            .rx_valid(outgoing_valid),.rx_ready(outgoing_ready),.rx_addr(outgoing_addr),.rx_data(outgoing_data),
            .rx_stored(outgoing_ack),.rx_stored_ready(outgoing_ack_ready),
            .sink_reserved(peer_rx_reserved && peer_rx_addr==outgoing_addr));
        reg held;
        reg [127:0] held_word;
        always @(posedge clk_i) begin
            if (reset) held<=0;
            else begin
                if (held && (!io_rsp_valid[1] || io_rsp_data[255:128]!==held_word))
                    $fatal(1,"P0 changed the held SRAM word");
                if (link_take && !(outgoing_ack && outgoing_ack_ready))
                    $fatal(1,"P0 released SRAM data before the destination commit ACK");
                held<=io_rsp_valid[1] && !link_take;
                held_word<=io_rsp_data[255:128];
            end
        end
    end else begin: sink
        assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,send_ready,send_done}=0;
        wire reserved_match = link_rx_reserved && incoming_addr==link_rx_addr;
        assign link_req=incoming_valid && reserved_match;
        assign link_addr=incoming_addr;
        assign incoming_ready=io_req_ready[1] && reserved_match;
        assign incoming_ack=io_rsp_valid[1];
        assign link_take=incoming_ack_ready;
    end

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

    reg [127:0] image[0:519];
    string path;
    integer words, n;
    task automatic cfg(input [2:0] op, input integer address, input [127:0] data);
        @(negedge clk_i);
        cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=release_epoch_i;
        cfg_req_address_i=14'(address); cfg_req_data_i=data; cfg_req_proof_i=1;
        cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=image_id;
        cfg_req_topology_id_i=image[4][0+:32]; cfg_req_abi_id_i=image[4][32+:32];
        cfg_req_capacity_id_i=image[5][32+:32];
        do @(posedge clk_i); while(!cfg_req_ready_o);
        @(negedge clk_i);
        cfg_req_valid_i=0;
        while(!cfg_rsp_valid_o) @(negedge clk_i);
        if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
            $fatal(1,"P16 LC %0d config op=%0d addr=%0d status=%0d",BLOCK,op,address,cfg_rsp_status_o);
        cfg_rsp_ready_i=1;
        @(negedge clk_i);
        cfg_rsp_ready_i=0;
    endtask
    initial begin
        release_valid_i=0; release_sequence_i=0; cfg_req_valid_i=0; cfg_rsp_ready_i=0;
        svc_rsp_kind_i=0;
        close_req_ready_i=0; close_rsp_valid_i=0; close_rsp_sequence_i=0;
        close_rsp_job_i=0; close_rsp_epoch_i=0; close_rsp_task_sequence_i=0;
        close_rsp_token_i=0; close_rsp_status_i=0;
        if(BLOCK==0) begin
            if(!$value$plusargs("LOCAL0=%s",path) || !$value$plusargs("WORDS0=%d",words))
                $fatal(1,"missing P0 image");
        end else if(!$value$plusargs("LOCAL1=%s",path) || !$value$plusargs("WORDS1=%d",words))
            $fatal(1,"missing P1 image");
        $readmemh(path,image,0,words-1);
        if (image[0][64+:16]!=2 || image[4][31:0]!=32'h01790161)
            $fatal(1,"expected compact P16 image");
        image_id=image[3][96+:32];
        wait(rst_ni);
        forever begin
            @(negedge clk_i); release_valid_i=1; release_sequence_i=release_epoch_i;
            @(negedge clk_i); release_valid_i=0;
            cfg(0,0,0);
            for(n=0;n<words;n=n+1) cfg(1,n*16,image[n]);
            for(n=0;n<words;n=n+1) cfg(2,n*16,0);
            cfg(3,0,0); cfg(4,0,0);
            wait(!rst_ni); wait(rst_ni);
        end
    end
endmodule
