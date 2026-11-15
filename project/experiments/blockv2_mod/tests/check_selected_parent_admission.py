"""Whole selected-assembly admission, including renamed/duplicated parent logic."""
import copy,json,sys
from pathlib import Path
import xml.etree.ElementTree as E
from check_selected_nine_assembly import inspect,ROOT
tree=E.parse(sys.argv[1]).getroot()
manifest=json.loads((ROOT/'hardware/selected-nine-assembly.json').read_text())
good=inspect(tree,manifest);checks=[]
def reject(name,t,m):
 try:inspect(t,m)
 except ValueError:checks.append(name)
 else:raise AssertionError('accepted '+name)
for name,master in [('renamed_arithmetic','new_arithmetic'),('duplicate_adapter','s32_a16_tile_quantizer'),
                    ('hidden_G','g_s32'),('hidden_argmax','s32_token_argmax')]:
 t=copy.deepcopy(tree);E.SubElement(t.find('netlist'),'module',name='injected',origName=master)
 root=t.find('./cells/cell')
 E.SubElement(root,'cell',name='injected',submodname='injected',hier=root.get('hier')+'.controls.injected')
 reject(name,t,manifest)
exclusions=json.loads((ROOT/'hardware/pr185-historical-source-disposition.json').read_text())['files']
for path in exclusions:
 t=copy.deepcopy(tree)
 E.SubElement(t.find('files'),'file',id='injected',filename=str(ROOT/path))
 reject('excluded_source:'+path,t,manifest)
m=copy.deepcopy(manifest);m['hard_boundary']=True
reject('composite_hard_boundary',tree,m)
t=copy.deepcopy(tree)
c=next(c for c in t.findall('./cells//cell') if c.get('hier','').endswith('.controls.P0.control'))
c.set('hier',c.get('hier').replace('.P0.','.U0.'))
reject('changed_control_owner',t,manifest)
print(json.dumps({'functional_macros':len(good['functional_instances']),'negative_cases':checks,
 'scope':'full elaborated assembly structural admission; no numerical or physical acceptance'}))
