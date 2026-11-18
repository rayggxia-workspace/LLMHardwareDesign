from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-m10-notch14-v2';src=root/'audit/C-m10-notch-v1/patched.def'
s=src.read_text();part=s.split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
m=next(m for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',part,re.M|re.S) if m[1].replace('\\','')=='dma_s_rsp_data[14]')
body=m[0].rstrip();assert body.endswith(';');body=body[:-1]+'\n      NEW metal10 ( 2732990 1161340 ) ( * 1162800 )\n      NEW metal10 ( 2732990 1161340 ) ( 2734990 * ) ;\n'
frag='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN cfj_group_c_memory_legacy ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 1 ;\n'+body+'END NETS\nEND DESIGN\n'
(out/'patch.def').write_text(frag)
(out/'source-binding.json').write_text(json.dumps({str(src):hashlib.sha256(src.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256(frag.encode()).hexdigest(),'net':'dma_s_rsp_data[14]','added_segments_dbu':[[2732990,1161340,2732990,1162800],[2732990,1161340,2734990,1161340]],'dbu_per_um':2000,'expected_added_union_area_um2':'pending actual geometry'},indent=2))
