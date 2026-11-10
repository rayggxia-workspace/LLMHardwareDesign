// One command uses one private-S client. Capture operands before execution so
// an output may alias an input. Only a consumed S write response completes it.
module ucf_s_compute_client #(parameter integer NEXP_S16=0) (
    input wire clk, reset,
    input wire cmd_valid, output wire cmd_ready,
    input wire [63:0] cmd_meta,
    input wire [1:0] cmd_sources,
    input wire [29:0] cmd_addresses,
    input wire cmd_store, input wire [9:0] cmd_dst,
    output wire done_valid, input wire done_ready,
    output reg [127:0] done_data, output reg done_error, done_saturated,
    output wire s_req_valid, input wire s_req_ready,
    output wire s_req_write, output wire [9:0] s_req_addr,
    output wire [127:0] s_req_data,
    input wire s_rsp_valid, output wire s_rsp_ready,
    input wire [127:0] s_rsp_data,
    output wire exec_valid, input wire exec_ready,
    output reg [63:0] exec_meta,
    output reg [127:0] exec_a, exec_b, exec_c,
    input wire result_valid, output wire result_ready,
    input wire [127:0] result_data, input wire result_error, result_saturated
);
    localparam [2:0] IDLE=0, READ_REQ=1, READ_RSP=2, EXEC=3,
                     RESULT=4, WRITE_REQ=5, WRITE_RSP=6, DONE=7;
    reg [2:0] phase;
    reg [1:0] sources_left, source_index;
    reg [29:0] addresses;
    reg store_result;
    reg [9:0] destination;
    // NX16 explicitly reads packed S16 and writes zero-extended U16 EXP
    // results as one/two S32 words. Ordinary descriptors are unchanged.
    wire bridge_command=NEXP_S16!=0 && cmd_meta[3:0]==15 && cmd_meta[39:8]==32'h4e583136;
    wire bridge_bad=cmd_meta[63:40]!=0 || cmd_sources!=1 || cmd_addresses[29:10]!=0 ||
        cmd_meta[7:4]==0 || cmd_meta[7:4]>8 ||
        (cmd_meta[7:4]>4 && (!cmd_store || cmd_dst==1023));
    reg bridge,second_write;
    reg [3:0] bridge_count;
    reg [127:0] upper_result;
    reg [127:0] read_payload,lower_mapped,upper_mapped;
    always @* begin
        read_payload=s_rsp_data;lower_mapped=0;upper_mapped=0;
        if(bridge)begin
            for(integer k=0;k<8;k=k+1)begin
                if(k>=bridge_count)read_payload[16*k+:16]=0;
                if(k<bridge_count)begin
                    if(k<4)lower_mapped[32*k+:32]={16'd0,result_data[16*k+:16]};
                    else upper_mapped[32*(k-4)+:32]={16'd0,result_data[16*k+:16]};
                end
            end
        end
    end

    assign cmd_ready = !reset && phase == IDLE;
    assign done_valid = !reset && phase == DONE;
    assign s_req_valid = !reset && (phase == READ_REQ || phase == WRITE_REQ);
    assign s_req_write = phase == WRITE_REQ;
    assign s_req_addr = s_req_write ? destination : addresses[9:0];
    assign s_req_data = bridge && second_write ? upper_result : done_data;
    assign s_rsp_ready = !reset && (phase == READ_RSP || phase == WRITE_RSP);
    assign exec_valid = !reset && phase == EXEC;
    assign result_ready = !reset && phase == RESULT;

    always @(posedge clk) begin
        if (reset) begin
            phase <= IDLE;
            bridge<=0;second_write<=0;bridge_count<=0;upper_result<=0;
        end else begin
            case (phase)
                IDLE: if (cmd_valid) begin
                    exec_meta <= bridge_command ? {24'd0,32'h4e455850,cmd_meta[7:0]} : cmd_meta;
                    bridge<=bridge_command;bridge_count<=cmd_meta[7:4];second_write<=0;
                    exec_a <= 0;
                    exec_b <= 0;
                    exec_c <= 0;
                    sources_left <= cmd_sources;
                    source_index <= 0;
                    addresses <= cmd_addresses;
                    store_result <= cmd_store;
                    destination <= cmd_dst;
                    phase <= cmd_sources == 0 ? EXEC : READ_REQ;
                    if(bridge_command && bridge_bad)begin
                        done_data<=0;done_error<=1;done_saturated<=0;phase<=DONE;
                    end
                end
                READ_REQ: if (s_req_ready) phase <= READ_RSP;
                READ_RSP: if (s_rsp_valid) begin
                    case (source_index)
                        0: exec_a <= bridge ? read_payload : s_rsp_data;
                        1: exec_b <= s_rsp_data;
                        2: exec_c <= s_rsp_data;
                        default: ;
                    endcase
                    addresses <= {10'b0, addresses[29:10]};
                    source_index <= source_index + 1'b1;
                    sources_left <= sources_left - 1'b1;
                    phase <= sources_left == 1 ? EXEC : READ_REQ;
                end
                EXEC: if (exec_ready) phase <= RESULT;
                RESULT: if (result_valid) begin
                    done_data <= bridge ? lower_mapped : result_data;
                    if(bridge)upper_result<=upper_mapped;
                    done_error <= result_error;
                    done_saturated <= result_saturated;
                    phase <= store_result && !result_error ? WRITE_REQ : DONE;
                end
                WRITE_REQ: if (s_req_ready) phase <= WRITE_RSP;
                WRITE_RSP: if (s_rsp_valid) begin
                    if(bridge && bridge_count>4 && !second_write)begin
                        second_write<=1;destination<=destination+1'b1;phase<=WRITE_REQ;
                    end else phase<=DONE;
                end
                DONE: if (done_ready) phase <= IDLE;
                default: phase <= IDLE;
            endcase
        end
    end
endmodule
