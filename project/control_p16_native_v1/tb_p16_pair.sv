module tb_p16_pair;
`define TB_NATIVE_P16
`include "tb_network_mc_wires.svh"
`undef TB_NATIVE_P16
    reg [31:0] cycle=0;
    initial clk_i=0;
    always #5 clk_i=~clk_i;
    always @(posedge clk_i) cycle<=cycle+1;
    reg grant=0;
    wire [1:0] lc_ready, lc_event, lc_poison, lc_image, reservation;
    wire [3:0] lc_life[2];
    wire [31:0] lc_id[2];
    wire [511:0] lc_packet[2];
    reg [1:0] seed_valid=0, check_read=0, check_take=0;
    reg [9:0] seed_addr=0, check_addr=0;
    reg [127:0] seed_data=0;
    wire [1:0] seed_ready, seed_ack, check_valid;
    wire [127:0] check_data[2];
    wire [1:0] link_valid, link_ready, link_ack, link_ack_ready;
    wire [9:0] link_addr[2], reservation_addr[2];
    wire [127:0] link_data[2];
    integer stall=0, transfers=0, reset_trial=0;
    integer offers=0, request_stall_cycles=0, ack_stall_cycles=0;
    reg force_no_ack=0;
    wire accept_request = stall==0 || (request_stall_cycles>=3 && cycle%7==1);
    wire accept_ack = !force_no_ack && (stall==0 || (ack_stall_cycles>=3 && cycle%11==3));

    assign deploy_valid_i=grant;
    assign local_enabled_i=2'b11;
    assign local_image_id0_i=lc_id[0];
    assign local_image_id1_i=lc_id[1];
    assign task_ready_i=task_target_o<2 && lc_ready[task_target_o[0]];
    assign return_valid_i=|lc_event;
    assign return_packet_i=lc_event[0] ? lc_packet[0] : lc_packet[1];

    for (genvar i=0; i<2; i=i+1) begin: local_block
        localparam integer PEER=1-i;
        tb_p16_local #(.BLOCK(8'(i))) endpoint(
            .clk_i,.rst_ni,.release_epoch_i(32'd1),.deploy_valid_i,.deploy_generation_i,
            .poison_o(lc_poison[i]),.image_valid_o(lc_image[i]),
            .task_valid_i(task_valid_o && task_target_o==8'(i)),.task_packet_i(task_packet_o),
            .task_credit_i(task_credit_o),.task_ready_o(lc_ready[i]),
            .event_ready_i(return_ready_o && (i==0 || !lc_event[0])),
            .event_valid_o(lc_event[i]),.event_packet_o(lc_packet[i]),.life_o(lc_life[i]),
            .cycle_i(cycle),.image_id(lc_id[i]),.seed_valid(seed_valid[i]),.seed_addr,.seed_data,
            .seed_ready(seed_ready[i]),.seed_ack(seed_ack[i]),
            .check_read(check_read[i]),.check_addr,.check_take(check_take[i]),
            .check_valid(check_valid[i]),.check_data(check_data[i]),
            .link_rx_reserved(reservation[i]),.link_rx_addr(reservation_addr[i]),
            .peer_rx_reserved(reservation[PEER]),.peer_rx_addr(reservation_addr[PEER]),
            .outgoing_valid(link_valid[i]),.outgoing_ready(link_ready[PEER] && accept_request),
            .outgoing_addr(link_addr[i]),.outgoing_data(link_data[i]),
            .outgoing_ack(link_ack[PEER] && accept_ack),.outgoing_ack_ready(link_ack_ready[i]),
            .incoming_valid(link_valid[PEER] && accept_request),.incoming_ready(link_ready[i]),
            .incoming_addr(link_addr[PEER]),.incoming_data(link_data[PEER]),
            .incoming_ack(link_ack[i]),.incoming_ack_ready(link_ack_ready[PEER] && accept_ack));
    end

    always @(posedge clk_i) begin
        if (!rst_ni) begin
            transfers<=0; offers<=0; request_stall_cycles<=0; ack_stall_cycles<=0;
        end else begin
            if (poison_o || |lc_poison) $fatal(1,"unexpected poison");
            if (link_valid[0] && link_ready[1] && accept_request) begin
                if (!reservation[1] || link_addr[0]!=20 || offers!=0)
                    $fatal(1,"unexpected destination offer");
                offers<=offers+1;
            end
            if (link_valid[0] && !accept_request) request_stall_cycles<=request_stall_cycles+1;
            if (link_ack[1] && !accept_ack) ack_stall_cycles<=ack_stall_cycles+1;
            if (link_ack[1] && link_ack_ready[0] && accept_ack) begin
                if (offers!=1 || transfers!=0) $fatal(1,"unexpected SRAM commit ACK");
                transfers<=transfers+1;
            end
        end
    end

    network_pm #(.BYTES(4736)) pm(.clk_i,.rst_ni,.cycle_i(cycle),.stall_i(32'd0),
        .pm_req_valid_o,.pm_req_write_o,.pm_req_address_o,.pm_req_data_o,.pm_req_ready_i,
        .pm_rsp_valid_i,.pm_rsp_data_i,.pm_rsp_error_i,.pm_rsp_ready_o,
        .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));

    reg [127:0] image[0:295];
    string path;
    integer words, n;
    task automatic cfg(input [2:0] op, input integer address, input [127:0] data);
        @(negedge clk_i);
        cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1;
        cfg_req_address_i=14'(address); cfg_req_data_i=data; cfg_req_proof_i=1;
        cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=image[3][96+:32];
        cfg_req_topology_id_i=image[4][0+:32]; cfg_req_abi_id_i=image[4][32+:32];
        cfg_req_capacity_id_i=image[5][32+:32];
        do @(posedge clk_i); while(!cfg_req_ready_o);
        @(negedge clk_i); cfg_req_valid_i=0;
        while(!cfg_rsp_valid_o) @(negedge clk_i);
        if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
            $fatal(1,"native MC config op=%0d status=%0d",op,cfg_rsp_status_o);
        cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
    endtask
    task automatic seed(input integer i, input [9:0] address, input [127:0] data);
        seed_addr=address; seed_data=data; seed_valid[i]=1;
        do @(posedge clk_i); while(!seed_ready[i]);
        @(negedge clk_i); seed_valid[i]=0;
        while(!seed_ack[i]) @(negedge clk_i);
        @(negedge clk_i);
    endtask
    task automatic verify(input integer i, input [9:0] address, input [127:0] expected);
        check_addr=address; check_read[i]=1;
        @(negedge clk_i); check_read[i]=0;
        while(!check_valid[i]) @(negedge clk_i);
        if(check_data[i]!==expected)
            $fatal(1,"P%0d SRAM addr=%0d got=%032h expected=%032h",i,address,check_data[i],expected);
        check_take[i]=1;
        @(negedge clk_i); check_take[i]=0;
    endtask
    task automatic configure_and_start;
        @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
        @(negedge clk_i); release_valid_i=0;
        cfg(0,0,0);
        for(n=0;n<words;n=n+1) cfg(1,n*16,image[n]);
        for(n=0;n<words;n=n+1) cfg(2,n*16,0);
        cfg(3,0,0); cfg(4,0,0);
        while(lc_life[0]!=4 || lc_life[1]!=4) @(negedge clk_i);
        seed(0,0,2); seed(0,1,0); seed(0,2,0); seed(0,3,0);
        seed(0,4,128'hfb0000000000000003); seed(0,5,0); seed(0,6,0); seed(0,7,0);
        seed(0,12,force_no_ack ? 128'hd8f0_1388 : 128'hd8f0_2710);
        seed(0,13,128'h0400_0200);
        seed(1,20,{16{8'had}});
        deploy_generation_i=1; grant=1; start_credit_i=1;
        while(life_o!=5 || lc_image!=2'b11) @(negedge clk_i);
        start_job_i=7; start_epoch_i=1; start_sequence_i=1; start_generation_i=1; start_valid_i=1;
        do @(posedge clk_i); while(!start_ready_o);
        @(negedge clk_i); start_valid_i=0;
    endtask
    initial begin
`include "tb_network_mc_init.svh"
        if(!$value$plusargs("MOTHER=%s",path) || !$value$plusargs("MWORDS=%d",words))
            $fatal(1,"missing native mother image");
        void'($value$plusargs("STALL=%d",stall));
        void'($value$plusargs("RESET_TRIAL=%d",reset_trial));
        $readmemh(path,image,0,words-1);
        if (image[0][64+:16]!=2) $fatal(1,"expected 64-bit mother image");
        repeat(3) @(negedge clk_i); rst_ni=1;
        if (reset_trial!=0) begin
            force_no_ack=1;
            configure_and_start();
            while(!link_ack[1]) @(negedge clk_i);
            if (transfers!=0) $fatal(1,"partial write was confirmed while ACK stalled");
            rst_ni=0; grant=0;
            repeat(6) @(negedge clk_i);
            if (|link_ack || |link_valid || |lc_event)
                $fatal(1,"coordinated reset exposed stale transfer");
            force_no_ack=0;
            rst_ni=1;
        end
        configure_and_start();
        while(!result_valid_o) @(negedge clk_i);
        if (result_status_o!=0 || transfers!=1 || offers!=1)
            $fatal(1,"unexpected result status=%0d offers=%0d transfers=%0d",result_status_o,offers,transfers);
        if (result_confirmed_write_bytes_o!=48)
            $fatal(1,"incorrect total confirmed write bytes %0d",result_confirmed_write_bytes_o);
        if (stall!=0 && (request_stall_cycles<3 || ack_stall_cycles<3))
            $fatal(1,"forward or ACK stall was not exercised");
        result_ready_i=1;
        @(negedge clk_i); result_ready_i=0;
        verify(0,8,128'hfffffff600000006);
        verify(0,14,128'd5000);
        verify(1,20,128'd5000);
        $display("PASS p16-pair stall=%0d reset=%0d offers=%0d acks=%0d request_stall=%0d ack_stall=%0d",
                 stall,reset_trial,offers,transfers,request_stall_cycles,ack_stall_cycles);
        $finish;
    end
    initial begin #1000000; $fatal(1,"native pair watchdog"); end
endmodule
