"""Register only parent compositions independently validated in fresh family XML."""
import json,sys,hashlib
from pathlib import Path
import xml.etree.ElementTree as E
from check_pr185_control_admission import validate
root=Path.cwd();control=Path(sys.argv[1]);assembly=Path(sys.argv[2]);seed=Path(sys.argv[3])
validate(json.loads(seed.read_text()),receipt_path=control/'receipt.json',xml_directory=control)
def instances(path):
 t=E.parse(path).getroot();mods={m.get('name'):m.get('origName') for m in t.findall('./netlist/module')}
 top=t.find('./cells/cell');prefix=top.get('hier')
 return {c.get('hier')[len(prefix):].lstrip('.'):mods[c.get('submodname')] for c in top.iter('cell')}
observed=instances(assembly/'parent.xml')
observed={k:v for k,v in observed.items() if k=='controls' or k.startswith('controls.')}
registry=root/'hardware/pr185-parent-resource-admission.json';prior=json.loads(registry.read_text())
expected=dict(prior['instances'])
for family,owners in [('p',['P0','P1','P2']),('n',['U0','U1']),('e',['C0','F0','J0','J1'])]:
 subtree=instances(control/(family+'.xml'))
 for owner in owners:
  prefix='controls.'+owner+'.control'
  expected={k:v for k,v in expected.items() if not(k==prefix or k.startswith(prefix+'.'))}
  expected.update({prefix+('.'+k if k else ''):v for k,v in subtree.items()})
for i in range(9):
 old=f'controls.memory.service_client__BRA__{i}__KET__.serial'
 new=f'controls.memory.service_client__BRA__{i}__KET__.read_window'
 if old in expected:
  if expected.pop(old)!='native64_dma_serial_client':raise ValueError('unexpected former read adapter')
 elif expected.get(new)!='native64_dma_read_window_client':raise ValueError('missing registered read adapter')
 expected[new]='native64_dma_read_window_client'
if observed!=expected:
 differences={k:(expected.get(k),observed.get(k)) for k in expected.keys()|observed.keys() if expected.get(k)!=observed.get(k)}
 raise ValueError('unvalidated parent differences '+str(differences))
prior.update(instances=expected,reference_xml_sha256=hashlib.sha256((assembly/'parent.xml').read_bytes()).hexdigest(),control_proof=str((control/'receipt.json').resolve()))
registry.write_text(json.dumps(prior,indent=2)+'\n')
print('registered independently validated parents',len(expected))
