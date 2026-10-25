"""Independent actual resource/cell-area inventory; all physical exclusions explicit."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources,sha,need
LIB=Path('/public/home/yuzelu/RuizhiLiang/issue80-block-circuit-20261025/nangate45-reference/NangateOpenCellLibrary_typical.lib')
def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();binding=json.loads((ROOT/'binding.json').read_text())
 for n,h in binding['sources'].items():need(sha(ROOT/n)==h,'inventory source SHA')
 r=resources(a.map,'chain97',LIB);ms=r['multipliers'];need(len(ms)==9,'only 9 arithmetic multiplier cells');need(sum(x['A_WIDTH']==8 and x['B_WIDTH']==8 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==8,'8 physical signed S8');need(sum(x['A_WIDTH']==32 and x['B_WIDTH']==32 and x['A_SIGNED']==1 and x['B_SIGNED']==1 for x in ms)==1,'one shared signed S32')
 r.update(status='PASS_ACTUAL97_LOGIC_INVENTORY_NOT_PPA',receiver_source=binding,notes=['All actual wide comparisons/RNE/barrel shifts/address/control, five128 V line registers,128delta and validity/owner/version/epoch are included in these mapped cells.','One behavioral16KiB128bit1RW SRAM excluded from logic area; SRAM wrapper registers in generic count, no macro area/timing.','No private V frame/ROM/program-fetch/8byte multiplier copies.512B reserved frame unused, not a hardware saving claim.','LUT reads use external constant window:128KiB reserved;65540B SiLU logical words plus8196B exp2, only SiLU used here.ROM macro/controller/physical boundary buffers are external and not in core cell area.','External recovery-response FIFO high-water2 costs at least2*(128+32)=320bit plus control, not in core.32bit epoch is sideband; reported wire_beats counts modeled128bit data/header, not physical epoch/owner wiring.','No CTS/parasitics/SRAM/ROM macros/PVT/multi-clock/physical signoff.97 does not inherit88STA.'])
 a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in('status','area_um2_logic_only','mapped_cells','DFF_X1','generic_register_bits_including_frame_wrapper','memory_bits')}))
if __name__=='__main__':main()
