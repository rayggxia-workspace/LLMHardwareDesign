"""Run actual native STA/RC and LEC mutation controls before final reception."""
from pathlib import Path
import subprocess,json,os
os.environ["OMP_NUM_THREADS"]="16"
from native_sta import fixture as sta_fixture
from lec_receive import fixture as lec_fixture
P=Path(__file__).resolve().parent;O=Path.cwd()/'controls';O.mkdir(exist_ok=False)
def run(args,log):
 with(O/log).open('w')as f:subprocess.run(args,cwd=O,stdout=f,stderr=subprocess.STDOUT,check=True)
(O/'sta').mkdir();sta_fixture(P,O/'sta',run)
(O/'lec').mkdir();lec_fixture(P,O/'lec',run)
(O/'receipt.json').write_text(json.dumps({'passed':True,'scope':'Actual positive/negative receiver controls only; no macro qualification'},indent=2)+'\n')
