// Native dual-P arithmetic, actual SRAM payload and held-response integration.
module tb_shared_pair #(parameter integer SHARED=1, TRUE_RW=1);
 logic clk=0,reset=1,cold_reset=1; always #5 clk=~clk;
 logic cfg_valid=0;
 logic [1:0] cfg_op=0;
 logic [7:0] cfg_epoch=0;
 logic [11:0] cfg_words=0;
 logic cfg_take=0;
 wire cfg_ready;
 wire cfg_done;
 wire cfg_error;
 logic fill_valid=0;
 logic [8:0] fill_addr=0;
 logic [511:0] fill_data=0;
 logic [3:0] fill_mask=0;
 logic fill_take=0;
 wire fill_ready;
 wire fill_done;
 wire fill_error;
 wire object_valid;
 wire [7:0] object_epoch;
 wire [11:0] object_words;
 logic [1:0] wide_write_req=0;
 logic [15:0] wide_write_addr=0;
 logic [1023:0] wide_write_data=0;
 logic [7:0] wide_write_mask=0;
 wire [1:0] wide_write_ready;
 wire [1:0] wide_write_valid;
 logic [1:0] wide_write_take=0;
 logic [1:0] load_a_shared=0;
 logic [21:0] load_pool_base=0;
 logic [15:0] load_pool_epoch=0;
 logic [3:0] io_req_valid=0;
 logic [3:0] io_req_write=0;
 logic [39:0] io_req_addr=0;
 logic [511:0] io_req_data=0;
 wire [3:0] io_req_ready;
 wire [3:0] io_rsp_valid;
 logic [3:0] io_rsp_ready=0;
 wire [511:0] io_rsp_data;
 logic [1:0] load_valid=0;
 wire [1:0] load_ready;
 logic [1:0] load_bank=0;
 logic [7:0] load_rows=0;
 logic [5:0] load_tiles=0;
 logic [1:0] load_a_wide=0;
 logic [1:0] load_b_wide=0;
 logic [1:0] load_reuse_b=0;
 logic [19:0] load_a_base=0;
 logic [19:0] load_b_base=0;
 wire [1:0] load_done;
 logic [1:0] load_take=0;
 wire [1:0] load_error;
 logic [1:0] cmd_valid=0;
 wire [1:0] cmd_ready;
 logic [7:0] cmd_op=0;
 logic [11:0] cmd_index=0;
 logic [127:0] cmd_data=0;
 logic [1:0] cmd_store=0;
 logic [1:0] cmd_route=0;
 logic [1:0] cmd_pack16=0;
 logic [19:0] cmd_dst=0;
 wire [1:0] cmd_done;
 logic [1:0] cmd_take=0;
 wire [1:0] cmd_error;
 wire [1:0] cmd_saturated;
 wire [255:0] cmd_result;
 logic [1:0] gate_valid=0;
 logic [1:0] gate_route=0;
 wire [1:0] gate_ready;
 logic [19:0] gate_a=0;
 logic [19:0] gate_b=0;
 logic [19:0] gate_dst=0;
 wire [1:0] gate_done;
 logic [1:0] gate_take=0;
 wire [1:0] gate_error;
 wire [1:0] gate_saturated;
 wire [1:0] m_to_g_valid;
 wire [63:0] m_to_g_data;
 logic [1:0] m_to_g_take=0;
 logic [1:0] g_from_m_valid=0;
 logic [63:0] g_from_m_data=0;
 wire [1:0] g_from_m_take;
 pu_p_shared_pair #(.ENABLE_SHARED(SHARED),.ENABLE_LOCAL_RW(TRUE_RW),.S_BANK_RW(1),.S_CONSUMER_PRIORITY(1),.M_CONTEXTS(8)) dut(.*);
 integer cycle=0,seed=247,scenario=0;
 integer a_count[0:1],b_count[0:1],shared_count[0:1],numeric_checks[0:1];
 integer loads[0:1],contexts[0:1],errors[0:1],io_words[0:1],wide_lines[0:1];
 integer lease_stalls[0:1],concurrent_writes[0:1],simultaneous_rw[0:1];
 integer release_cases=0,release_blocked_cycles=0,cold_cancelled_loads=0,lifecycle_numeric[0:1];
 wire [1:0] lease_active;
 bit aw=0,bw=0,prefix=0;
 // Persistent simulation processes avoid nested automatic-task fork frames.
 // Dispatch still starts both P workers together; hardware handshakes and all
 // acceptance/completion checks remain in the same per-P driver tasks.
 logic [1:0] worker_request=0,worker_done=0;
 integer worker_operation=0;
 logic refill_load_request=0,refill_load_done=0;
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(cycle>300000)$fatal(1,"pair watchdog");
 end
 for(genvar p=0;p<2;p++)begin: monitors
  assign lease_active[p]=dut.groups[p].block_p.store.lease;
  always @(posedge clk)if(!reset)begin
   if(dut.groups[p].block_p.a_valid&&dut.groups[p].block_p.a_ready)a_count[p]<=a_count[p]+1;
   if(dut.groups[p].block_p.b_valid&&dut.groups[p].block_p.b_ready)b_count[p]<=b_count[p]+1;
   if(dut.pool_a_valid[p]&&dut.pool_a_ready[p])shared_count[p]<=shared_count[p]+1;
   if(wide_write_req[p]&&wide_write_ready[p]&&lease_active[p])concurrent_writes[p]<=concurrent_writes[p]+1;
   if(wide_write_req[p]&&wide_write_ready[p]&&dut.groups[p].block_p.store.wide_req&&dut.groups[p].block_p.store.wide_ready)
    simultaneous_rw[p]<=simultaneous_rw[p]+1;
  end
  initial begin
   forever begin
    wait(worker_request[p]);
    case(worker_operation)
     0:initialize_local(p);
     1:compute(p);
     2:cold_numeric(p,1);
     3:cold_numeric(p,0);
     4:lease_probe(p);
     default:$fatal(1,"unknown P worker operation");
    endcase
    worker_done[p]=1;
    wait(!worker_request[p]);
    worker_done[p]=0;
   end
  end
 end
 initial begin
  forever begin
   wait(refill_load_request);
   accept_both_loads();retire_both_loads();
   refill_load_done=1;
   wait(!refill_load_request);
   refill_load_done=0;
  end
 end
 task automatic run_both(input integer operation);
  begin
   if(worker_request!=0||worker_done!=0)$fatal(1,"P worker dispatcher already busy");
   @(negedge clk);worker_operation=operation;worker_request=2'b11;
   wait(worker_done==2'b11);
   @(negedge clk);worker_request=0;
   wait(worker_done==0);
  end
 endtask
 task automatic refill_with_pending_loads;
  begin
   if(refill_load_request||refill_load_done)$fatal(1,"refill LOAD dispatcher already busy");
   @(negedge clk);refill_load_request=1;
   initialize_pool();
   wait(refill_load_done);
   @(negedge clk);refill_load_request=0;
   wait(!refill_load_done);
  end
 endtask
 function automatic integer aval(input integer s,r,k);
  return ((s*5+r*7+k)%13-6)*(aw?31:1);
 endfunction
 function automatic integer bval(input integer p,s,g,n,k);
  return ((p*5+s*3+g*3+n*2+k)%15-7)*(bw?19:1);
 endfunction
 function automatic longint signed gold(input integer p,r,g,n);
  longint signed total;
  begin
   total=0;
   if(n<5)for(integer s=0;s<2;s++)for(integer k=0;k<(s==1?11:16);k++)
    total+=64'(aval(s,r,k))*64'(bval(p,s,g,n,k));
   return total;
  end
 endfunction
 function automatic longint signed rounded(input longint signed value);
  longint signed quotient,remainder;
  begin
   quotient=value>>>2;remainder=value-quotient*4;
   if(remainder>2||(remainder==2&&(quotient&1)!=0))quotient++;
   return quotient;
  end
 endfunction
 function automatic logic [127:0] a_word(input integer s,r,t);
  logic [127:0] value;
  begin
   value=0;
   if(r<3)for(integer k=0;k<8;k++)begin
    if(aw)value[16*k+:16]=16'(aval(s,r,t*8+k));
    else value[8*k+:8]=8'(aval(s,r,t*8+k));
   end
   return value;
  end
 endfunction
 function automatic logic [511:0] b_line(input integer p,s,g,t,half);
  logic [511:0] value;
  integer n,k;
  begin
   value=0;
   for(integer element=0;element<(bw?32:64);element++)begin
    n=(element+(bw?half*32:0))/8;k=element%8;
    if(bw)value[16*element+:16]=16'(bval(p,s,g,n,t*8+k));
    else value[8*element+:8]=8'(bval(p,s,g,n,t*8+k));
   end
   return value;
  end
 endfunction
 function automatic integer pool_base(input integer s);return s==0?1021:1040;endfunction
 function automatic integer local_b(input integer s,g);return 64+(s*8+g)*(bw?16:8);endfunction
 task automatic access(input integer p,input bit wr,input integer address,input logic [127:0] data,output logic [127:0] result);
  integer port_id;logic [127:0] held;
  begin
   port_id=p*2;
   @(negedge clk);io_req_valid[port_id]=1;io_req_write[port_id]=wr;
   io_req_addr[10*port_id+:10]=10'(address);io_req_data[128*port_id+:128]=data;
   do @(posedge clk);while(!io_req_ready[port_id]);
   @(negedge clk);io_req_valid[port_id]=0;
   do @(posedge clk);while(!io_rsp_valid[port_id]);
   held=io_rsp_data[128*port_id+:128];
   repeat(2)begin @(negedge clk);if(!io_rsp_valid[port_id]||io_rsp_data[128*port_id+:128]!==held)$fatal(1,"IO response unstable");end
   result=held;io_rsp_ready[port_id]=1;
   @(negedge clk);io_rsp_ready[port_id]=0;io_words[p]++;
  end
 endtask
 task automatic lease_probe(input integer p);
  logic [511:0] data;
  logic [127:0] got;
  integer address;
  begin
   // The last scenario has initialized native S16 inputs. Explicitly select
   // the local suffix for this probe so no pool object is required.
   for(integer protected_test=0;protected_test<2;protected_test++)begin
    address=protected_test!=0?local_b(1,0):700;
    data={4{128'(32'h76540000+p*16+protected_test)}};
    start_load(p,1,0,0);
      wait(lease_active[p]);
      @(negedge clk);wide_write_req[p]=1;wide_write_addr[p*8+:8]=8'(address/4);
      wide_write_data[p*512+:512]=data;wide_write_mask[p*4+:4]=4'hf;
      do begin
       @(posedge clk);
       if(protected_test!=0&&lease_active[p])begin
        if(wide_write_ready[p])$fatal(1,"write accepted into owned B range");
        lease_stalls[p]++;
       end
      end while(!wide_write_ready[p]);
      @(negedge clk);wide_write_req[p]=0;
      do @(posedge clk);while(!wide_write_valid[p]);
      @(negedge clk);wide_write_take[p]=1;@(negedge clk);wide_write_take[p]=0;
    finish_load(p,1,0,0);
    for(integer lane=0;lane<4;lane++)begin
     access(p,0,address+lane,0,got);
     if(got!==data[128*lane+:128])$fatal(1,"lease probe post-ACK SRAM mismatch");
    end
   end
   if(lease_stalls[p]==0||concurrent_writes[p]==0||simultaneous_rw[p]==0)$fatal(1,"lease/concurrency coverage absent p=%0d",p);
  end
 endtask
 task automatic write_line(input integer p,address,input logic [511:0] data);
  logic [127:0] ignored;
  begin
   if(TRUE_RW)begin
    @(negedge clk);wide_write_req[p]=1;wide_write_addr[p*8+:8]=8'(address/4);
    wide_write_data[p*512+:512]=data;wide_write_mask[p*4+:4]=4'hf;
    do @(posedge clk);while(!wide_write_ready[p]);
    @(negedge clk);wide_write_req[p]=0;
    do @(posedge clk);while(!wide_write_valid[p]);
    repeat(2)begin @(negedge clk);if(!wide_write_valid[p])$fatal(1,"write ACK not held");end
    wide_write_take[p]=1;@(negedge clk);wide_write_take[p]=0;wide_lines[p]++;
   end else for(integer lane=0;lane<4;lane++)access(p,1,address+lane,data[128*lane+:128],ignored);
  end
 endtask
 task automatic pool_config(input integer op,words,input bit expect_error=0);
  begin
   @(negedge clk);cfg_valid=1;cfg_op=2'(op);cfg_words=12'(words);cfg_epoch=8'(scenario+17);
   do @(posedge clk);while(!cfg_ready);
   @(negedge clk);cfg_valid=0;
   do @(posedge clk);while(!cfg_done);
   if(cfg_error!==expect_error)$fatal(1,"pool config error op=%0d",op);
   repeat(3)begin @(negedge clk);if(!cfg_done||cfg_error!==expect_error)$fatal(1,"config ACK unstable");end
   cfg_take=1;@(negedge clk);cfg_take=0;
  end
 endtask
 task automatic initialize_pool;
  logic [511:0] data;
  integer word_index;
  begin
   pool_config(0,1050);
   for(integer line_id=0;line_id<263;line_id++)begin
    data=0;
    for(integer lane=0;lane<4;lane++)begin
     word_index=line_id*4+lane;
     for(integer s=0;s<2;s++)if(word_index>=pool_base(s)&&word_index<pool_base(s)+6)
      data[128*lane+:128]=a_word(s,(word_index-pool_base(s))%3,(word_index-pool_base(s))/3);
    end
    @(negedge clk);fill_valid=1;fill_addr=9'(line_id);fill_data=data;fill_mask=line_id==262?4'b0011:4'b1111;
    do @(posedge clk);while(!fill_ready);
    @(negedge clk);fill_valid=0;
    do @(posedge clk);while(!fill_done);
    if(fill_error)$fatal(1,"pool fill error line=%0d",line_id);
    if(line_id%17==0)repeat(3)begin @(negedge clk);if(!fill_done||fill_error)$fatal(1,"fill ACK unstable");end
    @(negedge clk);fill_take=1;@(negedge clk);fill_take=0;
   end
   pool_config(1,0);
   if(!object_valid||object_words!=1050||object_epoch!=8'(scenario+17))$fatal(1,"sealed metadata mismatch");
  end
 endtask
 task automatic initialize_local(input integer p);
  logic [511:0] data;
  begin
   for(integer s=0;s<2;s++)begin
    // Explicit local suffix when the shared capacity policy covers only s=0.
    if(!SHARED||(prefix&&s==1))for(integer t=0;t<2;t++)begin
     data=0;for(integer r=0;r<4;r++)data[128*r+:128]=a_word(s,r,t);
     write_line(p,s*16+t*4,data);
    end
    for(integer g=0;g<8;g++)for(integer t=0;t<2;t++)for(integer half=0;half<(bw?2:1);half++)
     write_line(p,local_b(s,g)+(t*(bw?2:1)+half)*4,b_line(p,s,g,t,half));
   end
  end
 endtask
 task automatic start_load(input integer p,s,g,input bit reuse_a,input integer bad=0);
  bit selected;
  begin
   selected=SHARED&&!reuse_a&&!(prefix&&s==1);
   @(negedge clk);load_bank[p]=0;load_rows[p*4+:4]=reuse_a?4'd0:4'd3;load_tiles[p*3+:3]=3'd2;
   load_a_wide[p]=aw;load_b_wide[p]=bw;load_reuse_b[p]=0;
   load_a_base[p*10+:10]=10'(s*16);load_b_base[p*10+:10]=10'(local_b(s,g));
   load_a_shared[p]=selected;load_pool_base[p*11+:11]=11'(bad==2?1049:pool_base(s));
   load_pool_epoch[p*8+:8]=8'(scenario+17+(bad==1?1:0));
   if(bad==3)load_rows[p*4+:4]=4'd9;
   load_valid[p]=1;
   do @(posedge clk);while(!load_ready[p]);
   @(negedge clk);load_valid[p]=0;
  end
 endtask
 task automatic finish_load(input integer p,s,g,input integer bad=0);
  bit expected_error;
  begin
   expected_error=bad!=0;
   do @(posedge clk);while(!load_done[p]);
   if(load_error[p]!==expected_error)$fatal(1,"LOAD result p=%0d s=%0d g=%0d bad=%0d",p,s,g,bad);
   repeat(3)begin @(negedge clk);if(!load_done[p]||load_error[p]!==expected_error)$fatal(1,"LOAD completion unstable");end
   load_take[p]=1;@(negedge clk);load_take[p]=0;
   loads[p]++;if(expected_error)errors[p]++;
  end
 endtask
 task automatic load(input integer p,s,g,input bit reuse_a,input integer bad=0);
  begin
   start_load(p,s,g,reuse_a,bad);
   finish_load(p,s,g,bad);
  end
 endtask
 task automatic command(input integer p,op,index,input logic [63:0] data,input bit writes,input bit expect_error,output logic [127:0] result);
  logic [127:0] held;
  begin
   @(negedge clk);cmd_op[p*4+:4]=4'(op);cmd_index[p*6+:6]=6'(index);cmd_data[p*64+:64]=data;
   cmd_store[p]=writes;cmd_valid[p]=1;
   do @(posedge clk);while(!cmd_ready[p]);
   @(negedge clk);cmd_valid[p]=0;
   do @(posedge clk);while(!cmd_done[p]);
   if(cmd_error[p]!==expect_error||cmd_saturated[p])$fatal(1,"command result p=%0d op=%0d index=%0d error=%0d",p,op,index,cmd_error[p]);
   held=cmd_result[128*p+:128];
   repeat(2)begin @(negedge clk);if(!cmd_done[p]||cmd_result[128*p+:128]!==held||cmd_error[p]!==expect_error)$fatal(1,"command completion unstable");end
   result=held;cmd_take[p]=1;@(negedge clk);cmd_take[p]=0;
   if(expect_error)errors[p]++;
  end
 endtask
 task automatic compute(input integer p);
  logic [63:0] descriptor;
  logic [127:0] got;
  longint signed expected;
  begin
   if(SHARED&&scenario==2)begin
    load(p,0,0,0,1);load(p,0,0,0,2);load(p,0,0,0,3);
   end
   for(integer row=0;row<3;row++)begin
    for(integer s=0;s<2;s++)for(integer g=0;g<8;g++)begin
     load(p,s,g,g!=0);
     descriptor=0;descriptor[0]=aw;descriptor[1]=bw;descriptor[2]=s==0;descriptor[3]=s==1;
     descriptor[7:4]=s==1?4'd3:4'd8;descriptor[11:8]=4'd5;descriptor[14:12]=3'd2;
     descriptor[17:15]=3'(row);descriptor[33:18]=16'(s*16);descriptor[49:34]=16'(100+row*100+g);
     command(p,13,g,descriptor,0,0,got);contexts[p]++;
    end
    for(integer g=0;g<8;g++)begin
     for(integer pair_id=0;pair_id<4;pair_id++)begin
      command(p,3,g*8+pair_id,0,0,0,got);
      for(integer lane=0;lane<2;lane++)begin
       expected=gold(p,row,g,pair_id*2+lane);
       if($signed(got[64*lane+:64])!==expected)$fatal(1,"raw numeric p=%0d row=%0d group=%0d lane=%0d got=%h expected=%0d",p,row,g,pair_id*2+lane,got,expected);
       numeric_checks[p]++;
      end
     end
     for(integer half=0;half<2;half++)begin
      cmd_dst[p*10+:10]=10'(600+row*16+g*2+half);
      command(p,5,g*8+half,64'h202,1,0,got);
      for(integer lane=0;lane<4;lane++)begin
       expected=rounded(gold(p,row,g,half*4+lane));
       if($signed(got[32*lane+:32])!=expected)$fatal(1,"RNE numeric mismatch");numeric_checks[p]++;
      end
     end
     command(p,14,g,64'(100+row*100+g)<<1,0,0,got);
    end
    command(p,3,0,0,0,1,got); // Released context cannot be read.
   end
   for(integer row=0;row<3;row++)for(integer g=0;g<8;g++)for(integer half=0;half<2;half++)begin
    access(p,0,600+row*16+g*2+half,0,got);
    for(integer lane=0;lane<4;lane++)begin
     expected=rounded(gold(p,row,g,half*4+lane));
     if($signed(got[32*lane+:32])!=expected)$fatal(1,"actual SRAM writeback mismatch p=%0d",p);
     numeric_checks[p]++;
    end
   end
  end
 endtask
 task automatic prepare_both_loads;
  begin
   @(negedge clk);load_valid=2'b11;load_take=0;load_bank=0;
   load_rows=8'h33;load_tiles={3'd2,3'd2};load_a_wide={2{aw}};load_b_wide={2{bw}};
   load_reuse_b=0;load_a_base=0;load_b_base={10'(local_b(0,0)),10'(local_b(0,0))};
   load_a_shared={2{SHARED!=0}};load_pool_base={11'(pool_base(0)),11'(pool_base(0))};
   load_pool_epoch={2{8'(scenario+17)}};
  end
 endtask
 task automatic accept_both_loads;
  logic [1:0] accepted;
  begin
   while(load_valid!=0)begin
    @(posedge clk);accepted=load_valid&load_ready;
    @(negedge clk);load_valid=load_valid&~accepted;
   end
  end
 endtask
 task automatic wait_both_loads;
  begin
   while(load_done!=2'b11)@(negedge clk);
   if(load_error!=0)$fatal(1,"lifecycle reload failed");
  end
 endtask
 task automatic retire_both_loads;
  begin
   wait_both_loads();
   @(negedge clk);load_take=2'b11;@(negedge clk);load_take=0;
  end
 endtask
 task automatic request_release;
  begin
   cfg_valid=1;cfg_op=2;cfg_epoch=8'(scenario+17);cfg_words=0;cfg_take=0;
  end
 endtask
 task automatic finish_release;
  begin
   do @(posedge clk);while(!cfg_ready);
   @(negedge clk);cfg_valid=0;
   while(!cfg_done)@(negedge clk);
   if(cfg_error)$fatal(1,"lifecycle RELEASE error");
   repeat(3)begin
    @(negedge clk);
    if(!cfg_done||cfg_error||load_ready!=0)$fatal(1,"held RELEASE must block new LOAD");
   end
   cfg_take=1;@(negedge clk);cfg_take=0;
   if(object_valid)$fatal(1,"RELEASE retained object validity");
  end
 endtask
 task automatic release_races;
  begin
   initialize_pool();
   // RELEASE wins when the two valid requests first appear on the same edge.
   // The producer holds LOAD valid until it is accepted after a complete refill.
   prepare_both_loads();request_release();
   @(posedge clk);if(load_ready!=0||!cfg_ready)$fatal(1,"same-edge RELEASE did not take priority");
   @(negedge clk);cfg_valid=0;
   while(!cfg_done)@(negedge clk);
   repeat(4)begin
    @(negedge clk);if(load_ready!=0||load_done!=0||cfg_error)$fatal(1,"new LOAD escaped held RELEASE");
    release_blocked_cycles++;
   end
   cfg_take=1;@(negedge clk);cfg_take=0;
   repeat(4)begin
    @(negedge clk);if(load_ready!=0||load_done!=0||object_valid)$fatal(1,"shared LOAD admitted while pool EMPTY");
    release_blocked_cycles++;
   end
   refill_with_pending_loads();
   release_cases++;
   // The descriptor is still pending inside P when RELEASE arrives one cycle
   // after the public LOAD handshake. Pool RELEASE must not prevent its issue.
   prepare_both_loads();accept_both_loads();request_release();
   // Sample the actual handshake edge, after the request's combinational
   // ready path has settled; the preceding task drives it on the falling edge.
   @(posedge clk);if(cfg_ready)$fatal(1,"RELEASE accepted before admitted LOAD completed");
   wait_both_loads();
   repeat(5)begin
    @(negedge clk);
    if(cfg_ready||!object_valid||load_done!=2'b11||load_error!=0)$fatal(1,"RELEASE overtook held LOAD completion");
    release_blocked_cycles++;
   end
   retire_both_loads();finish_release();release_cases++;
   // Distinct case: request RELEASE only after both public completions exist.
   initialize_pool();prepare_both_loads();accept_both_loads();wait_both_loads();
   @(negedge clk);request_release();
   repeat(5)begin
    @(negedge clk);
    if(cfg_ready||!object_valid||load_done!=2'b11)$fatal(1,"held LOAD completion lost ownership");
    release_blocked_cycles++;
   end
   retire_both_loads();finish_release();release_cases++;
  end
 endtask
 task automatic cold_numeric(input integer p,input bit expect_empty);
  logic [63:0] descriptor;
  logic [127:0] got;
  longint signed expected;
  integer column;
  begin
   descriptor=0;descriptor[2]=1;descriptor[3]=1;descriptor[7:4]=8;
   descriptor[11:8]=5;descriptor[14:12]=2;descriptor[49:34]=400;
   command(p,13,0,descriptor,0,expect_empty,got);
   if(!expect_empty)begin
    for(integer pair_id=0;pair_id<4;pair_id++)begin
     command(p,3,pair_id,0,0,0,got);
     for(integer lane=0;lane<2;lane++)begin
      column=pair_id*2+lane;expected=0;
      if(column<5)for(integer k=0;k<16;k++)expected+=64'(aval(0,0,k))*64'(bval(p,0,0,column,k));
      if($signed(got[64*lane+:64])!==expected)$fatal(1,"post-cold-reset native numeric mismatch");
      lifecycle_numeric[p]++;
     end
    end
    command(p,14,0,64'd400<<1,0,0,got);
   end
  end
 endtask
 task automatic cold_reset_refill;
  begin
   // Cancel two admitted P operations and the common pool object together.
   // No outstanding protocol producer task survives the deliberate reset.
   initialize_pool();prepare_both_loads();accept_both_loads();
   if(SHARED)wait(dut.pool.active==2'b11);
   else wait(lease_active==2'b11);
   @(negedge clk);
   if(load_done!=0)$fatal(1,"cold-reset fixture completed too early");
   cold_cancelled_loads=2;cold_reset=1;load_valid=0;load_take=0;
   repeat(4)@(negedge clk);cold_reset=0;
   repeat(8)begin
    @(negedge clk);
    if(object_valid||cfg_done||fill_done||load_done||cmd_done||io_rsp_valid||dut.pool_a_valid)
     $fatal(1,"stale P/pool event survived cold reset");
   end
   aw=0;bw=0;prefix=0;
   run_both(2);
   // Cold-reset memory is invalid, so rewrite B and any local A before use.
   run_both(0);
   if(SHARED)begin
    prepare_both_loads();
    repeat(4)begin @(negedge clk);if(load_ready!=0)$fatal(1,"post-reset LOAD admitted before SEAL");end
    refill_with_pending_loads();
   end else begin
    initialize_pool();prepare_both_loads();accept_both_loads();retire_both_loads();
   end
   run_both(3);
   pool_config(2,0);
  end
 endtask
 integer wall_start,compute_start,compute_cycles,a_before,b_before,shared_before;
 initial begin
  if(!$value$plusargs("SEED=%d",seed))seed=247;
  for(integer p=0;p<2;p++)begin
   a_count[p]=0;b_count[p]=0;shared_count[p]=0;numeric_checks[p]=0;
   loads[p]=0;contexts[p]=0;errors[p]=0;io_words[p]=0;wide_lines[p]=0;
   lease_stalls[p]=0;concurrent_writes[p]=0;simultaneous_rw[p]=0;
   lifecycle_numeric[p]=0;
  end
  gate_take=2'b11;m_to_g_take=2'b11;
  repeat(4)@(negedge clk);reset=0;cold_reset=0;repeat(5)@(negedge clk);
  for(scenario=0;scenario<3;scenario++)begin
   aw=scenario!=0;bw=scenario==2;prefix=scenario==1;
   wall_start=cycle;a_before=a_count[0]+a_count[1];b_before=b_count[0]+b_count[1];shared_before=shared_count[0]+shared_count[1];
   if(SHARED)initialize_pool();
   run_both(0);
   compute_start=cycle;
   run_both(1);
   compute_cycles=cycle-compute_start;
   if(SHARED)begin pool_config(2,0);if(object_valid)$fatal(1,"pool release did not invalidate");end
   if(a_count[0]+a_count[1]-a_before!=72)$fatal(1,"A work conservation");
   if(shared_count[0]+shared_count[1]-shared_before!=(SHARED?(prefix?36:72):0))$fatal(1,"shared prefix/local fallback conservation");
   $display("SHARED_PAIR_MEASURE scenario=%0d shared=%0d true_rw=%0d Awide=%0d Bwide=%0d prefix=%0d cycles=%0d compute_cycles=%0d A=%0d B=%0d shared_A=%0d numeric=%0d",
    scenario,SHARED,TRUE_RW,aw,bw,prefix,cycle-wall_start,compute_cycles,a_count[0]+a_count[1]-a_before,
    b_count[0]+b_count[1]-b_before,shared_count[0]+shared_count[1]-shared_before,numeric_checks[0]+numeric_checks[1]);
  end
  if(contexts[0]!=144||contexts[1]!=144||numeric_checks[0]!=1728||numeric_checks[1]!=1728)$fatal(1,"arithmetic coverage incomplete");
  if(TRUE_RW&&(wide_lines[0]==0||wide_lines[1]==0))$fatal(1,"wide local fill untested");
  if(!TRUE_RW&&(wide_write_ready!=0||wide_write_valid!=0))$fatal(1,"disabled wide port not inert");
  if(TRUE_RW)begin
   prefix=1; // Use initialized local segment 1 in every parameter variant.
   if(SHARED)begin
    // The full-shared last case intentionally never initialized local A.
    // Populate only the suffix before a local lease probe.
    run_both(0);
   end
   compute_start=cycle;
   run_both(4);
   $display("SHARED_PAIR_MEASURE scenario=lease shared=%0d true_rw=%0d cycles=%0d protected_stalls=%0d concurrent_writes=%0d simultaneous_rw=%0d",
    SHARED,TRUE_RW,cycle-compute_start,lease_stalls[0]+lease_stalls[1],concurrent_writes[0]+concurrent_writes[1],simultaneous_rw[0]+simultaneous_rw[1]);
  end
  // Invalid LOADs may have changed part of an operand bank; no arithmetic is
  // attempted until a complete valid reload. Atomic rollback is not promised.
  prefix=0;run_both(0);
  compute_start=cycle;
  if(SHARED)release_races();
  cold_reset_refill();
  if(release_cases!=(SHARED?3:0)||cold_cancelled_loads!=2||lifecycle_numeric[0]+lifecycle_numeric[1]!=16)
   $fatal(1,"lifecycle coverage missing");
  $display("SHARED_PAIR_MEASURE scenario=lifecycle shared=%0d true_rw=%0d cycles=%0d release_cases=%0d release_blocked_cycles=%0d cold_cancelled_loads=%0d refill_numeric=%0d",
   SHARED,TRUE_RW,cycle-compute_start,release_cases,release_blocked_cycles,cold_cancelled_loads,lifecycle_numeric[0]+lifecycle_numeric[1]);
  @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;repeat(8)@(negedge clk);
  if(io_rsp_valid||load_done||cmd_done||object_valid||fill_done||cfg_done)$fatal(1,"stale completion after reset");
  $display("SHARED_PAIR_PASS shared=%0d true_rw=%0d numeric=%0d contexts=%0d errors=%0d loads=%0d",
    SHARED,TRUE_RW,numeric_checks[0]+numeric_checks[1],contexts[0]+contexts[1],errors[0]+errors[1],loads[0]+loads[1]);
  $finish;
 end
endmodule
