`timescale 1ns/1ps
// Single-head Q16 causal attention. The LC supplies the finite window and KV region.
module s128_attention_core_scope #(
    parameter logic [31:0] TOPOLOGY=0,
    parameter bit PIPELINE_KV_WRITES=1'b0,
    parameter int V_READS_PER_16=4
) (
    input logic clk,reset,
    input logic service_valid,
    output logic service_ready,
    input logic [127:0] service_owner,
    input logic [31:0] service_ticket,
    input logic [1023:0] service_descriptor,
    input logic service_cancel_valid,
    output logic service_cancel_ready,
    output logic service_done_valid,
    input logic service_done_ready,
    output logic [127:0] service_done_owner,
    output logic [31:0] service_done_ticket,
    output logic [15:0] service_done_status,
    output logic [31:0] service_done_read_bytes,service_done_write_bytes,
    output logic rd_valid,
    input logic rd_ready,
    output logic [63:0] rd_address,rd_tag,
    input logic rd_rsp_valid,
    output logic rd_rsp_ready,
    input logic [63:0] rd_rsp_tag,
    input logic [511:0] rd_rsp_data,
    input logic rd_rsp_error,
    output logic s_req_valid,s_req_write,
    input logic s_req_ready,
    output logic [9:0] s_req_address,
    output logic [127:0] s_req_data,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [127:0] s_rsp_data,
    input logic s_rsp_error
);
    localparam logic [31:0] SCHEMA=32'h31545441, ABI=32'h02500002;
    localparam logic [15:0] BAD_DESCRIPTOR=16'h0240, ABORTED=16'h0241, SERVICE_FAULT=16'h0242;
    typedef enum logic [4:0] {
        IDLE,K_REFILL,K_WAIT,DOT_BEGIN,DOT_BEGIN_WAIT,DOT_STEP,DOT_WAIT,
        SCALE_READ,SCALE_READ_WAIT,SCALE_SEND,SCALE_RESULT,SCALE_WRITE,SCALE_ACK,
        N_START,N_WAIT,V_REFILL,V_WAIT,V_SAVE,V_SAVE_WAIT,V_RESTORE,V_RESTORE_WAIT,RECOVER,REPORT
    } state_t;
    state_t state;
    logic [15:0] count,first,filled;
    logic [3:0] group_index;
    logic [9:0] q_base,score_base,work_base,out_base,score_word;
    logic [63:0] k_base,v_base;
    logic [31:0] coefficient,serial;
    logic av,cancelled;
    logic [127:0] scale_input,scale_output;
    logic [1:0] scale_send;
    logic scale_high;
    wire [15:0] launch_count=service_descriptor[143:128];
    wire [15:0] launch_position=service_descriptor[159:144];
    wire [15:0] launch_q=service_descriptor[175:160],launch_score=service_descriptor[191:176];
    wire [15:0] launch_work=service_descriptor[207:192],launch_out=service_descriptor[223:208];
    wire [31:0] launch_scale=service_descriptor[255:224];
    wire [63:0] launch_k=service_descriptor[319:256],launch_v=service_descriptor[383:320];
    // Dot validates a full 32-word A reservation even for the final short chunk.
    wire [15:0] score_span=((launch_count+16'd127)>>7)<<5;
    wire [64:0] kv_span={40'd0,launch_count,9'd0};
    wire [64:0] k_end={1'b0,launch_k}+kv_span,v_end={1'b0,launch_v}+kv_span;

    function automatic logic disjoint(input logic [15:0] a, a_words, b, b_words);
        return {1'b0,a}+{1'b0,a_words}<={1'b0,b} || {1'b0,b}+{1'b0,b_words}<={1'b0,a};
    endfunction
    wire valid_descriptor=TOPOLOGY!=0 && service_descriptor[31:0]==SCHEMA &&
        service_descriptor[47:32]==128 && service_descriptor[63:48]==1 &&
        service_descriptor[95:64]==ABI && service_descriptor[127:96]==TOPOLOGY &&
        service_descriptor[991:384]=='0 && launch_count!=0 && launch_count<=639 &&
        launch_position==launch_count-1'b1 && launch_scale!=0 && launch_scale<=32'h40000000 &&
        launch_q<=992 && launch_out<=992 && launch_work<=768 && {1'b0,launch_score}+{1'b0,score_span}<=1024 &&
        disjoint(launch_q,32,launch_out,32) && disjoint(launch_q,32,launch_work,256) &&
        disjoint(launch_q,32,launch_score,score_span) && disjoint(launch_out,32,launch_work,256) &&
        disjoint(launch_out,32,launch_score,score_span) && disjoint(launch_work,256,launch_score,score_span) &&
        launch_k[5:0]==0 && launch_v[5:0]==0 && k_end<=(65'd1<<64) && v_end<=(65'd1<<64) &&
        (k_end<={1'b0,launch_v} || v_end<={1'b0,launch_k});
    // Descriptor CRC is checked on fetched DDR bytes by the LC.
    wire _unused_crc=^service_descriptor[1023:992];
    wire datapath_reset=reset||state==RECOVER;
    wire cancel=service_cancel_valid&&service_cancel_ready;
    assign service_ready=!reset&&state==IDLE;
    assign service_cancel_ready=!reset&&state!=IDLE&&state!=RECOVER&&state!=REPORT&&!cancelled;
    assign service_done_valid=!reset&&state==REPORT;

    wire [15:0] remaining=count-first;
    wire [3:0] qk_columns=remaining>=8 ? 4'd8 : remaining[3:0];
    localparam bit REUSE_V=V_READS_PER_16==1;
    initial assert(V_READS_PER_16 inside {1,2,4});
    localparam logic [7:0] AV_CHUNK=REUSE_V ? 8'd32 : 8'd128;
    wire [7:0] av_length=remaining>=16'(AV_CHUNK) ? AV_CHUNK : remaining[7:0];
    wire [10:0] score_words=(11'(count)+11'd3)>>2;
    wire load_active=state==K_REFILL||state==K_WAIT||state==V_REFILL||state==V_WAIT;
    wire value_refill=state==V_REFILL||state==V_WAIT;
    wire [15:0] v_position=first+filled;
    wire [63:0] v_beat_offset={55'd0,group_index[3:2],7'd0}+
        ((V_READS_PER_16!=4 && group_index[1]) ? 64'd64 : 64'd0);
    wire [63:0] refill_base=value_refill ?
        v_base+{39'd0,v_position,9'd0}+v_beat_offset : k_base+{39'd0,first,9'd0};
    wire [9:0] v_row_offset=REUSE_V ? {filled[7:0],2'b0} : {filled[8:0],1'b0};
    wire [9:0] refill_s_base=value_refill ? work_base+v_row_offset : work_base;
    wire load_ready,load_done,load_error,load_s_valid,load_s_take,load_rd_take;
    wire [9:0] load_s_address;
    wire [127:0] load_s_data;
    wire [31:0] load_s_tag;
    wire [63:0] load_rd_tag;
    logic [31:0] load_s_tags[2];
    logic load_s_head,load_s_tail;
    wire [31:0] accepted_s_tag=load_s_tags[load_s_head];
    logic [63:0] accepted_rd_tag,accepted_load_tag;
    assign rd_tag={service_done_ticket,serial};
    wire good_rd=rd_rsp_tag==accepted_rd_tag&&!rd_rsp_error;
    s128_ddr_range_load #(.PIPELINE_WRITES(PIPELINE_KV_WRITES)) load_span(
        .clk,.reset(datapath_reset),.launch_valid(state==K_REFILL||state==V_REFILL),.launch_ready(load_ready),
        .launch_base(refill_base),.launch_s_base(refill_s_base),
        .launch_bursts(value_refill ? (V_READS_PER_16==4 ? 8'd2 : 8'd1) : {1'b0,qk_columns,3'b0}),
        .launch_pair(value_refill&&!REUSE_V),.launch_pair_beat(V_READS_PER_16==4&&group_index[1]),
        .launch_pair_high(group_index[0]),
        .done_valid(load_done),.done_error(load_error),.done_ready(state==K_WAIT||state==V_WAIT),
        .rd_valid,.rd_ready,.rd_address,.rd_tag(load_rd_tag),.rd_rsp_valid,.rd_rsp_ready(load_rd_take),
        .rd_rsp_tag(good_rd ? accepted_load_tag : accepted_load_tag ^ 64'd1),.rd_rsp_data,
        .s_valid(load_s_valid),.s_ready(load_active&&s_req_ready),.s_address(load_s_address),
        .s_data(load_s_data),.s_tag(load_s_tag),.s_rsp_valid(load_active&&s_rsp_valid),
        .s_rsp_ready(load_s_take),.s_rsp_tag(s_rsp_error ? accepted_s_tag ^ 32'd1 : accepted_s_tag));
    assign rd_rsp_ready=load_rd_take;

    wire dot_snapshot=state==V_SAVE||state==V_SAVE_WAIT||state==V_RESTORE||state==V_RESTORE_WAIT;
    wire dot_restore=state==V_RESTORE||state==V_RESTORE_WAIT;
    wire dot_active=state==DOT_BEGIN||state==DOT_BEGIN_WAIT||state==DOT_STEP||state==DOT_WAIT||dot_snapshot;
    wire dot_begin=state==DOT_BEGIN||state==DOT_BEGIN_WAIT;
    wire dot_ready,dot_done,dot_error,dot_aborted,dot_final;
    wire [1:0] dot_kind,dot_mask;
    wire [31:0] dot_tag;
    wire [127:0] dot_key;
    wire dot_s_valid,dot_s_write,dot_s_take;
    wire [9:0] dot_s_address;
    wire [127:0] dot_s_data;
    wire [9:0] dot_result=av ? out_base+{5'd0,group_index,1'b0} : score_base+first[11:2];
    wire [9:0] snapshot_base=work_base+(group_index[0] ? 10'd135 : 10'd128);
    wire [9:0] b_offset=dot_s_address-work_base;
    // Dot sees its existing two-word rows. One physical four-word row serves
    // the even and odd output groups in separate passes over the same span.
    wire shared_v_word=REUSE_V&&av&&!dot_snapshot&&!dot_s_write&&b_offset<10'd64;
    wire [9:0] physical_dot_address=shared_v_word ?
        work_base+{b_offset[8:1],group_index[0],b_offset[0]} : dot_s_address;
    dot_s32_s128 #(.ROWS(1),.REFILL_NEXT(1'b1),.CHECKPOINT(1'b1),
                   .AV_MAX_K(32'(AV_CHUNK))) dot(
        .clk,.reset(datapath_reset),.cmd_valid(state==DOT_BEGIN||state==DOT_STEP||
                 state==V_SAVE||state==V_RESTORE),.cmd_ready(dot_ready),
        .cmd_kind(dot_snapshot ? 2'd3 : dot_begin ? 2'd0 : 2'd1),.cmd_key(service_done_owner),.cmd_tag(serial),
        .cmd_full_k(av ? count : 16'd128),
        .cmd_k_offset(state==V_SAVE ? first+{8'd0,av_length} : av&&!dot_begin ? first : 16'd0),
        .cmd_chunk_k(dot_begin ? 8'd0 : av ? av_length : 8'd128),.cmd_n(av ? 4'd8 : qk_columns),
        .cmd_rows(3'd1),.cmd_shift(6'd16),.cmd_layout(dot_snapshot ? dot_restore : av),
        .cmd_a_base(dot_snapshot ? snapshot_base : av ? score_base+first[11:2] : q_base),
        .cmd_b_base(dot_snapshot ? 10'd1 : work_base),.cmd_result_base(dot_result),.cmd_sources_committed(1'b1),
        .abort_valid(1'b0),.abort_key(128'd0),.abort_ready(),
        .rsp_valid(dot_done),.rsp_ready(state==DOT_BEGIN_WAIT||state==DOT_WAIT||
                    state==V_SAVE_WAIT||state==V_RESTORE_WAIT),.rsp_kind(dot_kind),
        .rsp_key(dot_key),.rsp_tag(dot_tag),.rsp_error(dot_error),.rsp_aborted(dot_aborted),
        .rsp_done(dot_final),.rsp_written_mask(dot_mask),.s_req_valid(dot_s_valid),
        .s_req_ready(dot_active&&s_req_ready),.s_req_write(dot_s_write),.s_req_address(dot_s_address),
        .s_req_wdata(dot_s_data),.s_rsp_valid(dot_active&&s_rsp_valid),.s_rsp_ready(dot_s_take),
        .s_rsp_data,.s_rsp_error);

    wire norm_active=state==N_START||state==N_WAIT;
    wire norm_ready,norm_done,norm_error,norm_aborted,norm_s_valid,norm_s_write,norm_s_take;
    wire [9:0] norm_s_address;
    wire [127:0] norm_s_data;
    wire [31:0] norm_tag;
    wire [11:0] norm_writes;
    n_s32_softmax_s128 norm(
        .clk,.reset(datapath_reset),.cmd_valid(state==N_START),.cmd_ready(norm_ready),.cmd_tag(serial),
        .cmd_base(score_base),.cmd_count(13'(count)),.cmd_committed(1'b1),
        .abort_valid(1'b0),.abort_ready(),.abort_tag(32'd0),
        .rsp_valid(norm_done),.rsp_ready(state==N_WAIT),.rsp_tag(norm_tag),.rsp_error(norm_error),
        .rsp_aborted(norm_aborted),.rsp_writes(norm_writes),.s_req_valid(norm_s_valid),
        .s_req_ready(norm_active&&s_req_ready),.s_req_write(norm_s_write),.s_req_address(norm_s_address),
        .s_req_data(norm_s_data),.s_rsp_valid(norm_active&&s_rsp_valid),.s_rsp_ready(norm_s_take),
        .s_rsp_data,.s_rsp_error);

    wire e_ready,e_done,e_error;
    wire [63:0] e_result;
    wire [3:0] e_clipped;
    e_s32_ap64 scale(
        .clk,.reset(datapath_reset),.in_valid(state==SCALE_SEND),.in_ready(e_ready),
        .in_data(scale_send[1] ? {coefficient,coefficient} : scale_input[64*scale_send[0]+:64]),
        .in_op(4'd2),.in_mask(4'hf),.in_shift(8'd30),.in_minus(3'd0),
        .out_valid(e_done),.out_ready(state==SCALE_RESULT),.out_data(e_result),
        .out_clipped(e_clipped),.out_error(e_error));

    always_comb begin
        s_req_valid=state==SCALE_READ||state==SCALE_WRITE;
        s_req_write=state==SCALE_WRITE;
        s_req_address=score_base+score_word;
        s_req_data=scale_output;
        s_rsp_ready=state==SCALE_READ_WAIT||state==SCALE_ACK;
        if(load_active) begin
            s_req_valid=load_s_valid;
            s_req_write=1;
            s_req_address=load_s_address;
            s_req_data=load_s_data;
            s_rsp_ready=load_s_take;
        end else if(dot_active) begin
            s_req_valid=dot_s_valid;
            s_req_write=dot_s_write;
            s_req_address=physical_dot_address;
            s_req_data=dot_s_data;
            s_rsp_ready=dot_s_take;
        end else if(norm_active) begin
            s_req_valid=norm_s_valid;
            s_req_write=norm_s_write;
            s_req_address=norm_s_address;
            s_req_data=norm_s_data;
            s_rsp_ready=norm_s_take;
        end
    end
    wire dot_tag_ok=dot_tag==serial&&dot_key==service_done_owner&&!dot_error&&!dot_aborted;
    wire final_chunk=!av||first+{8'd0,av_length}==count;

    task automatic fault();
        service_done_status<=SERVICE_FAULT;
        state<=RECOVER;
    endtask

    always_ff @(posedge clk) begin
        if(reset) begin
            state<=IDLE; av<=0; cancelled<=0; count<=0; first<=0; filled<=0; group_index<=0;
            q_base<=0; score_base<=0; work_base<=0; out_base<=0; score_word<=0; k_base<=0; v_base<=0;
            coefficient<=0; serial<=0; scale_input<=0; scale_output<=0; scale_send<=0; scale_high<=0;
            load_s_tags[0]<=0; load_s_tags[1]<=0;
            load_s_head<=0; load_s_tail<=0;
            accepted_rd_tag<=0; accepted_load_tag<=0;
            service_done_owner<=0; service_done_ticket<=0; service_done_status<=0;
            service_done_read_bytes<=0; service_done_write_bytes<=0;
        end else begin
            if(cancel) cancelled<=1;
            if(load_s_valid&&load_active&&s_req_ready) begin
                load_s_tags[load_s_tail]<=load_s_tag;
                load_s_tail<=!load_s_tail;
            end
            if(load_active&&s_rsp_valid&&load_s_take) load_s_head<=!load_s_head;
            if(rd_valid&&rd_ready) begin
                accepted_rd_tag<=rd_tag;
                accepted_load_tag<=load_rd_tag;
                serial<=serial+1'b1;
            end
            if(rd_rsp_valid&&rd_rsp_ready&&good_rd) service_done_read_bytes<=service_done_read_bytes+64;
            case(state)
                IDLE: if(service_valid&&service_ready) begin
                    service_done_owner<=service_owner; service_done_ticket<=service_ticket;
                    service_done_status<=valid_descriptor ? 16'd0 : BAD_DESCRIPTOR;
                    service_done_read_bytes<=0; service_done_write_bytes<=0;
                    count<=launch_count; q_base<=launch_q[9:0]; score_base<=launch_score[9:0];
                    work_base<=launch_work[9:0]; out_base<=launch_out[9:0];
                    k_base<=launch_k; v_base<=launch_v; coefficient<=launch_scale;
                    av<=0; cancelled<=0; first<=0; filled<=0; group_index<=0; score_word<=0; serial<=0;
                    state<=valid_descriptor ? K_REFILL : REPORT;
                end
                K_REFILL: if(load_ready) state<=K_WAIT;
                K_WAIT: if(load_done) begin
                    if(load_error) fault();
                    else state<=DOT_BEGIN;
                end
                DOT_BEGIN: if(dot_ready) state<=DOT_BEGIN_WAIT;
                DOT_BEGIN_WAIT: if(dot_done) begin
                    if(!dot_tag_ok||dot_kind!=0||dot_final||dot_mask!=0) fault();
                    else state<=!av||REUSE_V ? DOT_STEP : V_REFILL;
                end
                DOT_STEP: if(dot_ready) state<=DOT_WAIT;
                DOT_WAIT: if(dot_done) begin
                    if(!dot_tag_ok||dot_kind!=1||dot_final!=final_chunk||dot_mask!=(final_chunk ? 2'b11 : 2'b00))
                        fault();
                    else if(!av) begin
                        if(remaining<=8) state<=SCALE_READ;
                        else begin first<=first+8; state<=K_REFILL; end
                    end else if(!final_chunk) begin
                        if(REUSE_V) state<=V_SAVE;
                        else begin first<=first+{8'd0,av_length}; filled<=0; state<=V_REFILL; end
                    end else begin
                        service_done_write_bytes<=service_done_write_bytes+32;
                        if(group_index==15) begin
                            if(service_done_read_bytes!=32'(count)*(512+512*V_READS_PER_16) ||
                                service_done_write_bytes!=480) fault();
                            else begin
                                if(cancelled||cancel) service_done_status<=ABORTED;
                                state<=REPORT;
                            end
                        end else begin
                            group_index<=group_index+1'b1;
                            if(REUSE_V&&!group_index[0]) state<=first==0 ? DOT_BEGIN : V_RESTORE;
                            else begin
                                first<=0; filled<=0;
                                state<=REUSE_V ? V_REFILL : DOT_BEGIN;
                            end
                        end
                    end
                end
                SCALE_READ: if(s_req_ready) state<=SCALE_READ_WAIT;
                SCALE_READ_WAIT: if(s_rsp_valid) begin
                    if(s_rsp_error) fault();
                    else begin scale_input<=s_rsp_data; scale_send<=0; scale_high<=0; state<=SCALE_SEND; end
                end
                SCALE_SEND: if(e_ready) begin
                    if(&scale_send) state<=SCALE_RESULT;
                    else scale_send<=scale_send+1'b1;
                end
                SCALE_RESULT: if(e_done) begin
                    if(e_error||e_clipped!=0) fault();
                    else begin
                        scale_output[64*scale_high+:64]<=e_result;
                        if(scale_high) state<=SCALE_WRITE;
                        else scale_high<=1;
                    end
                end
                SCALE_WRITE: if(s_req_ready) state<=SCALE_ACK;
                SCALE_ACK: if(s_rsp_valid) begin
                    if(s_rsp_error) fault();
                    else if({1'b0,score_word}+11'd1==score_words) state<=N_START;
                    else begin score_word<=score_word+1'b1; state<=SCALE_READ; end
                end
                N_START: if(norm_ready) state<=N_WAIT;
                N_WAIT: if(norm_done) begin
                    if(norm_error||norm_aborted||norm_tag!=serial||norm_writes!={score_words,1'b0}) fault();
                    else begin
                        av<=1; first<=0; filled<=0;
                        state<=REUSE_V ? V_REFILL : DOT_BEGIN;
                    end
                end
                V_REFILL: if(load_ready) state<=V_WAIT;
                V_WAIT: if(load_done) begin
                    if(load_error) fault();
                    else if(filled+16'd1=={8'd0,av_length})
                        state<=!REUSE_V ? DOT_STEP : first==0 ? DOT_BEGIN : V_RESTORE;
                    else begin filled<=filled+1'b1; state<=V_REFILL; end
                end
                V_SAVE: if(dot_ready) state<=V_SAVE_WAIT;
                V_SAVE_WAIT: if(dot_done) begin
                    if(!dot_tag_ok||dot_kind!=3||dot_final||dot_mask!=0) fault();
                    else if(group_index[0]) begin
                        group_index<=group_index-1'b1;
                        first<=first+{8'd0,av_length}; filled<=0; state<=V_REFILL;
                    end else begin
                        group_index<=group_index+1'b1;
                        state<=first==0 ? DOT_BEGIN : V_RESTORE;
                    end
                end
                V_RESTORE: if(dot_ready) state<=V_RESTORE_WAIT;
                V_RESTORE_WAIT: if(dot_done) begin
                    if(!dot_tag_ok||dot_kind!=3||dot_final||dot_mask!=0) fault();
                    else state<=DOT_STEP;
                end
                // The child terminal has drained accepted SRAM/DDR requests.
                // Clear any AV accumulator or E output retained on a failed service.
                RECOVER: state<=REPORT;
                REPORT: if(service_done_ready) state<=IDLE;
                default: fault();
            endcase
        end
    end
endmodule
