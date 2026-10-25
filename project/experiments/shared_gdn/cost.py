"""Independent actual resource/cell-area inventory; all physical exclusions explicit."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources,sha,need
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():need(sha(ROOT/n)==h,'inventory source SHA')
 r=resources(a.map,'shared109',LIB);ms=r['multipliers'];need(len(ms)==10,'9 dynamic arithmetic plus one constant49 address cell');need(sum(x['A_WIDTH']==8 and x['B_WIDTH']==8 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==8,'8 physical signed S8');need(sum(x['A_WIDTH']==32 and x['B_WIDTH']==32 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==1,'one shared signed S32')
 mods=json.loads((a.map/'generic.json').read_text())['modules'];top=mods['shared109'];instances={k:c['type']for k,c in top['cells'].items()if c['type']in mods}
 need(sum(v=='store82'for v in instances.values())==1,'one actual top store')
 need(sum(v=='memory_link'for v in instances.values())==1,'one actual top bridge')
 need(sum('sfu84'in v for v in instances.values())==1,'one actual SFU instance')
 need(sum('mul84'in v for v in instances.values())==1,'one actual S32 service instance')
 for n in ['m106','a106','r106','norm106','mfront106','attention106','gdn109']:
  if n in mods:need(not any(c['type']in ['store82','memory_link']or 'mul84'in c['type']or'sfu84'in c['type']for c in mods[n]['cells'].values()),'controller contains no bank '+n)
 details=[]
 def walk(mod,path):
  for name,c in mods[mod]['cells'].items():
   if c['type']in mods:walk(c['type'],path+'/'+name)
   elif c['type']=='$mul':details.append({'path':path+'/'+name,'A':c['connections']['A'],'B':c['connections']['B'],'parameters':c['parameters']})
 walk('shared109','shared109');dynamic=[m for m in details if any(type(x)is int for x in m['A'])and any(type(x)is int for x in m['B'])];constant=[m for m in details if m not in dynamic]
 need(len(dynamic)==9 and len(constant)==1,'actual dynamic/constant separation');c=constant[0];bits=c['B']if all(type(x)is str for x in c['B'])else c['A'];need(all(x in('0','1')for x in bits)and int(''.join(reversed(bits)),2)==49,'only constant49 address cell')
 r.update(dynamic_multipliers=dynamic,constant_address_multipliers=constant)
 r.update(status='PASS_UNIQUE109_LOGIC_INVENTORY_NOT_PPA',receiver_source=binding,top_instances=instances,notes=['One real 16KiB128bit1RW,8signed8x8,1signed32x32 with two64bit response slots,1SFU and1bridge. No copies hidden in M/A/R controllers.','All four controllers, all lineholders, wide comparison/shift/RNE, metadata/registry, lease mux/control, result export and abort-drain counters are mapped. Arithmetic sharing does not remove inactive controller area.','SRAM is a behavioral wrapper omitted from logic area, no SRAM/ROM macro/CTS/RC/PVT/physical qualification.','External readonly C0 LUT128KiB, mutable Falcon1MiB plus GDN1MiB and M/A backing payloads remain finite explicitly allocated inventories; all reads/writes pay the same five128bit beats.','External two response slots at least320bit+control,32bit request/response epoch sideband serialization not included in five128bit packet payload beats.','Granite dedicated V/M, materialized GQA A, singlehead Falcon R have actual unique service bank; GDN109 complete twohead recurrence shares the same bank and S32; wide104 is a bounded controller with three S32 handshakes.','Area sum of old independent cores has different resource inventory and is only a descriptive reference, not a same-resource PPA improvement.'])

 a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({k:r[k]for k in('status','area_um2_logic_only','mapped_cells','DFF_X1','generic_register_bits_including_frame_wrapper','memory_bits')}))
if __name__=='__main__':main()
