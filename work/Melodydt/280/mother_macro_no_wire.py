"""Repeat the accepted four-macro PM calculation without loading wire RC."""
import json
from pathlib import Path
import re
import sys
import qwen3_mother_pm_power as reference

root, out = map(Path, sys.argv[1:])
out.mkdir()
original = reference.tcl_for
def tcl_without_wire(*args):
    text = original(*args)
    if len(re.findall(r'(?m)^read_spef .*$', text)) != 1:
        raise ValueError('expected exactly one original SPEF load')
    return re.sub(r'(?m)^read_spef .*\n?', '', text)
reference.tcl_for = tcl_without_wire
bank=root/'incoming/macro-views/source/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib'
sys.argv=[sys.argv[0],str(root/'pm-real-length/pm-38795749'),
          str(root/'incoming/macro-views/mother128/physical'),str(bank),str(out),'--cores','12']
reference.main()
path=out/'mother-pm-macro-power.json'
data=json.loads(path.read_bytes())
data['scope']='four existing program_store macros, with no wire RC loaded'
data['opensta']='same measured pin activities on macro instances; no external wire capacitance'
data['wire_parasitics_loaded']=False
data['physical_sha256'].pop('6_final.spef')
path.write_text(json.dumps(data,indent=2)+'\n')
print('MOTHER_MACRO_NO_WIRE_PASS')
