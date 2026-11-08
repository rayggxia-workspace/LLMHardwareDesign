`timescale 1ns/1ps
module control_boot_manager(
    input wire clk_i,
    input wire rst_ni,
    input wire cmd_valid_i,
    output reg cmd_ready_o,
    input wire [3:0] cmd_op_i,
    input wire [1:0] cmd_target_i,
    input wire [13:0] cmd_address_i,
    input wire [255:0] cmd_data_i,
    output reg reply_valid_o,
    input wire reply_ready_i,
    output reg [15:0] reply_status_o,
    output reg [511:0] reply_data_o,
    output reg deploy_valid_i,
    output reg [31:0] deploy_generation_i,
    output reg [2:0] release_valid_i,
    output reg [95:0] release_sequence_i,
    output reg [95:0] release_epoch_i,
    input wire [2:0] release_ready_o,
    input wire [2:0] poison_o,
    input wire [2:0] image_valid_o,
    output reg [2:0] cfg_req_valid_i,
    output reg [8:0] cfg_req_op_i,
    output reg [95:0] cfg_req_generation_i,
    output reg [41:0] cfg_req_address_i,
    output reg [383:0] cfg_req_data_i,
    output reg [47:0] cfg_req_total_bytes_i,
    output reg [95:0] cfg_req_image_id_i,
    output reg [95:0] cfg_req_topology_id_i,
    output reg [95:0] cfg_req_abi_id_i,
    output reg [95:0] cfg_req_capacity_id_i,
    output reg [2:0] cfg_req_proof_i,
    output reg [2:0] cfg_rsp_ready_i,
    input wire [2:0] cfg_req_ready_o,
    input wire [2:0] cfg_rsp_valid_o,
    input wire [47:0] cfg_rsp_status_o,
    input wire [383:0] cfg_rsp_data_o,
    input wire [95:0] cfg_rsp_generation_o,
    input wire [11:0] life_o,
    output reg start_valid_i,
    output reg start_credit_i,
    output reg [31:0] start_job_i,
    output reg [31:0] start_epoch_i,
    output reg [31:0] start_sequence_i,
    output reg [31:0] start_generation_i,
    output reg [255:0] start_args_i,
    input wire start_ready_o,
    input wire result_valid_o,
    output reg result_ready_i,
    input wire [31:0] result_job_o,
    input wire [31:0] result_epoch_o,
    input wire [31:0] result_sequence_o,
    input wire [15:0] result_status_o,
    input wire [31:0] result_error_pc_o,
    input wire [7:0] result_source_o,
    input wire [31:0] result_child_error_pc_o,
    input wire [31:0] result_failed_task_sequence_o,
    input wire [31:0] result_confirmed_read_bytes_o,
    input wire [31:0] result_confirmed_write_bytes_o,
    input wire result_counter_overflow_o,
    input wire result_saturated_o,
    output reg [1:0] host_req_valid_i,
    output reg [1:0] host_req_write_i,
    output reg [19:0] host_req_address_i,
    output reg [255:0] host_req_data_i,
    input wire [1:0] host_req_ready_o,
    input wire [1:0] host_rsp_valid_o,
    output reg [1:0] host_rsp_ready_i,
    input wire [255:0] host_rsp_data_o,
    input wire reset_ready_o,
    input wire deployment_ready_o,
    input wire run_active_o,
    input wire link_pending_o
);

    localparam [3:0] RELEASE=0,BEGIN_IMAGE=1,WRITE16=2,READ16=3,VERIFY=4,PREPARE=5,
                     ABORT_IMAGE=6,DEPLOY=7,START_JOB=8,STATUS=9,RESULT=10,S_READ=11,S_WRITE=12;
    localparam [3:0] IDLE=0,CFG_REQ=1,CFG_WAIT=2,CRC=3,RESPOND=4,RELEASE_REQ=5,
                     START_REQ=6,DEPLOY_WAIT=7,S_REQ=8,S_WAIT=9;
    localparam [15:0] BAD_COMMAND=16'h101,BAD_TARGET=16'h102,BAD_FIELDS=16'h103,
                      CRC_MISMATCH=16'h104,NOT_READY=16'h105,BUSY=16'h106,BAD_SEQUENCE=16'h107;
    reg [3:0] state,operation;
    reg [1:0] target;
    reg [13:0] address;
    reg [255:0] payload;
    reg [2:0] cfg_operation;
    reg [15:0] error_override;
    reg [2:0] begun,verified,prepared;
    reg [31:0] generation[0:2],image_id[0:2],topology[0:2],abi[0:2],capacity[0:2];
    reg [15:0] total[0:2],written[0:2],readback[0:2];
    reg [31:0] write_crc[0:2],read_crc[0:2];
    reg [127:0] crc_word;
    reg [31:0] crc_state;
    reg [6:0] crc_bit;
    reg crc_is_read;
    reg [31:0] release_sequence,release_epoch,last_start;
    integer i;
    wire active=run_active_o || link_pending_o || result_valid_o;
    wire [31:0] crc_next=(crc_state>>1)^((crc_state[0]^crc_word[0]) ? 32'hedb88320 : 32'b0);
    wire [15:0] cfg_status=cfg_rsp_status_o[target*16+:16];
    wire [127:0] cfg_data=cfg_rsp_data_o[target*128+:128];
    always @* begin
        cmd_ready_o=rst_ni && state==IDLE;
        reply_valid_o=rst_ni && state==RESPOND;
        cfg_req_valid_i=0;cfg_req_op_i=0;cfg_req_generation_i=0;cfg_req_address_i=0;
        cfg_req_data_i=0;cfg_req_total_bytes_i=0;cfg_req_image_id_i=0;
        cfg_req_topology_id_i=0;cfg_req_abi_id_i=0;cfg_req_capacity_id_i=0;
        cfg_req_proof_i=0;cfg_rsp_ready_i=0;
        if(target<3)begin
            cfg_req_valid_i[target]=rst_ni && state==CFG_REQ;
            cfg_rsp_ready_i[target]=rst_ni && state==CFG_WAIT;
            cfg_req_op_i[target*3+:3]=cfg_operation;
            cfg_req_generation_i[target*32+:32]=operation==BEGIN_IMAGE ? payload[31:0] : generation[target];
            cfg_req_total_bytes_i[target*16+:16]=operation==BEGIN_IMAGE ? payload[47:32] : total[target];
            cfg_req_image_id_i[target*32+:32]=operation==BEGIN_IMAGE ? payload[79:48] : image_id[target];
            cfg_req_topology_id_i[target*32+:32]=operation==BEGIN_IMAGE ? payload[111:80] : topology[target];
            cfg_req_abi_id_i[target*32+:32]=operation==BEGIN_IMAGE ? payload[143:112] : abi[target];
            cfg_req_capacity_id_i[target*32+:32]=operation==BEGIN_IMAGE ? payload[175:144] : capacity[target];
            cfg_req_address_i[target*14+:14]=address;
            cfg_req_data_i[target*128+:128]=payload[127:0];
            cfg_req_proof_i[target]=operation==VERIFY && error_override==0;
        end
        release_valid_i={3{rst_ni && state==RELEASE_REQ}};
        release_sequence_i={3{payload[31:0]}};release_epoch_i={3{payload[63:32]}};
        start_valid_i=rst_ni && state==START_REQ;
        start_credit_i=1;start_job_i=payload[31:0];start_epoch_i=payload[63:32];
        start_sequence_i=payload[95:64];start_generation_i=payload[127:96];start_args_i=0;
        result_ready_i=rst_ni && state==RESPOND && operation==RESULT && reply_status_o==0 && reply_ready_i;
        host_req_valid_i=0;host_req_write_i=0;host_req_address_i=0;host_req_data_i=0;host_rsp_ready_i=0;
        if(target==1 || target==2)begin
            host_req_valid_i[target-1]=rst_ni && state==S_REQ;
            host_req_write_i[target-1]=operation==S_WRITE;
            host_req_address_i[(target-1)*10+:10]=address[13:4];
            host_req_data_i[(target-1)*128+:128]=payload[127:0];
            host_rsp_ready_i[target-1]=rst_ni && state==S_WAIT;
        end
    end
    always @(posedge clk_i)begin
        if(!rst_ni)begin
            state<=IDLE;operation<=0;target<=0;address<=0;payload<=0;cfg_operation<=0;
            error_override<=0;reply_status_o<=0;reply_data_o<=0;
            begun<=0;verified<=0;prepared<=0;crc_word<=0;crc_state<=0;crc_bit<=0;crc_is_read<=0;
            release_sequence<=0;release_epoch<=0;last_start<=0;deploy_valid_i<=0;deploy_generation_i<=0;
            for(i=0;i<3;i=i+1)begin
                generation[i]<=0;image_id[i]<=0;topology[i]<=0;abi[i]<=0;capacity[i]<=0;
                total[i]<=0;written[i]<=0;readback[i]<=0;write_crc[i]<=32'hffffffff;read_crc[i]<=32'hffffffff;
            end
        end else case(state)
            IDLE:if(cmd_valid_i && cmd_ready_o)begin
                operation<=cmd_op_i;target<=cmd_target_i;address<=cmd_address_i;payload<=cmd_data_i;
                reply_status_o<=0;reply_data_o<=0;error_override<=0;state<=RESPOND;
                if(cmd_op_i==STATUS)begin
                    if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i!=0)reply_status_o<=BAD_FIELDS;
                    else begin
                        reply_data_o[2:0]<=image_valid_o;reply_data_o[5:3]<=poison_o;
                        reply_data_o[8:6]<=prepared;reply_data_o[11:9]<=verified;reply_data_o[14:12]<=begun;
                        reply_data_o[15]<=deploy_valid_i;reply_data_o[16]<=run_active_o;reply_data_o[17]<=link_pending_o;
                        reply_data_o[18]<=result_valid_o;reply_data_o[31:20]<=life_o;
                        reply_data_o[63:32]<=deploy_generation_i;reply_data_o[95:64]<=release_epoch;
                        reply_data_o[127:96]<=last_start;
                    end
                end else if(cmd_op_i==RESULT)begin
                    if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i!=0)reply_status_o<=BAD_FIELDS;
                    else if(!result_valid_o)reply_status_o<=NOT_READY;
                    else begin
                        reply_data_o[31:0]<=result_job_o;reply_data_o[63:32]<=result_epoch_o;
                        reply_data_o[95:64]<=result_sequence_o;reply_data_o[111:96]<=result_status_o;
                        reply_data_o[143:112]<=result_error_pc_o;reply_data_o[151:144]<=result_source_o;
                        reply_data_o[183:152]<=result_child_error_pc_o;reply_data_o[215:184]<=result_failed_task_sequence_o;
                        reply_data_o[247:216]<=result_confirmed_read_bytes_o;reply_data_o[279:248]<=result_confirmed_write_bytes_o;
                        reply_data_o[280]<=result_counter_overflow_o;reply_data_o[281]<=result_saturated_o;
                    end
                end else if(cmd_op_i>12)reply_status_o<=BAD_COMMAND;
                else if(active)reply_status_o<=BUSY;
                else if(cmd_op_i==RELEASE)begin
                    if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i[255:64]!=0 || cmd_data_i[31:0]<=release_sequence || cmd_data_i[63:32]==0)reply_status_o<=BAD_FIELDS;
                    else if(!(&release_ready_o))reply_status_o<=NOT_READY;
                    else state<=RELEASE_REQ;
                end else if(cmd_op_i==DEPLOY)begin
                    if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i[255:32]!=0)reply_status_o<=BAD_FIELDS;
                    else if(prepared!=3'b111 || !deployment_ready_o || |poison_o)reply_status_o<=NOT_READY;
                    else if(generation[0]!=cmd_data_i[31:0] || generation[1]!=cmd_data_i[31:0] || generation[2]!=cmd_data_i[31:0])reply_status_o<=BAD_SEQUENCE;
                    else begin deploy_valid_i<=1;deploy_generation_i<=cmd_data_i[31:0];state<=DEPLOY_WAIT;end
                end else if(cmd_op_i==START_JOB)begin
                    if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i[255:128]!=0)reply_status_o<=BAD_FIELDS;
                    else if(!deploy_valid_i || image_valid_o!=3'b111 || |poison_o)reply_status_o<=NOT_READY;
                    else if(cmd_data_i[127:96]!=deploy_generation_i || cmd_data_i[63:32]!=release_epoch || cmd_data_i[95:64]<=last_start)reply_status_o<=BAD_SEQUENCE;
                    else state<=START_REQ;
                end else if(cmd_op_i==S_READ || cmd_op_i==S_WRITE)begin
                    if(cmd_target_i==0 || cmd_target_i==3)reply_status_o<=BAD_TARGET;
                    else if(cmd_address_i[3:0]!=0 || cmd_data_i[255:128]!=0 || (cmd_op_i==S_READ && cmd_data_i!=0))reply_status_o<=BAD_FIELDS;
                    else state<=S_REQ;
                end else if(cmd_target_i==3)reply_status_o<=BAD_TARGET;
                else if(cmd_op_i==BEGIN_IMAGE)begin
                    if(cmd_address_i!=0 || cmd_data_i[255:176]!=0)reply_status_o<=BAD_FIELDS;
                    else if(!cfg_req_ready_o[cmd_target_i])reply_status_o<=NOT_READY;
                    else begin cfg_operation<=0;state<=CFG_REQ;end
                end else if(cmd_op_i==ABORT_IMAGE)begin
                    if(cmd_address_i!=0 || cmd_data_i!=0)reply_status_o<=BAD_FIELDS;
                    else if(!begun[cmd_target_i] || !cfg_req_ready_o[cmd_target_i])reply_status_o<=NOT_READY;
                    else begin cfg_operation<=5;state<=CFG_REQ;end
                end else if(!begun[cmd_target_i] || !cfg_req_ready_o[cmd_target_i])reply_status_o<=NOT_READY;
                else case(cmd_op_i)
                    WRITE16:begin
                        if(cmd_address_i[3:0]!=0 || {2'b0,cmd_address_i}!=written[cmd_target_i] || written[cmd_target_i]>=total[cmd_target_i] || cmd_data_i[255:128]!=0)reply_status_o<=BAD_SEQUENCE;
                        else if(cmd_address_i==0 && (cmd_data_i[63:0]!=64'h313041534943424c || cmd_data_i[79:64]!=2 || cmd_data_i[87:80]!=(cmd_target_i==0 ? 8'd0 : 8'd1)))reply_status_o<=BAD_FIELDS;
                        else begin cfg_operation<=1;state<=CFG_REQ;end
                    end
                    READ16:begin
                        if(cmd_address_i[3:0]!=0 || {2'b0,cmd_address_i}!=readback[cmd_target_i] || written[cmd_target_i]!=total[cmd_target_i] || readback[cmd_target_i]>=total[cmd_target_i] || cmd_data_i!=0)reply_status_o<=BAD_SEQUENCE;
                        else begin cfg_operation<=2;state<=CFG_REQ;end
                    end
                    VERIFY:begin
                        if(cmd_address_i!=0 || cmd_data_i!=0)reply_status_o<=BAD_FIELDS;
                        else if(written[cmd_target_i]!=total[cmd_target_i] || readback[cmd_target_i]!=total[cmd_target_i])reply_status_o<=NOT_READY;
                        else begin
                            reply_data_o[31:0]<=~write_crc[cmd_target_i];reply_data_o[63:32]<=~read_crc[cmd_target_i];
                            if(write_crc[cmd_target_i]!=read_crc[cmd_target_i])begin cfg_operation<=5;error_override<=CRC_MISMATCH;end
                            else cfg_operation<=3;
                            state<=CFG_REQ;
                        end
                    end
                    PREPARE:begin
                        if(cmd_address_i!=0 || cmd_data_i!=0)reply_status_o<=BAD_FIELDS;
                        else if(!verified[cmd_target_i])reply_status_o<=NOT_READY;
                        else begin cfg_operation<=4;state<=CFG_REQ;end
                    end
                    default:reply_status_o<=BAD_COMMAND;
                endcase
            end
            RELEASE_REQ:if(&release_ready_o)begin
                release_sequence<=payload[31:0];release_epoch<=payload[63:32];state<=RESPOND;
            end
            CFG_REQ:if(cfg_req_ready_o[target])state<=CFG_WAIT;
            CFG_WAIT:if(cfg_rsp_valid_o[target])begin
                reply_status_o<=error_override!=0 ? error_override : cfg_status;state<=RESPOND;
                if(cfg_status==0)case(cfg_operation)
                    0:begin
                        if(deploy_valid_i)begin begun<=0;verified<=0;prepared<=0;deploy_valid_i<=0;end
                        begun[target]<=1;verified[target]<=0;prepared[target]<=0;
                        generation[target]<=payload[31:0];total[target]<=payload[47:32];image_id[target]<=payload[79:48];
                        topology[target]<=payload[111:80];abi[target]<=payload[143:112];capacity[target]<=payload[175:144];
                        written[target]<=0;readback[target]<=0;write_crc[target]<=32'hffffffff;read_crc[target]<=32'hffffffff;
                    end
                    1,2:begin
                        crc_word<=cfg_operation==1 ? payload[127:0] : cfg_data;
                        crc_state<=cfg_operation==1 ? write_crc[target] : read_crc[target];
                        crc_is_read<=cfg_operation==2;crc_bit<=0;state<=CRC;
                        if(cfg_operation==2)reply_data_o[127:0]<=cfg_data;
                    end
                    3:verified[target]<=1;
                    4:prepared[target]<=1;
                    5:begin begun[target]<=0;verified[target]<=0;prepared[target]<=0;end
                    default:begin end
                endcase
                else if(operation!=BEGIN_IMAGE)begin verified[target]<=0;prepared[target]<=0;end
            end
            CRC:begin
                crc_state<=crc_next;crc_word<=crc_word>>1;
                if(crc_bit==127)begin
                    if(crc_is_read)begin read_crc[target]<=crc_next;readback[target]<=readback[target]+16;end
                    else begin write_crc[target]<=crc_next;written[target]<=written[target]+16;end
                    reply_data_o[159:128]<=~crc_next;state<=RESPOND;
                end else crc_bit<=crc_bit+1;
            end
            DEPLOY_WAIT:if(image_valid_o==3'b111)state<=RESPOND;
                        else if(|poison_o)begin reply_status_o<=NOT_READY;state<=RESPOND;end
            START_REQ:if(start_ready_o)begin last_start<=payload[95:64];state<=RESPOND;end
            S_REQ:if(host_req_ready_o[target-1])state<=S_WAIT;
            S_WAIT:if(host_rsp_valid_o[target-1])begin reply_data_o[127:0]<=host_rsp_data_o[(target-1)*128+:128];state<=RESPOND;end
            RESPOND:if(reply_ready_i)state<=IDLE;
            default:state<=IDLE;
        endcase
    end
endmodule
