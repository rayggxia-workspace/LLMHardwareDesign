"""Derive isolated dynamic-S32 admission candidate from the pinned finite fabric."""
from pathlib import Path
import subprocess

base='0b60b134e'
dest=Path('project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv')
s=subprocess.check_output(['git','show',f'{base}:project/rtl/mother_control_native/mc_dma_fabric.sv']).decode('utf-8')
s=s.replace('module mc_dma_fabric #(', 'module mc_dma_fabric_typed_p #(')
s=s.replace(' input wire clk,reset,', ''' input wire clk,reset,
 // Runtime mode has independent real local and transport drain proofs.
 // A rejected request consumes VALID for diagnosis but creates no owner.
 input wire [2:0] p_mode_valid,p_mode_native64,p_mode_client_drained,
 output reg [2:0] p_mode_ready,p_mode_active,p_req_rejected,''')
s=s.replace(' localparam [2:0] FREE=0', ''' reg [2:0] native_tag_seen;
 reg [30:0] last_native_serial[0:2];
 localparam [2:0] FREE=0''')
a=s.index(' // These physical outputs depend')
s=s[:a]+''' // A descriptor remains live through its last held return, even if
 // backend service completed earlier. Mode updates can never overlap a new
 // request or pending close/cancel/fence, nor an unconsumed local DONE.
 always @*begin: typed_mode_admission
  integer m,x;
  for(m=0;m<3;m=m+1)begin
   p_mode_ready[m]=!reset&&fence_state==F_IDLE&&p_mode_client_drained[m]&&
       !c_req_valid[m]&&!c_close_valid[m]&&!c_cancel_valid[m]&&!c_cancel_ack_valid[m]&&
       !c_fence_valid[m]&&!(fault_valid&&fault_client==4'(m));
   for(x=0;x<64;x=x+1)begin
    if(desc_live[x]&&desc_client[x]==4'(m))p_mode_ready[m]=0;
    if(b_state[x]!=FREE&&b_client[x]==4'(m))p_mode_ready[m]=0;
   end
  end
 end
'''+s[a:]
s=s.replace('c_req_ready=0;c_close_ready=0;c_cancel_ready=0;', 'c_req_ready=0;c_close_ready=0;c_cancel_ready=0;p_req_rejected=0;')
a=s.index('     d=-1;for(j=0;j<32;j=j+1)if(desc_live[ch*32+j]')
b=s.index('     if(close_client==c',a)
s=s[:a]+'''     d=-1;
     for(j=0;j<64;j=j+1)if((c<3||j/32==ch)&&desc_live[j]&&int'(desc_client[j])==c&&desc_base[j]==req_base)d=j;
     bad=req_address[5:0]!=0||(c>=9&&(req_length!=17&&req_length!=18))||req_beat>=req_length;
     if(c<3&&p_mode_active[c])begin
      bad=bad||req_length!=1||req_tag[0]||
          (native_tag_seen[c]&&req_tag[31:1]<=last_native_serial[c]);
     end else if(c<9)bad=bad||req_length!=2||req_record_address[6:0]!=0;
     if(d<0)bad=bad||req_beat!=0||int'(req_record_address[11])!=ch;
     else bad=bad||d/32!=ch||desc_closed[d]||int'(desc_length[d])!=req_length||
           int'(desc_next[d])!=req_beat||desc_address[d]!=req_record_address;
'''+s[b:]
s=s.replace("c_req_ready[c]=1;new_fault=1;new_fault_kind=8'd4;", "c_req_ready[c]=1;if(c<3)p_req_rejected[c]=1;new_fault=1;new_fault_kind=8'd4;")
s=s.replace('desc_live<=0;desc_closed<=0;offer_valid<=0;', '''p_mode_active<=0;native_tag_seen<=0;
   for(r=0;r<3;r=r+1)last_native_serial[r]<=0;
   desc_live<=0;desc_closed<=0;offer_valid<=0;''')
s=s.replace('   if(fault_valid&&fault_ready)fault_valid<=0;', '''   for(r=0;r<3;r=r+1)begin
    if(p_mode_valid[r]&&p_mode_ready[r])p_mode_active[r]<=p_mode_native64[r];
    if(accepted_entry[r]>=0&&p_mode_active[r])begin
     native_tag_seen[r]<=1;last_native_serial[r]<=c_req_tag[r*32+1+:31];
    end
    if(fence_state==F_REPLY&&fence_external&&fence_client==4'(r)&&c_fence_done_ready[r])native_tag_seen[r]<=0;
   end
   if(fault_valid&&fault_ready)fault_valid<=0;''')
assert 'p_req_rejected[c]' in s and 'if(c<3&&p_mode_active[c])' in s
dest.write_text(s,encoding='utf-8')

