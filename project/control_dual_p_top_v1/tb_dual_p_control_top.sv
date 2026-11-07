module tb_dual_p_control_top;
    reg clk_i;
    reg rst_ni;
    reg deploy_valid_i;
    reg [31:0] deploy_generation_i;
    reg [2:0] release_valid_i;
    reg [95:0] release_sequence_i;
    reg [95:0] release_epoch_i;
    wire [2:0] release_ready_o;
    wire [2:0] poison_o;
    wire [2:0] image_valid_o;
    reg [2:0] cfg_req_valid_i;
    reg [8:0] cfg_req_op_i;
    reg [95:0] cfg_req_generation_i;
    reg [41:0] cfg_req_address_i;
    reg [383:0] cfg_req_data_i;
    reg [47:0] cfg_req_total_bytes_i;
    reg [95:0] cfg_req_image_id_i;
    reg [95:0] cfg_req_topology_id_i;
    reg [95:0] cfg_req_abi_id_i;
    reg [95:0] cfg_req_capacity_id_i;
    reg [2:0] cfg_req_proof_i;
    reg [2:0] cfg_rsp_ready_i;
    wire [2:0] cfg_req_ready_o;
    wire [2:0] cfg_rsp_valid_o;
    wire [47:0] cfg_rsp_status_o;
    wire [383:0] cfg_rsp_data_o;
    wire [95:0] cfg_rsp_generation_o;
    reg [2:0] pm_req_ready_i;
    reg [2:0] pm_rsp_valid_i;
    reg [383:0] pm_rsp_data_i;
    reg [2:0] pm_rsp_error_i;
    wire [2:0] pm_req_valid_o;
    wire [2:0] pm_req_write_o;
    wire [41:0] pm_req_address_o;
    wire [383:0] pm_req_data_o;
    wire [2:0] pm_rsp_ready_o;
    wire [11:0] life_o;
    wire [11:0] seq_o;
    reg start_valid_i;
    reg start_credit_i;
    reg [31:0] start_job_i;
    reg [31:0] start_epoch_i;
    reg [31:0] start_sequence_i;
    reg [31:0] start_generation_i;
    reg [255:0] start_args_i;
    wire start_ready_o;
    wire result_valid_o;
    reg result_ready_i;
    wire [31:0] result_job_o;
    wire [31:0] result_epoch_o;
    wire [31:0] result_sequence_o;
    wire [15:0] result_status_o;
    wire [31:0] result_error_pc_o;
    wire [7:0] result_source_o;
    wire [31:0] result_child_error_pc_o;
    wire [31:0] result_failed_task_sequence_o;
    wire [31:0] result_confirmed_read_bytes_o;
    wire [31:0] result_confirmed_write_bytes_o;
    wire result_counter_overflow_o;
    wire result_saturated_o;
    reg [1:0] host_req_valid_i;
    reg [1:0] host_req_write_i;
    reg [19:0] host_req_address_i;
    reg [255:0] host_req_data_i;
    wire [1:0] host_req_ready_o;
    wire [1:0] host_rsp_valid_o;
    reg [1:0] host_rsp_ready_i;
    wire [255:0] host_rsp_data_o;
    wire reset_ready_o;
    wire deployment_ready_o;
    wire run_active_o;
    wire link_pending_o;
    wire ack_rejected_o;
    wire [31:0] commit_count_o;
    wire [31:0] ack_count_o;
    dual_p_control_top dut(.*);
    initial clk_i=0;always #5 clk_i=~clk_i;
    reg [31:0] cycle=0,epoch=1;
    integer mode=0,stall=0;
    always @(posedge clk_i) cycle<=cycle+1;
    for(genvar i=0;i<3;i=i+1) begin: programs
        network_pm pm(.clk_i,.rst_ni(reset_ready_o),.cycle_i(cycle),.stall_i(stall),
            .pm_req_valid_o(pm_req_valid_o[i]),.pm_req_write_o(pm_req_write_o[i]),
            .pm_req_address_o(pm_req_address_o[i*14+:14]),.pm_req_data_o(pm_req_data_o[i*128+:128]),
            .pm_req_ready_i(pm_req_ready_i[i]),.pm_rsp_valid_i(pm_rsp_valid_i[i]),
            .pm_rsp_data_i(pm_rsp_data_i[i*128+:128]),.pm_rsp_error_i(pm_rsp_error_i[i]),
            .pm_rsp_ready_o(pm_rsp_ready_o[i]),.fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
    end
    reg [127:0] im0[0:519],im1[0:519],im2[0:519];
    integer words[3];
    string path0,path1,path2;
    function automatic [127:0] word_at(input integer who,index);
        case(who) 0:return im0[index];1:return im1[index];default:return im2[index];endcase
    endfunction
    task automatic tick;@(negedge clk_i);endtask
    task automatic cfg(input integer who,input [2:0] op,input integer address,input [127:0] value);
        reg [127:0] h3,h4,h5;
        h3=word_at(who,3);h4=word_at(who,4);h5=word_at(who,5);
        tick();cfg_req_valid_i[who]=1;cfg_req_op_i[who*3+:3]=op;
        cfg_req_generation_i[who*32+:32]=epoch;cfg_req_address_i[who*14+:14]=14'(address);
        cfg_req_data_i[who*128+:128]=value;cfg_req_total_bytes_i[who*16+:16]=16'(words[who]*16);
        cfg_req_image_id_i[who*32+:32]=h3[96+:32];cfg_req_topology_id_i[who*32+:32]=h4[0+:32];
        cfg_req_abi_id_i[who*32+:32]=h4[32+:32];cfg_req_capacity_id_i[who*32+:32]=h5[32+:32];
        cfg_req_proof_i[who]=1;
        do @(posedge clk_i);while(!cfg_req_ready_o[who]);
        tick();cfg_req_valid_i[who]=0;
        while(!cfg_rsp_valid_o[who])tick();
        if(cfg_rsp_status_o[who*16+:16]!=0 || (op==2 && cfg_rsp_data_o[who*128+:128]!==word_at(who,address>>4)))
            $fatal(1,"top config who=%0d op=%0d address=%0d status=%0d",who,op,address,cfg_rsp_status_o[who*16+:16]);
        cfg_rsp_ready_i[who]=1;tick();cfg_rsp_ready_i[who]=0;
    endtask
    task automatic host(input integer who,input bit wr,input [9:0] address,input [127:0] value);
        host_req_write_i[who]=wr;host_req_address_i[who*10+:10]=address;
        host_req_data_i[who*128+:128]=value;host_req_valid_i[who]=1;
        do @(posedge clk_i);while(!host_req_ready_o[who]);
        tick();host_req_valid_i[who]=0;
        while(!host_rsp_valid_o[who])tick();
        if(!wr && host_rsp_data_o[who*128+:128]!==value)
            $fatal(1,"top SRAM mismatch side=%0d address=%0d got=%032h expected=%032h",who,address,host_rsp_data_o[who*128+:128],value);
        host_rsp_ready_i[who]=1;tick();host_rsp_ready_i[who]=0;
    endtask
    task automatic configure;
        while(!reset_ready_o)tick();
        release_valid_i=3'b111;release_sequence_i={3{epoch}};release_epoch_i={3{epoch}};
        tick();release_valid_i=0;
        for(integer c=0;c<3;c=c+1)begin
            cfg(c,0,0,0);
            for(integer n=0;n<words[c];n=n+1)cfg(c,1,n*16,word_at(c,n));
            for(integer n=0;n<words[c];n=n+1)cfg(c,2,n*16,0);
            cfg(c,3,0,0);cfg(c,4,0,0);
        end
        if(!deployment_ready_o) $fatal(1,"top images did not reach deployment readiness");
        host(0,1,0,2);host(0,1,1,0);host(0,1,2,0);host(0,1,3,0);
        host(0,1,4,128'hfb0000000000000003);host(0,1,5,0);host(0,1,6,0);host(0,1,7,0);
        host(0,1,12,128'hd8f0_2710);host(0,1,13,128'h0400_0200);
        host(1,1,20,{16{8'had}});
        deploy_generation_i=epoch;deploy_valid_i=1;start_credit_i=1;
        while(!start_ready_o)tick();
    endtask
    task automatic start_job(input [31:0] job_id,sequence_id);
        start_job_i=job_id;start_epoch_i=epoch;start_sequence_i=sequence_id;start_generation_i=epoch;
        start_valid_i=1;do @(posedge clk_i);while(!start_ready_o);tick();start_valid_i=0;
        if(!run_active_o)$fatal(1,"top did not track active job");
        host_req_valid_i=2'b11;
        repeat(3)begin if(host_req_ready_o!=0)$fatal(1,"host access admitted during job");tick();end
        host_req_valid_i=0;
    endtask
    task automatic finish_job(input [31:0] job_id,sequence_id,input integer transfers);
        reg [143:0] held;
        while(!result_valid_o)tick();
        if(result_status_o!=0 || result_job_o!=job_id || result_sequence_o!=sequence_id || result_epoch_o!=epoch ||
            result_confirmed_write_bytes_o!=48 || commit_count_o!=transfers || ack_count_o!=transfers)
            $fatal(1,"top completion status=%0d writes=%0d commits=%0d acks=%0d",result_status_o,result_confirmed_write_bytes_o,commit_count_o,ack_count_o);
        held={result_job_o,result_epoch_o,result_sequence_o,result_status_o,32'b0};
        repeat(7)begin tick();if(!result_valid_o || held!={result_job_o,result_epoch_o,result_sequence_o,result_status_o,32'b0})$fatal(1,"top result changed under backpressure");end
        result_ready_i=1;tick();result_ready_i=0;
        host(0,0,8,128'hfffffff600000006);host(0,0,14,128'd5000);host(1,0,20,128'd5000);
    endtask
    always @(posedge clk_i)if(reset_ready_o)begin
        if(ack_count_o>commit_count_o)$fatal(1,"top released source before destination commit");
    end
    initial begin
        rst_ni='0;
        deploy_valid_i='0;
        deploy_generation_i='0;
        release_valid_i='0;
        release_sequence_i='0;
        release_epoch_i='0;
        cfg_req_valid_i='0;
        cfg_req_op_i='0;
        cfg_req_generation_i='0;
        cfg_req_address_i='0;
        cfg_req_data_i='0;
        cfg_req_total_bytes_i='0;
        cfg_req_image_id_i='0;
        cfg_req_topology_id_i='0;
        cfg_req_abi_id_i='0;
        cfg_req_capacity_id_i='0;
        cfg_req_proof_i='0;
        cfg_rsp_ready_i='0;
        start_valid_i='0;
        start_credit_i='0;
        start_job_i='0;
        start_epoch_i='0;
        start_sequence_i='0;
        start_generation_i='0;
        start_args_i='0;
        result_ready_i='0;
        host_req_valid_i='0;
        host_req_write_i='0;
        host_req_address_i='0;
        host_req_data_i='0;
        host_rsp_ready_i='0;
        if(!$value$plusargs("MOTHER=%s",path0)||!$value$plusargs("MWORDS=%d",words[0])||
           !$value$plusargs("LOCAL0=%s",path1)||!$value$plusargs("WORDS0=%d",words[1])||
           !$value$plusargs("LOCAL1=%s",path2)||!$value$plusargs("WORDS1=%d",words[2]))$fatal(1,"top missing images");
        void'($value$plusargs("MODE=%d",mode));stall=mode==1 ? 2 : 0;
        $readmemh(path0,im0,0,words[0]-1);$readmemh(path1,im1,0,words[1]-1);$readmemh(path2,im2,0,words[2]-1);
        repeat(5)tick();rst_ni=1;configure();start_job(7,1);
        if(mode==3)begin
            while(!link_pending_o)tick();
            rst_ni=0;deploy_valid_i=0;repeat(6)tick();
            if(link_pending_o || result_valid_o || ack_count_o!=0 || commit_count_o!=0)$fatal(1,"top retained reset transaction");
            epoch=2;rst_ni=1;configure();start_job(8,1);finish_job(8,1,1);
        end else if(mode==4)begin
            while(!dut.raw_ack_valid)tick();
            force dut.returned_identity=128'hbad;
            tick();release dut.returned_identity;
            while(poison_o==0)tick();
            if(commit_count_o!=1 || ack_count_o!=0 || !link_pending_o ||
               !dut.p0.io_rsp_valid[1] || dut.p0.link_take)$fatal(1,"bad identity released source");
            rst_ni=0;deploy_valid_i=0;repeat(6)tick();epoch=2;rst_ni=1;
            configure();start_job(8,1);finish_job(8,1,1);
        end else begin
            finish_job(7,1,1);
            if(mode==2)begin host(1,1,20,{16{8'h5a}});start_job(8,2);finish_job(8,2,2);end
        end
        if(|poison_o)$fatal(1,"top ended poisoned");
        $display("PASS dual-p-top mode=%0d epoch=%0d commits=%0d acks=%0d",mode,epoch,commit_count_o,ack_count_o);
        $finish;
    end
    initial begin #2000000;$fatal(1,"top watchdog life=%h poison=%h",life_o,poison_o);end
endmodule
