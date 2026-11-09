`timescale 1ns/1ps
// Candidate transport boundary only. Both stores and stored_link are frozen
// sources. This fixture has no P/U local controllers or physical top-level.
module tb_resident_transport;
 reg clk=0,reset=1,start=0,reserved=0,offer_pause=0,ack_pause=0;
 always #5 clk=~clk;
 reg host=1,hwrite=0,hvalid=0,htake=0,hstore=0;
 reg[9:0] haddress=0,source_address=0,destination_address=0;
 reg[127:0] hdata=0;
 wire ready,done,tx_req,tx_ready,tx_valid,tx_take,rx_valid,rx_ready,rx_stored,rx_stored_ready;
 wire[9:0] tx_address,rx_address;
 wire[127:0] tx_data,rx_data;
 wire[1:0] sready,svalid,stake,sreq,swrite;
 wire[19:0] saddress;wire[255:0] sdata,sresult;
 assign sreq[0]=host ? (hvalid && !hstore) : tx_req;
 assign sreq[1]=host ? (hvalid && hstore) : (rx_valid && !offer_pause);
 assign swrite[0]=host && hwrite;assign swrite[1]=host ? hwrite : 1'b1;
 assign saddress=host ? {haddress,haddress} : {rx_address,tx_address};
 assign sdata=host ? {hdata,hdata} : {rx_data,128'b0};
 assign stake[0]=host ? (htake && !hstore) : tx_take;
 assign stake[1]=host ? (htake && hstore) : (rx_stored_ready && !ack_pause);
 assign tx_ready=sready[0];assign tx_valid=svalid[0];assign tx_data=sresult[127:0];
 assign rx_ready=sready[1] && !offer_pause;
 // Negative control corrupts the ACK source, not the observer verdict.
 assign rx_stored=fault!=0 ? 1'b1 : (svalid[1] && !ack_pause);
 stored_link link(.clk,.reset,.start,.ready,.source_addr(source_address),.destination_addr(destination_address),
  .done,.tx_req,.tx_ready,.tx_addr(tx_address),.tx_valid,.tx_take,.tx_data,
  .rx_valid,.rx_ready,.rx_addr(rx_address),.rx_data,.rx_stored,.rx_stored_ready,.sink_reserved(reserved));
 for(genvar side=0;side<2;side=side+1)begin: side
  local_s_base store(.clk,.reset,.req_valid(sreq[side]),.req_write(swrite[side]),
   .req_addr(saddress[side*10+:10]),.req_data(sdata[side*128+:128]),
   .req_ready(sready[side]),.rsp_valid(svalid[side]),.rsp_ready(stake[side]),.rsp_data(sresult[side*128+:128]));
  for(genvar bank=0;bank<4;bank=bank+1)begin: bank
   defparam store.storage.banks[bank].memory.VERBOSE=0;
   initial begin : initialize
    integer mode,i;
    if(!$value$plusargs("INIT=%d",mode)) mode=0;
    for(i=0;i<256;i=i+1)
     if(mode==1)store.storage.banks[bank].memory.mem[i]=128'b0;
     else if(mode==2)store.storage.banks[bank].memory.mem[i]=~128'b0;
   end
  end
 end
 integer cycle=0,transfers=0,commits=0,releases=0,minimum=1000000,maximum=0;
 integer fault=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!reset && !host)begin
   if(tx_take && !(svalid[1] && stake[1]))$fatal(1,"source release before destination ACK");
   if(done && (ack_pause || !svalid[1]))$fatal(1,"fabricated transfer done");
   if(tx_take)releases=releases+1;
   if(svalid[1] && stake[1])commits=commits+1;
  end
 end
 task access(input integer side_id,input integer wr,input integer address,input[127:0] data,output[127:0] value);
  @(negedge clk);host=1;hstore=side_id;hwrite=wr;haddress=address;hdata=data;hvalid=1;
  @(posedge clk);while(!sready[side_id])@(posedge clk);
  @(negedge clk);hvalid=0;
  while(!svalid[side_id])@(negedge clk);
  value=sresult[side_id*128+:128];htake=1;
  @(negedge clk);htake=0;
 endtask
 task transfer(input integer src,input integer dst,input integer wait_reservation,input integer wait_offer,input integer wait_ack,input[127:0] expected);
  integer begin_cycle,i,span;reg[127:0] held,observed;
  @(negedge clk);host=0;reserved=0;offer_pause=1;ack_pause=1;
  source_address=src;destination_address=dst;start=1;begin_cycle=cycle+1;
  @(posedge clk);if(!ready)$fatal(1,"transport start busy");
  @(negedge clk);start=0;
  for(i=0;i<wait_reservation;i=i+1)begin
   if(rx_valid || done || tx_take)$fatal(1,"unreserved destination admitted");
   @(negedge clk);
  end
  reserved=1;
  while(!rx_valid)@(negedge clk);held=rx_data;
  for(i=0;i<wait_offer;i=i+1)begin
   if(!rx_valid || rx_data!==held || tx_take || done)$fatal(1,"offer holding differs");
   @(negedge clk);
  end
  offer_pause=0;
  @(posedge clk);while(!(rx_valid && rx_ready))@(posedge clk);
  @(negedge clk);
  while(!svalid[1])@(negedge clk);
  for(i=0;i<wait_ack;i=i+1)begin
   if(!tx_valid || tx_data!==held || tx_take || done)$fatal(1,"source released during ACK stall");
   @(negedge clk);
  end
  ack_pause=0;
  @(posedge clk);while(!done)@(posedge clk);
  @(negedge clk);span=cycle-begin_cycle+1;host=1;reserved=0;transfers=transfers+1;
  access(1,0,dst,0,observed);if(observed!==expected)$fatal(1,"destination SRAM value differs");
  access(0,0,src,0,observed);if(observed!==expected)$fatal(1,"source SRAM value changed");
  if(wait_reservation==0 && wait_offer==0 && wait_ack==0)begin
   if(span<minimum)minimum=span;if(span>maximum)maximum=span;
  end
  $display("TRANSFER src=%0d dst=%0d reserve=%0d offer=%0d ack=%0d slots=%0d",src,dst,wait_reservation,wait_offer,wait_ack,span);
 endtask
 integer i,src,dst;reg[127:0] word,unused;
 initial begin
  if(!$value$plusargs("FAULT=%d",fault))fault=0;
  repeat(3)@(negedge clk);reset=0;
  for(i=0;i<32;i=i+1)begin
   src=(i*33)%1024;dst=1023-src;
   word={32'h89abcdef^i,32'h76543210+i,32'hffffffff-i,32'h80000000+i};
   access(0,1,src,word,unused);
   transfer(src,dst,0,0,0,word);
   transfer(src,dst,3+i%5,2+i%3,4+i%7,word);
  end
  if(transfers!=64 || commits!=64 || releases!=64 || minimum!=maximum)$fatal(1,"transport completion/profile counts differ");
  $display("PASS candidate_transport transfers=%0d commits=%0d releases=%0d min_slots=%0d max_slots=%0d",transfers,commits,releases,minimum,maximum);
  $finish;
 end
 initial begin #1000000;$fatal(1,"transport watchdog");end
endmodule
