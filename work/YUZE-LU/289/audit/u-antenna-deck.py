from pathlib import Path
import xml.etree.ElementTree as E,hashlib,json
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-antenna');root.mkdir(exist_ok=True)
p=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');tree=E.parse(str(p));t=tree.getroot().find('text');old=t.text
s=old.replace('FEOL    = true','FEOL    = false').replace('BEOL    = true','BEOL    = false').replace('OFFGRID = true','OFFGRID = false')
s=s.replace('\n# Antenna checks\n\nif ANTENNA','\n# Antenna checks\ngate = poly & active\n\nif ANTENNA')
assert s!=old and s[s.index('if ANTENNA'):]==old[old.index('if ANTENNA'):]
t.text=s;out=root/'antenna-only-v2.lydrc';tree.write(str(out),encoding='utf-8',xml_declaration=True)
(root/'diagnostic-deck-v2.json').write_text(json.dumps(dict(scope='Antenna localization only, not full physical signoff',original=str(p),original_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),diagnostic_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),antenna_rule_block_exact=True),indent=2))
