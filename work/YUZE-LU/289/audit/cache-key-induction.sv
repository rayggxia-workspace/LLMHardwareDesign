// Abstract exact scheduling for the cached-address validity invariant.
// allocate_req/ack_clear/finish_req over-approximate their real predicates.
// cfg includes every captured variable read by addr(): f,cols,aa,bb,ast,bst,cst,a_words.
module cache_key_induction(
 input reset,active,report,start,allocate_req,ack_clear,ack_slot,finish_req,
 input [1:0] pv,
 input [8:0] pi0,pi1,allocated_words,
 input [251:0] cfg,newcfg,
 input [260:0] key0,key1,
 output bad_induction,bad_reset
);
reg na;reg [1:0] npv;reg [8:0] np0,np1;reg [251:0] ncfg;reg [260:0] nk0,nk1;
wire ready=!reset&&!active&&!report;
wire pre=(!( |pv )||active)&&(!pv[0]||key0=={cfg,pi0})&&(!pv[1]||key1=={cfg,pi1});
always @* begin
 na=active;npv=pv;np0=pi0;np1=pi1;ncfg=cfg;nk0=key0;nk1=key1;
 if(reset)begin na=0;npv=0;np0=0;np1=0;ncfg=0;nk0=0;nk1=0;end
 else begin
  if(start&&ready)begin na=1;npv=0;ncfg=newcfg;end
  if(active&&allocate_req&&pv!=3)begin
   if(!pv[0])begin npv[0]=1;np0=allocated_words;nk0={cfg,allocated_words};end
   else begin npv[1]=1;np1=allocated_words;nk1={cfg,allocated_words};end
  end
  if(ack_clear)npv[ack_slot]=0;
  if(active&&finish_req)begin na=0;npv=0;end
 end
end
wire post=(!( |npv )||na)&&(!npv[0]||nk0=={ncfg,np0})&&(!npv[1]||nk1=={ncfg,np1});
assign bad_induction=pre&&!post;
assign bad_reset=reset&&!post;
endmodule
