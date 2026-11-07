module tb_recovery_boot;
    parameter integer KIND=0;parameter bit PM_USE_SRAM=1;
    reg clk_i;
    reg rst_ni;
    reg cmd_valid_i;
    wire cmd_ready_o;
    reg [3:0] cmd_op_i;
    reg [1:0] cmd_target_i;
    reg [13:0] cmd_address_i;
    reg [255:0] cmd_data_i;
    wire reply_valid_o;
    reg reply_ready_i;
    wire [15:0] reply_status_o;
    wire [511:0] reply_data_o;
    wire [2:0] poison_o;
    wire [2:0] image_valid_o;
    wire reset_ready_o;
    wire deployment_ready_o;
    wire run_active_o;
    wire link_pending_o;
    wire [31:0] commit_count_o;
    wire [31:0] ack_count_o;
    recovery_boot_top #(.KIND(KIND),.PM_USE_SRAM(PM_USE_SRAM)) dut(.*);

    initial clk_i=0;always #5 clk_i=~clk_i;
    reg [127:0] im0[0:519],im1[0:519],im2[0:519];
    reg [31:0] counts[0:4],expected_crc[0:2];
    reg [275:0] seeds[0:63];
    reg [1043:0] checks[0:31];
    reg [31:0] epoch=1;
    integer mode=0,negative_checks=0;
    string root,folder;
    reg [511:0] answer;
    function automatic [127:0] word_at(input integer who,index);
        case(who)0:return im0[index];1:return im1[index];default:return im2[index];endcase
    endfunction
    function automatic [255:0] manifest(input integer who,input [31:0] gen);
        reg [127:0] h3,h4,h5;reg [255:0] v;
        h3=word_at(who,3);h4=word_at(who,4);h5=word_at(who,5);v=0;
        v[31:0]=gen;v[47:32]=16'(counts[who]*16);v[79:48]=h3[96+:32];
        v[111:80]=h4[0+:32];v[143:112]=h4[32+:32];v[175:144]=h5[32+:32];return v;
    endfunction
    task automatic tick;@(negedge clk_i);endtask
    task automatic request(input [3:0] op,input [1:0] target,input [13:0] addr,input [255:0] value,input [15:0] status);
        reg [527:0] held;
        tick();cmd_valid_i=1;cmd_op_i=op;cmd_target_i=target;cmd_address_i=addr;cmd_data_i=value;
        do @(posedge clk_i);while(!cmd_ready_o);
        tick();cmd_valid_i=0;cmd_op_i=15;cmd_target_i=3;cmd_address_i='1;cmd_data_i='1;
        while(!reply_valid_o)tick();
        if(reply_status_o!==status)$fatal(1,"hetero status kind=%0d mode=%0d op=%0d target=%0d addr=%0d got=%h expected=%h",KIND,mode,op,target,addr,reply_status_o,status);
        answer=reply_data_o;held={reply_status_o,reply_data_o};
        repeat(4)begin tick();if(!reply_valid_o || cmd_ready_o || {reply_status_o,reply_data_o}!==held)$fatal(1,"hetero reply not held");end
        reply_ready_i=1;tick();reply_ready_i=0;tick();
        if(status!=0)negative_checks++;
    endtask
    task automatic load_case(input integer variant,input bit fault);
        folder=fault ? $sformatf("%s/e%0d-fault",root,epoch) : $sformatf("%s/e%0d-v%0d",root,epoch,variant);
        $readmemh({folder,"/counts.mem"},counts);$readmemh({folder,"/crc.mem"},expected_crc);
        $readmemh({folder,"/mother.mem"},im0,0,counts[0]-1);$readmemh({folder,"/local0.mem"},im1,0,counts[1]-1);$readmemh({folder,"/local1.mem"},im2,0,counts[2]-1);
        $readmemh({folder,"/seeds.mem"},seeds,0,counts[3]-1);$readmemh({folder,"/checks.mem"},checks,0,counts[4]-1);
    endtask
    task automatic reset_cohort;
        rst_ni=0;cmd_valid_i=0;reply_ready_i=0;repeat(6)tick();
        if(reply_valid_o || cmd_ready_o || image_valid_o!=0 || link_pending_o)$fatal(1,"hetero reset retained state");
        rst_ni=1;while(!reset_ready_o)tick();repeat(4)tick();
        request(8,3,0,{128'b0,epoch,32'd1,epoch,32'd7},16'h105);
        if(KIND==4)begin request(13,1,0,0,16'h105);request(0,3,0,{192'b0,32'd256,32'd1},16'h103);end
        else begin request(13,1,0,0,4);request(14,1,0,0,4);end
    endtask
    task automatic configure(output bit configured);
        reg [255:0] v;reg [127:0] expected;
        configured=1;
        request(0,3,0,{192'b0,epoch,epoch},0);request(7,3,0,epoch,16'h105);
        for(integer c=0;c<3;c++)begin
            v=manifest(c,epoch);v[143:112]^=1;request(1,2'(c),0,v,3);
            request(1,2'(c),0,manifest(c,epoch),0);
            request(2,2'(c),16,{128'b0,word_at(c,0)},16'h107);
            expected=word_at(c,0);expected[79:64]=1;request(2,2'(c),0,{128'b0,expected},16'h103);
            for(integer n=0;n<counts[c];n++)request(2,2'(c),14'(n*16),{128'b0,word_at(c,n)},0);
            request(4,2'(c),0,0,16'h105);request(5,2'(c),0,0,16'h105);
            for(integer n=0;n<counts[c];n++)begin
                expected=word_at(c,n);
                request(3,2'(c),14'(n*16),0,0);
                if(answer[127:0]!==expected)$fatal(1,"hetero PM readback mismatch");
            end
            request(4,2'(c),0,0,0);
            if(answer[31:0]!==expected_crc[c] || answer[63:32]!==expected_crc[c])$fatal(1,"hetero independent CRC32 mismatch");
            request(5,2'(c),0,0,0);
        end
        request(7,3,0,epoch,0);
        if(image_valid_o!=7)$fatal(1,"hetero deployment");
    endtask
    task automatic seed_data;
        if(KIND==4)begin
            request(11,1,0,0,4);request(12,1,0,0,4);
            request(14,1,0,{93'b0,1'b1,2'b00,32'hba000007,128'd0},5);
        end
        for(integer n=0;n<counts[3];n++)request(seeds[n][275:272],seeds[n][271:270],seeds[n][269:256],seeds[n][255:0],0);
    endtask
    task automatic run_job(input [31:0] job_id,sequence_id,input bit fault);
        integer polls;integer write_bytes;integer transfers;
        case(KIND)0:write_bytes=80;1:write_bytes=64;2:write_bytes=80;default:write_bytes=144;endcase
        transfers=KIND==4 ? 4 : 1;
        request(8,3,0,{128'b0,epoch,sequence_id,epoch,job_id},0);
        if(!run_active_o)$fatal(1,"hetero START");
        request(2,0,0,0,16'h106);request(12,2,0,0,16'h106);
        polls=0;
        do begin request(9,3,0,0,0);polls++;if(polls>4000)$fatal(1,"hetero job stalled");end while(!answer[18]);
        request(10,3,0,0,0);
        if(answer[31:0]!=job_id || answer[63:32]!=epoch || answer[95:64]!=sequence_id || answer[111:96]!=0 || answer[279:248]!=write_bytes)
            $fatal(1,"hetero result kind=%0d got=%h writes=%0d",KIND,answer,answer[279:248]);
        if(link_pending_o || commit_count_o!=transfers*sequence_id || ack_count_o!=transfers*sequence_id)$fatal(1,"hetero obligations/counts");
        for(integer n=0;n<counts[4];n++)begin
            request(checks[n][1043:1040],checks[n][1039:1038],checks[n][1037:1024],0,0);
            if((answer&checks[n][1023:512])!==checks[n][511:0])$fatal(1,"hetero numeric kind=%0d check=%0d got=%h expected=%h",KIND,n,answer,checks[n][511:0]);
        end
        if(|poison_o)$fatal(1,"hetero poisoned");
    endtask

    function automatic [255:0] recovery_command(input [7:0] operation,mask,input [31:0] job_id);
        reg [255:0] v;v=0;v[7:0]=operation;v[15:8]=mask;
        v[47:16]=job_id;v[79:48]=epoch;v[111:80]=1;v[143:112]=epoch;return v;
    endfunction
    task automatic start_trial;
        request(8,3,0,{128'b0,epoch,32'd1,epoch,32'd7},0);
        if(!run_active_o)$fatal(1,"recovery trial did not start");
    endtask
    task automatic read_failure(input [15:0] expected_status,input bit quarantined,input integer commits,input [7:0] mask);
        integer polls;polls=0;
        do begin request(9,3,0,0,0);polls++;if(polls>1000)$fatal(1,"recovery missing failure");end while(!answer[18]);
        request(10,3,0,0,0);
        if(answer[31:0]!=7 || answer[63:32]!=epoch || answer[95:64]!=1 || answer[111:96]!=expected_status ||
           !answer[282] || answer[283]!=quarantined || !answer[284] || answer[356:349]!=mask)
            $fatal(1,"recovery failure packet kind=%0d mode=%0d data=%h",KIND,mode,answer);
        if(commits>=0 && answer[316:285]!=commits)$fatal(1,"recovery commit accounting got=%0d expected=%0d",answer[316:285],commits);
        if(!quarantined && (image_valid_o!=0 || !reset_ready_o))$fatal(1,"recovery cohort not invalidated");
        request(10,3,0,0,16'h105);
        if(!quarantined && commits>=0)begin
            request(11,2,14'(60*16),0,0);
            if(commits==0 && answer[127:0]!==128'hffffffffffffffffffffffffffffffff)$fatal(1,"uncommitted destination changed");
            if(commits!=0)begin
                for(integer n=0;n<counts[4];n++)if(checks[n][1039:1038]==2 && checks[n][1037:1024]==60*16)
                    if(answer[127:0]!==checks[n][127:0])$fatal(1,"committed data lost across coordinated reset");
            end
        end
    endtask
    task automatic wait_idle_recovery;
        integer polls;polls=0;
        do begin request(15,3,0,256'd2,0);polls++;if(polls>1000)$fatal(1,"recovery retry did not reset");end while(answer[22:20]!=0 || !reset_ready_o);
        if(image_valid_o!=0)$fatal(1,"idle reset retained deployment");
    endtask
    task automatic finish_success;
        integer polls;integer expected;integer words;
        case(KIND)0:expected=80;1:expected=64;2:expected=80;default:expected=144;endcase
        words=KIND==4 ? 4 : 1;polls=0;
        do begin request(9,3,0,0,0);polls++;if(polls>4000)$fatal(1,"successful trial stalled");end while(!answer[18]);
        if(mode==16)request(15,3,0,recovery_command(0,0,7),16'h106);
        request(10,3,0,0,0);
        if(answer[111:96]!=0 || answer[279:248]!=expected || commit_count_o!=words || ack_count_o!=words || link_pending_o)$fatal(1,"normal behavior changed");
        for(integer n=0;n<counts[4];n++)begin
            request(checks[n][1043:1040],checks[n][1039:1038],checks[n][1037:1024],0,0);
            if((answer&checks[n][1023:512])!==checks[n][511:0])$fatal(1,"recovery final data mismatch");
        end
    endtask
    task automatic reload_and_run;
        // Supervisor survives inner reset: old epoch is rejected before forwarding.
        request(0,3,0,{192'b0,32'd1,32'd1},16'h107);
        epoch=2;load_case(0,0);configure(configured);seed_data();
        if(mode==13)fresh_job=1;
        run_job(8,1,0);
        if(mode==13 && !late_ack_tested)$fatal(1,"old-epoch ACK injection missed");
    endtask
    bit configured,fresh_job=0,late_ack_tested=0;
    initial begin
        wait(fresh_job);wait(dut.engine.control.ack_valid[0]);
        force dut.engine.control.ack_identity[0+:128]=dut.engine.control.data_link.identity ^ (128'd3<<64);
        repeat(16)begin tick();if(ack_count_o!=0 || dut.engine.control.local0.transfer.mem_rsp_ready || dut.engine.control.local0.transfer.committed_take)$fatal(1,"old epoch ACK consumed new source");end
        release dut.engine.control.ack_identity[0+:128];late_ack_tested=1;
    end
    initial begin
        rst_ni=0;cmd_valid_i=0;cmd_op_i=0;cmd_target_i=0;cmd_address_i=0;cmd_data_i=0;reply_ready_i=0;
        if(!$value$plusargs("ROOT=%s",root))$fatal(1,"missing recovery images");
        void'($value$plusargs("MODE=%d",mode));load_case(0,mode==7);reset_cohort();configure(configured);seed_data();
        if(mode==18)begin
            force dut.engine.control.data_link.source_valid=0;force dut.engine.control.local0.transfer.tx_ready=0;
            start_trial();wait(dut.engine.control.local0.transfer.state==2);
            tick();cmd_valid_i=1;cmd_op_i=10;cmd_target_i=3;cmd_address_i=0;cmd_data_i=0;
            do @(posedge clk_i);while(!cmd_ready_o);
            tick();cmd_valid_i=0;while(!reply_valid_o)tick();
            if(reply_status_o!=16'h105)$fatal(1,"RESULT probe was not pending");
            force dut.engine.control.fault_o=1;
            repeat(1500)begin tick();if(!reply_valid_o || reply_status_o!=16'h105 || !dut.inner_rst_ni)$fatal(1,"fault lost held unsuccessful RESULT response");end
            reply_ready_i=1;tick();reply_ready_i=0;tick();
            release dut.engine.control.fault_o;release dut.engine.control.data_link.source_valid;release dut.engine.control.local0.transfer.tx_ready;
            read_failure(16'h200,0,0,3);reload_and_run();
        end else if(mode==17)begin
            start_trial();
            do begin request(9,3,0,0,0);end while(!answer[18]);
            tick();cmd_valid_i=1;cmd_op_i=10;cmd_target_i=3;cmd_address_i=0;cmd_data_i=0;
            do @(posedge clk_i);while(!cmd_ready_o);
            tick();cmd_valid_i=0;while(!reply_valid_o)tick();
            answer=reply_data_o;
            if(reply_status_o!=0 || answer[111:96]!=0)$fatal(1,"normal terminal before late fault");
            force dut.engine.control.fault_o=1;
            repeat(1500)begin tick();if(!reply_valid_o || reply_status_o!=0 || reply_data_o!==answer || !dut.inner_rst_ni)$fatal(1,"late fault changed owned RESULT or reset before host acceptance");end
            reply_ready_i=1;tick();reply_ready_i=0;tick();
            release dut.engine.control.fault_o;
            wait_idle_recovery();request(10,3,0,0,16'h105);reload_and_run();
        end else if(mode==15)begin
            request(15,3,0,256'h101,0);wait_idle_recovery();request(10,3,0,0,16'h105);reload_and_run();
        end else if(mode==16)begin start_trial();finish_success();end
        else if(mode==14)begin
            force dut.engine.control.data_link.source_valid=0;force dut.engine.control.local0.transfer.tx_ready=0;start_trial();
            wait(dut.engine.control.local0.transfer.state==2);
            request(15,3,0,recovery_command(0,0,999),16'h107);
            if(dut.halt_i)$fatal(1,"foreign cancel stopped job");
            release dut.engine.control.data_link.source_valid;release dut.engine.control.local0.transfer.tx_ready;finish_success();
        end else begin
            if(mode==1)begin force dut.engine.control.data_link.source_valid=0;force dut.engine.control.local0.transfer.tx_ready=0;end
            if(mode==2)force dut.engine.control.reserved_identity[128+:128]=0;
            if(mode==3)begin force dut.engine.control.local1.data_host_req_valid_i=0;force dut.engine.control.local1.m_ready=0;end
            if(mode==4 || mode==12)force dut.engine.control.data_link.destination_ack_ready=0;
            if(mode==5 || mode==10 || mode==11)force dut.engine.control.data_link.ack_valid=0;
            if(mode==8)force dut.engine.pm_rsp_error_i[1]=1;
            if(mode==9)force dut.engine.control.local0.adapter_take=0;
            start_trial();
            case(mode)
                0,6,9,13:wait(dut.engine.control.local0.service_active);
                1:wait(dut.engine.control.local0.transfer.state==2 && dut.engine.control.local0.transfer.available);
                2:wait(dut.engine.control.data_link.busy);
                3:wait(dut.engine.control.data_link.offered);
                4,12:wait(dut.engine.control.local1.transfer.rx_pending);
                5,10,11:wait(commit_count_o==1);
                default:begin end
            endcase
            if(mode==7 || mode==8)begin
                read_failure(16'h200,0,0,3);
                if(mode==8)release dut.engine.pm_rsp_error_i[1];
            end else if(mode==12)begin
                rst_ni=0;repeat(6)tick();release dut.engine.control.data_link.destination_ack_ready;
                epoch=2;load_case(0,0);reset_cohort();configure(configured);seed_data();run_job(8,1,0);
            end else begin
                if(mode==6)begin
                    tick();cmd_valid_i=1;cmd_op_i=15;cmd_target_i=3;cmd_address_i=0;cmd_data_i=recovery_command(0,0,7);
                    do @(posedge clk_i);while(!cmd_ready_o);
                    tick();cmd_valid_i=0;while(!reply_valid_o)tick();
                    if(reply_status_o!=0)$fatal(1,"cancel rejected");
                    repeat(1500)begin tick();if(!reply_valid_o || reply_status_o!=0 || reply_data_o!=0 || cmd_ready_o)$fatal(1,"recovery reset lost held host response");end
                    reply_ready_i=1;tick();reply_ready_i=0;tick();
                end else request(15,3,0,recovery_command(mode==10 || mode==11 ? 8'd1 : 8'd0,mode==10 ? 8'd1 : mode==11 ? 8'd2 : 8'd0,7),0);
                if(mode==3 || mode==4 || mode==5 || mode==10 || mode==11)begin
                    repeat(24)begin tick();if(!dut.inner_rst_ni || dut.quiescent_o)$fatal(1,"reset before accepted obligation drained");end
                    if(mode==3)begin
                        if(!dut.engine.control.data_link.destination_valid)$fatal(1,"offered destination request was withdrawn");
                        release dut.engine.control.local1.data_host_req_valid_i;release dut.engine.control.local1.m_ready;
                    end
                    if(mode==4)release dut.engine.control.data_link.destination_ack_ready;
                    if(mode==5 || mode==10 || mode==11)release dut.engine.control.data_link.ack_valid;
                end
                if(mode==9)begin
                    read_failure(16'h201,1,-1,3);
                    if(!dut.inner_rst_ni)$fatal(1,"quarantine reset live service");
                    request(8,3,0,{128'b0,epoch,32'd2,epoch,32'd8},16'h106);
                    request(0,3,0,{192'b0,32'd2,32'd2},16'h106);
                    release dut.engine.control.local0.adapter_take;
                    request(15,3,0,256'd3,0);wait_idle_recovery();request(10,3,0,0,16'h105);
                end else read_failure(11,0,(mode==3 || mode==4 || mode==5 || mode==10 || mode==11) ? 1 : 0,mode==10 ? 8'd1 : mode==11 ? 8'd2 : 8'd3);
                if(mode==1)begin release dut.engine.control.data_link.source_valid;release dut.engine.control.local0.transfer.tx_ready;end
                if(mode==2)release dut.engine.control.reserved_identity[128+:128];
            end
            if(mode!=12)reload_and_run();
        end
        $display("PASS recovery kind=%0d backend=%0d mode=%0d negatives=%0d",KIND,PM_USE_SRAM,mode,negative_checks);$finish;
    end
    initial begin #100000000;$fatal(1,"recovery watchdog kind=%0d mode=%0d",KIND,mode);end
endmodule
