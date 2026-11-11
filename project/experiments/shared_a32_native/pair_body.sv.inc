 integer cycle=0,seed=247,scenario=0,nrows=1,ntiles=1,lastk=1,base=0;
 bit aw=0,bw=0;
 logic [1:0] request=0,finished=0;integer work_kind=0;
 integer numeric[0:1],commands[0:1],load_cycles[0:1],compute_cycles[0:1];
 integer shared_words[0:1],shared_beats[0:1],first_a[0:1],last_a[0:1];
 longint signed checksum[0:1];
 integer scenarios=0,total_numeric=0;
 always @(posedge clk)begin cycle<=cycle+1;if(cycle>2000000)$fatal(1,"equal pair watchdog");end
 for(genvar p=0;p<2;p++)begin: workers
  always @(posedge clk)if(!reset&&(|dut.pool_a_valid[p*WORDS+:WORDS])&&dut.pool_a_ready[p])begin
   if(first_a[p]<0)first_a[p]=cycle;last_a[p]=cycle;shared_beats[p]++;
   for(integer lane=0;lane<WORDS;lane++)if(dut.pool_a_valid[p*WORDS+lane])shared_words[p]++;
  end
  initial forever begin
   wait(request[p]);if(work_kind==0)initialize_B(p);else compute(p);
   finished[p]=1;wait(!request[p]);finished[p]=0;
  end
 end
 task automatic both(input integer kind);
  begin
   @(negedge clk);work_kind=kind;request=3;wait(finished==3);
   @(negedge clk);request=0;wait(finished==0);
  end
 endtask
 function automatic integer aval(input integer row,k);
  return ((row*7+k*3+scenario*5)%23-11)*(aw?313:1);
 endfunction
 function automatic integer bval(input integer p,col,k);
  return ((p*11+col*5+k*7+scenario*3)%19-9)*(bw?211:1);
 endfunction
 function automatic [127:0] aword(input integer row,tile);
  logic [127:0] v;
  begin v=0;for(integer k=0;k<8;k++)begin
   if(aw)v[k*16+:16]=16'(aval(row,tile*8+k));else v[k*8+:8]=8'(aval(row,tile*8+k));
  end return v;end
 endfunction
 function automatic [511:0] bline(input integer p,tile,half);
  logic [511:0] v;
  begin v=0;for(integer e=0;e<(bw?32:64);e++)begin
   if(bw)v[e*16+:16]=16'(bval(p,(e+half*32)/8,tile*8+e%8));else v[e*8+:8]=8'(bval(p,e/8,tile*8+e%8));
  end return v;end
 endfunction
 function automatic longint signed expected(input integer p,row,col);
  longint signed v;
  begin v=0;for(integer k=0;k<(ntiles-1)*8+lastk;k++)v+=64'(aval(row,k))*64'(bval(p,col,k));return v;end
 endfunction
 task automatic config_pool(input integer op,words);
  begin
   @(negedge clk);cfg_valid=1;cfg_op=2'(op);cfg_words=12'(words);cfg_epoch=8'(scenario+17);
   do @(posedge clk);while(!cfg_ready);
   @(negedge clk);cfg_valid=0;while(!cfg_done)@(negedge clk);
   if(cfg_error)$fatal(1,"equal pair pool config error");
   cfg_take=1;@(negedge clk);cfg_take=0;
  end
 endtask
 task automatic initialize_pool;
  integer words,index;logic [511:0] v;
  begin
   words=base+nrows*ntiles;config_pool(0,words);
   for(integer line_id=0;line_id<(words+3)/4;line_id++)begin
    v=0;for(integer lane=0;lane<4;lane++)begin
     index=line_id*4+lane-base;
     if(index>=0&&index<nrows*ntiles)v[lane*128+:128]=aword(index%nrows,index/nrows);
    end
    @(negedge clk);fill_valid=1;fill_addr=9'(line_id);fill_data=v;
    fill_mask=(words-line_id*4)>=4?4'hf:4'((1<<(words-line_id*4))-1);
    do @(posedge clk);while(!fill_ready);
    @(negedge clk);fill_valid=0;while(!fill_done)@(negedge clk);
    if(fill_error)$fatal(1,"equal pair fill error");fill_take=1;@(negedge clk);fill_take=0;
   end
   config_pool(1,0);
  end
 endtask
 task automatic initialize_B(input integer p);
  begin
   for(integer t=0;t<ntiles;t++)for(integer half=0;half<(bw?2:1);half++)begin
    @(negedge clk);wide_write_req[p]=1;wide_write_addr[p*8+:8]=8'(16+t*(bw?2:1)+half);
    wide_write_data[p*512+:512]=bline(p,t,half);wide_write_mask[p*4+:4]=15;
    do @(posedge clk);while(!wide_write_ready[p]);
    @(negedge clk);wide_write_req[p]=0;while(!wide_write_valid[p])@(negedge clk);
    wide_write_take[p]=1;@(negedge clk);wide_write_take[p]=0;
   end
  end
 endtask
 task automatic load(input integer p);
  integer mark;
  begin
   @(negedge clk);mark=cycle;load_valid[p]=1;load_bank[p]=0;load_rows[p*4+:4]=4'(nrows);load_tiles[p*3+:3]=3'(ntiles);
   load_a_wide[p]=aw;load_b_wide[p]=bw;load_reuse_b[p]=0;load_a_shared[p]=1;
   load_pool_base[p*11+:11]=11'(base);load_pool_epoch[p*8+:8]=8'(scenario+17);load_a_base[p*10+:10]=0;load_b_base[p*10+:10]=64;
   do @(posedge clk);while(!load_ready[p]);
   @(negedge clk);load_valid[p]=0;while(!load_done[p])@(negedge clk);
   if(load_error[p])$fatal(1,"equal pair load error");load_cycles[p]+=cycle-mark;
   repeat(2)begin @(negedge clk);if(!load_done[p]||load_error[p])$fatal(1,"equal pair LOAD ACK unstable");end
   load_take[p]=1;@(negedge clk);load_take[p]=0;
  end
 endtask
 task automatic command(input integer p,op,index,input logic [63:0] data,output logic [127:0] got);
  integer mark;logic [127:0] held;
  begin
   @(negedge clk);cmd_valid[p]=1;cmd_op[p*4+:4]=4'(op);cmd_index[p*6+:6]=6'(index);cmd_data[p*64+:64]=data;
   do @(posedge clk);while(!cmd_ready[p]);
   @(negedge clk);cmd_valid[p]=0;mark=cycle;while(!cmd_done[p])@(negedge clk);
   if(cmd_error[p]||cmd_saturated[p])$fatal(1,"equal pair command error p=%0d op=%0d",p,op);
   if(op==10||op==13)compute_cycles[p]+=cycle-mark;
   held=cmd_result[p*128+:128];
   repeat(2)begin @(negedge clk);if(!cmd_done[p]||cmd_result[p*128+:128]!==held)$fatal(1,"equal pair command ACK unstable");end
   got=held;commands[p]++;cmd_take[p]=1;@(negedge clk);cmd_take[p]=0;
  end
 endtask
 task automatic compute(input integer p);
  logic [127:0] got;logic [63:0] desc;longint signed want;
  begin
   load(p);
   if(CONTEXTS==0)begin
    desc=0;desc[0]=aw;desc[1]=bw;desc[2]=1;desc[7:4]=4'(lastk);desc[11:8]=8;desc[14:12]=3'(ntiles);desc[18:15]=4'(nrows);
    command(p,10,0,desc,got);
   end
   for(integer row=0;row<nrows;row++)begin
    if(CONTEXTS!=0)begin
     desc=0;desc[0]=aw;desc[1]=bw;desc[2]=1;desc[3]=1;desc[7:4]=4'(lastk);desc[11:8]=8;desc[14:12]=3'(ntiles);
     desc[17:15]=3'(row);desc[49:34]=16'(scenario);command(p,13,row,desc,got);
    end
    for(integer pair_id=0;pair_id<4;pair_id++)begin
     command(p,3,row*8+pair_id,0,got);
     for(integer lane=0;lane<2;lane++)begin
      want=expected(p,row,pair_id*2+lane);
      if($signed(got[lane*64+:64])!==want)$fatal(1,"equal pair scalar mismatch p=%0d case=%0d row=%0d col=%0d",p,scenario,row,pair_id*2+lane);
      numeric[p]++;checksum[p]+=$signed(got[lane*64+:64]);
     end
    end
    if(CONTEXTS!=0)command(p,14,row,64'(scenario)<<1,got);
   end
  end
 endtask
 initial begin
  integer mark,compute_mark,init_cycles;
  if($value$plusargs("SEED=%d",seed))begin end
  repeat(4)@(negedge clk);cold_reset=0;reset=0;
  for(integer fmt=0;fmt<4;fmt++)for(integer ri=0;ri<4;ri++)for(integer nt=1;nt<=4;nt++)begin
   scenario=fmt*16+ri*4+nt-1;aw=1'(fmt/2);bw=1'(fmt%2);nrows=ri==0?1:ri==1?3:ri==2?7:8;ntiles=nt;lastk=scenario%8+1;base=scenario%4;
   for(integer p=0;p<2;p++)begin numeric[p]=0;commands[p]=0;load_cycles[p]=0;compute_cycles[p]=0;shared_words[p]=0;shared_beats[p]=0;first_a[p]=-1;last_a[p]=-1;checksum[p]=0;end
   mark=cycle;initialize_pool();both(0);init_cycles=cycle-mark;compute_mark=cycle;both(1);
   if(shared_words[0]!=nrows*ntiles||shared_words[1]!=nrows*ntiles||numeric[0]!=nrows*8||numeric[1]!=nrows*8)$fatal(1,"equal pair work conservation");
   $display("A32_PAIR_MEASURE scenario=%0d words=%0d contexts=%0d Awide=%0d Bwide=%0d rows=%0d tiles=%0d lastk=%0d base=%0d cycles=%0d initialization_cycles=%0d processing_cycles=%0d load_cycles=%0d compute_cycles=%0d feed_span_cycles=%0d a_words=%0d a_beats=%0d commands=%0d numeric=%0d checksum0=%0d checksum1=%0d",scenario,WORDS,CONTEXTS,int'(aw),int'(bw),nrows,ntiles,lastk,base,cycle-mark,init_cycles,cycle-compute_mark,load_cycles[0]+load_cycles[1],compute_cycles[0]+compute_cycles[1],last_a[0]-first_a[0]+1+last_a[1]-first_a[1]+1,shared_words[0]+shared_words[1],shared_beats[0]+shared_beats[1],commands[0]+commands[1],numeric[0]+numeric[1],checksum[0],checksum[1]);
   total_numeric+=numeric[0]+numeric[1];scenarios++;config_pool(2,0);
  end
  if(scenarios!=64||total_numeric!=4864)$fatal(1,"equal pair coverage");
  $display("A32_PAIR_PASS scenarios=%0d numeric=%0d seed=%0d",scenarios,total_numeric,seed);$finish;
 end
endmodule
