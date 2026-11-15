`timescale 1ns/1ps
// Retire a native vocabulary page into the product controller and stream its
// full committed S32 logits. An unaccepted logit retains the original P lease.
module native_vocabulary_product_terminal (
    input logic clk, reset,
    input logic phase_valid,
    output logic phase_ready,
    input logic [31:0] phase_job_tag,phase_step,phase_generation,phase_epoch,
    input logic [31:0] phase_version,phase_length,

    input logic launch_valid,
    output logic launch_ready,
    input logic [127:0] launch_owner,
    input logic [31:0] launch_first,launch_version,
    input logic [7:0] launch_count,
    input logic [9:0] launch_s_base,
    input logic p_done_valid,
    output logic p_done_ready,
    input logic [127:0] p_done_owner,
    input logic [15:0] p_done_status,
    input logic [31:0] p_done_read_bytes,p_done_write_bytes,

    output logic service_done_valid,
    input logic service_done_ready,
    output logic [127:0] service_done_owner,
    output logic [15:0] service_done_status,
    output logic [31:0] service_done_read_bytes,service_done_write_bytes,
    output logic s_read_valid,
    input logic s_read_ready,
    output logic [9:0] s_read_address,
    output logic [31:0] s_read_tag,
    input logic s_rsp_valid,
    output logic s_rsp_ready,
    input logic [31:0] s_rsp_tag,
    input logic [127:0] s_rsp_data,
    input logic s_rsp_error,

    output logic logit_valid,
    input logic logit_ready,
    output logic [31:0] logit_first,
    output logic [3:0] logit_mask,
    output logic [127:0] logit_data,
    output logic logit_last,
    output logic token_valid,
    input logic token_ready,
    output logic [31:0] token_job_tag,token_step,token_value,
    output logic signed [31:0] token_logit,
    output logic token_error,
    output logic fault
);
    logic consumer_phase_ready,consumer_rsp_ready;
    logic result_valid,result_ready,result_error,active;
    logic [31:0] result_id,result_version,version,length,consumed;
    logic signed [31:0] result_logit;
    wire phase_legal=phase_job_tag!=0&&phase_generation!=0&&phase_epoch!=0&&phase_length!=0;
    wire response_error=s_rsp_error||s_rsp_tag!=s_read_tag||s_rsp_tag!=consumed||consumed>=length;
    wire [31:0] remaining=length-consumed;
    wire [2:0] lanes=remaining>=4 ? 3'd4 : remaining[2:0];
    wire release_response=response_error||logit_ready;

    assign phase_ready=!reset&&!active&&!token_valid&&consumer_phase_ready;
    assign s_rsp_ready=consumer_rsp_ready&&release_response;
    assign logit_valid=!reset&&active&&consumer_rsp_ready&&s_rsp_valid&&!response_error;
    assign logit_first=s_rsp_tag;
    assign logit_mask=4'hf>>(3'd4-lanes);
    assign logit_data=s_rsp_data;
    assign logit_last=remaining<=4;
    assign result_ready=active&&!token_valid;

    s128_vocabulary_tile_consumer consumer(
        .clk,.reset,.job_valid(phase_valid&&phase_ready&&phase_legal),.job_ready(consumer_phase_ready),
        .job_owner({phase_generation,phase_job_tag,phase_epoch}),.job_length(phase_length),.job_tag(phase_version),
        .launch_valid,.launch_ready,.launch_owner,.launch_first,.launch_version,.launch_count,.launch_s_base,
        .p_done_valid,.p_done_ready,.p_done_owner,.p_done_status,.p_done_read_bytes,.p_done_write_bytes,
        .service_done_valid,.service_done_ready,.service_done_owner,.service_done_status,
        .service_done_read_bytes,.service_done_write_bytes,.s_read_valid,.s_read_ready,.s_read_address,.s_read_tag,
        .s_rsp_valid(s_rsp_valid&&release_response),.s_rsp_ready(consumer_rsp_ready),.s_rsp_tag,.s_rsp_data,
        .s_rsp_error(response_error),.token_valid(result_valid),.token_ready(result_ready),.token_id(result_id),
        .token_tag(result_version),.token_logit(result_logit),.token_error(result_error),.fault);

    always_ff @(posedge clk) begin
        if(reset) begin
            active<=0; version<=0; length<=0; consumed<=0;
            token_valid<=0; token_job_tag<=0; token_step<=0; token_value<=0; token_logit<=0; token_error<=0;
        end else begin
            if(token_valid&&token_ready) token_valid<=0;
            if(phase_valid&&phase_ready) begin
                active<=phase_legal;
                version<=phase_version;
                length<=phase_length;
                consumed<=0;
                token_valid<=!phase_legal;
                token_job_tag<=phase_job_tag;
                token_step<=phase_step;
                token_value<=0;
                token_logit<=0;
                token_error<=!phase_legal;
            end
            if(logit_valid&&logit_ready) consumed<=consumed+32'(lanes);
            if(result_valid&&result_ready) begin
                active<=0;
                token_valid<=1;
                token_value<=result_id;
                token_logit<=result_logit;
                token_error<=result_error||result_version!=version||consumed!=length||result_id>=length;
            end else if(active&&service_done_valid&&service_done_status!=0) begin
                active<=0;
                token_valid<=1;
                token_error<=1;
            end
        end
    end
endmodule
