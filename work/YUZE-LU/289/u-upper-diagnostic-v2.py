"""Generate a fast diagnostic only; final signoff still uses unmodified full deck."""
from pathlib import Path
import xml.etree.ElementTree as E,hashlib,json
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
tree=E.parse(deck)
text=tree.find('text');assert text is not None
text.text='''source($in_gds)
report("Upper spacing diagnostic only - NOT full DRC", $report_file)
tiles(1000.um)
deep
threads(4)
metal9 = input(27, 0)
metal10 = input(29, 0)
via7 = input(24, 0)
via9 = input(28, 0)
metal9.space(800.nm, euclidian).output("METAL9.2", "Exact original spacing threshold")
metal10.space(800.nm, euclidian).output("METAL10.2", "Exact original spacing threshold")
via7.space(440.nm, euclidian).output("VIA7_SPACING", "Original mislabeled VIA6.2; actual via7")
via9.space(880.nm, euclidian).output("VIA9.2", "Exact original spacing threshold")
'''
out=root/'u-physical/upper-spacing-diagnostic-v2.lydrc'
tree.write(out,encoding='utf-8',xml_declaration=True)
(out.parent/'upper-diagnostic-origin-v2.json').write_text(json.dumps({'scope':'4 spacing rules only; not acceptance','original_full_deck':str(deck),'original_full_deck_sha256':hashlib.sha256(deck.read_bytes()).hexdigest(),'diagnostic_sha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2)+'\n')
