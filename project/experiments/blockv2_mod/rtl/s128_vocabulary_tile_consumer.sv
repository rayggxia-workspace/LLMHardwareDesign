`timescale 1ns/1ps
// Retire a committed P tile through signed argmax before returning its LC terminal.
module s128_vocabulary_tile_consumer (
    input logic clk, reset,
    input logic job_valid,
    output logic job_ready,
    input logic [95:0] job_owner,
    input logic [31:0] job_length, job_tag,

    input logic launch_valid,
    output logic launch_ready,
    input logic [127:0] launch_owner,
    input logic [31:0] launch_first, launch_version,
    input logic [7:0] launch_count,
    input logic [9:0] launch_s_base,
    input logic p_done_valid,
    output logic p_done_ready,
    input logic [127:0] p_done_owner,
    input logic [15:0] p_done_status,
    input logic [31:0] p_done_read_bytes, p_done_write_bytes,

    output logic service_done_valid,
    input logic service_done_ready,
    output logic [127:0] service_done_owner,
    output logic [15:0] service_done_status,
    output logic [31:0] service_done_read_bytes, service_done_write_bytes,
    output logic s_read_valid,
    input logic s_read_ready,
    output logic [9:0] s_read_address,
    output logic [31:0] s_read_tag,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [31:0] s_rsp_tag,
    input logic [127:0] s_rsp_data,
    input logic s_rsp_error,
    output logic token_valid,
    input logic token_ready,
    output logic [31:0] token_id, token_tag,
    output logic signed [31:0] token_logit,
    output logic token_error,
    output logic fault
);
    localparam logic [15:0] CONSUMER_FAULT=16'h0240;
    typedef enum logic [2:0] {IDLE, PROJECT, CONSUME, FINAL_TOKEN, REPORT, FAILED} state_t;
    state_t state;
    logic job_live, last_tile, lease_ready, retire_job_ready;
    logic [95:0] active_owner;
    logic [31:0] active_length, active_tag;
    logic [127:0] expected_owner, read_owner, tile_owner;
    logic [31:0] tile_first, tile_tag, release_first;
    logic [7:0] tile_count;
    logic [9:0] tile_s_base;
    logic tile_valid, tile_ready, release_valid, release_ready, lease_fault;
    logic result_valid, result_ready, result_error;
    wire owner_match = tile_owner[127:32]==active_owner;
    wire [31:0] retire_tag = owner_match ? tile_tag : ~active_tag;
    wire [32:0] tile_end={1'b0,tile_first}+{25'd0,tile_count};
    wire last_release=release_valid&&release_ready&&last_tile;
    wire bad_response=s_rsp_error||s_rsp_tag!=s_read_tag;

    assign job_ready=!reset&&state==IDLE&&!job_live&&retire_job_ready;
    assign launch_ready=!reset&&state==IDLE&&job_live&&lease_ready;
    assign p_done_ready=!reset&&state==PROJECT;
    assign service_done_valid=!reset&&state==REPORT;
    assign token_valid=result_valid;
    assign token_error=result_error;
    assign result_ready=token_ready;
    assign fault=lease_fault||state==FAILED;

    p_static_output_lease lease(
        .clk,.reset,.launch_ready(lease_ready),.launch_valid(launch_valid&&launch_ready),
        .launch_owner,.launch_first,.launch_version,.launch_count,.launch_s_base,
        .commit_valid(p_done_valid&&p_done_ready),.commit_owner(p_done_owner),
        .commit_status(p_done_status),.tile_valid,.tile_ready,.tile_owner,.tile_first,.tile_tag,
        .tile_count,.tile_s_base,.release_valid,.release_ready,.release_owner(read_owner),.release_first,
        .fault(lease_fault));

    s128_vocabulary_retire retire(
        .clk,.reset,.job_valid(job_valid&&job_ready),.job_ready(retire_job_ready),.job_length,.job_tag,
        .tile_valid,.tile_ready,.tile_first,.tile_tag(retire_tag),.tile_count,.tile_s_base,
        .tile_release_valid(release_valid),.tile_release_ready(release_ready),.tile_release_first(release_first),
        .s_read_valid,.s_read_ready,.s_read_address,.s_read_tag,.s_rsp_valid,.s_rsp_ready,
        .s_rsp_tag,.s_rsp_data,.s_rsp_error,.token_valid(result_valid),.token_ready(result_ready),
        .token_id,.token_tag,.token_logit,.token_error(result_error));

    always_ff @(posedge clk) begin
        if (reset) begin
            state<=IDLE;
            job_live<=0;
            active_owner<=0;
            active_length<=0;
            active_tag<=0;
            last_tile<=0;
            expected_owner<=0;
            read_owner<=0;
            service_done_owner<=0;
            service_done_status<=0;
            service_done_read_bytes<=0;
            service_done_write_bytes<=0;
        end else begin
            if(job_valid&&job_ready) begin
                job_live<=1;
                active_owner<=job_owner;
                active_length<=job_length;
                active_tag<=job_tag;
            end
            if(result_valid&&result_ready) job_live<=0;
            if(tile_valid&&tile_ready) begin
                read_owner<=tile_owner;
                last_tile<=tile_end=={1'b0,active_length};
            end
            case(state)
                IDLE: if(launch_valid&&launch_ready) begin
                    expected_owner<=launch_owner;
                    state<=PROJECT;
                end
                PROJECT: if(p_done_valid&&p_done_ready) begin
                    service_done_owner<=expected_owner;
                    service_done_status<=p_done_owner==expected_owner ? p_done_status : CONSUMER_FAULT;
                    service_done_read_bytes<=p_done_read_bytes;
                    service_done_write_bytes<=p_done_write_bytes;
                    state<=p_done_status==0&&p_done_owner==expected_owner ? CONSUME : REPORT;
                end
                CONSUME: begin
                    if(s_rsp_valid&&s_rsp_ready&&!bad_response)
                        service_done_read_bytes<=service_done_read_bytes+32'd16;
                    if(lease_fault || (result_valid&&result_error)) begin
                        service_done_status<=CONSUMER_FAULT;
                        state<=REPORT;
                    end else if(release_valid&&release_ready) state<=last_release ? FINAL_TOKEN : REPORT;
                end
                FINAL_TOKEN: if(result_valid&&result_ready) begin
                    if(result_error) service_done_status<=CONSUMER_FAULT;
                    state<=REPORT;
                end
                REPORT: if(service_done_valid&&service_done_ready)
                    state<=service_done_status==0 ? IDLE : FAILED;
                FAILED: state<=FAILED;
                default: state<=FAILED;
            endcase
        end
    end
endmodule
