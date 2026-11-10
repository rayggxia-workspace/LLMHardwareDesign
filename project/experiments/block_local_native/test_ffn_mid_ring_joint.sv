`timescale 1ns/1ps
// Whole 11008-column ring lifetime, actual three P.S / twelve SRAM banks,
// G leaf and quantizer. The host supplies projection scratch words as a
// fixture; this test does not claim execution of the upstream M or Down.
module test_ffn_mid_ring_joint;
 localparam integer COLS=11008,TILES=COLS/128;
 localparam [63:0] JOB=64'h250_ff01;
 reg clk;initial clk=0;always #5 clk=!clk;
 reg reset=1,start_valid=0,allow_stripe=0,mid_ready=0,done_ready=0;
 wire stripe_ready,stripe_commit_valid,stripe_commit_error;
 wire [63:0] stripe_commit_owner;
 wire [15:0] stripe_commit_first;
 wire start_ready,stripe_valid,stripe_commit_ready,mid_valid,done_valid,done_error;
 wire [63:0] stripe_owner,mid_owner;
 wire [15:0] stripe_first,mid_first;
 wire [7:0] stripe_width;
 wire [1:0] mid_destination;
 wire [9:0] mid_destination_base;
 wire [5:0] mid_shift;
 wire [31:0] rejected_commits;
 wire [2:0] fs_valid,fs_write,fs_ready,fs_rsp_valid,fs_rsp_ready;
 wire [29:0] fs_address;
 wire [383:0] fs_data,fs_rsp_data;
 wire [95:0] fs_tag,fs_rsp_tag;
 ffn_gate_up_mid dut(.clk,.reset,.start_valid,.start_ready,.start_owner(JOB),
  .stripe_valid,.stripe_ready,.stripe_owner,.stripe_first,.stripe_width,
  .stripe_commit_valid,.stripe_commit_ready,.stripe_commit_owner,.stripe_commit_first,.stripe_commit_error,
  .s_valid(fs_valid),.s_write(fs_write),.s_ready(fs_ready),.s_address(fs_address),.s_data(fs_data),.s_tag(fs_tag),
  .s_rsp_valid(fs_rsp_valid),.s_rsp_ready(fs_rsp_ready),.s_rsp_data(fs_rsp_data),.s_rsp_tag(fs_rsp_tag),
  .mid_valid,.mid_ready,.mid_owner,.mid_first,.mid_destination,.mid_destination_base,.mid_shift,
  .done_valid,.done_ready,.done_error,.rejected_commits);

 wire copy_stage,copy_start,copy_take;
 wire [1:0] source_p;
 wire [15:0] copy_generation;
 wire [31:0] copy_first;
 wire [9:0] copy_src,copy_ring;
 wire [4:0] copy_words;
 wire copy_ready,copy_done,copy_error,copy_drained;
 wire [10:0] copy_prefix;
 wire [127:0] copy_key,copy_word;
 wire [31:0] copy_faults,copy_committed;
 wire cs_valid,cs_ready,cs_rsp_valid,cs_rsp_ready,cd_valid,cd_ready,cd_rsp_valid,cd_rsp_ready;
 wire [9:0] cs_address,cd_address;
 wire [31:0] cs_tag,cs_rsp_tag,cd_tag,cd_rsp_tag;
 wire [127:0] cs_rsp_data;
 wire [127:0] current_key;
 wire [15:0] copy_mask=16'hffff>>(5'd16-copy_words);
 wire join_ready;
 assign stripe_ready=join_ready&&allow_stripe;
 wire [2:0] project_valid,project_done_ready;
 reg [2:0] project_ready=0,project_done_valid=0,project_done_error=0;
 wire [63:0] project_owner;
 wire [47:0] project_first;
 wire [11:0] project_groups;
 reg [191:0] project_done_owner=0;
 reg [47:0] project_done_first=0;
 reg [14:0] project_done_gate_words=0,project_done_up_words=0;
 wire [31:0] rejected_terminals;
 ffn_stripe_commit gather(.clk,.reset,.stripe_valid(stripe_valid&&allow_stripe),.stripe_ready(join_ready),
  .stripe_owner,.stripe_first,.stripe_width,.project_valid,.project_ready,.project_owner,.project_first,.project_groups,
  .project_done_valid,.project_done_ready,.project_done_owner,.project_done_first,.project_done_gate_words,
  .project_done_up_words,.project_done_error,.copy_stage,.copy_valid(copy_start),.copy_ready,
  .copy_source(source_p),.copy_key(current_key),.copy_generation,.copy_first,.copy_scratch(copy_src),.copy_ring,.copy_words,
  .copy_done_valid(copy_done),.copy_done_ready(copy_take),.copy_done_key(copy_key),.copy_done_prefix(copy_prefix),
  .copy_done_error(copy_error),.commit_valid(stripe_commit_valid),.commit_ready(stripe_commit_ready),
  .commit_owner(stripe_commit_owner),.commit_first(stripe_commit_first),.commit_error(stripe_commit_error),.rejected_terminals);
 s32_stripe_copy scatter(.clk,.reset,.halt(1'b0),.start_valid(copy_start),.start_ready(copy_ready),
  .start_key(current_key),.start_generation(copy_generation),.start_first_col(copy_first),
  .start_source_base(copy_src),.start_ring_base(copy_ring),.start_words(copy_words),
  .start_written_mask(copy_mask),.start_producer_error(1'b0),.destination_window_released(1'b1),
  .source_valid(cs_valid),.source_ready(cs_ready),.source_address(cs_address),.source_tag(cs_tag),
  .source_response_valid(cs_rsp_valid),.source_response_ready(cs_rsp_ready),.source_response_tag(cs_rsp_tag),
  .source_response_data(cs_rsp_data),.source_response_error(1'b0),.destination_valid(cd_valid),.destination_ready(cd_ready),
  .destination_address(cd_address),.destination_tag(cd_tag),.destination_data(copy_word),
  .destination_ack_valid(cd_rsp_valid),.destination_ack_ready(cd_rsp_ready),.destination_ack_tag(cd_rsp_tag),
  .destination_ack_error(1'b0),.copy_key,.committed_prefix(copy_prefix),.done_valid(copy_done),.done_ready(copy_take),
  .done_error(copy_error),.quiescent(copy_drained),.fault_cycles(copy_faults),.committed_words(copy_committed));

 reg host_valid=0,host_write=0,host_take=0;
 reg [1:0] host_p=0;
 reg [9:0] host_address=0;
 reg [127:0] host_data=0;
 wire [2:0] cr[3],rv[3];
 wire [95:0] tags[3];
 wire [127:0] data[3];
 wire [1:0] occupied[3];
 wire [2:0] allow_response;
 integer mode,cycle,fg_reads,fg_writes,fg_responses,scatter_reads,scatter_writes,scatter_acks;
 for(genvar p=0;p<3;p=p+1)begin: memories
   wire choose_copy=copy_stage&&source_p==2'(p);
   wire scatter_dest=copy_stage&&p==0;
   wire side_req=choose_copy ? cs_valid:fs_valid[p];
   wire side_rsp=choose_copy ? cs_rsp_ready:fs_rsp_ready[p];
   wire accept_req=mode==0||(cycle+2*p)%7>=2;
   assign allow_response[p]=mode==0||(cycle+3*p)%11>=4;
   assign fs_ready[p]=cr[p][2]&&!copy_stage&&accept_req;
   assign fs_rsp_valid[p]=rv[p][2]&&!copy_stage&&allow_response[p];
   assign fs_rsp_data[p*128+:128]=data[p];
   assign fs_rsp_tag[p*32+:32]=tags[p][95:64];
   wire n_valid,n_write,n_ready,n_rsp_valid,n_rsp_ready;
   wire [9:0] n_address;
   wire [127:0] n_data,n_rsp_data;
   native_s128_mux3 mux(.clk,.reset,
    .c_valid({side_req&&accept_req,scatter_dest&&cd_valid&&accept_req,host_valid&&host_p==2'(p)}),
    .c_write({!choose_copy&&fs_write[p],1'b1,host_write}),
    .c_address({choose_copy ? cs_address:fs_address[p*10+:10],cd_address,host_address}),
    .c_data({choose_copy ? 128'd0:fs_data[p*128+:128],copy_word,host_data}),
    .c_tag({choose_copy ? cs_tag:fs_tag[p*32+:32],cd_tag,32'h600d}),
    .c_ready(cr[p]),.c_response_valid(rv[p]),
    .c_response_ready({side_rsp&&allow_response[p],scatter_dest&&cd_rsp_ready&&allow_response[p],host_take}),
    .c_response_data(data[p]),.c_response_tag(tags[p]),.owners_occupied(occupied[p]),
    .req_valid(n_valid),.req_write(n_write),.req_address(n_address),.req_data(n_data),.req_ready(n_ready),
    .rsp_valid(n_rsp_valid),.rsp_ready(n_rsp_ready),.rsp_data(n_rsp_data));
   local_s_base storage(.clk,.reset,.req_valid(n_valid),.req_write(n_write),.req_addr(n_address),.req_data(n_data),
    .req_ready(n_ready),.rsp_valid(n_rsp_valid),.rsp_ready(n_rsp_ready),.rsp_data(n_rsp_data));
 end
 assign cs_ready=copy_stage&&cr[source_p][2]&&(mode==0||(cycle+2*int'(source_p))%7>=2);
 assign cs_rsp_valid=copy_stage&&rv[source_p][2]&&allow_response[source_p];
 assign cs_rsp_tag=tags[source_p][95:64];assign cs_rsp_data=data[source_p];
 assign cd_ready=cr[0][1]&&(mode==0||cycle%7>=2);
 assign cd_rsp_valid=rv[0][1]&&allow_response[0];assign cd_rsp_tag=tags[0][63:32];
 wire [67:0] _unused_dest_lanes={cr[1][1],cr[2][1],rv[1][1],rv[2][1],tags[1][63:32],tags[2][63:32]};
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(cycle>250000)$fatal(1,"full FFN ring watchdog");
  if(!reset)begin
   fg_reads<=fg_reads+$countones(fs_valid&fs_ready&~fs_write);
   fg_writes<=fg_writes+$countones(fs_valid&fs_ready&fs_write);
   fg_responses<=fg_responses+$countones(fs_rsp_valid&fs_rsp_ready);
   if(cs_valid&&cs_ready)scatter_reads<=scatter_reads+1;
   if(cd_valid&&cd_ready)scatter_writes<=scatter_writes+1;
   if(cd_rsp_valid&&cd_rsp_ready)scatter_acks<=scatter_acks+1;
   if(copy_stage&&fs_valid!=0)$fatal(1,"scatter and G/Mid contend for the same S owner");
   for(integer p=0;p<3;p=p+1)
    if(occupied[p]>2)$fatal(1,"unexpected S owner capacity");
  end
 end
 task automatic host_access(input integer p,input bit wr,input integer addr,input reg[127:0] word_in,
                            output reg[127:0] word_out);
  if(p<0||p>2||addr<0||addr>=1024)$fatal(1,"host window overflow");
  @(negedge clk);host_p=2'(p);host_write=wr;host_address=10'(addr);host_data=word_in;host_valid=1;
  do @(posedge clk);while(!cr[host_p][0]);@(negedge clk);host_valid=0;
  while(!rv[host_p][0])@(negedge clk);
  if(tags[host_p][31:0]!=32'h600d)$fatal(1,"host S response owner");
  word_out=data[host_p];host_take=1;@(negedge clk);host_take=0;
 endtask
 reg [127:0] vectors[COLS/2+TILES*17],readback;
 string vector_path;
 integer produced,retired,expected_width,local_groups,reference_index,begin_cycle,scope_begin;
 task automatic project_done(input integer p,first,words,input bit fail);
  if(p<0||p>2||first<0||first>=COLS||words<0||words>16)$fatal(1,"fixture terminal invalid");
  project_done_owner[p*64+:64]=JOB;project_done_first[p*16+:16]=16'(first);
  project_done_gate_words[p*5+:5]=5'(words);project_done_up_words[p*5+:5]=5'(words);
  project_done_error[p]=fail;project_done_valid[p]=1;
  do @(posedge clk);while(!project_done_ready[p]);@(negedge clk);project_done_valid[p]=0;
 endtask
 initial begin
  cycle=0;fg_reads=0;fg_writes=0;fg_responses=0;scatter_reads=0;scatter_writes=0;scatter_acks=0;
  produced=0;retired=0;
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("vectors=%s",vector_path))$fatal(1,"ring oracle required");
  $readmemh(vector_path,vectors);
  repeat(4)@(negedge clk);reset=0;start_valid=1;
  do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;scope_begin=cycle;
  while(!done_valid)begin
   if(stripe_valid)begin
    begin_cycle=cycle;expected_width=COLS-produced>=192 ? 192:COLS-produced;
    repeat(3)begin
     @(negedge clk);
     if(!stripe_valid||stripe_owner!=JOB||int'(stripe_first)!=produced||int'(stripe_width)!=expected_width)
       $fatal(1,"stripe offer not held");
    end
    allow_stripe=1;do @(posedge clk);while(!stripe_ready);@(negedge clk);allow_stripe=0;
    if(project_valid!=3'b111||project_owner!=JOB)$fatal(1,"did not fork stripe to three P owners");
    project_ready=3'b111;@(negedge clk);project_ready=0;
    if(produced==0)begin
     project_done(0,8,16,0);
     if(rejected_terminals!=1||copy_stage)$fatal(1,"stale P terminal released ring");
    end
    for(integer p=0;p<3;p=p+1)begin
     local_groups=(expected_width/8+2-p)/3;
     if(int'(project_groups[p*4+:4])!=local_groups||int'(project_first[p*16+:16])!=produced+8*p)
       $fatal(1,"P typed stripe recipe differs");
     for(integer way=0;way<2;way=way+1)begin
      for(integer w=0;w<local_groups*2;w=w+1)begin
       reference_index=way*(COLS/4)+produced/4+2*p+6*(w/2)+w%2;
       host_access(p,1,896+16*way+w,vectors[reference_index],readback);
      end
     end
     project_done(p,produced+8*p,local_groups*2,0);
     if(p<2&&copy_stage)$fatal(1,"scatter issued before every projection SACK");
    end
    while(!stripe_commit_valid)@(negedge clk);
    if(stripe_commit_error||stripe_commit_owner!=JOB||int'(stripe_commit_first)!=produced||!copy_drained)
      $fatal(1,"stripe commit lacks complete scatter");
    do @(posedge clk);while(!stripe_commit_ready);@(negedge clk);
    $display("FFN_STRIPE mode=%0d first=%0d width=%0d cycles=%0d",mode,produced,expected_width,cycle-begin_cycle);
    produced=produced+expected_width;
   end else if(mid_valid)begin
    begin_cycle=cycle;
    reference_index=COLS/2+retired*17;
    if(mid_owner!=JOB||int'(mid_first)!=128*retired||int'(mid_destination)!=retired%3||
       int'(mid_destination_base)!=256+16*(retired/3)||{122'd0,mid_shift}!==vectors[reference_index])
      $fatal(1,"Mid ownership, order or scaling");
    for(integer w=0;w<16;w=w+1)begin
     host_access(retired%3,0,256+16*(retired/3)+w,0,readback);
     if(!mid_valid||mid_owner!=JOB||int'(mid_first)!=128*retired||readback!==vectors[reference_index+1+w])
      $fatal(1,"released Mid before true ACK or integer mismatch tile=%0d word=%0d",retired,w);
    end
    mid_ready=1;@(negedge clk);mid_ready=0;
    $display("FFN_MID mode=%0d tile=%0d owner=%0d shift=%0d observed_hold_cycles=%0d",
      mode,retired,retired%3,mid_shift,cycle-begin_cycle);
    retired=retired+1;
   end else @(negedge clk);
  end
  if(done_error||produced!=COLS||retired!=TILES||copy_faults!=0||int'(copy_committed)!=COLS/2||
     scatter_reads!=COLS/2||scatter_writes!=COLS/2||scatter_acks!=COLS/2||
     fg_reads!=TILES*96||fg_writes!=TILES*48||fg_responses!=TILES*144||rejected_commits!=0||rejected_terminals!=1)
    $fatal(1,"full FFN Mid conservation");
  done_ready=1;@(negedge clk);
  if(!start_ready)$fatal(1,"FFN controller did not drain");
  // A failing real provider must drain its siblings, then return error
  // without presenting even one scratch-to-ring request.
  done_ready=0;start_valid=1;do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;
  while(!stripe_valid)@(negedge clk);
  allow_stripe=1;do @(posedge clk);while(!stripe_ready);@(negedge clk);allow_stripe=0;
  project_ready=3'b111;@(negedge clk);project_ready=0;
  project_done(0,0,14,0);project_done(1,8,16,0);project_done(2,16,16,0);
  while(!done_valid)@(negedge clk);
  if(!done_error||scatter_acks!=COLS/2||fg_writes!=TILES*48)
    $fatal(1,"partial projection terminal exposed new data");
  $display("PASS ffn_mid_ring_joint columns=%0d tiles=%0d actual_banks=12 extra_SRAM=0 copy_ack=%0d GQ_reads=%0d GQ_writes=%0d cycles=%0d mode=%0d",
   COLS,TILES,scatter_acks,fg_reads,fg_writes,cycle-scope_begin,mode);
  $finish;
 end
endmodule
