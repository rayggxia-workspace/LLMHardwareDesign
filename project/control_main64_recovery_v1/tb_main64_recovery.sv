module tb_main64_recovery;
    parameter integer KIND0=0,KIND1=KIND0;
    parameter bit PM_USE_SRAM=1;
    reg clk_i=0;always #5 clk_i=~clk_i;
    reg rst_ni=0,cmd_valid_i=0,reply_ready_i=0;
    reg [3:0] cmd_op_i=0;reg [1:0] cmd_target_i=0;
    reg [13:0] cmd_address_i=0;reg [255:0] cmd_data_i=0;
    wire cmd_ready_o,reply_valid_o,reset_ready_o,deployment_ready_o,run_active_o,link_pending_o;
    wire [15:0] reply_status_o;wire [511:0] reply_data_o;
    wire [2:0] poison_o,image_valid_o;
    wire [31:0] commit_count_o,ack_count_o;
    main64_recovery_top #(.KIND0(KIND0),.KIND1(KIND1)) dut(.*);
    reg [31:0] flow_counts[0:1];reg [127:0] flows0[0:3],flows1[0:3];integer seen0=0,seen1=0;
    always @(posedge clk_i)begin
        if(!rst_ni)begin seen0<=0;seen1<=0;end
        else if(dut.engine.start_valid_i && dut.engine.start_ready_o)begin seen0<=0;seen1<=0;end
        else begin
            if(dut.halt_i && (dut.engine.control.local0.request_seen || dut.engine.control.local1.request_seen))$fatal(1,"new native service accepted during halt");
            if(dut.engine.control.forward_valid[0] && dut.engine.control.forward_ready[0])begin
                if(seen0>=flow_counts[0] || dut.engine.control.forward_data[127:0]!==flows0[seen0])$fatal(1,"source0 held data/echo mismatch");
                seen0<=seen0+1;
            end
            if(dut.engine.control.forward_valid[1] && dut.engine.control.forward_ready[1])begin
                if(seen1>=flow_counts[1] || dut.engine.control.forward_data[255:128]!==flows1[seen1])$fatal(1,"source1 held data/echo mismatch");
                seen1<=seen1+1;
            end
        end
    end
    wire guarded_response_valid;
    generate
    if(KIND0==0)begin: injection_u
        assign guarded_response_valid=dut.engine.control.local0.u.implementation.rsp_valid;
        always @(negedge clk_i)begin
            if(inject_bad_descriptor)force dut.engine.control.local0.u.implementation.descriptor[47:32]=16'hffff;
            else release dut.engine.control.local0.u.implementation.descriptor[47:32];
            if(inject_foreign_response)force dut.engine.control.local0.u.implementation.response_epoch=32'hffffffff;
            else release dut.engine.control.local0.u.implementation.response_epoch;
        end
    end
    else if(KIND0==1)begin: injection_f
        assign guarded_response_valid=dut.engine.control.local0.f.implementation.svc_rsp_valid_i;
        always @(negedge clk_i)begin
            if(inject_bad_descriptor)force dut.engine.control.local0.f.implementation.svc_req_descriptor_o[47:32]=16'hffff;
            else release dut.engine.control.local0.f.implementation.svc_req_descriptor_o[47:32];
            if(inject_foreign_response)force dut.engine.control.local0.f.implementation.svc_rsp_epoch_i=32'hffffffff;
            else release dut.engine.control.local0.f.implementation.svc_rsp_epoch_i;
        end
    end
    else if(KIND0==2)begin: injection_c
        assign guarded_response_valid=dut.engine.control.local0.c.implementation.svc_rsp_valid_i;
        always @(negedge clk_i)begin
            if(inject_bad_descriptor)force dut.engine.control.local0.c.implementation.svc_req_descriptor_o[47:32]=16'hffff;
            else release dut.engine.control.local0.c.implementation.svc_req_descriptor_o[47:32];
            if(inject_foreign_response)force dut.engine.control.local0.c.implementation.svc_rsp_epoch_i=32'hffffffff;
            else release dut.engine.control.local0.c.implementation.svc_rsp_epoch_i;
        end
    end
    else if(KIND0==3)begin: injection_p
        assign guarded_response_valid=dut.engine.control.local0.p.implementation.rsp_valid;
        always @(negedge clk_i)begin
            if(inject_bad_descriptor)force dut.engine.control.local0.p.implementation.descriptor[47:32]=16'hffff;
            else release dut.engine.control.local0.p.implementation.descriptor[47:32];
            if(inject_foreign_response)force dut.engine.control.local0.p.implementation.response_epoch=32'hffffffff;
            else release dut.engine.control.local0.p.implementation.response_epoch;
        end
    end
    else if(KIND0==4)begin: injection_j
        assign guarded_response_valid=dut.engine.control.local0.j.implementation.svc_rsp_valid_i;
        always @(negedge clk_i)begin
            if(inject_bad_descriptor)force dut.engine.control.local0.j.implementation.svc_req_descriptor_o[47:32]=16'hffff;
            else release dut.engine.control.local0.j.implementation.svc_req_descriptor_o[47:32];
            if(inject_foreign_response)force dut.engine.control.local0.j.implementation.svc_rsp_epoch_i=32'hffffffff;
            else release dut.engine.control.local0.j.implementation.svc_rsp_epoch_i;
        end
    end
    endgenerate
    reg [1319:0] commands[0:4095];reg [31:0] counts[0:2];
    reg [1319:0] cmd;reg [511:0] answer;reg [527:0] held;
    integer variant=0,stall=0,position,polls,accepted=0,mode=0;
    reg injected=0,inject_bad_descriptor=0,inject_foreign_response=0;
    reg [127:0] start_identity;reg [511:0] corrupt_ack;
    string next_root;
    string root;
    task automatic tick;@(negedge clk_i);endtask
    task automatic issue(input [1319:0] entry);
        tick();cmd_valid_i=1;cmd_op_i=entry[1315:1312];cmd_target_i=entry[1311:1310];
        cmd_address_i=entry[1309:1296];cmd_data_i=entry[1295:1040];
        do @(posedge clk_i);while(!cmd_ready_o);
        tick();cmd_valid_i=0;cmd_op_i=15;cmd_target_i=3;cmd_address_i='1;cmd_data_i='1;
        while(!reply_valid_o)tick();
        if(reply_status_o!==entry[1039:1024])$fatal(1,"compiled status pos=%0d op=%0d got=%h expected=%h",position,entry[1315:1312],reply_status_o,entry[1039:1024]);
        answer=reply_data_o;held={reply_status_o,reply_data_o};
        repeat(stall+position%3)begin
            tick();if(!reply_valid_o || cmd_ready_o || {reply_status_o,reply_data_o}!==held)$fatal(1,"compiled host response lost under backpressure");
        end
        reply_ready_i=1;tick();reply_ready_i=0;tick();accepted++;
    endtask

    task automatic command(input [3:0] op,input [255:0] data,input [15:0] status);
        reg [1319:0] entry;
        begin entry=0;entry[1315:1312]=op;entry[1311:1310]=3;entry[1295:1040]=data;entry[1039:1024]=status;issue(entry);end
    endtask
    task automatic load_case(input string folder);
        begin
            $readmemh({folder,"/count.mem"},counts);$readmemh({folder,"/replay.mem"},commands,0,counts[0]-1);
            $readmemh({folder,"/flow-counts.mem"},flow_counts);
            if(flow_counts[0])$readmemh({folder,"/flows0.mem"},flows0,0,flow_counts[0]-1);
            if(flow_counts[1])$readmemh({folder,"/flows1.mem"},flows1,0,flow_counts[1]-1);
        end
    endtask
    task automatic cancel_job(input bit foreign);
        reg [255:0] data;
        begin
            data=0;data[47:16]=start_identity[31:0];data[79:48]=start_identity[63:32];
            data[111:80]=start_identity[95:64];data[143:112]=start_identity[127:96];
            if(foreign)data[16]^=1'b1;
            command(15,data,foreign ? 16'h107 : 16'd0);
        end
    endtask
    task automatic recovery_status;
        begin command(15,256'd2,0);end
    endtask
    task automatic wait_failure(input bit quarantine,input [15:0] reason);
        reg [511:0] failure;
        integer n;
        begin
            n=0;
            do begin recovery_status();n++;if(n>1000)$fatal(1,"recovery failed to publish");end while(!answer[18]);
            if(answer[19]!==quarantine)$fatal(1,"quarantine status mismatch");
            command(10,0,0);failure=answer;
            if(failure[31:0]!==start_identity[31:0] || failure[63:32]!==start_identity[63:32] ||
               failure[95:64]!==start_identity[95:64] || failure[111:96]!==reason ||
               !failure[282] || failure[283]!==quarantine || !failure[284])$fatal(1,"persistent failure identity/status mismatch");
            // A result is consumed exactly once, even while quarantine persists.
            command(10,0,16'h105);
        end
    endtask
    task automatic wait_normal;
        integer n;
        begin
            n=0;
            do begin recovery_status();n++;if(n>1000)$fatal(1,"recovery did not return to NORMAL");end while(answer[22:20]!=0);
            if(image_valid_o!=0 || run_active_o || link_pending_o)$fatal(1,"coordinated reset did not revoke complete cohort");
            command(0,{192'b0,start_identity[63:32],start_identity[127:96]},16'h107);
        end
    endtask
    task automatic fault_flow;
        integer n;reg [31:0] before_ack;reg [127:0] held_data;
        begin
            if(mode==8)begin
                command(15,256'd1,16'h103);
                command(15,256'h101,0);
                wait_normal();
            end else if(mode==7)begin
                inject_bad_descriptor=1;
                n=0;while(!dut.engine.control.local0.request_seen)begin tick();n++;if(n>20000)$fatal(1,"no native ingress for descriptor fault");end
                repeat(2)tick();inject_bad_descriptor=0;tick();
                wait_failure(0,16'h200);wait_normal();
            end else if(mode==3)begin
                inject_foreign_response=1;
                n=0;while(!guarded_response_valid)begin tick();n++;if(n>20000)$fatal(1,"no guarded native response");end
                repeat(8)begin tick();if(dut.engine.control.local0.response_seen)$fatal(1,"foreign service identity accepted");end
                cancel_job(0);inject_foreign_response=0;tick();
                wait_failure(0,16'd11);wait_normal();
            end else if(mode==5 || mode==6 || mode==10)begin
                n=0;
                if(mode==10)begin
                    while(!dut.engine.control.link_ack_valid[1])begin tick();n++;if(n>20000)$fatal(1,"reverse ACK not offered");end
                    corrupt_ack=dut.engine.control.ack_identity[1023:512]^(512'd1<<262);
                    force dut.engine.control.ack_identity[1023:512]=corrupt_ack;
                    held_data=dut.engine.control.links[1].transfer.data;
                end else begin
                    while(!dut.engine.control.link_ack_valid[0])begin tick();n++;if(n>20000)$fatal(1,"ACK not offered");end
                    corrupt_ack=dut.engine.control.ack_identity[511:0]^(512'd1<<99);
                    force dut.engine.control.ack_identity[511:0]=corrupt_ack;
                    held_data=dut.engine.control.links[0].transfer.data;
                end
                before_ack=ack_count_o;
                repeat(8)begin
                    tick();if(ack_count_o!=before_ack || !dut.inner_rst_ni)$fatal(1,"foreign ACK released ownership/reset");
                    if(mode==10 ? dut.engine.control.links[1].transfer.data!==held_data : dut.engine.control.links[0].transfer.data!==held_data)$fatal(1,"source data changed before acknowledged commit");
                end
                if(mode==6)begin
                    n=0;
                    do begin recovery_status();n++;if(n>1000)$fatal(1,"no drain timeout quarantine");if(!dut.inner_rst_ni)$fatal(1,"reset abandoned pending word");end while(!answer[19]);
                    command(8,start_identity,16'h106);
                    wait_failure(1,16'h201);
                end
                if(mode==10)release dut.engine.control.ack_identity[1023:512];
                else release dut.engine.control.ack_identity[511:0];
                tick();
                if(mode==6)begin command(15,256'd3,0);wait_normal();end
                else begin wait_failure(0,16'h200);wait_normal();end
            end else if(mode==9)begin
                force dut.engine.control.links[0].transfer.legal=1'b0;
                n=0;while(!dut.engine.control.link_busy[0])begin tick();n++;if(n>20000)$fatal(1,"no held unoffered word");end
                if(dut.engine.control.links[0].transfer.offered)$fatal(1,"expected unoffered ownership");
                cancel_job(0);
                release dut.engine.control.links[0].transfer.legal;
                wait_failure(0,16'd11);wait_normal();
            end else begin
                if(mode==4)begin
                    n=0;while(!dut.engine.control.links[0].transfer.sent)begin tick();n++;if(n>20000)$fatal(1,"no accepted destination write");end
                end
                if(mode==2)begin cancel_job(1);if(dut.halt_i)$fatal(1,"foreign cancel affected job");end
                cancel_job(0);wait_failure(0,16'd11);wait_normal();
            end
            injected=1;
        end
    endtask
    initial begin
        if(!$value$plusargs("ROOT=%s",root))$fatal(1,"missing audited replay root");
        void'($value$plusargs("MODE=%d",mode));void'($value$plusargs("NEXT=%s",next_root));
        void'($value$plusargs("CASE=%d",variant));void'($value$plusargs("STALL=%d",stall));
        $readmemh({root,"/count.mem"},counts);
        $readmemh({root,"/flow-counts.mem"},flow_counts);
        if(flow_counts[0])$readmemh({root,"/flows0.mem"},flows0,0,flow_counts[0]-1);
        if(flow_counts[1])$readmemh({root,"/flows1.mem"},flows1,0,flow_counts[1]-1);
        if(counts[0]==0 || counts[0]>4096)$fatal(1,"replay count");
        $readmemh({root,"/replay.mem"},commands,0,counts[0]-1);
        repeat(6)tick();rst_ni=1;while(!reset_ready_o)tick();repeat(4)tick();
        for(position=0;position<counts[0];position++)begin
            cmd=commands[position];polls=0;
            if(cmd[1319:1316]>1)$fatal(1,"unknown host replay mode");
            if(mode!=0 && !injected && cmd[1315:1312]==8 && cmd[1039:1024]==0)begin
                start_identity=cmd[1167:1040];
                if(mode!=8)issue(cmd);
                fault_flow();
                if(next_root=="")$fatal(1,"missing fresh-epoch reload");
                load_case(next_root);position=-1;tick();
            end else do begin
                issue(cmd);polls++;
                if(polls>5000)$fatal(1,"compiled task did not terminate pos=%0d",position);
            end while(cmd[1319:1316]==1 && (answer&cmd[1023:512])!==cmd[511:0]);
            if(position!=-1 && (answer&cmd[1023:512])!==cmd[511:0])$fatal(1,"compiled data/CRC/result pos=%0d got=%h expected=%h mask=%h",position,answer,cmd[511:0],cmd[1023:512]);
        end
        if(image_valid_o!=7 || |poison_o || run_active_o || link_pending_o)$fatal(1,"compiled cohort not clean");
        if(commit_count_o!=counts[1] || ack_count_o!=counts[1])$fatal(1,"compiled commits/ACK mismatch");
        if(seen0!=flow_counts[0] || seen1!=flow_counts[1])$fatal(1,"missing end-to-end transfer");
        if(dut.observed_writes_o!=counts[2])$fatal(1,"live committed write ledger mismatch got=%0d expected=%0d",dut.observed_writes_o,counts[2]);
        $display("PASS safe64 kinds=%0d/%0d case=%0d mode=%0d requests=%0d commits=%0d",KIND0,KIND1,variant,mode,accepted,commit_count_o);$finish;
    end
    initial begin #50000000;$fatal(1,"compiled replay watchdog");end
endmodule
