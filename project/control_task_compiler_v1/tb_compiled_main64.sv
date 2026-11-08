module tb_compiled_main64;
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
    main64_boot_top #(.KIND0(KIND0),.KIND1(KIND1)) dut(.*);
    reg [1319:0] commands[0:4095];reg [31:0] counts[0:1];
    reg [1319:0] cmd;reg [511:0] answer;reg [527:0] held;
    integer variant=0,stall=0,position,polls,accepted=0;
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
    initial begin
        if(!$value$plusargs("ROOT=%s",root))$fatal(1,"missing audited replay root");
        void'($value$plusargs("CASE=%d",variant));void'($value$plusargs("STALL=%d",stall));
        $readmemh({root,"/count.mem"},counts);
        if(counts[0]==0 || counts[0]>4096)$fatal(1,"replay count");
        $readmemh({root,"/replay.mem"},commands,0,counts[0]-1);
        repeat(6)tick();rst_ni=1;while(!reset_ready_o)tick();repeat(4)tick();
        for(position=0;position<counts[0];position++)begin
            cmd=commands[position];polls=0;
            if(cmd[1319:1316]>1)$fatal(1,"unknown host replay mode");
            do begin
                issue(cmd);polls++;
                if(polls>5000)$fatal(1,"compiled task did not terminate pos=%0d",position);
            end while(cmd[1319:1316]==1 && (answer&cmd[1023:512])!==cmd[511:0]);
            if((answer&cmd[1023:512])!==cmd[511:0])$fatal(1,"compiled data/CRC/result pos=%0d got=%h expected=%h mask=%h",position,answer,cmd[511:0],cmd[1023:512]);
        end
        if(image_valid_o!=7 || |poison_o || run_active_o || link_pending_o)$fatal(1,"compiled cohort not clean");
        if(commit_count_o!=counts[1] || ack_count_o!=counts[1])$fatal(1,"compiled commits/ACK mismatch");
        $display("PASS compiled-main64 kinds=%0d/%0d case=%0d requests=%0d commits=%0d",KIND0,KIND1,variant,accepted,commit_count_o);$finish;
    end
    initial begin #50000000;$fatal(1,"compiled replay watchdog");end
endmodule
