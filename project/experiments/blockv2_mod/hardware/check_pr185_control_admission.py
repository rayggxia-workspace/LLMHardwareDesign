"""Fail closed on stale/undeclared parent controls before graph compilation.

This admits the recorded RTL control hierarchy only. It does not certify the
nine-owner assembly, candidate data wiring, numerical execution or physical views.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json
import xml.etree.ElementTree as ET
from macro_inventory import build as baseline, build_mod
from check_parent_service_structure import FORBIDDEN
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'
RECEIPT=OUT/'native-owner-control-structure-receipt.json'
XML_DIR=OUT/'native-owner-controls-114847'

def check_hierarchy(tree, hardware, expected):
    modules={m.get('name'):m.get('origName') for m in tree.findall('./netlist/module')}
    counts=Counter()
    for cell in tree.findall('./cells//cell'):
        name=modules.get(cell.get('submodname'))
        if not name:raise ValueError('unresolved elaborated control instance')
        counts[name]+=1
    functional={m['master'] for m in hardware['macro_instances'].values()}
    functional.update(m['master'] for m in baseline()['macro_instances'].values())
    bad=(functional|FORBIDDEN).intersection(counts)
    if bad:raise ValueError('functional macro hidden in parent controls: '+str(sorted(bad)))
    if dict(counts)!=expected:
        raise ValueError('control hierarchy differs from recorded resource inventory')
    if counts['lc_native_scope_controller']!=1 or counts['lc_program_store_1k']!=1:
        raise ValueError('one real LC and finite 1 KiB PM required per control owner')
    return counts

def validate(hardware):
    reference=baseline()
    if set(hardware['control_groups'])!=set(reference['control_groups']):
        raise ValueError('PR185 requires the original nine control owners')
    if set(hardware['macro_instances'])!=set(reference['macro_instances']):
        raise ValueError('PR185 requires the original thirty functional macro instances')
    for name,group in hardware['control_groups'].items():
        old=reference['control_groups'][name]
        if group.get('hard_boundary') is not False:
            raise ValueError('control group cannot be a physical hard boundary: '+name)
        if set(group['macros'])!=set(old['macros']) or group['private_sram']!=old['private_sram']:
            raise ValueError('changed macro ownership or private SRAM: '+name)
    revised=build_mod()['macro_instances']
    for name,macro in hardware['macro_instances'].items():
        old=reference['macro_instances'][name]
        if macro['master']!=revised[name]['master']:
            raise ValueError('unregistered macro revision: '+name)
        if macro.get('hard_boundary') is not True or macro['control_owner']!=old['control_owner']:
            raise ValueError('invalid functional macro boundary or ownership: '+name)
    receipt=json.loads(RECEIPT.read_text())
    # Hashes are frozen evidence, never generated from current sources here.
    source_hashes={}
    for name,h in receipt['sources'].items():
        p=Path(name)
        if p.suffix not in ('.sv','.svh','.v'):continue
        p=p if p.is_absolute() else ROOT/p
        if not p.is_file() or sha256(p.read_bytes()).hexdigest()!=h:
            raise ValueError('stale control elaboration; rerun affected RTL: '+str(p))
        source_hashes[str(p)]=h
    parents=[]
    active=set()
    for row in receipt['rows']:
        path=XML_DIR/(row['family']+'.xml')
        if sha256(path.read_bytes()).hexdigest()!=row['xml_sha256']:
            raise ValueError('modified elaboration evidence: '+str(path))
        tree=ET.parse(path).getroot()
        counts=check_hierarchy(tree,hardware,row['instances'])
        files={f.get('id'):f.get('filename') for f in tree.findall('./files/file')}
        instances=[]
        for mod in tree.findall('./netlist/module'):
            name=files[mod.get('loc').split(',')[0]]
            p=Path(name);p=p if p.is_absolute() else ROOT/p
            if str(p) not in source_hashes:
                raise ValueError('elaborated module has no frozen source hash: '+str(p))
            active.add(str(p))
            instances.append({'module':mod.get('origName'),'source':str(p),
                              'sha256':source_hashes[str(p)]})
        parents.append({'family':row['family'],'instances':dict(counts),
                        'modules':instances,'xml_sha256':row['xml_sha256']})
    return {'schema':'pr185-control-admission/1','parents':parents,
            'active_module_sources':sorted(active),
            'frozen_dependency_sources':source_hashes,
            'recorded_hierarchy_admitted':True,'whole_base_accepted':False,
            'scope':'recorded control hierarchies only; data wiring, full assembly and execution still required'}

if __name__=='__main__':
    result=validate(json.loads((ROOT/'hardware/blockv2-mod-macros.json').read_text()))
    target=OUT/'current-control-admission.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'parents':len(result['parents']),
                     'module_sources':len(result['active_module_sources']),
                     'dependencies':len(result['frozen_dependency_sources']),
                     'whole_base_accepted':False}))
