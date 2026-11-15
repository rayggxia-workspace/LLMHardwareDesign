"""Explicit E32 revision: original multiplier lanes, four finite S80 accumulators."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'rtl/u0/e_s32_native.sv'
s=base.read_text().replace('module e_s32_native(', 'module e_s32_mac_native(')
s=s.replace('MASK_ZERO=10,MASK_FLOOR=11;', 'MASK_ZERO=10,MASK_FLOOR=11,MAC_BEGIN=12,MAC_STEP=13,MAC_END=14,MAC_ABORT=15;')
s=s.replace('SCALE=6,ROUND=7,PACK=8;', 'SCALE=6,ROUND=7,PACK=8,MAC_ADD=9,MAC_FINAL=10;')
a=s.index(' wire first_bad=')
b=s.index(' assign in_ready=',a)
s=s[:a]+""" reg mac_owned;
 reg [15:0] mac_length,mac_count;
 reg [3:0] mac_mask;
 reg [5:0] mac_shift;
 reg signed [79:0] mac_acc[0:3];
 wire legacy_bad=mac_owned || $signed(in_shift)<-8'sd63 || $signed(in_shift)>8'sd63 ||
    ((in_op!=PRODUCT&&in_op!=CONVERT32&&in_op!=CONVERT16)&&in_shift!=0) ||
    ((in_op!=ADD2&&in_op!=ADD3)&&in_minus!=0) || (in_op==ADD2&&in_minus[2]);
 wire mac_bad=in_minus!=0||in_mask==0||
   (in_op==MAC_BEGIN ? (mac_owned||in_data[127:16]!=0||in_data[15:0]==0||in_shift>63) :
    in_op==MAC_STEP ? (!mac_owned||mac_count>=mac_length||in_mask!=mac_mask||in_shift!=0) :
    in_op==MAC_END ? (!mac_owned||mac_count!=mac_length||in_mask!=mac_mask||
                     in_shift!={2'd0,mac_shift}||in_data!=0) :
    (in_shift!=0||in_data!=0));
 wire first_bad=in_op<=MASK_FLOOR?legacy_bad:mac_bad;
 wire unary=in_op==CONVERT32||in_op==CONVERT16||in_op==MASK_ZERO||in_op==MASK_FLOOR;
 function automatic [32:0] mac_round(input signed [79:0] value,input [5:0] bits);
  reg signed [79:0] q;
  reg [79:0] remainder,halfway;
  reg clipped_value;
  begin
   q=value>>>bits;remainder=$unsigned(value)&((80'd1<<bits)-80'd1);
   halfway=bits==0?80'd0:80'd1<<(bits-1'b1);
   if(bits!=0&&(remainder>halfway||(remainder==halfway&&q[0])))q=q+80'sd1;
   clipped_value=q>80'sd2147483647||q< -80'sd2147483648;
   mac_round={clipped_value,q>80'sd2147483647 ? 32'h7fffffff:
                           q< -80'sd2147483648 ? 32'h80000000:q[31:0]};
  end
 endfunction
 wire [32:0] mac_result[0:1];
 for(genvar mr=0;mr<2;mr++)begin: mac_rounding
  assign mac_result[mr]=mac_round(mac_acc[{high_half,1'(mr)}],mac_shift);
 end
"""+s[b:]
s=s.replace('PRODUCT:total[lane]<=product_value;','PRODUCT,MAC_STEP:total[lane]<=product_value;')
s=s.replace('a<=0;b<=0;c<=0;out_valid<=0;out_data<=0;out_clipped<=0;out_error<=0;',
'''a<=0;b<=0;c<=0;out_valid<=0;out_data<=0;out_clipped<=0;out_error<=0;
     mac_owned<=0;mac_length<=0;mac_count<=0;mac_mask<=0;mac_shift<=0;
     for(integer i=0;i<4;i++)mac_acc[i]<=0;''')
s=s.replace('else phase<=unary?TOTAL:SECOND;',"""else if(in_op==MAC_BEGIN)begin
          mac_owned<=1;mac_length<=in_data[15:0];mac_count<=0;mac_mask<=in_mask;mac_shift<=in_shift[5:0];
          for(integer i=0;i<4;i++)mac_acc[i]<=0;
          out_valid<=1;
         end else if(in_op==MAC_END)phase<=MAC_FINAL;
         else if(in_op==MAC_ABORT)begin mac_owned<=0;mac_count<=0;out_valid<=1;end
         else phase<=unary?TOTAL:SECOND;""")
s=s.replace('op==PRODUCT?PARTIAL:TOTAL','(op==PRODUCT||op==MAC_STEP)?PARTIAL:TOTAL')
s=s.replace('TOTAL:phase<=SCALE;', 'TOTAL:phase<=op==MAC_STEP?MAC_ADD:SCALE;')
needle='       PACK:begin'
assert needle in s
s=s.replace(needle,"""       MAC_ADD:begin
         for(integer lane=0;lane<2;lane++)begin
          if(mac_mask[2*int'(high_half)+lane])
           mac_acc[2*int'(high_half)+lane]<=mac_acc[2*int'(high_half)+lane]+
                                         $signed({{16{total[lane][63]}},total[lane]});
         end
         if(high_half)begin mac_count<=mac_count+1'b1;out_valid<=1;phase<=FIRST;end
         else begin high_half<=1;phase<=PARTIAL;end
       end
       MAC_FINAL:begin
         for(integer lane=0;lane<2;lane++)begin
          out_data[32*(2*int'(high_half)+lane)+:32]<=mac_mask[2*int'(high_half)+lane]?mac_result[lane][31:0]:32'd0;
          out_clipped[2*int'(high_half)+lane]<=mac_mask[2*int'(high_half)+lane]&&mac_result[lane][32];
         end
         if(high_half)begin out_valid<=1;phase<=FIRST;mac_owned<=0;end
         else high_half<=1;
       end
"""+needle)
(ROOT/'rtl/macros/e_s32_mac_native.sv').write_text('// Explicit E32 MAC revision; no additional multiply lane or external data pin.\n'+s)
p=ROOT/'rtl/u0/e_s32_ap64.sv'
wrapper=p.read_text().replace('module e_s32_ap64(', 'module e_s32_mac_ap64(').replace(' e_s32_native core(', ' e_s32_mac_native core(')
(ROOT/'rtl/macros/e_s32_mac_ap64.sv').write_text(wrapper)
manifest={'profile':'E32-mac80-mod-v1','master':'e_s32_mac_ap64',
 'baseline_master':'e_s32_ap64','extra_external_pins':0,'extra_macro_instances':0,
 'opcodes':{'12':'BEGIN: in_data[15:0] is nonzero full K, remaining data zero; mask and final shift',
            '13':'STEP: two four-lane S32 operands, exact signed products accumulated in S80',
            '14':'END: require exactly K steps; one RNE and S32 saturation per active lane',
            '15':'ABORT: clear accumulation ownership'},
 'capacity':{'contexts':1,'lanes_per_context':4,'accumulator_bits_per_lane':80,'max_k':65535},
 'arithmetic':'reuse original two product lanes; added S80 accumulation and final rounding',
 'old_operations':'0..11 unchanged when no MAC context is owned; reject while MAC owns macro',
 'required_lease':'exclusive E32 ownership from BEGIN acceptance through END or ABORT result consumption',
 'status':'candidate; numeric and old-operation equivalence not yet verified',
 'physical_views':None,'timing_calibrated':False,
 'baseline_sources':{str(base):sha256(base.read_bytes()).hexdigest(),str(p):sha256(p.read_bytes()).hexdigest()}}
(ROOT/'hardware/e32-mac-mod-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
