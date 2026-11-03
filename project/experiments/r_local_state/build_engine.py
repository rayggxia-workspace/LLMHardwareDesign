from pathlib import Path
P=Path(__file__).resolve().parents[3]; src=(P/'project/experiments/r_architecture/rtl/r_stream.sv').read_text()
src=src.replace('module r_stream #','module r_stream_local #')
src=src.replace('input wire rd_bank,input wire [9:0] rd_index,output wire [127:0] rd_data,','input wire rd_bank,input wire [9:0] rd_index,input wire rd_valid,output wire rd_ready,\n output wire rd_rsp_valid,input wire rd_rsp_ready,output wire [127:0] rd_data,')
src=src.replace('FRESP=8;','FRESP=8,DRAIN=9;')
src=src.replace(' reg signed [31:0] bank0[0:WORDS-1],bank1[0:WORDS-1];','')
start=src.index(' wire signed [31:0] arow');end=src.index(' always @*begin',start)
extra='''
 localparam AW=$clog2(WORDS/8);
 wire [255:0] sr0,sr1;wire srvalid,write_pending;
 wire host_fire=rd_valid&&rd_ready;
 wire compute_read=(phase==PASS)&&(op!=6)&&(issue_row<rows);
 wire load_fire=load_valid&&load_ready;
 wire state_load=load_fire&&(load_target<2);
 wire compute_write=(phase==PASS)&&product_valid&&(op==0||op==2);
 reg [255:0] write_data;reg [7:0] write_mask;
 always @*begin
  write_data=0;write_mask=0;
  if(compute_write)begin
   write_mask=8'hff;
   for(integer l=0;l<8;l=l+1)write_data[32*l+:32]=value[l][31:0];
  end else if(state_load)begin
   if(load_index[0])begin write_data[255:128]=load_data;write_mask=8'hf0;end
   else begin write_data[127:0]=load_data;write_mask=8'h0f;end
  end
 end
 wire store_read=compute_read||host_fire;
 wire [AW-1:0] store_row=compute_read?issue_row[AW-1:0]:rd_index[AW:1];
 r_state_store #(.WORDS(WORDS)) state_store(
  .clk(clk),.reset(reset),.rd_valid(store_read),.rd_row(store_row),
  .out_valid(srvalid),.out_bank0(sr0),.out_bank1(sr1),
  .wr_valid(compute_write||state_load),.wr_bank(compute_write?!role:load_target[0]),
  .wr_row(compute_write?product_row[AW-1:0]:load_index[AW:1]),
  .wr_mask(write_mask),.wr_data(write_data),.write_pending(write_pending));
 reg [3:0] ct,ht,hbank,hhalf;
 reg [8:0] rowtag[0:3];
 reg [127:0] read_fifo[0:3];reg [1:0] rp,wp;reg [2:0] outstanding,available;
 wire host_return=srvalid&&ht[3];
 wire host_take=rd_rsp_valid&&rd_rsp_ready;
 assign rd_rsp_valid=!reset&&(available!=0);
 assign rd_data=read_fifo[rp];
 assign rd_ready=!reset&&(phase==IDLE)&&!cmd_valid&&!load_valid&&!write_pending&&(outstanding<4)&&(rd_index<WORDS/4);
 // Command wins simultaneous command/read requests; read_ready already masks cmd_valid.
 assign cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready)&&!write_pending&&(outstanding==0);
 assign load_ready=cmd_ready&&!cmd_valid;
 always @(posedge clk)begin
  if(reset)begin ct<=0;ht<=0;hbank<=0;hhalf<=0;rp<=0;wp<=0;outstanding<=0;available<=0;end
  else begin
   ct<={ct[2:0],compute_read};ht<={ht[2:0],host_fire};
   hbank<={hbank[2:0],rd_bank};hhalf<={hhalf[2:0],rd_index[0]};
   rowtag[0]<=issue_row;for(integer t=1;t<4;t=t+1)rowtag[t]<=rowtag[t-1];
   case({host_fire,host_take})2'b10:outstanding<=outstanding+1'b1;2'b01:outstanding<=outstanding-1'b1;default:begin end endcase
   case({host_return,host_take})2'b10:available<=available+1'b1;2'b01:available<=available-1'b1;default:begin end endcase
   if(host_take)rp<=rp+1'b1;
   if(host_return)begin
    if(hbank[3])read_fifo[wp]<=hhalf[3]?sr1[255:128]:sr1[127:0];
    else read_fifo[wp]<=hhalf[3]?sr0[255:128]:sr0[127:0];
    wp<=wp+1'b1;
   end
  end
 end
 wire signed [31:0] arow[0:7],brow[0:7];
 for(genvar l=0;l<8;l=l+1)begin
  assign arow[l]=role?$signed(sr1[32*l+:32]):$signed(sr0[32*l+:32]);
  assign brow[l]=role?$signed(sr0[32*l+:32]):$signed(sr1[32*l+:32]);
 end
'''
src=src[:start]+extra+src[end:]
src=src.replace('0,1:if(load_index<WORDS/4)for(i=0;i<4;i=i+1)begin if(load_target==0)bank0[load_index*4+i]<=load_data[32*i+:32];else bank1[load_index*4+i]<=load_data[32*i+:32];end','0,1:begin end // state_store owns state writes')
start=src.index('     if(issue_row<rows)begin');end=src.index('     if(product_valid)begin',start)
src=src[:start]+'''     if(issue_row<rows)issue_row<=issue_row+1'b1;
     if((op==6&&issue_row<rows)||(op!=6&&srvalid&&ct[3]))begin
      operand_valid<=1;operand_row<=op==6?issue_row:rowtag[3];
      for(i=0;i<8;i=i+1)begin
       if(op==0)begin oa[i]<=arow[i];ob[i]<=mode==1?{1'b0,$unsigned(brow[i])}:{1'b0,decay};end
       else if(op==1||op==3)begin oa[i]<=brow[i];ob[i]<=op==1?$signed(key[rowtag[3]]):$signed(query[rowtag[3]]);end
       else if(op==2)begin oa[i]<=update[i];ob[i]<=$signed(key[rowtag[3]]);obase[i]<=brow[i];end
       else begin oa[i]<=issue_row==0?x[i]:hist[(issue_row-1)*8+i];ob[i]<=$signed(taps[issue_row*8+i]);end
      end
     end
'''+src[end:]
src=src.replace('       for(i=0;i<8;i=i+1)begin if(role)bank0[product_row*8+i]<=value[i][31:0];else bank1[product_row*8+i]<=value[i][31:0];end','       // state_store owns the writeback pipeline')
src=src.replace('phase<=IDLE;rsp_valid<=1;rsp_error<=failed||((op==0||op==2)&&bad);','phase<=DRAIN;rsp_error<=failed||((op==0||op==2)&&bad);')
src=src.replace('    EPREP:begin','    DRAIN:if(!write_pending)begin phase<=IDLE;rsp_valid<=1;end\n    EPREP:begin')
(P/'project/rtl/r_local_state/r_stream_local.sv').write_text(src)
