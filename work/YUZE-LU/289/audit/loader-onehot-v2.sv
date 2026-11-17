// Generic strided S32 -> explicitly allocated SRAM tile. Two DMA owners and
// two 128-bit packing slots; no arithmetic macro or hidden storage macro.
module e32_tiled_dot_loader(
 input wire clk,reset,start,cancel,clear_cache,
 output wire ready,done,output reg failed,
 input wire [31:0] session,
 input wire [15:0] first,elements,tile_k,
 input wire [2:0] columns,
 input wire [63:0] a_base,b_base,
 input wire [31:0] a_stride,b_k_stride,b_column_stride,
 input wire [9:0] destination,
 output wire rd_valid,input wire rd_ready,output wire [63:0] rd_address,rd_tag,
 input wire rsp_valid,output wire rsp_ready,input wire [63:0] rsp_tag,
 input wire [511:0] rsp_data,input wire rsp_error,
 output wire s_valid,input wire s_ready,output wire [9:0] s_address,
 output wire [127:0] s_data,output wire s_slot,
 input wire ack_valid,ack_slot,ack_error,
 output wire [1:0] dma_pending,
 output reg [31:0] read_bytes
);
 reg active,report,stopped;
 reg [15:0] f,n,tk;
 reg [2:0] cols;
 reg [63:0] aa,bb;reg [31:0] ast,bst,cst,epoch,serial;
 reg [9:0] dest;
 reg [8:0] a_words,total_words,allocated_words,write_words,committed;
 reg [1:0] pv,pwriting;
 reg [8:0] pi[0:1];
 reg [127:0] pd[0:1];
 reg [3:0] pm[0:1];
 reg [4:0] cv;
 reg [63:0] ca[0:4];reg [511:0] cd[0:4];
 reg [1:0] pending;
 reg [63:0] tags[0:1],lines[0:1];reg [2:0] caches[0:1];
 reg offer,offer_slot;reg [63:0] offer_address,offer_tag;reg [2:0] offer_cache;
 reg write_held;
 wire stop=stopped||cancel||failed;
 wire m0=pending[0]&&rsp_tag==tags[0],m1=pending[1]&&rsp_tag==tags[1];
 wire match=m0||m1;wire response_slot=m1;
 wire rf=rd_valid&&rd_ready;
 wire sf=s_valid&&s_ready;
 wire chosen_write=(pv[0]&&pi[0]==write_words)?1'b0:1'b1;
 assign ready=!reset&&!active&&!report;
 assign done=!reset&&report;
 assign dma_pending=pending;
 assign rd_valid=!reset&&active&&offer;
 assign rd_address=offer_address;assign rd_tag=offer_tag;
 assign rsp_ready=!reset&&active;
 assign s_valid=!reset&&active&&(write_held||!stop)&&pv[chosen_write]&&
   pi[chosen_write]==write_words&&pm[chosen_write]==15&&!pwriting[chosen_write];
 assign s_address=dest+{1'b0,pi[chosen_write]};assign s_data=pd[chosen_write];assign s_slot=chosen_write;
 function automatic [10:0] flat(input [8:0] word_index,input [1:0] lane);
  flat=(11'(word_index)-11'(a_words))*4+11'(lane);
 endfunction
 function automatic [10:0] div3_exact(input [10:0] index);
  reg [20:0] product;
  begin product=index*21'd683;div3_exact={1'b0,product[20:11]};end
 endfunction
 function automatic [2:0] mod3_exact(input [10:0] index);
  reg [10:0] q,r;
  begin q=div3_exact(index);r=index-(q+(q<<1));mod3_exact=r[2:0];end
 endfunction
 function automatic [10:0] row_of(input [10:0] index);
  case(cols)1:row_of=index;2:row_of=index>>1;3:row_of=div3_exact(index);default:row_of=index>>2;endcase
 endfunction
 function automatic [2:0] col_of(input [10:0] index);
  case(cols)1:col_of=0;2:col_of={2'd0,index[0]};3:col_of=mod3_exact(index);default:col_of={1'b0,index[1:0]};endcase
 endfunction
 function automatic [63:0] addr(input [8:0] word_index,input [1:0] lane);
  begin
   if(word_index<a_words)addr=aa+({48'd0,f}+64'(word_index)*4+64'(lane))*ast;
   else addr=bb+({48'd0,f}*{32'd0,bst})+({53'd0,row_of(flat(word_index,lane))}*{32'd0,bst})+({61'd0,col_of(flat(word_index,lane))}*{32'd0,cst});
  end
 endfunction
 function automatic is_pad(input [8:0] word_index,input [1:0] lane);
  begin
   if(word_index<a_words)is_pad=16'(word_index)*4+16'(lane)>=n;
   else is_pad=(16'(word_index)-16'(a_words))*4+16'(lane)>=n*cols;
  end
 endfunction
 function automatic [2:0] cache_index(input [8:0] word_index,input [1:0] lane);
  cache_index=word_index<a_words?0:3'(1+col_of(flat(word_index,lane)));
 endfunction
 // Search only finite packing slots. Pending same-line requests are coalesced:
 // one real response fills every currently owned operand from that line.
 reg candidate,hit,pad,waiting,cp,free_owner;reg [1:0] cl;
 reg [2:0] cc,hc;reg [63:0] address;
 reg [7:0] lane_winner,lane_selected;
 reg [76:0] lane_result[0:7];
 reg [63:0] lane_address[0:7];
 reg [7:0] lane_exam,lane_hit,lane_pad,lane_wait,lane_eligible;
 reg [2:0] lane_hc[0:7],lane_cc[0:7];
 always @* begin
  for(integer j=0;j<8;j=j+1)begin
   lane_address[j]=addr(pi[j/4],2'(j%4));
   lane_exam[j]=pv[j/4]&&!pwriting[j/4]&&!pm[j/4][j%4];
   lane_wait[j]=(pending[0]&&lines[0]=={lane_address[j][63:6],6'd0})||
      (pending[1]&&lines[1]=={lane_address[j][63:6],6'd0})||
      (offer&&offer_address=={lane_address[j][63:6],6'd0});
   lane_hit[j]=0;lane_hc[j]=0;
   for(integer c=0;c<5;c=c+1)
    if(!lane_hit[j]&&cv[c]&&ca[c]=={lane_address[j][63:6],6'd0})begin
     lane_hit[j]=1;lane_hc[j]=3'(c);
    end
   lane_pad[j]=is_pad(pi[j/4],2'(j%4));
   lane_cc[j]=cache_index(pi[j/4],2'(j%4));
   lane_eligible[j]=lane_exam[j]&&(lane_pad[j]||lane_hit[j]||(!lane_wait[j]&&pending!=3&&!offer));
  end
  for(integer j=0;j<8;j=j+1)begin
   lane_winner[j]=lane_eligible[j]&&!(|(lane_eligible & 8'((9'd1<<j)-1)));
   lane_selected[j]=lane_winner[j]||((!(|lane_eligible))&&lane_exam[j]&&!(|(lane_exam & (8'hff << (j+1)))));
   lane_result[j]={lane_winner[j],
      lane_hit[j]&lane_selected[j],lane_pad[j]&lane_selected[j],lane_wait[j]&lane_selected[j],
      1'(j/4)&lane_winner[j],2'(j%4)&{2{lane_winner[j]}},
      lane_cc[j]&{3{lane_winner[j]}},lane_hc[j]&{3{lane_selected[j]}},
      lane_address[j]&{64{lane_selected[j]}}};
  end
  {candidate,hit,pad,waiting,cp,cl,cc,hc,address}=
     ((lane_result[0]|lane_result[1])|(lane_result[2]|lane_result[3]))|
     ((lane_result[4]|lane_result[5])|(lane_result[6]|lane_result[7]));
  free_owner=!pending[0]?0:1;
 end
 always @(posedge clk)begin
  if(reset)begin
   active<=0;report<=0;failed<=0;stopped<=0;pv<=0;pwriting<=0;pending<=0;offer<=0;write_held<=0;cv<=0;
   allocated_words<=0;write_words<=0;committed<=0;read_bytes<=0;serial<=0;
   f<=0;n<=0;tk<=0;cols<=0;aa<=0;bb<=0;ast<=0;bst<=0;cst<=0;epoch<=0;dest<=0;a_words<=0;total_words<=0;
   offer_slot<=0;offer_address<=0;offer_tag<=0;offer_cache<=0;
   for(integer p=0;p<2;p=p+1)begin pi[p]<=0;pd[p]<=0;pm[p]<=0;tags[p]<=0;lines[p]<=0;caches[p]<=0;end
   for(integer c=0;c<5;c=c+1)begin ca[c]<=0;cd[c]<=0;end
  end else begin
   report<=0;
   if(start&&ready)begin
    active<=1;failed<=0;stopped<=cancel;pv<=0;pwriting<=0;pending<=0;offer<=0;write_held<=0;
    f<=first;n<=elements;tk<=tile_k;cols<=columns;aa<=a_base;bb<=b_base;ast<=a_stride;bst<=b_k_stride;cst<=b_column_stride;
    dest<=destination;epoch<=session;serial<=0;read_bytes<=0;
    a_words<=9'((tile_k+3)>>2);total_words<=9'(((tile_k+3)>>2)+((tile_k*columns+3)>>2));
    allocated_words<=0;write_words<=0;committed<=0;if(clear_cache)cv<=0;
   end
   if(active&&cancel)stopped<=1;
   if(active&&!stop&&allocated_words<total_words&&pv!=3)begin
    pv[!pv[0]?0:1]<=1;pi[!pv[0]?0:1]<=allocated_words;pd[!pv[0]?0:1]<=0;pm[!pv[0]?0:1]<=0;
    pwriting[!pv[0]?0:1]<=0;allocated_words<=allocated_words+1;
   end
   // Do not conflict with the multi-operand response deposit in this cycle.
   if(active&&!stop&&candidate&&!rsp_valid)begin
    if(pad||hit)begin
     pd[cp][32*cl+:32]<=pad?32'd0:cd[hc][32*address[5:2]+:32];pm[cp][cl]<=1;
    end else begin offer<=1;offer_slot<=free_owner;offer_address<={address[63:6],6'd0};
     offer_tag<={epoch,serial};offer_cache<=cc;serial<=serial+1;end
   end
   if(rf)begin offer<=0;pending[offer_slot]<=1;tags[offer_slot]<=offer_tag;lines[offer_slot]<=offer_address;caches[offer_slot]<=offer_cache;end
   if(rsp_valid&&rsp_ready)begin
    if(!match)failed<=1;
    else begin
     pending[response_slot]<=0;read_bytes<=read_bytes+64;
     if(rsp_error)failed<=1;
     else if(!stop)begin
      cv[caches[response_slot]]<=1;ca[caches[response_slot]]<=lines[response_slot];cd[caches[response_slot]]<=rsp_data;
      for(integer p=0;p<2;p=p+1)for(integer l=0;l<4;l=l+1)
       if(pv[p]&&!pwriting[p]&&!is_pad(pi[p],2'(l))&&((addr(pi[p],2'(l))>>6)==(lines[response_slot]>>6)))begin
        pd[p][32*l+:32]<=rsp_data[32*((addr(pi[p],2'(l))>>2)&15)+:32];pm[p][l]<=1;
       end
     end
    end
   end
   if(s_valid)write_held<=!s_ready;
   if(sf)begin pwriting[chosen_write]<=1;write_words<=write_words+1;end
   if(ack_valid)begin
    if(!pwriting[ack_slot])failed<=1;
    else begin pv[ack_slot]<=0;pwriting[ack_slot]<=0;committed<=committed+1;if(ack_error)failed<=1;end
   end
   if(active&&!offer&&!write_held&&pending==0&&pwriting==0&&
     (stop||committed==total_words))begin active<=0;report<=1;pv<=0;end
  end
 end
endmodule
