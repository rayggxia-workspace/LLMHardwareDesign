from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');source=(root/'audit/f-qualify-fidelity.py').read_text();tail=source[source.index("body='set_thread_count"):]
head='''import sys,re,os,json,subprocess,hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
c=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4';q=c/'qualification-final';res=q/'flow/results/nangate45/f-native-frame/base'
assert 'Total elapsed:' in (q/'full-deck.log').read_text()
identity=json.loads((root/'audit/F-gds-timestamp-identity.json').read_text());assert identity['passed']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(res/'6_final.gds')==identity['files'][str(res/'6_final.gds')]['raw_sha256']
review=json.loads((root/'audit/F-new-marker-gds-connectivity.json').read_text());assert review['passed']
marker_diff=json.loads((root/'audit/F-native-marker-diff.json').read_text())
assert marker_diff['sha256'][str(c/'native-drc.rpt')]==sha(c/'native-drc.rpt')
items=len(ET.parse(q/'full-deck.lyrdb').findall('.//items/item'));assert items==0,items
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');deck=platform/'drc/FreePDK45.lydrc'
assert sha(deck)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(c/'config.mk').read_text(),re.M)[1].split()
def run(args,name):
 with (q/name).open('w') as f:subprocess.run(list(map(str,args)),cwd=q,stdout=f,stderr=subprocess.STDOUT,check=True)
'''
(root/'audit/f-final-resume.py').write_text(head+tail.replace('write_abstract_lef cfj_group_f.lef','write_abstract_lef -bloat_factor 0 cfj_group_f.lef'))
