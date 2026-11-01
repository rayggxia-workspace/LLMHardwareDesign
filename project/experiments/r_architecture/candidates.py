from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'work/YUZE-LU/157'
def make(original,kind):
    if kind=='A0':return original
    start=original.index(' wire signed [31:0] active[0:2047]');end=original.index(' reg row_valid;',start)
    common=''' wire [8:0] state_read_row=phase==IDLE?cmd_index[9:1]:row;
 wire signed [31:0] active_row[0:7],shadow_row[0:7];
 genvar read_lane;
 generate for(read_lane=0;read_lane<8;read_lane=read_lane+1)begin: state_read
'''
    if kind=='A1':
        logic='''  wire signed [31:0] first=bank0[state_read_row*8+read_lane];
  wire signed [31:0] second=bank1[state_read_row*8+read_lane];
  assign active_row[read_lane]=bank_role?second:first;
  assign shadow_row[read_lane]=bank_role?first:second;
'''
    else:
        assert kind=='A2'
        logic='''  wire signed [31:0] group_active[0:31],group_shadow[0:31];
  for(genvar group_id=0;group_id<32;group_id=group_id+1)begin: group_read
   wire signed [31:0] first=bank0[group_id*64+state_read_row[2:0]*8+read_lane];
   wire signed [31:0] second=bank1[group_id*64+state_read_row[2:0]*8+read_lane];
   assign group_active[group_id]=bank_role?second:first;
   assign group_shadow[group_id]=bank_role?first:second;
  end
  assign active_row[read_lane]=group_active[state_read_row[8:3]];
  assign shadow_row[read_lane]=group_shadow[state_read_row[8:3]];
'''
    result=original[:start]+common+logic+' end endgenerate\n'+original[end:]
    changes={'active[row*8+l]':'active_row[l]','shadow[row*8+l]':'shadow_row[l]','shadow[row*8+i]':'shadow_row[i]','active[cmd_index*4+i]':'active_row[cmd_index[0]*4+i]'}
    for a,b in changes.items():assert a in result,a;result=result.replace(a,b)
    assert not re.search(r'\b(?:active|shadow)\[',result)
    if kind=='A2':
        old='for(i=0;i<8;i=i+1)if(bank_role)bank0[product_row*8+i]<=value[i][31:0];else bank1[product_row*8+i]<=value[i][31:0];'
        assert result.count(old)==2
        new='for(integer write_group=0;write_group<32;write_group=write_group+1)if(product_row[8:3]==write_group)begin\n        for(i=0;i<8;i=i+1)if(bank_role)bank0[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];else bank1[write_group*64+product_row[2:0]*8+i]<=value[i][31:0];\n       end'
        result=result.replace(old,new)
        old='for(i=0;i<4;i=i+1)if((cmd_op==1)^bank_role)bank0[cmd_index*4+i]<=cmd_data[32*i+:32];else bank1[cmd_index*4+i]<=cmd_data[32*i+:32];'
        assert old in result
        result=result.replace(old,'for(integer write_group=0;write_group<32;write_group=write_group+1)if(cmd_index[9:4]==write_group)begin\n        for(i=0;i<4;i=i+1)if((cmd_op==1)^bank_role)bank0[write_group*64+cmd_index[3:0]*4+i]<=cmd_data[32*i+:32];else bank1[write_group*64+cmd_index[3:0]*4+i]<=cmd_data[32*i+:32];\n       end')
    return result
def main():
    original=(OUT/'inputs/block_v1_r.sv').read_text();rows=[]
    for kind in ('A0','A1','A2'):
        folder=OUT/'candidates'/kind;folder.mkdir(parents=True,exist_ok=True)
        data=make(original,kind).encode();(folder/'block_v1_r.sv').write_bytes(data)
        rows.append(dict(candidate=kind,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),state_elements_per_bank=2048,lanes=8,full_equivalence='NOT_RUN',mapping='NOT_RUN'))
    (OUT/'CANDIDATES.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
if __name__=='__main__':main()
