module tb_projection_source_pipeline #(parameter MODE=0);
 reg clk=0;always #5 clk=~clk;
 reg reset=1,scope_start=0,scope_end=0,scope_cancel=0,need_valid=0,proof_valid=0;
 reg [15:0] need_k=0;wire proof_ready,failed,drained,window_valid;
 wire [127:0] window_key;wire [15:0] window_generation,window_k;
 wire [31:0] window_session,window_ticket;wire [5:0] window_shift;
 wire rd_valid,rd_rsp_ready;reg rd_ready=1,rd_rsp_valid=0,rd_rsp_error=0;
 wire [63:0] rd_address,rd_tag;reg [63:0] rd_rsp_tag;reg [511:0] rd_rsp_data;
 wire load_valid,load_rsp_ready;reg load_ready=1,load_rsp_valid=0,load_rsp_error=0;
 wire [9:0] load_address;wire [127:0] load_data;wire [31:0] load_tag;reg [31:0] load_rsp_tag;
 wire quant_valid,quant_write,quant_rsp_ready;reg quant_ready=1,quant_rsp_valid=0;
 wire [9:0] quant_address;wire [127:0] quant_data;wire [31:0] quant_tag;
 reg [31:0] quant_rsp_tag;reg [127:0] quant_rsp_data;
 projection_local_source dut(.clk,.reset,.scope_start,.scope_end,.scope_cancel,
 .scope_key(128'd1),.scope_source_address(64'h10000),.scope_full_k(16'd256),
 .scope_source_word(10'd832),.scope_a_word(10'd880),
 .need_valid,.need_k,.need_key(128'd1),.window_valid,.window_key,.window_generation,
 .window_k,.window_session,.window_ticket,.window_shift,.proof_valid,.proof_ready,
 .proof_error(1'b0),.proof_source_drained(1'b1),.proof_shift(window_shift),.failed,.drained,
 .rd_valid,.rd_ready,.rd_address,.rd_tag,.rd_rsp_valid,.rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data,.rd_rsp_error,
 .load_valid,.load_ready,.load_address,.load_data,.load_tag,.load_rsp_valid,.load_rsp_ready,.load_rsp_tag,
 .load_rsp_error,.quant_valid,.quant_ready,.quant_write,.quant_address,.quant_data,.quant_tag,
 .quant_rsp_valid,.quant_rsp_ready,.quant_rsp_tag,.quant_rsp_data,.quant_rsp_error(1'b0));
 reg [127:0] ram[0:1023];
 reg [63:0] tags[0:15];bit [15:0] pending=0;
 integer lhead=0,ltail=0,qhead=0,qtail=0,cycle=0,issued=0,awrites=0,qreads=0,qpeak=0,packpeak=0,observed_words=0,first_published=-1,stage=0;
 reg [31:0] ltags[0:255],qtags[0:511];integer ld[0:255],qd[0:511];
 reg [127:0] qdata[0:511];integer chosen=-1,selected=-1;bit injected=0,bad_offer=0,bad_load_offer=0,load_injected=0;
 always @(posedge clk)if(!reset)begin
  cycle=cycle+1;
  if(dut.loader_launch&&dut.loader_ready)observed_words=0;
  if(dut.quantizer.count>qpeak)qpeak=dut.quantizer.count;
  if($countones(dut.quantizer.allocated)>packpeak)packpeak=$countones(dut.quantizer.allocated);
  if(dut.quantizer.cmd_valid&&dut.quantizer.cmd_ready)
   if(!dut.observed_valid||observed_words!=32||!dut.quantizer.cmd_shift_known)$fatal(1,"observer before quant");
  if(dut.quantizer.count>2||$countones(dut.quantizer.allocated)>2)$fatal(1,"quantizer capacity");
  if(rd_valid&&rd_ready)begin
   integer index;index=(rd_address-64'h10000)/64;
   if(index>=16||pending[index])$fatal(1,"request address/reuse");
   tags[index]=rd_tag;pending[index]=1;issued=issued+1;
   if(index>=8&&first_published<0)$fatal(1,"prefetch before publication");
  end
  if(rd_rsp_valid&&rd_rsp_ready)begin
   if(!bad_offer)pending[selected]=0;else injected=1;
  end
  if(load_valid&&load_ready)begin
   observed_words=observed_words+1;
   if(load_address<832||load_address>=864)$fatal(1,"prefetch overwrites A window");
   ram[load_address]=load_data;ltags[ltail]=load_tag;ld[ltail]=cycle+3;ltail=ltail+1;
  end
  if(load_rsp_valid&&load_rsp_ready)begin
   if(bad_load_offer)load_injected=1;
   else lhead=lhead+1;
  end
  if(quant_valid&&quant_ready)begin
   if(!quant_write)qreads=qreads+1;
   if(quant_write)begin
    if(quant_address<880||quant_address>=896)$fatal(1,"A address");
    if(first_published>=0&&stage==0)$fatal(1,"A overwritten before proof/need");
    ram[quant_address]=quant_data;awrites=awrites+1;
   end
   qtags[qtail]=quant_tag;qdata[qtail]=quant_write?0:ram[quant_address];qd[qtail]=cycle+3;qtail=qtail+1;
  end
  if(quant_rsp_valid&&quant_rsp_ready)qhead=qhead+1;
  if(window_valid&&window_k==0&&first_published<0)first_published=cycle;
  if(MODE==0&&window_valid&&window_k==128)begin
   if(issued!=16||pending!=0||awrites!=32||qreads!=64||qpeak!=2||packpeak!=2||stage<2)$fatal(1,"normal end");
   $display("PASS real loader+quantizer cross-K publication/proof/ownership observer=32 reads=32 writes=16 response=2 pack=2");$finish;
  end
  if(MODE!=0&&cycle>20&&drained&&(failed||scope_cancel))begin
   if(pending!=0||lhead!=ltail||qhead!=qtail)$fatal(1,"premature drain");
   if(MODE!=1&&!failed)$fatal(1,"error not reported");
   $display("PASS cancel/error/identity drained mode=%0d",MODE);$finish;
  end
  if(cycle>6000)$fatal(1,"timeout mode=%0d stage=%0d pending=%h failed=%b",MODE,stage,pending,failed);
 end
 always @(negedge clk)if(!reset)begin
  rd_ready=cycle%5!=0;quant_ready=cycle%7!=0;load_ready=!quant_valid&&cycle%7!=0;
  load_rsp_valid=lhead<ltail&&cycle>=ld[lhead];load_rsp_tag=ltags[lhead];load_rsp_error=0;bad_load_offer=0;
  if(load_rsp_valid&&!load_injected)begin
   if(MODE==4)begin load_rsp_error=1;load_injected=1;end
   if(MODE==5)begin load_rsp_tag=ltags[lhead]^32'h400;bad_load_offer=1;end
  end
  quant_rsp_valid=qhead<qtail&&cycle>=qd[qhead];quant_rsp_tag=qtags[qhead];quant_rsp_data=qdata[qhead];
  rd_rsp_valid=0;rd_rsp_error=0;bad_offer=0;chosen=-1;
  if(cycle%6==0)for(integer i=0;i<16;i++)if(pending[i])chosen=i;
  if(chosen>=0)begin
   selected=chosen;rd_rsp_valid=1;rd_rsp_tag=tags[chosen];
   rd_rsp_data={16{32'(chosen<8?1:2)}};
   if(MODE==2&&!injected)begin rd_rsp_error=1;injected=1;end
   if(MODE==3&&!injected)begin rd_rsp_tag=tags[chosen]^(64'd1<<32);bad_offer=1;end
  end
  if(MODE==1&&issued>8)scope_cancel=1;
  if(MODE==0&&stage==0&&issued==16&&pending==0&&lhead==ltail)begin
   if(first_published<0||need_k!=0||awrites!=16)$fatal(1,"prefetch ownership");
   proof_valid=1;stage=1;
  end else if(stage==1)begin proof_valid=0;need_k=128;stage=2;end
 end
 initial begin
  repeat(3)@(negedge clk);reset=0;scope_start=1;
  @(negedge clk);scope_start=0;need_valid=1;
 end
endmodule
