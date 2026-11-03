"""Independent source-binding/schema negative controls before any EDA call."""
from pathlib import Path
import tempfile, importlib.util, hashlib, json

module=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1\openroad_snapshot.py')
s=importlib.util.spec_from_file_location('snapshot',module);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory()as t:
    root=Path(t);files={}
    for n in ['before.odb','route.guide','terminals.json','run.tcl']:
        p=root/n;p.write_text(n);files[n]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    original=dict(schema='control162-openroad-search-snapshot-v1',iterations=1,nx=48,ny=48,inputs=files)
    controls=[]
    for name in ['schema','iterations','missing-input','wrong-sha','path-name','different-directory']:
        cfg=json.loads(json.dumps(original))
        if name=='schema':cfg['schema']='other'
        elif name=='iterations':cfg['iterations']=64
        elif name=='missing-input':del cfg['inputs']['run.tcl']
        elif name=='wrong-sha':cfg['inputs']['route.guide']['sha256']='0'*64
        elif name=='path-name':cfg['inputs']['run.tcl']['path']=str(root/'route.guide')
        else:
            p=root/'other/run.tcl';p.parent.mkdir();p.write_text('run.tcl');cfg['inputs']['run.tcl']['path']=str(p)
        path=root/'config.json';path.write_text(json.dumps(cfg))
        def bind(p,expected):assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==expected
        try:m.inspect(path,root,bind)
        except AssertionError:controls.append(dict(name=name,rejected=True))
        else:raise AssertionError('Invalid snapshot input accepted: '+name)
print(json.dumps(dict(passed=True,tested_module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),negative_cases=controls,scope='Six actual invalid schema/input-binding cases rejected before tool invocation. Positive read_db/read_guides replay requires separate actual server fixture; no physical qualification.')))
