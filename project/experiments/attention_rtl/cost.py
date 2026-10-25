"""Independent actual resource/cell-area inventory; all physical exclusions explicit."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources,sha,need
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():need(sha(ROOT/n)==h,'inventory source SHA')
 r=resources(a.map,'chain102',LIB);ms=r['multipliers'];need(len(ms)==9,'only 9 arithmetic multiplier cells');need(sum(x['A_WIDTH']==8 and x['B_WIDTH']==8 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==8,'8 physical signed S8');need(sum(x['A_WIDTH']==32 and x['B_WIDTH']==32 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==1,'one shared signed S32')
 r.update(status='PASS_ACTUAL102_LOGIC_INVENTORY_NOT_PPA',receiver_source=binding,notes=['Actual dedicated complete GQA controller, eight signed8 products, one signed32 multiplier, width conversion/RNE/guards, eight I32 PV accumulators, lineholders, metadata/FSM and epoch are mapped.','SFU invoked only for U128 division; unused sqrt branch may be pruned. This standalone A inventory does not prove physical sharing with the Granite M or R cores.','One16KiB128bit1RW behavioral SRAM excluded from mapped logic area; no SRAM macro/ROM/CTS/RC/physical qualification.','Three score passes plus separate PV, full8 heads sequential; no online state or hardware KV append.','External C0 table128KiB includes2049 new U32Q30 exp words(8196logical/8208physicalB). All lookups pay external transactions; ROM/controller area outside core.','External two-response recovery FIFO costs at least320bit plus control;32bit epoch is sideband not included in five128bit packet beats.'])
 a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({k:r[k]for k in('status','area_um2_logic_only','mapped_cells','DFF_X1','generic_register_bits_including_frame_wrapper','memory_bits')}))
if __name__=='__main__':main()
