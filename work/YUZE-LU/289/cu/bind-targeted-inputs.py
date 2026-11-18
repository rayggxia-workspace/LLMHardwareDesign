from pathlib import Path
import hashlib,json
p=Path(__file__).parent
source=p/'runs/U-v8-postroute-h02-e10/flow/results/nangate45/u-overlay-current/base'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
inputs={str(f):sha(f) for f in [source/'6_final.odb',source/'6_final.sdc',source/'6_final.spef',p/'u-targeted-edit-v2.tcl',p/'u-targeted-route.tcl']}
for n in (2,3,4):
 for drive in (4,8):
  r=p/('runs/U-v11-targeted-n%d-x%d'%(n,drive))
  out=r/'targeted-input-binding.json'
  if out.exists():continue
  result={'actual_immediate_source':'U-v8-postroute-h02-e10','inputs_raw_sha256':inputs,'inherited_eco_source_sha_file':'The older eco-source-sha256.txt names the v7 ancestor, not the immediate v8 seed. This receipt binds the actual seed and edit scripts.','intended_edits':{'driver_names':['wire40497','wire40491','wire38369','wire40500','wire40492','wire40494','wire38339'],'driver_master':'BUF_X%d'%drive,'score120_inserted_CLKBUF_X1':n,'score110_inserted_CLKBUF_X1':1},'accepted':False,'status':'pending full gates'}
  out.write_text(json.dumps(result,indent=2)+'\n')
