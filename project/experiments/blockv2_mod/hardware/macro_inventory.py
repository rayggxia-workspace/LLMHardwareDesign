"""PR185 functional macro inventory, independent of control-group RTL hierarchy.

No product connection or group rectangle is inferred from this inventory.
Native port bindings and adapter implementations must be registered separately.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'evidence/architecture-revision-185/product-base-v1-inventory.json'

def build(contract_path=CONTRACT):
    path = Path(contract_path)
    contract = json.loads(path.read_text())
    groups, macros, controllers = {}, {}, {}
    for family, template in contract['templates'].items():
        for name in template['instances']:
            owned = []
            for role, profile_name in template['leaf_roles'].items():
                instance = name + '.' + role
                profile = deepcopy(contract['leaf_profiles'][profile_name])
                macros[instance] = {
                    'instance': instance, 'control_owner': name, 'role': role,
                    'profile': profile_name, 'master': profile['master'],
                    'hard_boundary': True, 'source_profile': profile,
                    'rtl_binding_status': 'requires_mod_instance_binding',
                }
                owned.append(instance)
            groups[name] = {
                'family': family, 'hard_boundary': False,
                'macros': owned, 'private_sram': name + '.S',
                'controller': name + '.LC',
                'implementation_id': template['implementation_id'],
            }
            controllers[name + '.LC'] = {
                'control_owner': name, 'implementation': 'parent_standard_cells',
                'program_memory': deepcopy(template['program_memory']),
            }
    assert len(groups) == 9 and len(macros) == 30
    assert sum(m['source_profile'].get('capacity_bytes', 0)
               for m in macros.values() if m['role'] == 'S') == 144 * 1024
    inventory = {
        'schema': 'blockv2-mod-macro-inventory/2',
        'contract_revision': contract['contract_revision'],
        'contract_sha256': sha256(path.read_bytes()).hexdigest(),
        'control_groups': groups, 'macro_instances': macros,
        'controllers': controllers,
        'system_resources': deepcopy(contract['system_resources']),
        'adapter_instances': {},
        'fixed_connections': [], 'candidate_connections': [],
        'connection_registration_status': 'not_yet_bound',
        'scope': 'Authoritative functional inventory; empty connection lists are not a claim that the hardware has no fixed control/service wires.',
        'mod_elaboration_accepted': False,
    }
    from service_resources import register
    inventory['adapter_instances'] = register(inventory)
    return inventory

def build_mod(contract_path=CONTRACT):
    inventory=build(contract_path)
    revision=json.loads((Path(__file__).parent/'n32-mod-revision.json').read_text())
    inventory['schema']='blockv2-mod-macro-inventory/2'
    inventory['mod_revision']='macro-services-v2-candidate'
    for macro in inventory['macro_instances'].values():
        if macro['profile']=='N32':
            macro['baseline_profile']='N32'
            macro['profile']=revision['profile']
            macro['master']=revision['master']
            macro['mod_revision']=deepcopy(revision)
            macro['inherited_physical_acceptance']=False
            macro['physical_views']=None
            macro['rtl_binding_status']='macro unit tested; full parent assembly pending'
    e_revision=json.loads((Path(__file__).parent/'e32-mac-mod-revision.json').read_text())
    if not e_revision.get('unit_evidence'):raise ValueError('E32 revision is not unit qualified')
    for macro in inventory['macro_instances'].values():
        if macro['profile']=='E32':
            macro['baseline_profile']='E32'
            macro['profile']=e_revision['profile'];macro['master']=e_revision['master']
            macro['mod_revision']=deepcopy(e_revision)
            macro['compatible_native_masters']=['e_s32_ap64']
            macro['compatibility_scope']='identical pins and old operations under an exclusive macro lease'
            macro['inherited_physical_acceptance']=False;macro['physical_views']=None
            macro['rtl_binding_status']='macro and dot service unit tested; full parent assembly pending'
    from service_resources import register
    inventory['adapter_instances']=register(inventory)
    return inventory

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, default=CONTRACT)
    p.add_argument('--mod',action='store_true',help='apply explicitly registered macro RTL revisions')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.write_text(json.dumps((build_mod if args.mod else build)(args.contract), indent=2) + '\n')
