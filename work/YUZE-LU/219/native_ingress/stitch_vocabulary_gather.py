"""Join the live vocabulary terminal to the native MC/U0 Gather regression."""
import argparse
from pathlib import Path


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'expected exactly one source anchor: {old}')
    return text.replace(old, new)


def gather(text):
    r = replace
    text = r(text, 'module tb_u_gather_frame;\n  logic clk=0,reset=1;\n  always #5 clk=~clk;', '''module live_token_gather (
  input logic clk,reset,retired_valid,retired_error,stall_mode,
  input logic [31:0] retired_token,retired_tag,expected_token,
  output wire retired_ready,
  output logic completed=0,
  output wire dma_req_valid,dma_req_channel,dma_rsp_ready,
  input wire dma_req_ready,dma_rsp_valid,
  output wire [63:0] dma_req_address,
  output wire [31:0] dma_req_tag,
  output wire [4:0] dma_req_record_beats,
  input wire [31:0] dma_rsp_tag,
  input wire [511:0] dma_rsp_data
);''')
    text = r(text,'  localparam integer LOGIT_WORDS=37984;\n','')
    text = r(text,'  reg [127:0] logits[0:LOGIT_WORDS-1];\n','')
    start = text.index('  logic [31:0] logit_word')
    stop = text.index('  wire index_done', start)
    text = text[:start] + text[stop:]
    text = r(text,'  string logits_path, mode;\n','  // Token validity comes from the upstream terminal.\n')
    start = text.index('  s32_token_argmax')
    stop = text.index('  native_retired_token_index', start)
    text = text[:start] + text[stop:]
    text = r(text, '  localparam logic [31:0] TOKEN_GENERATION=32\'d127;',
             '  localparam logic [31:0] TOKEN_GENERATION=32\'d126;')
    text = r(text,'.request_generation(retired_tag)',".request_generation(TOKEN_GENERATION + 1)")
    text = r(text,'index_tag==TOKEN_GENERATION','index_tag==TOKEN_GENERATION + 1')
    text = r(text,'retired_token==81917 && logit_word==LOGIT_WORDS','retired_token==expected_token')
    start = text.index('  wire dma_req_valid,dma_req_ready')
    stop = text.index('  wire [127:0] tx_data;',start)
    text = text[:start] + text[stop:]
    text = r(text, '  // The trace drives the vocabulary reduction. The MC alone executes the',
             '  // The live vocabulary terminal supplies the token. The MC executes the')
    start = text.index('  integer backend_count')
    stop = text.index('    if (retired_valid && retired_ready)',start)
    text = text[:start] + '''  integer beats_returned=0;
  always @(posedge clk) if (!reset) begin
    cycle<=cycle+1;
    assert(!poison && !link_fault);
    if (dma_rsp_valid && dma_rsp_ready) beats_returned<=beats_returned+1;
''' + text[stop:]
    text = r(text,'commits==512 && issued==128 && backend_count==issued &&\n             response_count==issued && index_reads==1',
             'commits==512 && issued==128 && beats_returned==issued && index_reads==1')
    text = r(text,'#1000000;', '#400000000;')
    text = r(text,',issued,dma_fault);', ',issued,link_fault);')
    start = text.index('    assert($value$plusargs("image=')
    stop = text.index('    repeat(5) @(negedge clk);',start)
    text = text[:start] + '''    assert($value$plusargs("GATHER_IMAGE=%s",image_path) &&
           $value$plusargs("GATHER_ROW=%s",row_path) &&
           $value$plusargs("GATHER_MOTHER=%s",mother_path));
    pm_bytes=640;
    $readmemh(mother_path,mother_image);
    assert(mother_image[4][0+:32]==TOPOLOGY);
    $readmemh(image_path,image);
    $readmemh(row_path,expected_row);
    wait(!reset);
''' + text[stop:]
    text = r(text,'    reset=0;\n','')
    start = text.index('    token_cmd=1;')
    stop = text.index('    mc_start_request=1;',start)
    text = text[:start] + text[stop:]
    start = text.index('    $display("PASS mother-to-U0')
    text = text[:start] + '''    $display("PASS live retired Gather token=%0d call=%0d index_commit=%0d row_commit=%0d terminal=%0d DDR_reads=%0d writes=%0d",
             retired_token,call_at,index_commit_at,last_commit,terminal_at,issued,commits);
    completed=1;
  end
endmodule
'''
    return text


def vocabulary(text):
    r = replace
    text = r(text,'test_ffn_native_p_node #(.SHARED_MID_SOURCE(WITH_PROMPT_INPUT)',
             "p_native_coplacement_node #(.SHARED_MID_SOURCE(1'b1)")
    text = r(text,'.clk,.reset,.allow_req(mode==0||cycles%7>=2),.allow_rsp(mode==0||cycles%11>=4),','.clk,.reset,')
    text = r(text,' logic [63:0] embedding_base,embedding_bytes,emb_address,emb_tag;',
             ''' localparam logic [63:0] EMBEDDING_BASE=64'd3298373632;
 logic [63:0] embedding_base,embedding_bytes,emb_address;
 logic [31:0] emb_tag;
 logic [4:0] emb_beats;
 logic emb_channel;''')
    start = text.index('  logic emb_s_valid')
    stop = text.index('  int unsigned producer_tiles',start)
    text = text[:start] + '  logic accepted_token;\n' + text[stop:]
    text = r(text,'   embedding_trace=$fopen({path,"/embedding.hex"},"w");\n   assert(logits_trace!=0&&embedding_trace!=0);',
             '   assert(logits_trace!=0);')
    start = text.index('  logic index_ready,index_valid')
    stop = text.index('  always @(posedge clk) begin\n   if(reset) begin\n    checked_words',start)
    text = text[:start] + '''  logic [31:0] held_logits;
  assign product_logits_ready=mode==0||cycles%7==0;
  live_token_gather gather (
   .clk,.reset,.retired_valid(arg_token_valid),.retired_error(arg_error),
   .stall_mode(mode!=0),.retired_token(arg_token),.retired_tag(product_step),.expected_token,
   .retired_ready(arg_token_ready),.completed(embedding_done),
   .dma_req_valid(emb_valid),.dma_req_channel(emb_channel),.dma_rsp_ready(emb_take),
   .dma_req_ready(emb_ready),.dma_rsp_valid(rsp_valid[3]),.dma_req_address(emb_address),
   .dma_req_tag(emb_tag),.dma_req_record_beats(emb_beats),.dma_rsp_tag(rsp_tag[96+:32]),
   .dma_rsp_data(rsp_data[1536+:512]));
''' + text[stop:]
    text = r(text,'    embedding_writes<=0;', '    held_logits<=0;')
    start = text.index('    if(emb_valid&&emb_ready)')
    stop = text.index(' end else begin: vocab',start)
    text = text[:start] + '''    if(product_logits_valid&&!product_logits_ready) held_logits<=held_logits+1;
    if(embedding_done && mode!=0) assert(held_logits>0);
   end
  end
''' + text[stop:]
    text = r(text,'  task automatic check_embedding(); endtask\n','')
    text = r(text,'.c_req_channel({2\'d0,mr_channel,5\'d0,(VOCAB_HEAD?emb_address[11]:bias_rd_address[11]),dr_channel}),.c_req_record_beats({10\'d0,mr_length,25\'d0,5\'d2,dr_length}),',
             ".c_req_channel({2'd0,mr_channel,5'd0,(VOCAB_HEAD?emb_channel:bias_rd_address[11]),dr_channel}),.c_req_record_beats({10'd0,mr_length,25'd0,(VOCAB_HEAD?emb_beats:5'd2),dr_length}),")
    text = r(text,'(VOCAB_HEAD?emb_tag[31:0]:bias_rd_tag)','(VOCAB_HEAD?emb_tag:bias_rd_tag)')
    text = r(text,'   ddr_weight_image_add(embedding_base,embedding_path,embedding_bytes);',
             '   assert(embedding_base==EMBEDDING_BASE);\n   ddr_weight_image_add(embedding_base,embedding_path,embedding_bytes);')
    start = text.index('   assert(!embedding_error&&embedding_done_tag==1&&embedding_writes==512')
    stop = text.index('\n  end',start)
    text = text[:start] + '   assert(checked_words==TILES*32&&retired_tiles==TILES);' + text[stop:]
    text = r(text,'  $fclose(logits_trace);$fclose(embedding_trace);','  $fclose(logits_trace);')
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('vocabulary_fixture','gather_fixture','out'):
        parser.add_argument(name,type=Path)
    args = parser.parse_args()
    (args.out/'test_native_projection_live.sv').write_text(vocabulary(args.vocabulary_fixture.read_text()))
    (args.out/'live_token_gather.sv').write_text(gather(args.gather_fixture.read_text()))
