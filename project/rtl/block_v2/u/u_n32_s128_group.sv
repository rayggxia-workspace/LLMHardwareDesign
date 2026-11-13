// One local-controller service lease over the existing U private S16 KiB.
// The three service descriptors separate producer commit, execute and custody.
module u_n32_s128_group (
    input wire clk, reset,
    input wire svc_valid, output wire svc_ready,
    input wire [1:0] svc_kind, input wire [2:0] svc_resource,
    input wire [2:0] svc_token,
    input wire [31:0] svc_sequence, svc_job, svc_epoch, svc_task_sequence,
    input wire [1023:0] descriptor,
    output wire rsp_valid, input wire rsp_ready,
    output reg [1:0] rsp_kind, output reg [2:0] rsp_token,
    output reg [31:0] rsp_sequence, rsp_job, rsp_epoch, rsp_task_sequence,
    output reg [15:0] status,
    output reg [31:0] read_bytes, write_bytes,
    input wire score_valid, output wire score_ready,
    input wire [127:0] score_data, input wire [31:0] score_tag,
    input wire [6:0] score_word, input wire [1:0] score_source, input wire score_slot,
    output wire score_ack_valid, input wire score_ack_ready,
    output wire [31:0] score_ack_tag, output reg [6:0] score_ack_word,
    output reg [1:0] score_ack_source, output wire score_ack_slot,
    output wire probability_valid, input wire probability_ready,
    output reg [127:0] probability_data, output wire [31:0] probability_tag,
    output wire [6:0] probability_word, output wire [1:0] probability_head,
    output wire [31:0] probability_sequence,
    input wire probability_ack_valid, output wire probability_ack_ready,
    input wire [31:0] probability_ack_sequence,
    output wire legacy_available, input wire legacy_active,
    input wire legacy_req_valid, legacy_req_write, input wire [9:0] legacy_req_address,
    input wire [127:0] legacy_req_data, output wire legacy_req_ready,
    output wire legacy_rsp_valid, input wire legacy_rsp_ready, output wire [127:0] legacy_rsp_data
);
    localparam [15:0] STAGE_ROW=16'h0130, SOFTMAX_ROW=16'h0131, DRAIN_ROW=16'h0132;
    localparam [15:0] OK=0, SERVICE_ERROR=5;
    localparam [31:0] ABI=32'h01930001;
    localparam [3:0] IDLE=0, FILL=1, STORE=2, STORE_ACK=3, SCORE_ACK=4,
        N_COMMAND=5, N_ACTIVE=6, FETCH=7, FETCH_ACK=8, PROBABILITY=9, CUSTODY=10, REPLY=11;
    localparam [1:0] EMPTY=0, SCORES_COMMITTED=1, PROBABILITIES_COMMITTED=2;

    reg [3:0] state;
    reg [1:0] lease;
    reg [9:0] base, count;
    reg [7:0] words, committed_words, drain_index;
    reg [31:0] row_tag, owner_job, owner_epoch, owner_task, sequence_base;
    reg row_slot;
    reg [1:0] row_head;
    reg [127:0] seen, held_score;
    reg [8:0] n_read_acks;
    reg n_owned_write;

    wire [15:0] operation = descriptor[32+:16];
    wire [31:0] field = descriptor[512+:32];
    wire [31:0] descriptor_tag = descriptor[544+:32];
    wire [31:0] descriptor_sequence = descriptor[576+:32];
    wire [9:0] descriptor_base = field[9:0];
    wire [9:0] descriptor_count = field[19:10];
    wire [7:0] descriptor_words = 8'(({1'b0, descriptor_count} + 11'd3) >> 2);
    wire sequence_wrap = descriptor_sequence > 32'hffffffff - {24'b0, descriptor_words} + 32'd1;
    wire descriptor_ok = svc_kind == 0 && svc_resource == 0 &&
        descriptor[0+:32] == 1 && descriptor[48+:16] == 0 &&
        descriptor[64+:32] == 32'hffffffff && descriptor[96+:64] == 0 &&
        descriptor[160+:48] == 48'hffffffffffff && descriptor[208+:240] == 0 &&
        descriptor[448+:32] == ABI && descriptor[480+:32] == 0 &&
        field[31:23] == 9'h002 && descriptor[1023:608] == 0 &&
        descriptor_count != 0 && descriptor_count <= 10'd512 &&
        ({1'b0, descriptor_base} + {3'b0, descriptor_words}) <= 11'd1024 &&
        (operation == DRAIN_ROW ? !sequence_wrap : descriptor_sequence == 0);
    wire same_row = descriptor_base == base && descriptor_count == count &&
        descriptor_tag == row_tag && field[20] == row_slot && field[22:21] == row_head &&
        svc_job == owner_job && svc_epoch == owner_epoch && svc_task_sequence == owner_task;

    assign legacy_available = !reset && state == IDLE && lease == EMPTY;
    wire legacy_selected = legacy_available && legacy_active;
    assign svc_ready = !reset && state == IDLE && !legacy_active;
    assign rsp_valid = !reset && state == REPLY;
    assign score_ready = !reset && state == FILL && score_tag == row_tag && score_slot == row_slot &&
        score_source < 2'd3 && {1'b0, score_word} < words && !seen[score_word];
    assign score_ack_valid = !reset && state == SCORE_ACK;
    assign score_ack_tag = row_tag;
    assign score_ack_slot = row_slot;
    assign probability_valid = !reset && state == PROBABILITY;
    assign probability_tag = row_tag;
    assign probability_word = drain_index[6:0];
    assign probability_head = row_head;
    assign probability_sequence = sequence_base + {24'b0, drain_index};
    assign probability_ack_ready = !reset && state == CUSTODY && probability_ack_sequence == probability_sequence;

    wire n_cmd_ready, n_rsp_valid, n_rsp_error, n_rsp_aborted;
    wire unused_abort_ready;
    wire [31:0] n_rsp_tag;
    wire [11:0] n_rsp_writes;
    wire n_req_valid, n_req_write, n_rsp_ready;
    wire [9:0] n_req_address;
    wire [127:0] n_req_data;
    wire n_selected = state == N_ACTIVE;
    wire mem_ready, mem_valid;
    wire [127:0] mem_result;
    wire mem_req = !reset && (legacy_selected ? legacy_req_valid :
        n_selected ? n_req_valid : state == STORE || state == FETCH);
    wire mem_write = legacy_selected ? legacy_req_write : n_selected ? n_req_write : state == STORE;
    wire [9:0] mem_addr = legacy_selected ? legacy_req_address : n_selected ? n_req_address :
        base + (state == STORE ? {3'b0, score_ack_word} : {2'b0, drain_index});
    wire [127:0] mem_data = legacy_selected ? legacy_req_data :
        n_selected ? n_req_data : state == STORE ? held_score : 128'b0;
    wire mem_take = !reset && (legacy_selected ? legacy_rsp_ready :
        n_selected ? n_rsp_ready : state == STORE_ACK || state == FETCH_ACK);
    assign legacy_req_ready = legacy_selected && mem_ready;
    assign legacy_rsp_valid = legacy_selected && mem_valid;
    assign legacy_rsp_data = mem_result;

    local_s_base store (
        .clk, .reset, .req_valid(mem_req), .req_write(mem_write), .req_addr(mem_addr), .req_data(mem_data),
        .req_ready(mem_ready), .rsp_valid(mem_valid), .rsp_ready(mem_take), .rsp_data(mem_result)
    );
    n_s32_softmax_s128 n32 (
        .clk, .reset, .cmd_valid(!reset && state == N_COMMAND), .cmd_ready(n_cmd_ready), .cmd_tag(row_tag),
        .cmd_base(base), .cmd_count({3'b0, count}), .cmd_committed(lease == SCORES_COMMITTED),
        .abort_valid(1'b0), .abort_ready(unused_abort_ready), .abort_tag(32'b0),
        .rsp_valid(n_rsp_valid), .rsp_ready(n_selected), .rsp_tag(n_rsp_tag),
        .rsp_error(n_rsp_error), .rsp_aborted(n_rsp_aborted), .rsp_writes(n_rsp_writes),
        .s_req_valid(n_req_valid), .s_req_ready(n_selected && mem_ready), .s_req_write(n_req_write),
        .s_req_address(n_req_address), .s_req_data(n_req_data), .s_rsp_valid(n_selected && mem_valid),
        .s_rsp_ready(n_rsp_ready), .s_rsp_data(mem_result), .s_rsp_error(1'b0)
    );

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            lease <= EMPTY;
            committed_words <= 0;
            drain_index <= 0;
        end else case (state)
            IDLE: if (svc_valid && svc_ready) begin
                rsp_kind <= svc_kind;
                rsp_token <= svc_token;
                rsp_sequence <= svc_sequence;
                rsp_job <= svc_job;
                rsp_epoch <= svc_epoch;
                rsp_task_sequence <= svc_task_sequence;
                status <= OK;
                read_bytes <= 0;
                write_bytes <= 0;
                if (descriptor_ok && operation == STAGE_ROW && lease == EMPTY) begin
                    base <= descriptor_base;
                    count <= descriptor_count;
                    words <= descriptor_words;
                    row_tag <= descriptor_tag;
                    row_slot <= field[20];
                    row_head <= field[22:21];
                    owner_job <= svc_job;
                    owner_epoch <= svc_epoch;
                    owner_task <= svc_task_sequence;
                    committed_words <= 0;
                    seen <= 0;
                    state <= FILL;
                end else if (descriptor_ok && operation == SOFTMAX_ROW && same_row && lease == SCORES_COMMITTED) begin
                    n_read_acks <= 0;
                    state <= N_COMMAND;
                end else if (descriptor_ok && operation == DRAIN_ROW && same_row && lease == PROBABILITIES_COMMITTED) begin
                    sequence_base <= descriptor_sequence;
                    drain_index <= 0;
                    state <= FETCH;
                end else begin
                    status <= SERVICE_ERROR;
                    state <= REPLY;
                end
            end
            FILL: if (score_valid && score_ready) begin
                held_score <= score_data;
                score_ack_word <= score_word;
                score_ack_source <= score_source;
                state <= STORE;
            end
            STORE: if (mem_ready) state <= STORE_ACK;
            STORE_ACK: if (mem_valid) begin
                seen[score_ack_word] <= 1'b1;
                committed_words <= committed_words + 8'd1;
                state <= SCORE_ACK;
            end
            SCORE_ACK: if (score_ack_ready) begin
                if (committed_words == words) begin
                    lease <= SCORES_COMMITTED;
                    write_bytes <= {20'b0, committed_words, 4'b0};
                    state <= REPLY;
                end else state <= FILL;
            end
            N_COMMAND: if (n_cmd_ready) state <= N_ACTIVE;
            N_ACTIVE: begin
                if (mem_req && mem_ready) n_owned_write <= mem_write;
                if (mem_take && mem_valid && !n_owned_write) n_read_acks <= n_read_acks + 9'd1;
                if (n_rsp_valid) begin
                    read_bytes <= {19'b0, n_read_acks, 4'b0};
                    write_bytes <= {16'b0, n_rsp_writes, 4'b0};
                    if (n_rsp_error || n_rsp_aborted || n_rsp_tag != row_tag) begin
                        status <= SERVICE_ERROR;
                        lease <= EMPTY;
                    end else lease <= PROBABILITIES_COMMITTED;
                    state <= REPLY;
                end
            end
            FETCH: if (mem_ready) state <= FETCH_ACK;
            FETCH_ACK: if (mem_valid) begin
                probability_data <= mem_result;
                state <= PROBABILITY;
            end
            PROBABILITY: if (probability_ready) state <= CUSTODY;
            CUSTODY: if (probability_ack_valid && probability_ack_ready) begin
                if (drain_index + 8'd1 == words) begin
                    lease <= EMPTY;
                    read_bytes <= {20'b0, words, 4'b0};
                    state <= REPLY;
                end else begin
                    drain_index <= drain_index + 8'd1;
                    state <= FETCH;
                end
            end
            REPLY: if (rsp_ready) state <= IDLE;
            default: begin state <= IDLE; lease <= EMPTY; end
        endcase
    end
endmodule
