// Candidate LC-owned S128 stream adapter for G32_SILU. No SRAM added.
// Two input slots, each gate128+up128 (64B total); two Mid128 output
// slots (32B total). A written output slot remains owned until real S ACK.
// Each command covers 1..32 words of four S32 values in disjoint S windows.
// Faults drain accepted S/G work, report committed prefix words, and require
// LC recovery/replay; they do not claim a transactional rollback of SRAM.
module g_s128_frontend (
    input wire clk, reset,
    input wire cmd_valid, output wire cmd_ready,
    input wire [9:0] cmd_gate_base, cmd_up_base, cmd_mid_base,
    input wire [5:0] cmd_words, input wire cmd_gated,
    output reg done_valid, input wire done_take,
    output reg done_error, output reg [5:0] done_words,
    output reg s_req_valid, output reg s_req_write,
    output reg [9:0] s_req_addr, output reg [127:0] s_req_data,
    input wire s_req_ready, s_rsp_valid,
    output wire s_rsp_ready, input wire [127:0] s_rsp_data,
    output wire g_in_valid, input wire g_in_ready,
    output wire [63:0] g_in_gate, g_in_up,
    output wire g_in_gated, output wire [1:0] g_in_mask,
    input wire g_out_valid, output wire g_out_ready,
    input wire [63:0] g_out_data, input wire [1:0] g_out_mask,
    input wire g_out_error
);
    localparam [1:0] READ_GATE=0, READ_UP=1, WRITE_MID=2;
    reg busy, fault, gated;
    reg [9:0] gate_base, up_base, mid_base;
    reg [5:0] words, read_word, input_word, output_word, write_word, committed;
    reg [1:0] phase;
    reg [127:0] gate_hold[0:1], up_hold[0:1], mid_hold[0:1];
    reg [1:0] input_busy, gate_returned, up_returned;
    reg [1:0] output_busy, output_ready, output_pending;
    reg input_half, output_half;
    reg [2:0] g_pending;
    reg [1:0] tag_kind[0:1];
    reg tag_slot[0:1], tag_head, tag_tail;
    reg [1:0] tag_count;
    reg [1:0] request_kind;
    reg request_slot;
    reg request_stalled, held_slot;
    reg [1:0] held_kind;

    wire [10:0] gate_limit={1'b0,cmd_gate_base}+{5'b0,cmd_words};
    wire [10:0] up_limit={1'b0,cmd_up_base}+{5'b0,cmd_words};
    wire [10:0] mid_limit={1'b0,cmd_mid_base}+{5'b0,cmd_words};
    wire command_legal=(cmd_words!=0 && cmd_words<=6'd32 &&
        gate_limit<=11'd1024 && up_limit<=11'd1024 && mid_limit<=11'd1024 &&
        (gate_limit<={1'b0,cmd_up_base} || up_limit<={1'b0,cmd_gate_base}) &&
        (gate_limit<={1'b0,cmd_mid_base} || mid_limit<={1'b0,cmd_gate_base}) &&
        (up_limit<={1'b0,cmd_mid_base} || mid_limit<={1'b0,cmd_up_base}));
    assign cmd_ready=!reset && !busy && !done_valid;
    assign s_rsp_ready=!reset && busy && tag_count!=0;
    wire response_fire=s_rsp_valid && s_rsp_ready;
    wire tag_space=tag_count<2 || response_fire;
    wire request_fire=s_req_valid && s_req_ready;
    wire input_slot=input_word[0];
    wire result_slot=output_word[0];
    assign g_in_valid=!reset && busy && !fault && input_word<words &&
        gate_returned[input_slot] && up_returned[input_slot];
    assign g_in_gate=input_half ? gate_hold[input_slot][127:64] : gate_hold[input_slot][63:0];
    assign g_in_up=input_half ? up_hold[input_slot][127:64] : up_hold[input_slot][63:0];
    assign g_in_gated=gated;
    assign g_in_mask=2'b11;
    assign g_out_ready=!reset && busy && (fault || (!output_ready[result_slot] &&
        !output_pending[result_slot] && (!output_busy[result_slot] || output_half)));
    wire g_input_fire=g_in_valid && g_in_ready;
    wire g_output_fire=g_out_valid && g_out_ready;
    wire packet_fault=g_out_error || g_out_mask!=2'b11;

    always @* begin
        s_req_valid=0; s_req_write=0; s_req_addr=0; s_req_data=0;
        request_kind=READ_GATE; request_slot=read_word[0];
        if(!reset && busy && request_stalled) begin
            s_req_valid=1; request_kind=held_kind; request_slot=held_slot;
            if(held_kind==WRITE_MID) begin
                s_req_write=1; s_req_addr=mid_base+{4'b0,write_word}; s_req_data=mid_hold[held_slot];
            end else s_req_addr=(held_kind==READ_GATE ? gate_base : up_base)+{4'b0,read_word};
        end else if(!reset && busy && !fault && tag_space) begin
            if(phase==0 && read_word<words && !input_busy[read_word[0]]) begin
                s_req_valid=1; s_req_addr=gate_base+{4'b0,read_word};
            end else if(phase==1 && read_word<words && input_busy[read_word[0]] &&
                        !up_returned[read_word[0]]) begin
                s_req_valid=1; s_req_addr=up_base+{4'b0,read_word}; request_kind=READ_UP;
            end else if(phase==2 && write_word<words && output_ready[write_word[0]]) begin
                s_req_valid=1; s_req_write=1; s_req_addr=mid_base+{4'b0,write_word};
                s_req_data=mid_hold[write_word[0]]; request_kind=WRITE_MID; request_slot=write_word[0];
            end
        end
    end

    always @(posedge clk) begin
        if(reset) begin
            busy<=0; fault<=0; gated<=0; done_valid<=0; done_error<=0; done_words<=0;
            gate_base<=0; up_base<=0; mid_base<=0; words<=0; read_word<=0;
            input_word<=0; output_word<=0; write_word<=0; committed<=0;
            phase<=0; input_busy<=0; gate_returned<=0; up_returned<=0;
            output_busy<=0; output_ready<=0; output_pending<=0;
            input_half<=0; output_half<=0; g_pending<=0; tag_count<=0; tag_head<=0; tag_tail<=0;
            request_stalled<=0; held_slot<=0; held_kind<=0;
        end else begin
            if(done_valid && done_take) done_valid<=0;
            if(cmd_valid && cmd_ready) begin
                done_error<=!command_legal; done_words<=0;
                if(!command_legal) done_valid<=1;
                else begin
                    busy<=1; fault<=0; gated<=cmd_gated;
                    gate_base<=cmd_gate_base; up_base<=cmd_up_base; mid_base<=cmd_mid_base;
                    words<=cmd_words; read_word<=0; input_word<=0; output_word<=0;
                    write_word<=0; committed<=0; phase<=0; input_busy<=0;
                    gate_returned<=0; up_returned<=0; output_busy<=0; output_ready<=0;
                    output_pending<=0; input_half<=0; output_half<=0;
                    g_pending<=0; tag_count<=0; tag_head<=0; tag_tail<=0;
                    request_stalled<=0;
                end
            end
            if(busy) begin
                if(!(s_req_valid && !s_req_ready)) phase<=phase==2 ? 0 : phase+2'd1;
                if(s_req_valid && !s_req_ready) begin
                    request_stalled<=1; held_kind<=request_kind; held_slot<=request_slot;
                end
                if(request_fire) request_stalled<=0;
                case({request_fire,response_fire})
                    2'b10: tag_count<=tag_count+2'd1;
                    2'b01: tag_count<=tag_count-2'd1;
                    default: begin end
                endcase
                if(request_fire) begin
                    tag_kind[tag_tail]<=request_kind; tag_slot[tag_tail]<=request_slot; tag_tail<=!tag_tail;
                    case(request_kind)
                        READ_GATE: input_busy[request_slot]<=1;
                        READ_UP: read_word<=read_word+6'd1;
                        WRITE_MID: begin
                            output_ready[request_slot]<=0; output_pending[request_slot]<=1;
                            write_word<=write_word+6'd1;
                        end
                        default: begin end
                    endcase
                end
                if(response_fire) begin
                    tag_head<=!tag_head;
                    case(tag_kind[tag_head])
                        READ_GATE: begin gate_hold[tag_slot[tag_head]]<=s_rsp_data; gate_returned[tag_slot[tag_head]]<=1; end
                        READ_UP: begin up_hold[tag_slot[tag_head]]<=s_rsp_data; up_returned[tag_slot[tag_head]]<=1; end
                        WRITE_MID: begin
                            output_busy[tag_slot[tag_head]]<=0; output_pending[tag_slot[tag_head]]<=0;
                            committed<=committed+6'd1;
                        end
                        default: begin end
                    endcase
                end
                case({g_input_fire,g_output_fire})
                    2'b10: g_pending<=g_pending+3'd1;
                    2'b01: g_pending<=g_pending-3'd1;
                    default: begin end
                endcase
                if(g_input_fire) begin
                    input_half<=!input_half;
                    if(input_half) begin
                        input_word<=input_word+6'd1; input_busy[input_slot]<=0;
                        gate_returned[input_slot]<=0; up_returned[input_slot]<=0;
                    end
                end
                if(g_output_fire && !fault) begin
                    if(packet_fault) begin fault<=1; output_ready<=0; end
                    else begin
                        output_busy[result_slot]<=1;
                        if(output_half) begin
                            mid_hold[result_slot][127:64]<=g_out_data; output_ready[result_slot]<=1;
                            output_word<=output_word+6'd1;
                        end else mid_hold[result_slot][63:0]<=g_out_data;
                        output_half<=!output_half;
                    end
                end
                if((!fault && committed==words) || (fault && tag_count==0 && g_pending==0 && !s_req_valid)) begin
                    busy<=0; done_valid<=1; done_error<=fault; done_words<=committed;
                    input_busy<=0; gate_returned<=0; up_returned<=0;
                    output_busy<=0; output_ready<=0; output_pending<=0;
                end
            end
        end
    end
endmodule
