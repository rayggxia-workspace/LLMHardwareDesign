module tb_control_boot;
    parameter bit PM_USE_SRAM=1;
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
    control_boot_top #(.PM_USE_SRAM(PM_USE_SRAM)) dut(.*);

    initial clk_i=0;always #5 clk_i=~clk_i;
    localparam [3:0] RELEASE=0,BEGIN_IMAGE=1,WRITE16=2,READ16=3,VERIFY=4,PREPARE=5,
                     ABORT_IMAGE=6,DEPLOY=7,START_JOB=8,STATUS=9,RESULT=10,S_READ=11,S_WRITE=12;
    reg [127:0] im0[0:519],im1[0:519],im2[0:519];
    integer words[3],mode=0,negative_checks=0;
    reg [31:0] expected_crc[0:2];
    string path0,path1,path2;
    reg [31:0] epoch=1;
    reg [511:0] answer;
    function automatic [127:0] word_at(input integer who,index);
        case(who)0:return im0[index];1:return im1[index];default:return im2[index];endcase
    endfunction
    function automatic [255:0] manifest(input integer who,input [31:0] gen);
        reg [127:0] h3,h4,h5;reg [255:0] value;
        h3=word_at(who,3);h4=word_at(who,4);h5=word_at(who,5);value=0;
        value[31:0]=gen;value[47:32]=16'(words[who]*16);value[79:48]=h3[96+:32];
        value[111:80]=h4[0+:32];value[143:112]=h4[32+:32];value[175:144]=h5[32+:32];return value;
    endfunction
    task automatic tick;@(negedge clk_i);endtask
    task automatic request(input [3:0] op,input [1:0] target,input [13:0] address,input [255:0] value,input [15:0] status);
        reg [527:0] hold;
        tick();cmd_valid_i=1;cmd_op_i=op;cmd_target_i=target;cmd_address_i=address;cmd_data_i=value;
        do @(posedge clk_i);while(!cmd_ready_o);
        tick();cmd_valid_i=0;cmd_op_i=15;cmd_target_i=3;cmd_address_i=14'h3fff;cmd_data_i='1;
        while(!reply_valid_o)tick();
        if(reply_status_o!==status)$fatal(1,"boot status op=%0d target=%0d addr=%0d got=%h expected=%h",op,target,address,reply_status_o,status);
        answer=reply_data_o;hold={reply_status_o,reply_data_o};
        repeat(3)begin tick();if(!reply_valid_o || cmd_ready_o || {reply_status_o,reply_data_o}!==hold)$fatal(1,"boot reply lost under backpressure");end
        reply_ready_i=1;tick();reply_ready_i=0;tick();
        if(status!=0)negative_checks++;
    endtask
    task automatic reset_cohort;
        rst_ni=0;cmd_valid_i=0;reply_ready_i=0;repeat(5)tick();
        if(reply_valid_o || cmd_ready_o || image_valid_o!=0 || link_pending_o)$fatal(1,"boot reset retained protocol/deployment");
        rst_ni=1;while(!reset_ready_o)tick();repeat(3)tick();
        request(START_JOB,3,0,{128'b0,epoch,32'd1,epoch,32'd7},16'h105);
    endtask
    task automatic load_images(output bit configured);
        reg [255:0] data;reg [127:0] expected;
        configured=1;
        request(RELEASE,3,0,{192'b0,epoch,epoch},0);
        request(DEPLOY,3,0,epoch,16'h105);
        for(integer c=0;c<3;c++)begin
            data=manifest(c,epoch);
            if(c==0)begin
                data[143:112]^=1;request(BEGIN_IMAGE,2'(c),0,data,3);data=manifest(c,epoch);
            end
            request(BEGIN_IMAGE,2'(c),0,data,0);
            request(WRITE16,2'(c),16,{128'b0,word_at(c,0)},16'h107);
            expected=word_at(c,0);expected[79:64]=1;
            request(WRITE16,2'(c),0,{128'b0,expected},16'h103);
            for(integer n=0;n<words[c];n++)request(WRITE16,2'(c),14'(n*16),{128'b0,word_at(c,n)},0);
            request(VERIFY,2'(c),0,0,16'h105);request(PREPARE,2'(c),0,0,16'h105);
            request(READ16,2'(c),16,0,16'h107);
            for(integer n=0;n<words[c];n++)begin
                expected=word_at(c,n);
                if(mode==3 && epoch==1 && c==1 && n==words[c]-1)begin
                    if(expected==1)$fatal(1,"ineffective read corruption");
                    force dut.pm_rsp_data_i[128+:128]=128'd1;expected=1;
                end
                request(READ16,2'(c),14'(n*16),0,0);
                if(answer[127:0]!==expected)$fatal(1,"readback data mismatch target=%0d word=%0d",c,n);
                if(mode==3 && epoch==1 && c==1 && n==words[c]-1)release dut.pm_rsp_data_i[128+:128];
            end
            if(mode==3 && epoch==1 && c==1)begin
                request(VERIFY,1,0,0,16'h104);request(PREPARE,1,0,0,16'h105);
                if(image_valid_o!=0)$fatal(1,"corrupted image deployed");
                configured=0;return;
            end
            request(VERIFY,2'(c),0,0,0);
            if(answer[31:0]!==expected_crc[c] || answer[63:32]!==expected_crc[c])$fatal(1,"independent CRC32 mismatch target=%0d got=%h expected=%h",c,answer[63:0],expected_crc[c]);
            request(PREPARE,2'(c),0,0,0);
        end
        if(mode==4)request(DEPLOY,3,0,epoch+1,16'h107);
        request(DEPLOY,3,0,epoch,0);
        if(image_valid_o!=3'b111)$fatal(1,"deploy not atomic/complete");
        if(mode==4)begin
            request(BEGIN_IMAGE,0,0,manifest(0,epoch),3);
            if(image_valid_o!=3'b111)$fatal(1,"rejected BEGIN destroyed deployed cohort");
            request(START_JOB,3,0,{128'b0,epoch+1,32'd1,epoch,32'd7},16'h107);
            request(START_JOB,3,0,{128'b0,epoch,32'd0,epoch,32'd7},16'h107);
        end
    endtask
    task automatic storage(input [1:0] who,input bit wr,input integer word_address,input [127:0] value);
        request(wr ? S_WRITE : S_READ,who,14'(word_address*16),wr ? {128'b0,value} : 256'b0,0);
        if(!wr && answer[127:0]!==value)$fatal(1,"boot S read mismatch target=%0d addr=%0d",who,word_address);
    endtask
    task automatic seed_data;
        storage(1,1,0,2);storage(1,1,1,0);storage(1,1,2,0);storage(1,1,3,0);
        storage(1,1,4,128'hfb0000000000000003);storage(1,1,5,0);storage(1,1,6,0);storage(1,1,7,0);
        storage(1,1,12,128'hd8f0_2710);storage(1,1,13,128'h0400_0200);storage(2,1,20,{16{8'had}});
    endtask
    task automatic run_job(input [31:0] job_id,sequence_id,input integer expected_transfers);
        integer polls;
        request(START_JOB,3,0,{128'b0,epoch,sequence_id,epoch,job_id},0);
        if(!run_active_o)$fatal(1,"boot start did not run");
        request(WRITE16,0,0,0,16'h106);request(S_WRITE,2,320,0,16'h106);
        request(RESULT,3,0,0,16'h105);
        polls=0;
        do begin request(STATUS,3,0,0,0);polls++;if(polls>2000)$fatal(1,"boot job stalled");end while(!answer[18]);
        request(RESULT,3,0,0,0);
        if(answer[31:0]!=job_id || answer[63:32]!=epoch || answer[95:64]!=sequence_id || answer[111:96]!=0 || answer[279:248]!=48 ||
           commit_count_o!=expected_transfers || ack_count_o!=expected_transfers)$fatal(1,"boot result mismatch %h",answer);
        request(RESULT,3,0,0,16'h105);
        storage(1,0,8,128'hfffffff600000006);storage(1,0,14,5000);storage(2,0,20,5000);
    endtask
    bit configured;
    initial begin
        rst_ni=0;cmd_valid_i=0;cmd_op_i=0;cmd_target_i=0;cmd_address_i=0;cmd_data_i=0;reply_ready_i=0;
        if(!$value$plusargs("MOTHER=%s",path0)||!$value$plusargs("MWORDS=%d",words[0])||
           !$value$plusargs("LOCAL0=%s",path1)||!$value$plusargs("WORDS0=%d",words[1])||
           !$value$plusargs("LOCAL1=%s",path2)||!$value$plusargs("WORDS1=%d",words[2])||
           !$value$plusargs("CRC0=%h",expected_crc[0])||!$value$plusargs("CRC1=%h",expected_crc[1])||!$value$plusargs("CRC2=%h",expected_crc[2]))$fatal(1,"boot missing images");
        void'($value$plusargs("MODE=%d",mode));
        $readmemh(path0,im0,0,words[0]-1);$readmemh(path1,im1,0,words[1]-1);$readmemh(path2,im2,0,words[2]-1);
        reset_cohort();request(15,3,0,0,16'h101);request(WRITE16,3,0,0,16'h102);
        if(mode==5)begin
            request(RELEASE,3,0,{192'b0,epoch,epoch},0);request(BEGIN_IMAGE,0,0,manifest(0,epoch),0);
            request(WRITE16,0,0,{128'b0,word_at(0,0)},0);request(ABORT_IMAGE,0,0,0,0);
            request(READ16,0,0,0,16'h105);request(PREPARE,0,0,0,16'h105);
            request(BEGIN_IMAGE,0,0,manifest(0,epoch),3);request(DEPLOY,3,0,epoch,16'h105);
            epoch=2;reset_cohort();
        end
        if(mode==2)begin
            request(RELEASE,3,0,{192'b0,epoch,epoch},0);request(BEGIN_IMAGE,0,0,manifest(0,epoch),0);
            tick();cmd_valid_i=1;cmd_op_i=WRITE16;cmd_target_i=0;cmd_address_i=0;cmd_data_i={128'b0,word_at(0,0)};
            do @(posedge clk_i);while(!cmd_ready_o);
            tick();cmd_valid_i=0;repeat(20)tick();epoch=2;reset_cohort();
        end
        load_images(configured);
        if(!configured)begin epoch=2;reset_cohort();load_images(configured);if(!configured)$fatal(1,"CRC recovery failed");end
        seed_data();run_job(7,1,1);
        request(START_JOB,3,0,{128'b0,epoch,32'd1,epoch,32'd8},16'h107);
        if(mode==1)begin storage(2,1,20,{16{8'h5a}});run_job(8,2,2);end
        if(|poison_o)$fatal(1,"boot ended poisoned");
        $display("PASS control-boot backend=%0d mode=%0d negatives=%0d",PM_USE_SRAM,mode,negative_checks);$finish;
    end
    initial begin #30000000;$fatal(1,"boot watchdog");end
endmodule
