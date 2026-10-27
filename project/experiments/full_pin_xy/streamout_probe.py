"""Run in KLayout: strict ORFS stream merge, no allow-empty exemptions."""
import hashlib,json,os,runpy,sys
from pathlib import Path
import pya

out=Path(os.environ['PINXY_STREAM_OUT']);spec=json.loads((out/'input.json').read_text())
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
tech=pya.Technology();tech.load(str(platform/'FreePDK45.lyt'))
options=tech.load_layout_options
options.lefdef_config.lef_files=spec['lefs']
tech.load_layout_options=options
tech.save(str(out/'technology.lyt'))
functions=runpy.run_path('/OpenROAD-flow-scripts/flow/util/def2stream.py')
errors=functions['merge_gds'](pya,str(out/'technology.lyt'),'',spec['def'],spec['top'],
    str(platform/'gds/NangateOpenCellLibrary.gds'),'',str(out/'diagnostic.gds'),allow_empty='',allow_empty_cells=frozenset())
receipt={'merge_errors':errors,'allow_empty':'DISABLED','klayout_version':pya.__version__,
    'status':'STREAM_MERGE_EXECUTED_NOT_DRC_LVS_QUALIFIED' if errors==0 else 'ACTUAL_STREAM_MERGE_FAILED',
    'no_missing_macro_waiver':True,
    'inputs_sha256':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in spec['lefs']+[spec['def'],str(platform/'gds/NangateOpenCellLibrary.gds'),str(platform/'drc/FreePDK45.lydrc')]}}
(out/'merge.json').write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(min(errors,125))
