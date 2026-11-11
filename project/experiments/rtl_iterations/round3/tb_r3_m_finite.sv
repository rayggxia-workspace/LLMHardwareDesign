module tb_r3_m_finite #(parameter integer BUFFERS=1);
 reg clk=0,reset=1;always #5 clk=~clk;
 integer cycle=0,control_file,vector_file,case_id=-1,checks=0;
 reg enabled=0,service_mode=0,cv=0;
 reg [2:0] ctx=0;reg [31:0] tag=0;reg [15:0] ki=0,total=0;
 reg [4:0] k=0;reg [3:0] n=0;reg [5:0] shift=0;reg first=0,last=0;
 reg [13:0] aa=0,bb=0,oo=0;
 wire cr,dv,dr,de,dl,busy;wire [2:0] dc;wire [31:0] dt;wire [15:0] dn;
 wire [7:0] ds;wire [255:0] dd;
 wire rv,rr,rap,rvalid;wire [7:0] ra;wire [511:0] rdata;
 wire wv,wr,wap,wvalid;wire [9:0] wa;wire [127:0] wdata;
 r3_m_finite #(.BUFFERS(BUFFERS)) dut(.clk,.reset,.cmd_valid(cv),.cmd_ready(cr),.cmd_ctx(ctx),.cmd_tag(tag),
  .cmd_ki(ki),.cmd_total_k(total),.cmd_k(k),.cmd_n(n),.cmd_shift(shift),.cmd_first(first),.cmd_last(last),
  .cmd_a_addr(aa),.cmd_b_addr(bb),.cmd_out_addr(oo),.done_valid(dv),.done_ready(dr),.done_ctx(dc),.done_tag(dt),
  .done_next_k(dn),.done_last(dl),.done_error(de),.done_saturated(ds),.done_data(dd),.busy,
  .s_read_valid(rv),.s_read_ready(rr),.s_read_addr(ra),.s_read_rsp_valid(rvalid),.s_read_rsp_take(rap),.s_read_data(rdata),
  .s_write_valid(wv),.s_write_ready(wr),.s_write_addr(wa),.s_write_data(wdata),.s_write_ack_valid(wvalid),.s_write_ack_take(wap));
 reg hreq=0,hwrite=0,htake=0;reg [9:0] haddr=0;reg [127:0] hdata=0;
 wire nr,nv,br,bv;wire [127:0] nd;wire [511:0] bd;
 integer read_delay=0,ack_delay=0,done_hold=0,read_wait=0,ack_wait=0,done_wait=0;
 reg read_seen=0,ack_seen=0,done_seen=0;
 wire read_permit=read_delay==0||(read_seen&&read_wait==0);
 wire ack_permit=ack_delay==0||(ack_seen&&ack_wait==0);
 wire done_permit=done_hold==0||(done_seen&&done_wait==0);
 assign rr=service_mode&&br;assign rvalid=service_mode&&bv&&read_permit;assign rdata=bd;
 assign wr=service_mode&&nr;assign wvalid=service_mode&&nv&&ack_permit;
 assign dr=enabled&&done_permit;
 block_feed_s16k_sram #(.ECHO_WRITE_DATA(0)) bank(.clk,.reset,
  .req(service_mode?wv:hreq),.wr(service_mode?1'b1:hwrite),.addr(service_mode?wa:haddr),.din(service_mode?wdata:hdata),
  .ready(nr),.valid(nv),.take(service_mode?(wap&&ack_permit):htake),.dout(nd),
  .wide_req(service_mode&&rv),.wide_addr(ra),.wide_ready(br),.wide_valid(bv),
  .wide_take(service_mode&&rap&&read_permit),.wide_dout(bd));
 always @(posedge clk)begin
  if(reset||!service_mode)begin read_seen<=0;ack_seen<=0;done_seen<=0;read_wait<=0;ack_wait<=0;done_wait<=0;end
  else begin
   if(bv&&!read_seen)begin read_seen<=1;read_wait<=read_delay;end
   else if(read_seen&&read_wait>0)read_wait<=read_wait-1;
   if(rvalid&&rap)read_seen<=0;
   if(nv&&!ack_seen)begin ack_seen<=1;ack_wait<=ack_delay;end
   else if(ack_seen&&ack_wait>0)ack_wait<=ack_wait-1;
   if(wvalid&&wap)ack_seen<=0;
   if(dv&&!done_seen)begin done_seen<=1;done_wait<=done_hold;end
   else if(done_seen&&done_wait>0)done_wait<=done_wait-1;
   if(dv&&dr)done_seen<=0;
  end
 end
 typedef struct packed {
  reg [2:0] ctx;reg [31:0] tag;reg [15:0] ki,total;reg [4:0] k;reg [3:0] n;reg [5:0] shift;
  reg first,last;reg [13:0] a,b,out;reg error;reg [15:0] next_k;reg [7:0] saturation;
  reg [255:0] value;reg [767:0] raw;
 } command_t;
 command_t jobs[0:8191];integer ticket_seq[0:7],accept_cycle[0:8191],write_acks[0:8191];
 integer accepted=0,retired=0,committed=0,leafs=0,reads=0,read_acks=0,writes=0,acks=0,max_live=0,max_reads=0,max_buffers=0;
 integer ncmd=0,expected_reads=0,expected_writes=0,valid_commands=0,first_accept=-1,next_ready=-1,done_cycle=-1;
 reg producer_done=0,emit_events=0;
 reg prev_done_hold=0,prev_write_hold=0,prev_read_hold=0;
 reg [316:0] held_done;reg [137:0] held_write;reg [7:0] held_read;
 function automatic integer live_buffers;
  integer result;
  begin result=0;for(integer i=0;i<BUFFERS;i++)if(dut.state[i]!=0)result++;live_buffers=result;end
 endfunction
 task automatic event_line(input string kind,input integer seq);
  if(emit_events)$display("R3_EVENT case=%0d cycle=%0d kind=%s seq=%0d",case_id,cycle,kind,seq);
 endtask
 integer commit_seq,commit_ctx,seq;
 always @(posedge clk)begin
  cycle<=cycle+1;
  // First20 fields are the exact control_probe.cpp input protocol. The last27
  // are pre-NBA observations; invalid payload fields are compared under valid.
  if(control_file!=0)$fdisplay(control_file,
   "%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
   cycle,reset,cv,ctx,tag,ki,total,k,n,shift,first,last,aa,bb,oo,rr,rvalid,wr,wvalid,dr,
   cycle,cr,rv,ra,rap,wv,wa,wap,dv,dc,dt,dn,dl,de,
   dut.leaf_valid,dut.leaf_ready,dut.leaf_fire,dut.packet_ctx[dut.ready_id],dut.packet_end[dut.ready_id],dut.packet_sequence[dut.ready_id],
   dut.p1_valid&&dut.leaf_ready,dut.p1_ctx,dut.p1_end,dut.leaf_out_valid&&dut.leaf_out_ready,
   dut.reservation_count,dut.read_count,live_buffers());
  if(!reset&&enabled)begin
   if(rv&&rr&&wv&&wr)$fatal(1,"free simultaneous S read/write ports");
   if(dut.reservation_count>8||dut.read_count>2||live_buffers()>BUFFERS)$fatal(1,"finite resource overflow");
   if(dut.reservation_count>max_live)max_live=dut.reservation_count;
   if(dut.read_count>max_reads)max_reads=dut.read_count;
   if(live_buffers()>max_buffers)max_buffers=live_buffers();
   if(prev_done_hold&&(!dv||{dc,dt,dn,dl,de,ds,dd}!==held_done))$fatal(1,"done changed under hold");
   if(prev_write_hold&&(!wv||{wa,wdata}!==held_write))$fatal(1,"write changed under hold");
   if(prev_read_hold&&rv&&ra!==held_read)$fatal(1,"unaccepted read address changed");
   prev_done_hold=dv&&!dr;held_done={dc,dt,dn,dl,de,ds,dd};
   prev_write_hold=wv&&!wr;held_write={wa,wdata};prev_read_hold=rv&&!rr;held_read=ra;
   if(cv&&cr)begin
    if(accepted>=ncmd)$fatal(1,"unexpected command acceptance");
    ticket_seq[dut.reservation_tail]=accepted;accept_cycle[accepted]=cycle;write_acks[accepted]=0;
    if(first_accept<0)first_accept=cycle;
    if(emit_events)$display("R3_EVENT case=%0d cycle=%0d kind=cmd seq=%0d ctx=%0d ki=%0d k=%0d n=%0d first=%0d last=%0d",case_id,cycle,accepted,ctx,ki,k,n,first,last);
    accepted++;
   end
   if(rv&&rr)begin if(emit_events)$display("R3_EVENT case=%0d cycle=%0d kind=read seq=%0d addr=%0d",case_id,cycle,reads,ra);reads++;end
   if(rvalid&&rap)begin event_line("read_ack",read_acks);read_acks++;end
   if(dut.leaf_fire)begin
    seq=ticket_seq[dut.packet_reservation[dut.ready_id]];
    if(jobs[seq].error)$fatal(1,"invalid command issued MAC");
    event_line("leaf",seq);leafs++;
   end
   if(wv&&wr)begin
    seq=ticket_seq[dut.write_reservation];
    if(emit_events)$display("R3_EVENT case=%0d cycle=%0d kind=write seq=%0d addr=%0d",case_id,cycle,seq,wa);
    writes++;
   end
   if(wvalid&&wap)begin seq=ticket_seq[dut.write_reservation];event_line("write_ack",seq);write_acks[seq]++;acks++;end
   if(dv&&dr)begin
    if(retired>=accepted||dc!==jobs[retired].ctx||dt!==jobs[retired].tag||dn!==jobs[retired].next_k||
       dl!==jobs[retired].last||de!==jobs[retired].error||ds!==jobs[retired].saturation||dd!==jobs[retired].value)
     $fatal(1,"ordered completion mismatch case=%0d seq=%0d ctx=%0d next=%0d error=%b",case_id,retired,dc,dn,de);
    if(!de&&dl&&write_acks[retired]!=2)$fatal(1,"final retired before two S write ACKs");
    if(emit_events)$display("R3_EVENT case=%0d cycle=%0d kind=done seq=%0d next=%0d last=%0d error=%0d",case_id,cycle,retired,dn,dl,de);
    retired++;done_cycle=cycle;
   end
   if(producer_done&&retired==ncmd&&dut.descriptor_ok&&cr&&next_ready<0)begin next_ready=cycle;event_line("next_ready",ncmd);end
   if(dut.p1_valid&&dut.leaf_ready)begin
    commit_seq=ticket_seq[dut.p1_reservation];commit_ctx=int'(dut.p1_ctx);
    if(jobs[commit_seq].error||dut.p1_end!==jobs[commit_seq].next_k)$fatal(1,"commit identity");
    event_line("commit",commit_seq);committed++;
    #1;
    for(integer col=0;col<8;col++)if(dut.leaf.accum[commit_ctx][col]!==jobs[commit_seq].raw[96*col+:96])
     $fatal(1,"S96 prefix mismatch case=%0d seq=%0d col=%0d",case_id,commit_seq,col);
    checks++;
   end
  end
 end
 task automatic host(input bit writing,input integer address,input [127:0] value,output [127:0] got);
  integer guard;
  begin
   @(negedge clk);hreq=1;hwrite=writing;haddr=10'(address);hdata=value;htake=0;guard=0;
   do begin @(posedge clk);guard++;if(guard>10000)$fatal(1,"host request timeout");end while(!nr);
   @(negedge clk);hreq=0;htake=1;guard=0;
   do begin @(posedge clk);guard++;if(guard>10000)$fatal(1,"host response timeout");end while(!nv);
   got=nd;@(negedge clk);htake=0;
  end
 endtask
 task automatic drive(input integer index);
  begin
   ctx=jobs[index].ctx;tag=jobs[index].tag;ki=jobs[index].ki;total=jobs[index].total;k=jobs[index].k;n=jobs[index].n;
   shift=jobs[index].shift;first=jobs[index].first;last=jobs[index].last;aa=jobs[index].a;bb=jobs[index].b;oo=jobs[index].out;
  end
 endtask
 integer total_cases,fields,nwords,nbacks,qualified,word,guard,expect_valid,expect_reads,expect_writes;
 integer xctx,xtag,xki,xtotal,xk,xn,xshift,xf,xl,xa,xb,xout,xe,xnext;
 reg [7:0] xsat;reg [127:0] worddata,got;reg [255:0] xvalue;reg [767:0] xraw;
 integer init_addr[0:1023],back_addr[0:15];reg [127:0] init_data[0:1023],back_data[0:15];
 initial begin
  control_file=$fopen("control.txt","w");vector_file=$fopen("vectors.txt","r");
  if(!control_file||!vector_file)$fatal(1,"missing control/vector file");
  fields=$fscanf(vector_file,"%d\n",total_cases);if(fields!=1)$fatal(1,"vector header");
  for(integer c=0;c<total_cases;c++)begin
   fields=$fscanf(vector_file,"%d %d %d %d %d %d %d %d\n",case_id,ncmd,nwords,nbacks,read_delay,ack_delay,done_hold,qualified);
   if(fields!=8||ncmd>8192||nwords>1024||nbacks>16)$fatal(1,"case header");
   for(integer i=0;i<nwords;i++)begin fields=$fscanf(vector_file,"%d %h\n",init_addr[i],init_data[i]);if(fields!=2)$fatal(1,"init word");end
   expect_valid=0;expect_reads=0;expect_writes=0;
   for(integer i=0;i<ncmd;i++)begin
    fields=$fscanf(vector_file,"%d %d %d %d %d %d %d %d %d %d %d %d %d %d %h %h %h\n",
     xctx,xtag,xki,xtotal,xk,xn,xshift,xf,xl,xa,xb,xout,xe,xnext,xsat,xvalue,xraw);
    if(fields!=17)$fatal(1,"command vector");
    jobs[i].ctx=3'(xctx);jobs[i].tag=32'(xtag);jobs[i].ki=16'(xki);jobs[i].total=16'(xtotal);
    jobs[i].k=5'(xk);jobs[i].n=4'(xn);jobs[i].shift=6'(xshift);jobs[i].first=1'(xf);jobs[i].last=1'(xl);
    jobs[i].a=14'(xa);jobs[i].b=14'(xb);jobs[i].out=14'(xout);jobs[i].error=1'(xe);jobs[i].next_k=16'(xnext);
    jobs[i].saturation=xsat;jobs[i].value=xvalue;jobs[i].raw=xraw;
    if(!xe)begin expect_valid++;expect_reads+=1+((xb%64+xk*xn+63)/64);if(xl)expect_writes+=2;end
   end
   for(integer i=0;i<nbacks;i++)begin fields=$fscanf(vector_file,"%d %h\n",back_addr[i],back_data[i]);if(fields!=2)$fatal(1,"readback vector");end
   @(negedge clk);enabled=0;service_mode=0;cv=0;producer_done=0;reset=1;hreq=0;htake=0;
   repeat(3)@(negedge clk);reset=0;
   for(integer i=0;i<nwords;i++)host(1,init_addr[i],init_data[i],got);
   @(negedge clk);
   if(nv||bv||bank.pending)$fatal(1,"initialization response not retired");
   accepted=0;retired=0;committed=0;leafs=0;reads=0;read_acks=0;writes=0;acks=0;max_live=0;max_reads=0;max_buffers=0;
   first_accept=-1;next_ready=-1;done_cycle=-1;prev_done_hold=0;prev_read_hold=0;prev_write_hold=0;
   emit_events=qualified||read_delay!=0||ack_delay!=0||done_hold!=0;
   service_mode=1;enabled=1;cv=1;
   for(integer i=0;i<ncmd;i++)begin
    drive(i);guard=0;
    do begin @(posedge clk);guard++;if(guard>100000)$fatal(1,"descriptor timeout case=%0d i=%0d",case_id,i);end while(!cr);
    @(negedge clk);
   end
   cv=0;producer_done=1;
   // Offer a known legal future FIRST without asserting valid. This observes
   // genuine availability after final ACK/retirement, not an invalid-ready path.
   drive(0);tag=tag+1;ki=0;total=1;k=1;n=8;first=1;last=1;shift=16;
   guard=0;
   while(next_ready<0)begin @(negedge clk);guard++;if(guard>100000)$fatal(1,"drain timeout");end
   if(reads!=expect_reads||reads!=read_acks||writes!=expect_writes||writes!=acks||leafs!=expect_valid||committed!=expect_valid)
    $fatal(1,"work/traffic conservation case=%0d r=%0d/%0d w=%0d/%0d leaf=%0d/%0d",case_id,reads,expect_reads,writes,expect_writes,leafs,expect_valid);
   if(busy||dut.read_count||dut.p0_valid||dut.p1_valid||dut.p2_valid||dut.context_active||live_buffers())$fatal(1,"case did not drain");
   if(done_hold>=100&&ncmd>=8&&max_live!=8)$fatal(1,"completion pressure did not fill8 real reservations");
   $display("R3_CASE case=%0d buffers=%0d commands=%0d valid=%0d invalid=%0d read_lines=%0d read_acks=%0d write_words=%0d write_acks=%0d leaf_accepts=%0d commits=%0d completions=%0d peak_reservations=%0d peak_reads=%0d peak_buffers=%0d first_accept=%0d last_done=%0d next_ready=%0d accepted_to_done_cycles=%0d accepted_to_next_ready_cycles=%0d read_delay=%0d ack_delay=%0d done_hold=%0d",
    case_id,BUFFERS,ncmd,expect_valid,ncmd-expect_valid,reads,read_acks,writes,acks,leafs,committed,retired,max_live,max_reads,max_buffers,first_accept,done_cycle,next_ready,done_cycle-first_accept,next_ready-first_accept,read_delay,ack_delay,done_hold);
   enabled=0;service_mode=0;
   for(integer i=0;i<nbacks;i++)begin host(0,back_addr[i],0,got);if(got!==back_data[i])$fatal(1,"actual S readback mismatch case=%0d word=%0d",case_id,back_addr[i]);checks++;end
  end
  // Drop real work at multiple read/execute/held-completion points. Both the
  // service and its physical store share reset, matching this integration.
  for(integer delay_edges=0;delay_edges<20;delay_edges++)begin
   @(negedge clk);enabled=0;service_mode=0;reset=1;cv=0;repeat(2)@(negedge clk);reset=0;
   @(negedge clk);service_mode=1;ctx=0;tag=32'hdead;ki=0;total=16;k=16;n=8;shift=16;first=1;last=1;aa=0;bb=4096;oo=12288;cv=1;
   do @(posedge clk);while(!cr);@(negedge clk);cv=0;repeat(delay_edges)@(negedge clk);reset=1;
   repeat(2)@(negedge clk);reset=0;
   repeat(20)begin @(negedge clk);if(dv||busy||rv||wv)$fatal(1,"reset left ghost command");end
   checks++;
  end
  $fclose(vector_file);$fclose(control_file);
  $display("R3_PASS buffers=%0d cases=%0d checks=%0d reset_cases=20",BUFFERS,total_cases,checks);$finish;
 end
 initial begin #2000000000;$fatal(1,"R3 watchdog");end
endmodule
