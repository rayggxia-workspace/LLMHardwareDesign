`timescale 1ns/1ps
// Preserve the common loader; explicitly adapt J's fragment/committed-output API.
module main64_host_front #(parameter integer KIND0=0, KIND1=KIND0)(
    input wire clk_i,rst_ni,
    input wire cmd_valid_i,output wire cmd_ready_o,input wire [3:0] cmd_op_i,
    input wire [1:0] cmd_target_i,input wire [13:0] cmd_address_i,input wire [255:0] cmd_data_i,
    output wire reply_valid_o,input wire reply_ready_i,output wire [15:0] reply_status_o,output wire [511:0] reply_data_o,
    output wire down_cmd_valid_o,input wire down_cmd_ready_i,output wire [3:0] down_cmd_op_o,
    output wire [1:0] down_cmd_target_o,output wire [13:0] down_cmd_address_o,output wire [255:0] down_cmd_data_o,
    input wire down_reply_valid_i,output wire down_reply_ready_o,input wire [15:0] down_reply_status_i,input wire [511:0] down_reply_data_i,
    input wire deployed_i,input wire run_active_i,result_valid_i,input wire [1:0] native_pending_i,
    output reg [1:0] fragment_valid_o,input wire [1:0] fragment_ready_i,
    output reg [19:0] fragment_address_o,output reg [255:0] fragment_data_o,
    output reg [63:0] fragment_tag_o,output reg [3:0] fragment_slot_o,output reg [1:0] fragment_last_o,
    input wire [1:0] fragment_rsp_valid_i,output reg [1:0] fragment_rsp_ready_o,input wire [1:0] fragment_error_i,
    input wire [1:0] native_result_valid_i,output reg [1:0] native_result_ready_o,input wire [1023:0] native_result_packet_i
);
    localparam [2:0] IDLE=0,PASS=1,FRAGMENT_REQ=2,FRAGMENT_WAIT=3,LOCAL_REPLY=4;
    reg [2:0] state;
    reg selected,read_output;
    reg [13:0] address;
    reg [255:0] payload;
    reg [15:0] status;
    reg [511:0] packet;
    wire [2:0] selected_kind=cmd_target_i==2 ? 3'(KIND1) : 3'(KIND0);
    wire data_target=cmd_target_i==1 || cmd_target_i==2;
    wire unsupported_read=data_target && cmd_op_i==11 && (selected_kind==0 || selected_kind==4);
    wire blocked_write=data_target && cmd_op_i==12 && (selected_kind==4 || deployed_i);
    wire bad_epoch=cmd_op_i==0 && (KIND0==4 || KIND1==4) && cmd_data_i[63:32]>255;
    wire bad_topology=cmd_op_i==1 && cmd_target_i<3 && cmd_data_i[111:80]!=(32'h01938000+KIND0*16+KIND1);
    wire special=cmd_op_i==13 || cmd_op_i==14 || unsupported_read || blocked_write || bad_epoch || bad_topology;
    assign cmd_ready_o=rst_ni && state==IDLE && down_cmd_ready_i;
    assign down_cmd_valid_o=rst_ni && state==IDLE && cmd_valid_i && !special;
    assign down_cmd_op_o=cmd_op_i;assign down_cmd_target_o=cmd_target_i;
    assign down_cmd_address_o=cmd_address_i;assign down_cmd_data_o=cmd_data_i;
    assign down_reply_ready_o=rst_ni && state==PASS && reply_ready_i;
    assign reply_valid_o=rst_ni && (state==LOCAL_REPLY || state==PASS && down_reply_valid_i);
    assign reply_status_o=state==PASS ? down_reply_status_i : status;
    assign reply_data_o=state==PASS ? down_reply_data_i : packet;
    always @* begin
        fragment_valid_o=0;fragment_address_o=0;fragment_data_o=0;fragment_tag_o=0;
        fragment_slot_o=0;fragment_last_o=0;fragment_rsp_ready_o=0;native_result_ready_o=0;
        fragment_valid_o[selected]=rst_ni && state==FRAGMENT_REQ;
        fragment_rsp_ready_o[selected]=rst_ni && state==FRAGMENT_WAIT;
        fragment_address_o[selected*10+:10]=address[13:4];
        fragment_data_o[selected*128+:128]=payload[127:0];
        fragment_tag_o[selected*32+:32]=payload[159:128];
        fragment_slot_o[selected*2+:2]=payload[161:160];fragment_last_o[selected]=payload[162];
        native_result_ready_o[selected]=rst_ni && state==LOCAL_REPLY && read_output && status==0 && reply_ready_i;
    end
    always @(posedge clk_i)begin
        if(!rst_ni)begin state<=IDLE;selected<=0;address<=0;payload<=0;status<=0;packet<=0;read_output<=0;end
        else case(state)
            IDLE:if(cmd_valid_i && cmd_ready_o)begin
                selected<=cmd_target_i==2;address<=cmd_address_i;payload<=cmd_data_i;
                status<=0;packet<=0;read_output<=0;
                if(!special)state<=PASS;
                else begin
                    state<=LOCAL_REPLY;
                    if(bad_topology)status<=3;
                    else if(bad_epoch)status<=16'h103;
                    else if(unsupported_read || (blocked_write && selected_kind==4))status<=4;
                    else if(blocked_write)status<=16'h106;
                    else if(selected_kind!=4)status<=4;
                    else if(cmd_target_i!=1 && cmd_target_i!=2)status<=16'h102;
                    else if(run_active_i || result_valid_i)status<=16'h106;
                    else if(cmd_op_i==13)begin
                        if(cmd_address_i!=0 || cmd_data_i!=0)status<=16'h103;
                        else if(!native_result_valid_i[cmd_target_i==2])status<=16'h105;
                        else begin packet<=native_result_packet_i[(cmd_target_i==2)*512+:512];read_output<=1;end
                    end else begin
                        if(|native_pending_i)status<=16'h106;
                        else if(cmd_address_i[3:0]!=0 || cmd_data_i[255:163]!=0)status<=16'h103;
                        else state<=FRAGMENT_REQ;
                    end
                end
            end
            PASS:if(down_reply_valid_i && reply_ready_i)state<=IDLE;
            FRAGMENT_REQ:if(fragment_ready_i[selected])state<=FRAGMENT_WAIT;
            FRAGMENT_WAIT:if(fragment_rsp_valid_i[selected])begin status<=fragment_error_i[selected] ? 16'd5 : 16'd0;state<=LOCAL_REPLY;end
            LOCAL_REPLY:if(reply_ready_i)state<=IDLE;
            default:state<=IDLE;
        endcase
    end
endmodule
