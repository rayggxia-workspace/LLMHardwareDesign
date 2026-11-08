module tb_five_boot;
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
    five_boot_top #(.KIND(KIND),.PM_USE_SRAM(PM_USE_SRAM)) dut(.*);

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
        if(reply_status_o!==status)$fatal(1,"five status kind=%0d mode=%0d op=%0d target=%0d addr=%0d got=%h expected=%h",KIND,mode,op,target,addr,reply_status_o,status);
        answer=reply_data_o;held={reply_status_o,reply_data_o};
        repeat(4)begin tick();if(!reply_valid_o || cmd_ready_o || {reply_status_o,reply_data_o}!==held)$fatal(1,"five reply not held");end
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
        if(reply_valid_o || cmd_ready_o || image_valid_o!=0 || link_pending_o)$fatal(1,"five reset retained state");
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
                if(mode==3 && epoch==1 && c==1 && n==counts[c]-1)begin
                    if(expected==1)$fatal(1,"five ineffective corruption");force dut.pm_rsp_data_i[128+:128]=128'd1;expected=1;
                end
                request(3,2'(c),14'(n*16),0,0);
                if(answer[127:0]!==expected)$fatal(1,"five PM readback mismatch");
                if(mode==3 && epoch==1 && c==1 && n==counts[c]-1)release dut.pm_rsp_data_i[128+:128];
            end
            if(mode==3 && epoch==1 && c==1)begin request(4,1,0,0,16'h104);request(5,1,0,0,16'h105);configured=0;return;end
            request(4,2'(c),0,0,0);
            if(answer[31:0]!==expected_crc[c] || answer[63:32]!==expected_crc[c])$fatal(1,"five independent CRC32 mismatch");
            request(5,2'(c),0,0,0);
        end
        if(mode==4)request(7,3,0,epoch+1,16'h107);
        request(7,3,0,epoch,0);
        if(image_valid_o!=7)$fatal(1,"five deployment");
        if(mode==4)begin
            v=manifest(1,epoch+1);v[143:112]^=1;v[79:48]^=32'h10000000;request(1,1,0,v,3);
            if(image_valid_o!=7)$fatal(1,"failed LC BEGIN revoked existing deployment");
            request(8,3,0,{128'b0,epoch+1,32'd1,epoch,32'd7},16'h107);
        end
    endtask
    task automatic seed_data;
        if(KIND==4)begin
            request(11,1,0,0,4);request(12,1,0,0,4);
            request(14,1,0,{93'b0,1'b1,2'b00,32'hba000007,128'd0},5);
        end
        for(integer n=0;n<counts[3];n++)request(seeds[n][275:272],seeds[n][271:270],seeds[n][269:256],seeds[n][255:0],0);
    endtask
    task automatic run_job(input [31:0] job_id,sequence_id,input bit fault);
        integer polls;integer write_bytes;
        case(KIND)0:write_bytes=96;1:write_bytes=64;2:write_bytes=96;3:write_bytes=64;default:write_bytes=128;endcase
        request(8,3,0,{128'b0,epoch,sequence_id,epoch,job_id},0);
        if(!run_active_o)$fatal(1,"five START");
        request(2,0,0,0,16'h106);
        if(KIND!=4)request(12,1,0,0,16'h106);
        else request(14,1,0,0,16'h106);
        polls=0;
        do begin request(9,3,0,0,0);polls++;if(polls>4000)$fatal(1,"five job stalled");end while(!answer[18]);
        request(10,3,0,0,0);
        if(answer[31:0]!=job_id || answer[63:32]!=epoch || answer[95:64]!=sequence_id ||
           answer[111:96]!=(fault ? 4 : 0) || answer[279:248]!=(fault ? 0 : write_bytes))
            $fatal(1,"five result kind=%0d fault=%0d got=%h writes=%0d",KIND,fault,answer,answer[279:248]);
        if(!fault)begin
            if(KIND==4)begin
                if(!link_pending_o)$fatal(1,"native output ownership disappeared");
                request(8,3,0,{128'b0,epoch,sequence_id+1,epoch,job_id+1},16'h106);
                request(14,1,0,0,16'h106);
            end
            for(integer n=0;n<counts[4];n++)begin
                request(checks[n][1043:1040],checks[n][1039:1038],checks[n][1037:1024],0,0);
                if((answer&checks[n][1023:512])!==checks[n][511:0])$fatal(1,"five numeric kind=%0d check=%0d got=%h expected=%h mask=%h",KIND,n,answer,checks[n][511:0],checks[n][1023:512]);
                if(KIND==4 && (answer[202:171]!=job_id || answer[234:203]!=epoch || answer[266:235]!=sequence_id))$fatal(1,"native output identity");
            end
            if(KIND==4)begin request(13,1,0,0,16'h105);request(13,2,0,0,16'h105);if(link_pending_o)$fatal(1,"native output not released");end
        end
        if(|poison_o)$fatal(1,"five poison after bounded operation");
    endtask
    bit configured;
    initial begin
        rst_ni=0;cmd_valid_i=0;cmd_op_i=0;cmd_target_i=0;cmd_address_i=0;cmd_data_i=0;reply_ready_i=0;
        if(!$value$plusargs("ROOT=%s",root))$fatal(1,"missing five-type input");
        void'($value$plusargs("MODE=%d",mode));load_case(0,mode==6);reset_cohort();
        request(15,3,0,0,16'h101);
        if(mode==2 || mode==5)begin
            request(0,3,0,{192'b0,epoch,epoch},0);request(1,0,0,manifest(0,epoch),0);
            if(mode==5)begin request(2,0,0,{128'b0,word_at(0,0)},0);request(6,0,0,0,0);request(5,0,0,0,16'h105);end
            else begin
                tick();cmd_valid_i=1;cmd_op_i=2;cmd_target_i=0;cmd_address_i=0;cmd_data_i={128'b0,word_at(0,0)};
                do @(posedge clk_i);while(!cmd_ready_o);
                tick();cmd_valid_i=0;repeat(20)tick();
            end
            epoch=2;load_case(0,0);reset_cohort();
        end
        configure(configured);
        if(!configured)begin epoch=2;load_case(0,0);reset_cohort();configure(configured);if(!configured)$fatal(1,"five CRC recovery");end
        seed_data();run_job(7,1,mode==6);
        if(mode==6)begin epoch=2;load_case(0,0);reset_cohort();configure(configured);seed_data();run_job(8,1,0);end
        if(mode==1)begin load_case(1,0);seed_data();run_job(8,2,0);end
        if(!link_pending_o)request(8,3,0,{128'b0,epoch,32'd1,epoch,32'd9},16'h107);
        $display("PASS five-boot kind=%0d backend=%0d mode=%0d negatives=%0d",KIND,PM_USE_SRAM,mode,negative_checks);$finish;
    end
    initial begin #50000000;$fatal(1,"five boot watchdog kind=%0d mode=%0d",KIND,mode);end
endmodule
