// A committed native output stays owned until the host accepts its packet.
module native_result_fifo #(parameter integer DEPTH=4)(
    input wire clk_i,rst_ni,input wire push_valid_i,output wire push_ready_o,
    input wire [511:0] push_packet_i,output wire pop_valid_o,input wire pop_ready_i,
    output wire [511:0] pop_packet_o,output wire pending_o
);
    localparam integer IW=$clog2(DEPTH);
    reg [511:0] memory[0:DEPTH-1];
    reg [IW-1:0] head,tail;
    reg [IW:0] count;
    wire push=push_valid_i && push_ready_o;
    wire pop=pop_valid_o && pop_ready_i;
    assign push_ready_o=rst_ni && count<DEPTH;
    assign pop_valid_o=rst_ni && count!=0;
    assign pending_o=pop_valid_o;
    assign pop_packet_o=memory[head];
    always @(posedge clk_i)begin
        if(!rst_ni)begin head<=0;tail<=0;count<=0;end
        else begin
            if(push)begin memory[tail]<=push_packet_i;tail<=tail==DEPTH-1 ? IW'(0) : tail+1'b1;end
            if(pop)head<=head==DEPTH-1 ? IW'(0) : head+1'b1;
            case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
        end
    end
endmodule
