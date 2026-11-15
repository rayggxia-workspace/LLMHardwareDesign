"""Explicit parent DMA revision: preserve transport credits/bandwidth, add service owners."""
from pathlib import Path
from hashlib import sha256
import json,re
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project')
source=BASE/'rtl/mother_control_native/mc_dma_fabric_typed_p.sv'
s=source.read_text()
s=s.replace('// Refs250: finite shared read-DMA transport. Internal MC fabric, not a leaf\n// pin contract. Twelve registered clients: LC scopes0..8 and M weights9..11.', '// Parent standard-cell DMA, not an MC hard-macro interface.\n// Clients: LC scopes 0..8, M weights 9..11, native64 services 12..20.\n// Explicit mod revision; no implicit inter-owner data links.')
s=s.replace('module mc_dma_fabric_typed_p','module native_shared_read_dma')
s=s.replace('[11:0] debug_beats','[DEBUG_WIDTH] debug_beats')
for old,new in [('[11:0]','[20:0]'),('[0:11]','[0:20]'),('[767:0]','[1343:0]'),
 ('[383:0]','[671:0]'),('[59:0]','[104:0]'),('[6143:0]','[10751:0]'),('[107:0]','[188:0]')]:s=s.replace(old,new)
s=s.replace('[DEBUG_WIDTH]','[11:0]')
s=s.replace('reg [2:0] native_tag_seen','reg [20:0] native_tag_seen').replace('last_native_serial[0:2]','last_native_serial[0:20]')
for name in ['b_client','desc_client','request_rr','fence_client','new_fault_client','fault_client']:
 s=s.replace('[3:0] '+name,'[4:0] '+name)
s=re.sub(r"(?<![0-9])4'\(", "5'(", s).replace("4'hf","5'h1f")
s=s.replace('<12','<21').replace('%12','%21')
s=s.replace("b_client[entry],6'd0","b_client[entry],5'd0")
s=s.replace('client<9?', '(client<9||client>=12)?')
s=s.replace('(c<3||j/32==ch)','(c<3||c>=12||j/32==ch)')
s=s.replace('(c>=9&&(req_length!=17&&req_length!=18))','(c>=9&&c<12&&(req_length!=17&&req_length!=18))')
s=s.replace('if(c<3&&p_mode_active[c])begin','if((c<3&&p_mode_active[c])||c>=12)begin')
s=s.replace('for(r=0;r<3;r=r+1)last_native_serial','for(r=0;r<21;r=r+1)last_native_serial')
needle='   if(fault_valid&&fault_ready)fault_valid<=0;'
assert s.count(needle)==1
s=s.replace(needle,"""   // Native service identities do not alias descriptor client identities.
   for(r=12;r<21;r=r+1)begin
    if(accepted_entry[r]>=0)begin
     native_tag_seen[r]<=1;last_native_serial[r]<=c_req_tag[r*32+1+:31];
    end
    if(fence_state==F_REPLY&&fence_external&&fence_client==5'(r)&&c_fence_done_ready[r])
     native_tag_seen[r]<=0;
   end
"""+needle)
assert 'reg [4:0] b_client' in s and 'reg [4:0] fence_client' in s
target=ROOT/'rtl/control/native_shared_read_dma.sv';target.write_text(s)
owners=['P0','P1','P2','C0','U0','J0','F0','U1','J1']
manifest={'schema':'shared-read-dma-revision/1','implementation':'native_shared_read_dma',
 'hard_boundary':False,'implementation_kind':'parent_standard_cells',
 'upstream':{'path':str(source),'sha256':sha256(source.read_bytes()).hexdigest()},
 'source':str(target.relative_to(ROOT)),'sha256':sha256(target.read_bytes()).hexdigest(),
 'clients':[{'client':i,'owner':o,'kind':'LC_descriptor','record_bytes':128} for i,o in enumerate(owners)]
 +[{'client':9+i,'owner':o,'kind':'M_weight','record_beats':[17,18]} for i,o in enumerate(owners[:3])]
 +[{'client':12+i,'owner':o,'kind':'service','record_bytes':64,'tag_adapter_required':True} for i,o in enumerate(owners)],
 'transport':{'channels':2,'lanes_per_channel':2,'beat_bytes':64,'entries_per_channel':32,
 'descriptors_per_channel':32,'return_skids_per_channel':3,'issue_limit_per_3_cycles_per_channel':4},
 'delta':{'client_count':[12,21],'client_identity_bits':[4,5],
 'external_DDR_tag_bits':[64,64],'external_DDR_data_bits':[512,512],
 'transport_entries':[64,64],'return_payload_bytes':[384,384],
 'synthesis_area':None,'physical_acceptance':False},
 'registered_in_complete_base':False,'functional_acceptance':False,
 'scope':'candidate parent transport; source adapters, write transport and joined control execution pending'}
(ROOT/'hardware/shared-read-dma-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(target)
