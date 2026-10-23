"""Reuse the unchanged H1 strict PG and real hierarchical STA checks."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'h1'))
from implementation import qualify_parent_final
from run import INPUTS
try:
    qualify_parent_final()
finally:
    Path('h1-qualification-input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
