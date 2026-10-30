"""Run in KLayout; inspect installed reader API without loading/changing a design."""
from pathlib import Path
import hashlib,json,os
import pya

root=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
revision=os.environ.get('PINXY_READER_AUDIT_REV','streamout-reader-r01');assert revision.replace('-','').isalnum()
out=root/'tool_api'/revision;out.mkdir(parents=True,exist_ok=False)
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
tech=pya.Technology();tech.load(str(platform/'FreePDK45.lyt'))
# Keep the owning LoadLayoutOptions alive; cfg is a borrowed C++ child.
options=tech.load_layout_options;cfg=options.lefdef_config
attributes={}
for name in dir(cfg):
    if 'lef' not in name and 'read' not in name:continue
    try:value=getattr(cfg,name)
    except AttributeError as e:attributes[name]={'readable':False,'error':str(e)};continue
    if not callable(value):attributes[name]=value
docs={name:getattr(type(cfg),name).__doc__ for name in attributes}
source=Path('/OpenROAD-flow-scripts/flow/util/def2stream.py');text=source.read_text()
(out/'def2stream_reader_excerpt.txt').write_text('\n'.join(text.splitlines()[25:75])+'\n')
record={'scope':'INSTALLED_READER_API_ONLY_NOT_DESIGN_QUALIFICATION','klayout_version':pya.__version__,
        'scheduler_job':os.environ.get('SLURM_JOB_ID'),'attributes':attributes,'attribute_documentation':docs,
        'source_SHA256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,platform/'FreePDK45.lyt']},
        'full_qualification':False}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
print('STREAMOUT_READER_API_AUDITED',pya.__version__)
