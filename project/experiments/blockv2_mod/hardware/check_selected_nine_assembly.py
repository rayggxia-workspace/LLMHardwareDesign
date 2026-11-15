"""Audit actual elaboration boundaries/owners; generation alone is not evidence."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,sys,shutil
import xml.etree.ElementTree as E
from check_parent_service_structure import FORBIDDEN
ROOT=Path(__file__).resolve().parents[1]
def inspect(tree,manifest):
 exclusions=json.loads((ROOT/'hardware/pr185-historical-source-disposition.json').read_text())['files']
 excluded={(ROOT/name).resolve() for name in exclusions}
 for source in tree.findall('./files/file'):
  p=Path(source.get('filename',''));p=p if p.is_absolute() else ROOT/p
  if p.resolve() in excluded:
   raise ValueError('historical/rejected source in production closure: '+str(p))
 modules={m.get('name'):m for m in tree.findall('./netlist/module')}
 root=tree.find('./cells/cell');prefix=root.get('hier')+'.'
 cells={c.get('hier')[len(prefix):]:c for c in root.iter('cell') if c is not root}
 if manifest.get('hard_boundary') is not False:
  raise ValueError('selected product cannot be a composite hard macro')
 registry=json.loads((ROOT/'hardware/pr185-parent-resource-admission.json').read_text())
 observed={path:modules[c.get('submodname')].get('origName') for path,c in cells.items()
           if path=='controls' or path.startswith('controls.')}
 if observed!=registry['instances']:
  changed=sorted(k for k in set(observed)|set(registry['instances'])
                 if observed.get(k)!=registry['instances'].get(k))
  raise ValueError('unregistered parent resource composition: '+str(changed[:8]))
 actual={};owners={}
 for name,master in manifest['functional_instances'].items():
  if name not in cells:raise ValueError('missing functional macro '+name)
  module=modules[cells[name].get('submodname')].get('origName')
  if module!=master:raise ValueError('wrong master '+name)
  actual[name]=module
 roots=set(actual)
 for path,c in cells.items():
  module=modules[c.get('submodname')].get('origName')
  if path=='controls' or path.startswith('controls.'):
   if module in FORBIDDEN:
    # Program SRAM is explicitly registered system storage, not a private S.
    if not (module in ('block_feed_s16k_sram','s_sram_256x128_freepdk45') and path.startswith('controls.mother.mother.program_store.')):
     raise ValueError('hidden functional resource in controls '+path+' '+module)
  elif path.split('.')[0]+'.'+path.split('.')[1] not in roots:
   raise ValueError('unregistered non-control instance '+path)
  if module=='lc_native_scope_controller':
   value=modules[c.get('submodname')].find("./var[@name='TARGET']/const")
   if value is None:raise ValueError('LC target not elaborated')
   owner=path.split('.')[1];owners[owner]=int(value.get('name').split("'h")[1],16)
 expected={n:i for i,n in enumerate(('P0','P1','P2','C0','U0','J0','F0','U1','J1'))}
 if owners!=expected:raise ValueError('incorrect nine LC identities')
 counts=Counter(modules[c.get('submodname')].get('origName') for c in cells.values())
 for module,count in {'lc_native_scope_controller':9,'lc_program_store_1k':9,
 'mother_control_native64_transport128':1,'control_pm':1,'mc_lc_packet128_switch':1,
 'native_shared_memory_dma':1,'native64_dma_serial_client':9,'native64_dma_read_window_client':9}.items():
  if counts[module]!=count:raise ValueError('incorrect parent resource count '+module)
 return {'functional_instances':actual,'LC_targets':owners,'instance_counts':dict(counts)}
def main():
 folder=Path(sys.argv[1]);xml=folder/'parent.xml'
 manifest=json.loads((ROOT/'hardware/selected-nine-assembly.json').read_text())
 tree=E.parse(xml).getroot();result=inspect(tree,manifest)
 # Reject a copied G core hidden in control hierarchy even when all expected
 # thirty macros remain present.
 bad=E.fromstring(E.tostring(tree))
 original=next(m for m in bad.findall('./netlist/module') if m.get('origName')=='g_s32')
 E.SubElement(bad.find('./cells/cell'),'cell',name='hidden',submodname=original.get('name'),
  hier=bad.find('./cells/cell').get('hier')+'.controls.hidden_G')
 try:inspect(bad,manifest)
 except ValueError:pass
 else:raise AssertionError('hidden extra G accepted')
 deps={}
 for f in tree.findall('./files/file'):
  p=Path(f.get('filename',''))
  p=p if p.is_absolute() else ROOT/p
  if not p.is_file():continue
  deps[str(p)]=sha256(p.read_bytes()).hexdigest()
  q=folder/'validated-source'/(p.relative_to(ROOT) if p.is_relative_to(ROOT) else Path('external')/str(p).lstrip('/'))
  q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 result.update(schema='selected-nine-elaboration/1',xml_sha256=sha256(xml.read_bytes()).hexdigest(),
  source_sha256=deps,hidden_macro_negative_case=True,elaboration_accepted=True,
  whole_base_accepted=False,numerical_execution_accepted=False,
  scope='actual thirty leaf instances and nine control identities; instruction execution/physical acceptance not implied')
 (folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'functional_macros':len(result['functional_instances']),'LC_targets':result['LC_targets'],
 'source_files':len(deps),'hidden_macro_negative_case':True,'whole_base_accepted':False}))
if __name__=='__main__':main()
