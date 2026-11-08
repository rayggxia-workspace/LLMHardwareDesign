module tb_u_native_entry;
    reg clk=0, reset=1;
    always #5 clk=~clk;
    reg svc_valid=0, rsp_ready=0;
    reg [1023:0] descriptor=0;
    wire svc_ready, rsp_valid, saturated;
    wire [15:0] status;
    wire [31:0] read_bytes, write_bytes;
    reg incoming_valid=0, incoming_ack_ready=1;
    reg [9:0] incoming_addr=0;
    reg [127:0] incoming_data=0;
    wire incoming_ready, incoming_ack;
    reg outgoing_ready=0, outgoing_ack=0;
    wire outgoing_valid, outgoing_ack_ready;
    wire [9:0] outgoing_addr;
    wire [127:0] outgoing_data;
    wire link_rx_reserved;
    wire [9:0] link_rx_addr;
    wire n_to_e_valid, e_direct_a_ready;
    wire [127:0] n_to_e_data;
    wire late_path_enable=0, peer_rx_reserved=1;
    wire [9:0] peer_rx_addr=10'd55;
    wire n_to_e_ready=0, e_direct_a_valid=0;
    wire [127:0] e_direct_a_data=0;
    pu_u_native_endpoint dut(.*);
    integer reads=0, issued=0;
    always @(posedge clk) if (!reset) begin
        if (dut.datapath.request[1] && dut.datapath.accept[1] && !dut.datapath.write[1]) reads<=reads+1;
        if (|dut.cmd_valid) issued<=issued+1;
    end
    task automatic tick;
        @(posedge clk); @(negedge clk);
    endtask
    task automatic seed(input [9:0] a,input [15:0] v);
        incoming_addr=a; incoming_data={8{v}}; incoming_valid=1;
        do @(posedge clk); while(!incoming_ready);
        @(negedge clk); incoming_valid=0;
        while(!incoming_ack) tick();
        tick();
    endtask
    task automatic issue(input [15:0] op, input [31:0] n0, n1, n2);
        descriptor=0; descriptor[32+:16]=op;
        descriptor[512+:32]=n0; descriptor[544+:32]=n1; descriptor[576+:32]=n2;
        svc_valid=1;
        do @(posedge clk); while(!svc_ready);
        @(negedge clk); svc_valid=0;
    endtask
    task automatic response(input [15:0] s, input [31:0] r,w);
        while(!rsp_valid) tick();
        repeat(3) begin
            if (!rsp_valid || status!==s || read_bytes!==r || write_bytes!==w)
                $fatal(1,"native entry response got=%0d/%0d/%0d expected=%0d/%0d/%0d",status,read_bytes,write_bytes,s,r,w);
            tick();
        end
        rsp_ready=1; tick(); rsp_ready=0;
    endtask
    task automatic check_stored(input [15:0] want);
        issue(16'h101,31 | 55<<10,0,0);
        while(!outgoing_valid) tick();
        repeat(3) begin
            if (!outgoing_valid || outgoing_data!=={8{want}} || outgoing_addr!==55)
                $fatal(1,"native SEND stored mismatch got=%h want=%0d",outgoing_data,want);
            if (rsp_valid) $fatal(1,"SEND completed before stored ACK");
            tick();
        end
        outgoing_ready=1; tick(); outgoing_ready=0;
        repeat(4) begin
            if (rsp_valid) $fatal(1,"SEND completed before stored ACK");
            tick();
        end
        outgoing_ack=1;
        do @(posedge clk); while(!outgoing_ack_ready);
        @(negedge clk); outgoing_ack=0;
        response(0,16,0);
    endtask
    integer before_reads,before_issued;
    initial begin
        repeat(4) tick(); reset=0;
        seed(0,5); seed(1,2); seed(2,3); seed(3,5);
        for(integer n=0;n<=3;n=n+1) begin
            before_reads=reads;
            issue(16'h100, n<<2 | 16 | 31<<5, 1 | 2<<10 | 3<<20,3);
            response(0,n*16,16);
            if (reads-before_reads!=n) $fatal(1,"E native operand read count");
            check_stored(n<2 ? 0 : n==2 ? 6 : 11);
        end
        before_reads=reads; before_issued=issued;
        issue(16'h100,1 | 3<<2 | 16 | 31<<5,1|2<<10|3<<20,3);
        response(5,0,0);
        issue(16'h100,2 | 2<<2,0,0);
        response(5,0,0);
        if(reads!=before_reads || issued!=before_issued)
            $fatal(1,"invalid native descriptor reached a macro");
        $display("PASS U native entry FMA counts 0..3, exact S reads, delayed ACK, invalid N/lane");
        $finish;
    end
    initial begin #100000; $fatal(1,"native entry watchdog"); end
endmodule
