module matrix_probe(
 input wire clk_i,rst_ni,cmd_valid_i,cmd_ready_o,reply_valid_o,reply_ready_i,run_active_o,link_pending_o,
 input wire [3:0] cmd_op_i,input wire [15:0] reply_status_o,input wire [511:0] reply_data_o,
 input wire [2:0] image_valid_o,poison_o,input wire [31:0] commit_count_o,ack_count_o,
 input wire [11:0] life,seq,input wire recovery_enabled,input wire [2:0] recovery_phase,
 input wire [1:0] native_valid,native_ready,response_valid,response_ready,response_sat,
 input wire [31:0] response_status,input wire [2:0] retire,input wire [23:0] opcode
);
 reg [63:0] hits=0;
 reg [15:0] lm[0:2],sm[0:2];reg [255:0] transitions[0:2],ops[0:2];
 reg [3:0] previous_life[0:2];reg [7:0] supervisor=0;
 reg [3:0] active_op=0;integer cycles=0;reg have_previous=0;
 reg [31:0] old_commits=0,old_acks=0;integer services[0:1],responses[0:1],results=0;
 initial begin
  for(integer k=0;k<3;k++)begin lm[k]=0;sm[k]=0;transitions[k]=0;ops[k]=0;previous_life[k]=0;end
  for(integer k=0;k<2;k++)begin services[k]=0;responses[k]=0;end
 end
 always @(posedge clk_i)begin
  cycles<=cycles+1;
  if(cycles>3)begin
   for(integer k=0;k<3;k++)begin
    lm[k][life[k*4+:4]]=1;sm[k][seq[k*4+:4]]=1;
    if(have_previous)transitions[k][{previous_life[k],life[k*4+:4]}]=1;
    previous_life[k]=life[k*4+:4];
    if(retire[k])ops[k][opcode[k*8+:8]]=1;
   end
   have_previous=1;
   if(!rst_ni)hits[0]=1;
   if(image_valid_o==7)hits[1]=1;
   if(reply_valid_o && !reply_ready_i)hits[3]=1;
   if(link_pending_o)hits[12]=1;
   if(commit_count_o>old_commits)hits[13]=1;
   if(ack_count_o>old_acks)hits[14]=1;
   if(|poison_o)hits[15]=1;
   if(life[7:4]==7 || life[11:8]==7)hits[28]=1;
   if(recovery_enabled)begin
    supervisor[recovery_phase]=1;
    if(recovery_phase==1)hits[29]=1;
    if(recovery_phase==2)hits[30]=1;
    if(recovery_phase==5)hits[31]=1;
   end
   for(integer k=0;k<2;k++)begin
    if(native_valid[k] && native_ready[k])begin services[k]++;hits[8]=1;end
    if(response_valid[k] && response_ready[k])begin
     responses[k]++;hits[9]=1;
     if(response_sat[k])hits[10]=1;
     if(response_status[k*16+:16]!=0)hits[11]=1;
    end
    if(native_valid[k] && !native_ready[k])hits[34]=1;
   end
   if(cmd_valid_i && cmd_ready_o)active_op<=cmd_op_i;
   if(reply_valid_o && reply_ready_i)begin
    if(reply_status_o!=0)hits[5]=1;
    case(reply_status_o)
     16'h106:hits[18]=1;16'h104:hits[19]=1;16'h103:hits[20]=1;
     16'h102:hits[21]=1;16'h105:hits[22]=1;16'h107:hits[23]=1;16'h101:hits[32]=1;
     default:begin end
    endcase
    if(reply_status_o==0)case(active_op)
     2:hits[24]=1;3:hits[6]=1;4:hits[7]=1;8:hits[2]=1;
     10:begin hits[4]=1;results++;if(reply_data_o[111:96]!=0)hits[16]=1;end
     13:hits[26]=1;14:hits[25]=1;default:begin end
    endcase
   end
   old_commits=commit_count_o;old_acks=ack_count_o;
  end
 end
 final begin
  $display("COV_BINS hits=%016h supervisor=%02h results=%0d services0=%0d services1=%0d responses0=%0d responses1=%0d",hits,supervisor,results,services[0],services[1],responses[0],responses[1]);
  for(integer k=0;k<3;k++)$display("COV_STATE controller=%0d life=%04h seq=%04h transitions=%064h opcodes=%064h",k,lm[k],sm[k],transitions[k],ops[k]);
 end
endmodule
