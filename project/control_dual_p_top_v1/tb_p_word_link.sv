module tb_p_word_link;
    reg clk=0,reset=1;
    always #5 clk=~clk;
    reg source_valid=0;
    wire source_ready;
    reg [9:0] source_address=20,destination_reserved_address=20;
    reg [127:0] source_data=128'h1234,source_identity=128'habc;
    reg destination_reserved=0,destination_ready=0,destination_ack=0,ack_ready=0;
    wire destination_valid,destination_ack_ready,ack_valid,store_commit,busy;
    wire [9:0] destination_address;
    wire [127:0] destination_data,ack_identity;
    p_word_link dut(.*);
    task automatic tick;@(negedge clk);endtask
    task automatic send;
        source_valid=1;do @(posedge clk);while(!source_ready);tick();source_valid=0;
    endtask
    initial begin
        repeat(3)tick();reset=0;send();
        destination_ack=1;
        repeat(4)begin
            if(destination_valid || destination_ack_ready || ack_valid)$fatal(1,"unreserved/early ACK admitted");tick();
        end
        destination_ack=0;destination_reserved=1;destination_reserved_address=21;
        repeat(3)begin if(destination_valid)$fatal(1,"wrong reservation admitted");tick();end
        destination_reserved_address=20;tick();
        repeat(5)begin
            if(!destination_valid || destination_data!==128'h1234 || destination_address!=20 || source_ready)
                $fatal(1,"word changed under destination backpressure");tick();
        end
        destination_ready=1;tick();destination_ready=0;
        repeat(4)begin if(ack_valid || !destination_ack_ready)$fatal(1,"false commit");tick();end
        destination_ack=1;tick();destination_ack=0;
        repeat(5)begin
            if(!ack_valid || ack_identity!==128'habc || source_ready)$fatal(1,"ACK identity not held");tick();
        end
        ack_ready=1;tick();ack_ready=0;
        if(busy || !source_ready)$fatal(1,"completed slot not released");
        source_data=128'h5678;source_identity=128'hdef;send();
        reset=1;tick();tick();
        if(busy || destination_valid || ack_valid)$fatal(1,"reset retained old transaction");
        reset=0;destination_reserved=1;destination_reserved_address=20;send();
        destination_ready=1;tick();destination_ready=0;destination_ack=1;tick();destination_ack=0;
        if(!ack_valid || ack_identity!==128'hdef)$fatal(1,"new identity lost after reset");
        ack_ready=1;tick();
        $display("PASS p-word-link reservations, early ACK, backpressure, reset and new identity");
        $finish;
    end
    initial begin #10000;$fatal(1,"word-link watchdog");end
endmodule
