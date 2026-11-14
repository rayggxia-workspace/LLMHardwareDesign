"""Join the native request sequencer to the existing physical Gather fixture."""
import argparse
from pathlib import Path


def replace_one(source, old, new):
    if source.count(old) != 1:
        raise ValueError('unexpected Gather fixture version: ' + old[:90])
    return source.replace(old, new)


def stitch(source):
    start = source.index('  native_retired_token_index index_writer(')
    end = source.index('  localparam logic [31:0] TOPOLOGY=', start)
    source = source[:start] + """  // Component harness. The predecessor page terminal and KV receipt are
  // peers; the vocabulary reducer, Gather CALL, SRAM and DMA are real RTL.
  logic job_valid=0, job_ready, plan_valid;
  logic [31:0] plan_step, page_step, page_generation, page_input_token;
  logic page_valid, page_ready, page_done_valid, page_done_ready, page_done_error;
  logic [31:0] page_done_generation;
  logic kv_valid=0, kv_ready, retire_valid;
  logic [31:0] fresh_token, fresh_step, fresh_job;
  logic earlier_page_pending=0;
  logic executor_done_ready;
  logic gather_launched=0;
  integer token_source_at=-1, kv_at=-1, request_retire_at=-1;
  native_request_sequence sequencer(
    .clk,.reset,.job_valid,.job_ready,.job_tag(32'd7),
    .job_prompt_length(32'd512),.job_output_length(32'd2),.job_context_capacity(32'd639),
    .plan_valid,.plan_ready(1'b1),.plan_step,.plan_page_count(32'd1),
    .page_valid,.page_ready,.page_job_tag(),.page_step,.page_index(),
    .page_generation,.page_input_token,.page_done_valid,.page_done_ready,.page_done_generation,.page_done_error,
    .kv_valid,.kv_ready,.kv_job_tag(32'd7),.kv_step(32'd0),.kv_length(32'd512),.kv_error(1'b0),
    .token_valid(retired_valid),.token_ready(retired_ready),.token_job_tag(32'd7),.token_step(32'd0),
    .token_value(retired_token),.token_error(retired_error),
    .retire_valid,.retire_ready(1'b1),.retire_token(fresh_token),.retire_step(fresh_step),.retire_job_tag(fresh_job),
    .job_done_valid(),.job_done_ready(1'b0),.job_done_outputs(),.job_done_error());
  native_request_index_gate gate(
    .clk,.reset,.page_valid,.page_ready,.page_generation,.page_input_token,
    .page_uses_index(page_step==1),.page_index_word(10'd512),
    .launch_valid(page_launch),.launch_ready(page_step==0 || mc_start_ready),
    .executor_done_valid(earlier_page_pending || mc_result),.executor_done_ready,
    .executor_done_generation(earlier_page_pending ? 32'd1 : 32'd2),
    .executor_done_error(mc_result && mc_result_status!=0),
    .page_done_valid,.page_done_ready,.page_done_generation,.page_done_error,
    .reservation_valid(link_reserved),.reservation_word(link_addr),
    .s_valid(incoming_valid),.s_ready(incoming_ready),.s_word(index_word),.s_data(index_data),.s_tag(index_tag),
    .ack_valid(incoming_ack && ack_enable),.ack_ready(index_ack_ready),
    .ack_tag(index_tag),.ack_error(1'b0),.index_fault(index_error));
  wire page_launch;
  always @(posedge clk) if (!reset) begin
    assert(!index_error);
    if(page_valid && page_ready && page_step==0) earlier_page_pending<=1;
    if(earlier_page_pending && executor_done_ready) earlier_page_pending<=0;
    if(retired_valid && retired_ready) token_source_at<=cycle;
    if(kv_valid && kv_ready) kv_at<=cycle;
    if(retire_valid) begin
      assert(token_source_at>=0 && kv_at>token_source_at && cycle>kv_at &&
             fresh_token==81917 && fresh_step==0 && fresh_job==7);
      request_retire_at<=cycle;
    end
    if(mc_start_valid && mc_start_ready) begin
      assert(request_retire_at>=0 && page_generation==2 && page_input_token==81917);
      gather_launched<=1;
    end
  end
""" + source[end:]
    start = source.index('  // The trace drives the vocabulary reduction.')
    end = source.index('  assign task_valid=', start)
    source = source[:start] + '  wire mc_start_valid=page_launch && page_step==1;\n' + source[end:]
    source = replace_one(source, '.result_ready_i(1\'b1)', '.result_ready_i(executor_done_ready)')
    source = replace_one(source, 'assert(retired_valid && !retired_error && retired_tag==TOKEN_GENERATION);',
                         'assert(gather_launched && request_retire_at>=0);')
    source = replace_one(source, 'index_tag==TOKEN_GENERATION);', "index_tag==32'd2 && request_retire_at>=0);")
    source = replace_one(source, 'assert(mother_image[4][0+:32]==TOPOLOGY);',
                         "assert(mother_image[4][0+:32]==32'd25001);")
    source = replace_one(source, """    // Offer the page before the retirement is available. Its start can
    // handshake only after the previous token's actual reduction completes.
    mc_start_request=1;
    do @(posedge clk); while(!(mc_start_valid && mc_start_ready));
    @(negedge clk); mc_start_request=0;""", """    assert(job_ready);
    job_valid=1;
    @(negedge clk); job_valid=0;
    while(token_source_at<0) @(negedge clk);
    repeat(13) begin
      @(negedge clk); assert(!retire_valid && !gather_launched);
    end
    assert(kv_ready);
    kv_valid=1;
    @(negedge clk); kv_valid=0;""")
    source = replace_one(source, '    $finish;', '''    assert(request_retire_at<call_at && call_at<index_commit_at && index_commit_at<last_commit);
    $display("PASS sequencer-to-Gather vocabulary=%0d kv_receipt=%0d retire=%0d call=%0d index_ack=%0d row_ack=%0d",
             token_source_at, kv_at, request_retire_at, call_at, index_commit_at, last_commit);
    $finish;''')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(stitch(args.input.read_text()))


if __name__ == '__main__':
    main()
