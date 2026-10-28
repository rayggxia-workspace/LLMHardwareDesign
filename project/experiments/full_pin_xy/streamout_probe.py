"""Run in KLayout: strict ORFS stream merge, no allow-empty exemptions."""
import hashlib,json,os,runpy,sys
from pathlib import Path
import pya

out=Path(os.environ['PINXY_STREAM_OUT']);spec=json.loads((out/'input.json').read_text())
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
tech=pya.Technology();tech.load(str(platform/'FreePDK45.lyt'))
options=tech.load_layout_options
options.lefdef_config.lef_files=spec['lefs']
auto_read_before=options.lefdef_config.read_lef_with_def
# Installed 0.30.12 API audit: the default also reads *all* sibling LEFs.
# These export directories contain default/detailed views of the same top;
# neither is a child-cell dependency of its own DEF. Keep exactly the source
# configuration's explicit standard-cell/SRAM LEFs, without changing geometry.
options.lefdef_config.read_lef_with_def=False
tech.load_layout_options=options
tech.save(str(out/'technology.lyt'))
roundtrip=pya.Technology();roundtrip.load(str(out/'technology.lyt'));roundtrip_options=roundtrip.load_layout_options
assert not roundtrip_options.lefdef_config.read_lef_with_def
assert list(roundtrip_options.lefdef_config.lef_files)==spec['lefs']
(out/'reader_configuration.json').write_text(json.dumps({
    'klayout_version':pya.__version__,'read_lef_with_def_before':auto_read_before,
    'read_lef_with_def_after':False,'explicit_LEFs_roundtrip_exact':True,'explicit_LEFs':spec['lefs'],
    'sibling_LEFs_not_implicitly_loaded':[str(p) for p in Path(spec['def']).parent.glob('*.lef')],
    'strict_missing_GDS_policy':'allow_empty disabled; no empty-cell exemptions',
    'reason':'Two same-top abstract views are export products, not child-cell dependencies of the top DEF.'},indent=2)+'\n')
functions=runpy.run_path('/OpenROAD-flow-scripts/flow/util/def2stream.py')
errors=functions['merge_gds'](pya,str(out/'technology.lyt'),'',spec['def'],spec['top'],
    str(platform/'gds/NangateOpenCellLibrary.gds'),'',str(out/'diagnostic.gds'),allow_empty='',allow_empty_cells=frozenset())
receipt={'merge_errors':errors,'allow_empty':'DISABLED','klayout_version':pya.__version__,
    'status':'STREAM_MERGE_EXECUTED_NOT_DRC_LVS_QUALIFIED' if errors==0 else 'ACTUAL_STREAM_MERGE_FAILED',
    'no_missing_macro_waiver':True,
    'inputs_sha256':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in spec['lefs']+[spec['def'],str(platform/'gds/NangateOpenCellLibrary.gds'),str(platform/'drc/FreePDK45.lydrc')]}}
(out/'merge.json').write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(min(errors,125))
