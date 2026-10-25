"""Independent reparse of postphysical wrapper and all original functional pins."""
import sys
from common import *
from admission97 import SOURCE
from canonical97 import canonical_cut
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import library,certificate
from physical_structure import certify_physical

def audit_post(original,prepared,out,admission):
 pm=artifacts(prepared);need(pm['status']=='EXACT_POSTPHYSICAL97_GATE_EXPORT'and pm['original_prepared_manifest_sha256']==sha(original/'manifest.json')and pm['admission']==admission,'exact postphysical producer input');stage=Path(pm['physical_stage_directory']);sm=artifacts(stage);need(sha(stage/'manifest.json')==pm['physical_stage_manifest_sha256']and sha(stage/'final.v')==pm['physical_final_verilog_sha256'],'same exact executed physical netlist');rr=Path(pm['physical_receipt_directory']);need(sha(rr/'receipt.json')==pm['physical_receipt_sha256']and load(rr/'receipt.json')['result']['stage_manifest_sha256']==sha(stage/'manifest.json'),'same independent physical reception')
 for n in('cells.v','chain_gate.cpp'):need(sha(prepared/n)==sha(original/n),'unchanged original gate driver/library '+n)
 out.mkdir(exist_ok=False);raw=load(original/'mapped.json');bank={'modules':{'store82':raw['modules']['store82']}};need(load(prepared/'bank.json')==bank,'original behavioral bank interface only');put(out/'bank.json',bank)
 ys=out/'wrapper.ys';ys.write_text(f'read_liberty -lib {LIB}\nread_json {out}/bank.json\nread_verilog {prepared}/mapped.v\nhierarchy -top chain97\ncheck -assert\nwrite_json {out}/wrapper.json\n');command(out,'independent-wrapper',['yosys','-s',ys],300)
 design=load(out/'wrapper.json');top=design['modules']['chain97'];old=raw['modules']['chain97'];need(set(top['ports'])==set(old['ports'])and set(top['cells'])=={'core','frame'},'only exact original top ports and two wrapper instances');core=top['cells']['core'];frame=top['cells']['frame'];need(core['type']=='physical_core'and frame['type']=='store82','precise physical core and original bank types');cut=load(original/'cut-contract.json');need(set(core['connections'])==set(old['ports'])|{e['port']for e in cut['ports']},'all core connections');need(set(frame['connections'])==set(cut['original_connections']['connections']),'all original store connections')
 for n,p in old['ports'].items():
  q=top['ports'][n];need(q['direction']==p['direction']and len(q['bits'])==len(p['bits'])and core['connections'][n]==q['bits'],'every original top bit directly connects same core port')
 for e in cut['ports']:need(core['connections'][e['port']]==frame['connections'][e['original_pin']]and len(core['connections'][e['port']])==e['width'],'same actual memory cut connection '+e['port'])
 need(frame['connections']['clk']==top['ports']['clk']['bits'],'same proven shared clock');lib=library(LIB);physical=load(stage/'final.json')['modules']['chain97'];wrapped=design['modules']['physical_core'];same=certificate(physical,wrapped,lib);need(same['added_histogram']=={}and same['resized']==[],'no core change during wrapping');before=canonical_cut(original,out/'canonical');cert=certify_physical(before,wrapped,lib)
 return pm,cert,{'wrapper_status':'PASS_INDEPENDENT_REPARSE_ALL_TOP_BANK_BITS_AND_UNCHANGED_PHYSICAL_CORE','wrapper_json_sha256':sha(out/'wrapper.json'),'physical_stage_manifest_sha256':sha(stage/'manifest.json'),'physical_final_verilog_sha256':sha(stage/'final.v'),'store_model_sha256':sha(SOURCE/'project/rtl/norm_service/store82.sv'),'same_core_certificate':same}
