"""Reject hidden arithmetic/storage macros in elaborated parent service controls.

This checks hierarchy, not metal routability or complete instruction execution.
"""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'
FORBIDDEN={'m_native_leaf_s32','m_native_s32','g32','g16','g_s32','block_v2_g',
 'block_v2_e_compact','r_stream_local','transaction6k','e_s32_ap64',
 'e_s32_native','e_s32_mac_ap64','e_s32_mac_native','n_s32_mod',
 'n_s32_softmax_s128','block_v2_n','dot_s32_core','s32_token_argmax',
 'local_s_base','local_s_p','block_feed_s16k_sram','s_sram_256x128_freepdk45'}
def inspect(xml):
 tree=ET.parse(xml).getroot()
 modules={m.get('name'):m.get('origName') for m in tree.findall('./netlist/module')}
 counts=Counter(modules[c.get('submodname')] for c in tree.findall('./cells//cell'))
 bad=FORBIDDEN.intersection(counts)
 if bad:raise ValueError('hidden functional macro in parent controls: '+str(sorted(bad)))
 return dict(counts)
def main():
 results=[]
 for name in ('e32','n32'):
  xml=OUT/'scalar-clusters-114680'/(name+'.xml')
  counts=inspect(xml)
  deps={}
  for f in ET.parse(xml).getroot().findall('./files/file'):
   p=Path(f.get('filename',''))
   if p.is_file():deps[str(p)]=sha256(p.read_bytes()).hexdigest()
  results.append({'parent':name+'_service_cluster','job':114680,'instances':counts,
    'xml_sha256':sha256(xml.read_bytes()).hexdigest(),'source_snapshot_hashes':deps})
 # Negative regression: a functional fixture is forbidden as a parent-only control.
 try:inspect(OUT/'e32-dot-audit-114669/fixture.xml')
 except ValueError:pass
 else:raise AssertionError('hidden macro detection failed')
 result={'scope':'parent-control hierarchy only; shared-resource and graph acceptance pending',
  'parents':results,'hidden_macro_negative_check':True,'whole_base_accepted':False}
 (OUT/'scalar-parent-structure-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'parents':len(results),'hidden_macro_negative_check':True}))
if __name__=='__main__':main()
