module tb_native_local #(parameter [7:0] BLOCK=0, parameter integer KIND=2, parameter [31:0] TOPOLOGY_ID=32'h01930010)(
`include "tb_network_lc_ports.svh"
    ,input wire [31:0] cycle_i,
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
`define TB_NATIVE
`include "tb_network_lc_wires.svh"
`undef TB_NATIVE
    localparam LANES=KIND==2 ? 3 : 2;
    wire [LANES-1:0] cmd_valid, cmd_store, done_ready, cmd_ready, done_valid, done_error, done_saturated;
    wire [LANES*64-1:0] cmd_meta;
    wire [LANES*2-1:0] cmd_sources;
    wire [LANES*30-1:0] cmd_addresses;
    wire [LANES*10-1:0] cmd_dst;
    wire rx_ready, rx_stored, tx_ready, tx_valid, tx_req, tx_take;
    wire [9:0] tx_addr, source_addr, destination_addr;
    wire [127:0] tx_data;
    wire send_start, send_ready, send_done, response_valid;
    wire admit_peer = peer_rx_reserved && peer_rx_addr==outgoing_addr;
    wire seed_mode = !deploy_valid_i;
    wire [15:0] status;
    wire [31:0] read_bytes, write_bytes;
    wire saturated;
    network_pm pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(cycle_i),.stall_i(32'd0),
        .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),
        .pm_req_data_o(pm_req_data_o),.pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),
        .pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
        .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));

    if (KIND<3) begin: ucf
        assign seed_ready=seed_mode && rx_ready;
        assign seed_ack=seed_mode && rx_stored;
        assign incoming_ready=!seed_mode && rx_ready;
        assign incoming_ack=!seed_mode && rx_stored;
        assign check_valid=tx_valid;
        assign check_data=tx_data;

        block_ucf16 #(.KIND(KIND)) block(.clk(clk_i),.reset(!rst_ni),
            .cmd_valid,.cmd_store,.done_ready,.cmd_ready,.done_valid,.done_error,.done_saturated,
            .cmd_meta,.cmd_sources,.cmd_addresses,.cmd_dst,.done_data(),
            .rx_valid(seed_mode ? seed_valid : incoming_valid),
            .rx_ready,.rx_addr(seed_mode ? seed_addr : incoming_addr),
            .rx_data(seed_mode ? seed_data : incoming_data),.rx_stored,
            .rx_stored_ready(seed_mode || incoming_ack_ready),
            .tx_req(tx_req || check_read),.tx_ready,.tx_addr(check_read ? check_addr : tx_addr),
            .tx_valid,.tx_take(tx_take || check_take),.tx_data);

        stored_link transport(.clk(clk_i),.reset(!rst_ni),
            .start(send_start),.ready(send_ready),.source_addr,.destination_addr,.done(send_done),
            .tx_req,.tx_ready,.tx_addr,.tx_valid,.tx_take,.tx_data,
            .rx_valid(outgoing_valid),.rx_ready(outgoing_ready),.rx_addr(outgoing_addr),.rx_data(outgoing_data),
            .rx_stored(outgoing_ack),.rx_stored_ready(outgoing_ack_ready),.sink_reserved(admit_peer));

        ucf_native_service #(.LANES(LANES)) adapter(.clk(clk_i),.reset(!rst_ni),
            .svc_valid(svc_req_valid_o),.svc_ready(svc_req_ready_i),.descriptor(svc_req_descriptor_o),
            .rsp_valid(response_valid),.rsp_ready(svc_rsp_ready_o),.status,.saturated,.read_bytes,.write_bytes,
            .cmd_valid,.cmd_store,.done_ready,.cmd_ready,.done_valid,.done_error,.done_saturated,
            .cmd_meta,.cmd_sources,.cmd_addresses,.cmd_dst,
            .send_start,.send_ready,.send_done,.source_addr,.destination_addr,
            .receive_commit(incoming_ack && incoming_ack_ready),
            .receive_reserved(link_rx_reserved),.receive_address(link_rx_addr));

    end else begin: pj
        assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,
                incoming_ready,incoming_ack,link_rx_reserved,link_rx_addr,tx_take}=0;
        tb_pj_endpoint #(.JOIN_BLOCK(KIND==4)) endpoint(
            .clk(clk_i),.reset(!rst_ni),.svc_valid(svc_req_valid_o),.svc_ready(svc_req_ready_i),
            .descriptor(svc_req_descriptor_o),.rsp_valid(response_valid),.rsp_ready(svc_rsp_ready_o),
            .status,.saturated,.read_bytes,.write_bytes,.seed_valid,.seed_addr,.seed_data,
            .seed_ready,.seed_ack,.check_read,.check_addr,.check_take,.check_valid,.check_data);
    end
    always @* begin
        svc_rsp_valid_i=response_valid;
        svc_rsp_status_i=status;
        svc_rsp_read_bytes_i=read_bytes;
        svc_rsp_write_bytes_i=write_bytes;
        svc_rsp_saturated_i=saturated;
    end
    reg tx_was_held, observing;
    reg [127:0] held_word;
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            observing<=0; tx_was_held<=0; held_word<=0;
        end else if (KIND<3) begin
            if (tx_was_held && (!tx_valid || tx_data!==held_word))
                $fatal(1,"native source word changed before storage confirmation");
            if (check_read) observing<=1;
            if (check_take) observing<=0;
            tx_was_held<=deploy_valid_i && tx_valid && !tx_take && !observing && !check_read && !check_take;
            held_word<=tx_data;
        end
    end
    always @(posedge clk_i) if (rst_ni) begin
        if (svc_req_valid_o && svc_req_ready_i) begin
            svc_rsp_token_i<=svc_req_token_o;
            svc_rsp_sequence_i<=svc_req_sequence_o;
            svc_rsp_job_i<=svc_req_job_o;
            svc_rsp_epoch_i<=svc_req_epoch_o;
            svc_rsp_task_sequence_i<=svc_req_task_sequence_o;
        end
        if (tx_take && !(outgoing_ack && outgoing_ack_ready))
            $fatal(1, "released a native SRAM word before destination storage");
        if (tx_take) $display("ACK block=%0d cycle=%0d",BLOCK,cycle_i);
        if (incoming_ack && incoming_ack_ready)
            $display("STORED block=%0d cycle=%0d",BLOCK,cycle_i);
    end

    reg [127:0] image[0:519];
    string path;
    integer words, n;
    task automatic cfg(input [2:0] op, input integer address, input [127:0] data);
        @(negedge clk_i);
        cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1;
        cfg_req_address_i=14'(address); cfg_req_data_i=data; cfg_req_proof_i=1;
        cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=image_id;
        cfg_req_topology_id_i=image[4][0+:32]; cfg_req_abi_id_i=image[4][32+:32];
        cfg_req_capacity_id_i=image[5][32+:32];
        do @(posedge clk_i); while(!cfg_req_ready_o);
        @(negedge clk_i);
        cfg_req_valid_i=0;
        while(!cfg_rsp_valid_o) @(negedge clk_i);
        if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
            $fatal(1,"native LC %0d config op=%0d addr=%0d status=%0d",BLOCK,op,address,cfg_rsp_status_o);
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
                $fatal(1,"missing C image");
        end else if(!$value$plusargs("LOCAL1=%s",path) || !$value$plusargs("WORDS1=%d",words))
            $fatal(1,"missing U image");
        $readmemh(path,image,0,words-1);
        image_id=image[3][96+:32];
        wait(rst_ni);
        forever begin
            @(negedge clk_i); release_valid_i=1; release_sequence_i=1;
            @(negedge clk_i); release_valid_i=0;
            cfg(0,0,0);
            for(n=0;n<words;n=n+1) cfg(1,n*16,image[n]);
            for(n=0;n<words;n=n+1) cfg(2,n*16,0);
            cfg(3,0,0); cfg(4,0,0);
            wait(!rst_ni); wait(rst_ni);
        end
    end
endmodule
