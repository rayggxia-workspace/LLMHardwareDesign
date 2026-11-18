import xml.etree.ElementTree as E,collections
from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/e_compact/full-deck.lyrdb')
a=E.parse(str(p)).findall('.//items/item');print(str(p),len(a),collections.Counter((x.findtext('category'),x.findtext('cell')) for x in a))
