// Exercise actual compact SRAMs, both native group TX ports and stored_link.
module cfj_exchange_case #(parameter integer K0=2, K1=1) (
    input wire clk, output reg finished
);
    reg reset=1, seeding=1, peeking=0;
    reg [1:0] seed_valid=0, seed_take=0, start=0, peek_req=0, peek_take=0;
    reg [9:0] address=0;
    reg [127:0] seed_data=0;
    wire [1:0] seed_ready, seed_ack, tx_ready, tx_valid, tx_take, tx_req;
    wire [127:0] tx_data[2];
    wire [9:0] tx_addr[2], link_addr[2];
    wire [1:0] link_ready, link_done, link_valid, link_accept, link_ack, link_ack_take;
    wire [127:0] link_data[2];
    reg [1:0] allow_write=3, allow_ack=3;
    integer commits[2], offers[2];
    reg [127:0] expected[2];
    reg [1:0] needed;
    reg [1:0] completed;
    reg [31:0] version=0;

    for (genvar i=0;i<2;i=i+1) begin: side
        localparam integer KIND=i==0 ? K0 : K1;
        localparam integer PEER=1-i;
        wire ready, ack;
        wire [9:0] rx_addr=seeding ? address : link_addr[PEER];
        wire [127:0] rx_data=seeding ? seed_data : link_data[PEER];
        assign seed_ready[i]=ready;
        assign seed_ack[i]=ack;
        assign link_accept[PEER]=!seeding && ready && allow_write[PEER];
        assign link_ack[PEER]=!seeding && ack && allow_ack[PEER];
        block_cfj_cf #(.KIND(KIND)) group (
            .clk(clk),.reset(reset),.cmd_valid('0),.cmd_ready(),
            .cmd_meta('0),.cmd_sources('0),.cmd_addresses('0),.cmd_store('0),.cmd_dst('0),
            .done_valid(),.done_ready('1),.done_data(),.done_error(),.done_saturated(),
            .rx_valid(seeding ? seed_valid[i] : link_valid[PEER] && allow_write[PEER]),
            .rx_ready(ready),.rx_addr(rx_addr),.rx_data(rx_data),
            .rx_stored(ack),.rx_stored_ready(seeding ? seed_take[i] :
                                                     link_ack_take[PEER] && allow_ack[PEER]),
            .tx_req(peeking ? peek_req[i] : tx_req[i]),.tx_ready(tx_ready[i]),
            .tx_addr(peeking ? address : tx_addr[i]),.tx_valid(tx_valid[i]),
            .tx_take(peeking ? peek_take[i] : tx_take[i]),.tx_data(tx_data[i]),
            .late_g_valid(),.late_g_data(),.late_g_take(1'b0),
            .late_e_valid(1'b0),.late_e_data(32'b0),.late_e_take()
        );
        stored_link link (
            .clk(clk),.reset(reset),.start(start[i]),.ready(link_ready[i]),
            .source_addr(10'd4),.destination_addr(10'd8),.done(link_done[i]),
            .tx_req(tx_req[i]),.tx_ready(tx_ready[i]),.tx_addr(tx_addr[i]),
            .tx_valid(tx_valid[i]),.tx_take(tx_take[i]),.tx_data(tx_data[i]),
            .rx_valid(link_valid[i]),.rx_ready(link_accept[i]),
            .rx_addr(link_addr[i]),.rx_data(link_data[i]),
            .rx_stored(link_ack[i]),.rx_stored_ready(link_ack_take[i]),.sink_reserved(1'b1)
        );
        always @(posedge clk) begin
            if (reset) begin commits[i]<=0; offers[i]<=0; end
            else if (!seeding && !peeking) begin
                if (link_valid[i] && link_accept[i]) begin
                    if (link_data[i] !== expected[i]) $fatal(1,"exchange data changed");
                    offers[i]<=offers[i]+1;
                end
                if (link_done[i]) commits[i]<=commits[i]+1;
                if (tx_take[i] && !link_ack[i]) $fatal(1,"source released before remote ACK");
            end
        end
    end

    task automatic tick;
        @(negedge clk);
    endtask
    task automatic seed(input integer side_id,input [9:0] addr,input [127:0] value);
        address=addr; seed_data=value; seed_valid=2'b01<<side_id;
        do @(posedge clk); while (!seed_ready[side_id]);
        tick(); seed_valid=0; seed_take=2'b01<<side_id;
        while (!seed_ack[side_id]) tick();
        tick(); seed_take=0;
    endtask
    task automatic check_word(input integer side_id,input [9:0] addr,input [127:0] value);
        address=addr; peek_req=2'b01<<side_id;
        do @(posedge clk); while (!tx_ready[side_id]);
        tick(); peek_req=0;
        while (!tx_valid[side_id]) tick();
        if (tx_data[side_id] !== value) $fatal(1,"SRAM readback mismatch kind=%0d/%0d side=%0d addr=%0d",K0,K1,side_id,addr);
        peek_take=2'b01<<side_id; tick(); peek_take=0; tick();
    endtask
    task automatic trial(input bit bidirectional,input bit delayed,input bit abort_trial);
        reset=1; start=0; seeding=1; peeking=0;
        seed_valid=0; seed_take=0; peek_req=0; peek_take=0;
        allow_write=3; allow_ack=delayed ? 0 : 3;
        repeat(4) tick();
        reset=0; tick();
        version=version+1;
        expected[0]=128'h123456789abcdef0_123456789abcdef0 ^ {4{version}};
        expected[1]=128'hfedcba9876543210fedcba9876543210 ^ {4{version}};
        seed(0,4,expected[0]); seed(1,4,expected[1]);
        seed(0,8,0); seed(1,8,0);
        seeding=0; needed=bidirectional ? 3 : 1;
        start=needed; tick(); start=0;
        // Keep writes independently backpressured before permitting commits.
        for (integer cycle=0;cycle<160;cycle=cycle+1) begin
            allow_write=delayed ? {cycle%5!=0,cycle%3!=0} : 2'b11;
            tick();
            if (delayed && ((link_done & needed)!=0 || commits[0] || commits[1]))
                $fatal(1,"retired while commit was stalled");
        end
        if (offers[0]!=1 || offers[1]!=(bidirectional ? 1 : 0))
            $fatal(1,"no forward progress: two TX held, RX unable to write kind=%0d/%0d",K0,K1);
        if (delayed) begin
            if ((tx_valid & needed)!=needed || (tx_ready & needed)!=0)
                $fatal(1,"TX slot lost ownership while remote ACK stalled");
            if (tx_data[0]!==expected[0] || (bidirectional && tx_data[1]!==expected[1]))
                $fatal(1,"TX word changed while remote ACK stalled");
        end
        if (abort_trial) begin
            reset=1; tick(); tick();
            if (|tx_valid || |link_valid || |link_ack || |link_done)
                $fatal(1,"reset retained a stale transfer");
            return;
        end
        allow_write=3; allow_ack=3; completed=0;
        for (integer cycle=0;cycle<80;cycle=cycle+1) begin
            tick();
            if (commits[0]==1) completed[0]=1;
            if (commits[1]==1) completed[1]=1;
        end
        if ((completed & needed)!=needed || commits[0]!=1 || commits[1]!=(bidirectional ? 1 : 0))
            $fatal(1,"missing or duplicate remote commit");
        peeking=1;
        check_word(0,4,expected[0]); check_word(1,4,expected[1]);
        check_word(1,8,expected[0]);
        check_word(0,8,bidirectional ? expected[1] : 128'b0);
        $display("PASS exchange K0=%0d K1=%0d bidirectional=%0d delayed=%0d",K0,K1,bidirectional,delayed);
    endtask
    initial begin
        finished=0;
        trial(0,0,0);
        trial(1,0,0);
        trial(1,1,0);
        trial(1,1,1);
        trial(1,1,0);
        finished=1;
    end
endmodule

module tb_cfj_exchange;
    reg clk=0;
    always #5 clk=!clk;
    wire cc,cf,ff;
    cfj_exchange_case #(.K0(2),.K1(2)) case_cc(clk,cc);
    cfj_exchange_case #(.K0(2),.K1(1)) case_cf(clk,cf);
    cfj_exchange_case #(.K0(1),.K1(1)) case_ff(clk,ff);
    initial begin
        wait(cc && cf && ff);
        $display("PASS all C/F simultaneous exchanges, backpressure and reset");
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1,"exchange timeout");
    end
endmodule
