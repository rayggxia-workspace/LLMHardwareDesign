"""Architecture regressions: the compiler must not admit disguised old bases."""
from pathlib import Path
import json,copy
import xml.etree.ElementTree as ET
import check_pr185_control_admission as gate
ROOT=Path(__file__).resolve().parents[1]
hardware=json.loads((ROOT/'hardware/blockv2-mod-macros.json').read_text())
good=gate.validate(hardware)
receipt=json.loads(gate.RECEIPT.read_text())
row=receipt['rows'][0]
tree=ET.parse(gate.XML_DIR/'p.xml').getroot()
checks=[]
def rejected(name,fn):
    try:fn()
    except ValueError:checks.append(name)
    else:raise AssertionError('illegally admitted: '+name)
bad=copy.deepcopy(hardware);bad['control_groups']['P0']['hard_boundary']=True
rejected('opaque_P_hard_boundary',lambda:gate.validate(bad))
bad=copy.deepcopy(hardware);bad['macro_instances']['U0.extra_E']=copy.deepcopy(next(m for m in bad['macro_instances'].values() if m['control_owner']=='J0' and m['master']=='e_s32_mac_ap64'))
rejected('extra_undeclared_U_E',lambda:gate.validate(bad))
bad=copy.deepcopy(hardware);bad['macro_instances']['P0.M']['master']='invented_fast_M'
rejected('unregistered_macro_revision',lambda:gate.validate(bad))
bad=copy.deepcopy(hardware);bad['control_groups']['U0']['private_sram']='P0.S'
rejected('stolen_private_SRAM',lambda:gate.validate(bad))
for module in ('g_s32','block_v2_g','block_v2_e_compact','r_stream_local','transaction6k','dot_s32_core'):
    badtree=copy.deepcopy(tree)
    ET.SubElement(badtree.find('netlist'),'module',name='injected',origName=module)
    ET.SubElement(badtree.find('cells'),'cell',name='hidden',submodname='injected')
    rejected('hidden_'+module,lambda:gate.check_hierarchy(badtree,hardware,row['instances']))
badtree=copy.deepcopy(tree)
ET.SubElement(badtree.find('netlist'),'module',name='injected',origName='renamed_arithmetic')
ET.SubElement(badtree.find('cells'),'cell',name='hidden',submodname='injected')
rejected('unknown_parent_resource',lambda:gate.check_hierarchy(badtree,hardware,row['instances']))
# Change the expected digest in memory, never mutate RTL or frozen evidence.
original=gate.sha256
class WrongHash:
    def hexdigest(self):return '0'*64
gate.sha256=lambda _:WrongHash()
try:rejected('stale_source_evidence',lambda:gate.validate(hardware))
finally:gate.sha256=original
out={'schema':'pr185-control-admission-tests/1','negative_checks':checks,
     'positive_parents':len(good['parents']),'whole_base_accepted':False}
(ROOT/'evidence/architecture-revision-185/pr185-control-admission-tests.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
