"""Join independent completed GDS/STA and exact whole-die native computations.

Every original gate except native partition computation must already pass.
No timing/electrical/GDS failure can be repaired by reception or omitted.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, xml.etree.ElementTree as ET
from receive_native import receive
from lec_receive import inspect

p=argparse.ArgumentParser()
for name in ['evaluation','physical','complete-native']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
O=Path.cwd()/'evaluation';assert not O.exists()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
source=a.evaluation/'receipt.json';r=json.loads(source.read_text())
assert not r.get('error')and r['physical']==str(a.physical)and r['capacity']==a.capacity
assert r['checks']and all(v is True for k,v in r['checks'].items()if k!='native_full_chip_drc')
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
for path,row in r['artifacts'].items():assert sha(Path(path))==row['sha256']
assert json.loads((a.physical/'receipt.json').read_text())['exit']==0
assert inspect((a.physical/'flow/logs/nangate45'/('r166_'+str(a.capacity))/'base/6_final_lec_check.log').read_text())['passed']
assert len(ET.parse(a.evaluation/'full-deck.lyrdb').getroot().findall('./items/item'))==r['full_deck_items']==0
proof=receive(a.complete_native,R/'6_final.odb')
assert sha(a.evaluation/'before.def')==sha(a.evaluation/'after.def')
shutil.copytree(a.evaluation,O)
shutil.copyfile(source,O/'original-evaluation-receipt.json')
shutil.copyfile(O/'native-whole-drc.rpt',O/'native-fragmented-drc.rpt')
shutil.copyfile(a.complete_native/'complete.rpt',O/'native-whole-drc.rpt')
shutil.copytree(a.complete_native,O/'complete-native')
r['native_fragmented_diagnostic_count']=(O/'native-fragmented-drc.rpt').read_text().count('violation type:')
r['complete_native']=proof;r['source_receiver_receipt_sha256']=sha(source)
r['source_receiver']=str(a.evaluation);r['receiver_script_sha256']=sha(Path(__file__))
r['checks']['native_full_chip_drc']=True;r['passed']=all(r['checks'].values())
assert r['passed']
(O/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,checks=r['checks'],scope='All independent exact-final checks received; no gate excluded.')))
