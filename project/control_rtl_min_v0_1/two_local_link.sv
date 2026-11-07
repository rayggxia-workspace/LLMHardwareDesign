`timescale 1ns/1ps
// Two fixed task targets and one buffered return channel, in one clock domain.
module two_local_link (
    input wire clk_i, rst_ni,
    input wire task_valid_i, task_credit_i,
    input wire [7:0] task_target_i,
    input wire [511:0] task_packet_i,
    output wire task_ready_o,
    output wire [1:0] local_task_valid_o,
    output wire local_task_credit_o,
    output wire [511:0] local_task_packet_o,
    input wire [1:0] local_task_ready_i,
    input wire [1:0] local_return_valid_i,
    input wire [1023:0] local_return_packet_i,
    output wire [1:0] local_return_ready_o,
    output wire return_valid_o,
    output wire [511:0] return_packet_o,
    input wire return_ready_i
);
    reg buffered_valid;
    reg [511:0] buffered_packet;
    wire space = !buffered_valid || return_ready_i;

    assign local_task_valid_o = {rst_ni && task_valid_i && task_target_i==1,
                                 rst_ni && task_valid_i && task_target_i==0};
    assign task_ready_o = rst_ni && ((task_target_i==0 && local_task_ready_i[0]) ||
                                    (task_target_i==1 && local_task_ready_i[1]));
    assign local_task_credit_o = task_credit_i;
    assign local_task_packet_o = task_packet_i;
    assign local_return_ready_o = {rst_ni && space && !local_return_valid_i[0],
                                  rst_ni && space};
    assign return_valid_o = rst_ni && buffered_valid;
    assign return_packet_o = buffered_packet;

    always @(posedge clk_i) begin
        if (!rst_ni) begin
            buffered_valid<=0;
            buffered_packet<=0;
        end else if (space) begin
            buffered_valid<=|local_return_valid_i;
            if (|local_return_valid_i)
                buffered_packet<=local_return_valid_i[0] ?
                                  local_return_packet_i[511:0] : local_return_packet_i[1023:512];
        end
    end
endmodule
