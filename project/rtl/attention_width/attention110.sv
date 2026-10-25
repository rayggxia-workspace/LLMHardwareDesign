// Issue102 bounded complete8-head GQA. Three score passes, then PV; NOT online.
// Q8, K/V symmetricS16, QK/PV checkedI32, expQ30, P15. One physical8S8 bank.
module attention110 #(parameter STYLE=0)(input wire clk,reset,start,ack,input wire [10:0] length,
 input wire [63:0] query_units,input wire signed [7:0] key_unit,input wire [31:0] key_address,value_address,score_multiplier,
 output wire done,output reg [7:0] status,output wire [7:0] debug_state,
 output wire ereq,output wire [31:0] eaddr,input wire eready,evalid,output wire etake,input wire [127:0] edata,
 output wire sreq,swr,output wire [9:0] saddr,output wire [127:0] sdata,input wire sready,svalid,output wire stake,input wire [127:0] sdout,
 output wire mreq,output wire signed [31:0] ma,mb,input wire mready,mvalid,output wire mtake,input wire signed [63:0] mvalue,
 output wire freq,output wire [127:0] fa,fb,input wire fready,fvalid,output wire ftake,input wire [127:0] fvalue,fremainder,input wire ferror,
 output reg [63:0] cycles,output reg [31:0] macs,sreads,swrites,kloads,vloads,lut_reads,divides,score_products,
 output reg obs_valid,output reg [1:0] obs_kind,output reg [2:0] obs_head,output reg [10:0] obs_key,
 output reg signed [31:0] obs_x,obs_y,output reg [63:0] obs_sum,
 output wire [63:0] byte_a,byte_b,input wire [127:0] byte_p);
 localparam IDLE=0,LOAD=1,LWAIT=2,LSTORE=3,LSWAIT=4,QREAD=6,QWAIT=7,KREAD=8,KWAIT=9,DOT=10,
 MREQ=11,MWAIT=12,SCALE=13,SWRITE=14,SWWAIT=15,NEXTKEY=16,SUMINIT=17,SMREAD=18,SMWAIT=19,
 EVAL=20,EREAD=21,EWAIT=22,EXP=23,DREQ=24,DWAIT=25,PROB=26,PWRITE=27,PWWAIT=28,NEXTSM=29,
 GUARD=30,PVINIT=31,OREAD=32,ORWAIT=33,PREAD=34,PRWAIT=35,VREAD=36,VRWAIT=37,PMAC=38,
 PNEXT=39,OWRITE=40,OWWAIT=41,NEXTGROUP=42,DONE=44;
 reg [7:0] state;reg [2:0] head;reg [10:0] key,tile;reg [8:0] loadline;reg loading_v,pass_p,half;
 reg [3:0] dim,group;reg [1:0] limb,plimb,vlimb;reg [11:0] lutindex;
 reg [127:0] qline,kvline,loadbuf,scoreline,probline,preadline;
 reg signed [31:0] accum,maximum;reg signed [31:0] vacc[0:7];reg signed [63:0] product;
 reg [31:0] expcode,psum;reg [63:0] total;reg [15:0] probability,pcode;
 wire [10:0] remain=length-tile;wire [4:0] tilekeys=remain>=16?5'd16:remain[4:0];
 wire [8:0] tilelines={tilekeys,4'b0};wire [10:0] localkey=key-tile;
 wire signed [7:0] qe=$signed(query_units[8*head+:8]);
 wire signed [10:0] rshift=11'sd18-$signed({{3{qe[7]}},qe})-$signed({{3{key_unit[7]}},key_unit});
 function signed [7:0] digit16(input signed [15:0] x,input [1:0] which);
  reg signed [31:0] rest,d;integer n;begin rest=x;d=0;for(n=0;n<3;n=n+1)begin d=$signed({1'b0,rest[6:0]});if(d>=64)d=d-128;if(n==which)digit16=d[7:0];rest=(rest-d)>>>7;end end
 endfunction
 function [4:0] shift7(input [2:0] v);begin case(v)0:shift7=0;1:shift7=7;2:shift7=14;3:shift7=21;default:shift7=28;endcase end endfunction
 wire signed [7:0] aa[0:7],bb[0:7];wire signed [15:0] pp[0:7];genvar g;
 generate for(g=0;g<8;g=g+1)begin:BYTE
  assign aa[g]=state==PMAC?$signed((pcode>>(shift7({1'b0,plimb})))&16'd127):$signed(qline[(dim[0]?64:0)+8*g+:8]);
  assign bb[g]=digit16($signed(kvline[16*g+:16]),state==PMAC?vlimb:limb);
  assign byte_a[8*g+:8]=aa[g];assign byte_b[8*g+:8]=bb[g];assign pp[g]=$signed(byte_p[16*g+:16]);
 end endgenerate
 wire signed [31:0] part={{16{pp[0][15]}},pp[0]}+{{16{pp[1][15]}},pp[1]}+{{16{pp[2][15]}},pp[2]}+{{16{pp[3][15]}},pp[3]}+{{16{pp[4][15]}},pp[4]}+{{16{pp[5][15]}},pp[5]}+{{16{pp[6][15]}},pp[6]}+{{16{pp[7][15]}},pp[7]};
 localparam QK_W=STYLE==2?34:64,PV_W=STYLE==2?45:64;
 wire signed [QK_W-1:0] qkpart={{(QK_W-32){part[31]}},part};
 wire signed [QK_W-1:0] qkshift=STYLE==0?(qkpart<<<shift7({1'b0,limb})):
 limb==0?qkpart:limb==1?(qkpart<<<7):limb==2?(qkpart<<<14):(qkpart<<<21);
 wire signed [QK_W-1:0] qknext=$signed({{(QK_W-32){accum[31]}},accum})+qkshift;
 wire signed [63:0] dotnext={{(64-QK_W){qknext[QK_W-1]}},qknext};
 wire signed [63:0] pvnext[0:7];wire [7:0] pvbad;
 generate for(g=0;g<8;g=g+1)begin:ADD
  wire [2:0] shifts=plimb+{1'b0,vlimb};
  wire signed [PV_W-1:0] pvpart={{(PV_W-16){pp[g][15]}},pp[g]};
  wire signed [PV_W-1:0] pvshift=STYLE==0?(pvpart<<<shift7(shifts)):
   shifts==0?pvpart:shifts==1?(pvpart<<<7):shifts==2?(pvpart<<<14):shifts==3?(pvpart<<<21):(pvpart<<<28);
  wire signed [PV_W-1:0] pvsum=$signed({{(PV_W-32){vacc[g][31]}},vacc[g]})+pvshift;
  assign pvnext[g]={{(64-PV_W){pvsum[PV_W-1]}},pvsum};
  assign pvbad[g]=pvnext[g]>64'sd2147483647||pvnext[g]< -64'sd2147483648;
 end endgenerate
 reg [63:0] mag,rounded,rem,halfway;reg signed [63:0] converted;reg conversion_bad;reg [10:0] leftshift;
 always @* begin
  mag=product[63]?-product:product;rounded=mag;rem=0;halfway=0;converted=product;conversion_bad=0;leftshift=0;
  if(rshift< -63||rshift>63)conversion_bad=1;
  else if(rshift>0)begin rounded=mag>>rshift;rem=mag-(rounded<<rshift);halfway=64'd1<<(rshift-1);if(rem>halfway||(rem==halfway&&rounded[0]))rounded=rounded+1;converted=product[63]?-$signed(rounded):$signed(rounded);end
  else if(rshift<0)begin leftshift=-rshift;if(leftshift>31)begin if(mag!=0)conversion_bad=1;converted=0;end
   else begin if(mag>((product[63]?64'd2147483648:64'd2147483647)>>leftshift))conversion_bad=1;converted=product<<<leftshift;end end
  if(converted>64'sd2147483647||converted< -64'sd2147483648)conversion_bad=1;
 end
 reg bad_q,bad_k;integer z;always @* begin bad_q=0;bad_k=0;for(z=0;z<16;z=z+1)if(sdout[8*z+:8]==8'h80)bad_q=1;for(z=0;z<8;z=z+1)if(sdout[16*z+:16]==16'h8000)bad_k=1;end
 wire signed [31:0] score=$signed(scoreline[32*key[1:0]+:32]);
 wire signed [32:0] distance=$signed({maximum[31],maximum})-$signed({score[31],score});
 wire [32:0] idxbase=$unsigned(distance)>>5;wire idxup=distance[4:0]>16||(distance[4:0]==16&&idxbase[0]);
 wire [127:0] complement=fb-fremainder;wire [127:0] rounded_div=fvalue+((fremainder>complement||(fremainder==complement&&fvalue[0]))?128'd1:128'd0);
 assign done=state==DONE;assign debug_state=state;
 assign ereq=state==LOAD||state==EREAD;assign eaddr=state==LOAD?(loading_v?value_address:key_address)+({21'b0,tile}<<8)+({23'b0,loadline}<<4):32'h02012010+({20'b0,lutindex[11:2],2'b0}<<2);
 assign etake=state==LWAIT||state==EWAIT;
 assign sreq=state==LSTORE||state==QREAD||state==KREAD||state==SWRITE||state==SMREAD||state==PWRITE||state==OREAD||state==PREAD||state==VREAD||state==OWRITE;
 assign swr=state==LSTORE||state==SWRITE||state==PWRITE||state==OWRITE;
 assign saddr=state==LSTORE?10'd476+loadline:state==QREAD?{4'b0,head,3'b0}+{7'b0,dim[3:1]}:
  state==KREAD?10'd476+{localkey[3:0],4'b0}+dim:state==SWRITE||state==SMREAD?10'd80+key[10:2]:
  state==PWRITE||state==PREAD?10'd344+key[10:3]:state==VREAD?10'd476+{localkey[3:0],4'b0}+group:
  10'd732+{2'b0,head,5'b0}+{5'b0,group,1'b0}+half;
 assign sdata=state==LSTORE?loadbuf:state==SWRITE?scoreline:state==PWRITE?probline:
  half?{vacc[7],vacc[6],vacc[5],vacc[4]}:{vacc[3],vacc[2],vacc[1],vacc[0]};
 assign stake=state==LSWAIT||state==QWAIT||state==KWAIT||state==SWWAIT||state==SMWAIT||state==PWWAIT||state==ORWAIT||state==PRWAIT||state==VRWAIT||state==OWWAIT;
 assign mreq=state==MREQ;assign ma=accum;assign mb=$signed(score_multiplier);assign mtake=state==MWAIT;
 assign freq=state==DREQ;assign fa={81'b0,expcode,15'b0};assign fb={64'b0,total};assign ftake=state==DWAIT;
 integer j;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;status<=0;head<=0;key<=0;tile<=0;loadline<=0;loading_v<=0;pass_p<=0;half<=0;dim<=0;group<=0;limb<=0;plimb<=0;vlimb<=0;lutindex<=0;
   qline<=0;kvline<=0;loadbuf<=0;scoreline<=0;probline<=0;preadline<=0;accum<=0;maximum<=32'sh80000000;product<=0;expcode<=0;psum<=0;total<=0;probability<=0;pcode<=0;
   cycles<=0;macs<=0;sreads<=0;swrites<=0;kloads<=0;vloads<=0;lut_reads<=0;divides<=0;score_products<=0;obs_valid<=0;obs_kind<=0;obs_head<=0;obs_key<=0;obs_x<=0;obs_y<=0;obs_sum<=0;for(j=0;j<8;j=j+1)vacc[j]<=0;
  end else begin
   obs_valid<=0;if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
   if(sreq&&sready)begin if(swr)swrites<=swrites+1;else sreads<=sreads+1;end
   if(ereq&&eready)begin if(state==EREAD)lut_reads<=lut_reads+1;else if(loading_v)vloads<=vloads+1;else kloads<=kloads+1;end
   case(state)
    IDLE:if(start)begin state<=LOAD;status<=0;head<=0;key<=0;tile<=0;loadline<=0;loading_v<=0;pass_p<=0;half<=0;dim<=0;group<=0;limb<=0;plimb<=0;vlimb<=0;accum<=0;maximum<=32'sh80000000;scoreline<=0;probline<=0;total<=0;psum<=0;
     cycles<=0;macs<=0;sreads<=0;swrites<=0;kloads<=0;vloads<=0;lut_reads<=0;divides<=0;score_products<=0;
    end
    LOAD:if(eready)state<=LWAIT;
    LWAIT:if(evalid)begin loadbuf<=edata;state<=LSTORE;end
    LSTORE:if(sready)state<=LSWAIT;
    LSWAIT:if(svalid)begin if(loadline+1==tilelines)begin key<=tile;if(loading_v)begin group<=0;half<=0;for(j=0;j<8;j=j+1)vacc[j]<=0;state<=tile==0?PREAD:OREAD;end else begin dim<=0;limb<=0;accum<=0;state<=QREAD;end end else begin loadline<=loadline+1;state<=LOAD;end end
    QREAD:if(sready)state<=QWAIT;
    QWAIT:if(svalid)begin if(bad_q)begin status<=30;state<=DONE;end else begin qline<=sdout;state<=KREAD;end end
    KREAD:if(sready)state<=KWAIT;
    KWAIT:if(svalid)begin if(bad_k)begin status<=30;state<=DONE;end else begin kvline<=sdout;limb<=0;state<=DOT;end end
    DOT:begin macs<=macs+8;if(dotnext>64'sd2147483647||dotnext< -64'sd2147483648)begin status<=31;state<=DONE;end
     else begin accum<=dotnext[31:0];if(limb<2)limb<=limb+1;else if(dim==15)state<=MREQ;else begin dim<=dim+1;state<=QREAD;end end end
    MREQ:if(mready)begin score_products<=score_products+1;state<=MWAIT;end
    MWAIT:if(mvalid)begin product<=mvalue;state<=SCALE;end
    SCALE:if(conversion_bad)begin status<=32;state<=DONE;end else begin
     if(converted>maximum)maximum<=converted[31:0];if(key[1:0]==0)scoreline<= {96'b0,converted[31:0]};else scoreline[32*key[1:0]+:32]<=converted[31:0];
     obs_valid<=1;obs_kind<=0;obs_head<=head;obs_key<=key;obs_x<=accum;obs_y<=converted[31:0];obs_sum<=0;
     state<=key[1:0]==3||key+1==length?SWRITE:NEXTKEY;end
    SWRITE:if(sready)state<=SWWAIT;
    SWWAIT:if(svalid)state<=NEXTKEY;
    NEXTKEY:if(key+1==length)state<=SUMINIT;else begin key<=key+1;accum<=0;dim<=0;limb<=0;if(localkey==15)begin tile<=tile+16;loadline<=0;state<=LOAD;end else state<=QREAD;end
    SUMINIT:begin pass_p<=0;key<=0;total<=0;psum<=0;state<=SMREAD;end
    SMREAD:if(sready)state<=SMWAIT;
    SMWAIT:if(svalid)begin scoreline<=sdout;state<=EVAL;end
    EVAL:if(distance<0)begin status<=33;state<=DONE;end else if(distance>65536)begin expcode<=0;state<=EXP;end else begin lutindex<=idxbase[11:0]+idxup;state<=EREAD;end
    EREAD:if(eready)state<=EWAIT;
    EWAIT:if(evalid)begin expcode<=edata[32*lutindex[1:0]+:32];if(edata[32*lutindex[1:0]+:32]==0||edata[32*lutindex[1:0]+:32]>32'h40000000||(lutindex==0&&edata[31:0]!=32'h40000000))begin status<=34;state<=DONE;end else state<=EXP;end
    EXP:if(!pass_p)begin total<=total+expcode;obs_valid<=1;obs_kind<=1;obs_head<=head;obs_key<=key;obs_x<=expcode;obs_y<=maximum;obs_sum<=total+expcode;state<=NEXTSM;end
     else if(expcode==0)begin probability<=0;state<=PROB;end else state<=DREQ;
    DREQ:if(fready)begin divides<=divides+1;state<=DWAIT;end
    DWAIT:if(fvalid)begin if(ferror||rounded_div>32768)begin status<=35;state<=DONE;end else begin probability<=rounded_div>=32767?16'd32767:rounded_div[15:0];state<=PROB;end end
    PROB:begin psum<=psum+probability;if(key[2:0]==0)probline<={112'b0,probability};else probline[16*key[2:0]+:16]<=probability;
     obs_valid<=1;obs_kind<=2;obs_head<=head;obs_key<=key;obs_x<=probability;obs_y<=expcode;obs_sum<=total;state<=key[2:0]==7||key+1==length?PWRITE:NEXTSM;end
    PWRITE:if(sready)state<=PWWAIT;
    PWWAIT:if(svalid)state<=NEXTSM;
    NEXTSM:if(key+1==length)begin if(!pass_p)begin if(total<64'h40000000)begin status<=35;state<=DONE;end else begin pass_p<=1;key<=0;psum<=0;state<=SMREAD;end end else state<=GUARD;end
     else begin key<=key+1;state<=key[1:0]==3?SMREAD:EVAL;end
    GUARD:if(psum>32'd32769+(({21'b0,length}+1)>>1))begin status<=36;state<=DONE;end else state<=PVINIT;
    PVINIT:begin tile<=0;loadline<=0;loading_v<=1;group<=0;half<=0;state<=LOAD;end
    OREAD:if(sready)state<=ORWAIT;
    ORWAIT:if(svalid)begin for(j=0;j<8;j=j+1)if((half&&j>=4)||(!half&&j<4))vacc[j]<=sdout[32*(j%4)+:32];if(!half)begin half<=1;state<=OREAD;end else begin half<=0;state<=PREAD;end end
    PREAD:if(sready)state<=PRWAIT;
    PRWAIT:if(svalid)begin preadline<=sdout;pcode<=sdout[16*key[2:0]+:16];state<=VREAD;end
    VREAD:if(sready)state<=VRWAIT;
    VRWAIT:if(svalid)begin if(bad_k)begin status<=30;state<=DONE;end else begin kvline<=sdout;plimb<=0;vlimb<=0;state<=PMAC;end end
    PMAC:begin macs<=macs+8;if(|pvbad)begin status<=37;state<=DONE;end else begin for(j=0;j<8;j=j+1)vacc[j]<=pvnext[j][31:0];
     if(vlimb<2)vlimb<=vlimb+1;else if(plimb<2)begin plimb<=plimb+1;vlimb<=0;end else state<=PNEXT;end end
    PNEXT:if(localkey+1==tilekeys)begin half<=0;state<=OWRITE;end else begin key<=key+1;pcode<=preadline[16*((key+1)&7)+:16];state<=key[2:0]==7?PREAD:VREAD;end
    OWRITE:if(sready)state<=OWWAIT;
    OWWAIT:if(svalid)begin if(!half)begin half<=1;state<=OWRITE;end else begin half<=0;state<=NEXTGROUP;end end
    NEXTGROUP:if(group<15)begin group<=group+1;key<=tile;for(j=0;j<8;j=j+1)vacc[j]<=0;state<=tile==0?PREAD:OREAD;end
     else if(tile+tilekeys<length)begin tile<=tile+16;loadline<=0;state<=LOAD;end
     else if(head<7)begin head<=head+1;tile<=0;key<=0;loadline<=0;loading_v<=0;maximum<=32'sh80000000;accum<=0;scoreline<=0;pass_p<=0;state<=LOAD;end else state<=DONE;
    DONE:if(ack)state<=IDLE;
    default:begin status<=255;state<=DONE;end
   endcase
  end
 end
endmodule
