"""Compare elaborated functional instances against PR185; never infer from filenames."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from macro_inventory import build

def audit(xml_path, group, inventory):
    root = ET.parse(xml_path).getroot()
    modules = {m.get('name'): m.get('origName') for m in root.findall('./netlist/module')}
    profiles = {x['master']: x['profile'] for x in inventory['macro_instances'].values()}
    # These are arithmetic providers outside the registered functional inventory.
    extra = {'block_v2_n', 'dot_s32_core', 's32_token_argmax'}
    instances = []
    for cell in root.findall('./cells//cell'):
        module = modules[cell.get('submodname')]
        if module in profiles or module in extra:
            instances.append({'rtl_path':cell.get('hier'), 'master':module,
                              'profile':profiles.get(module), 'location':cell.get('loc')})
    actual = Counter(x['master'] for x in instances)
    expected = Counter(inventory['macro_instances'][m]['master']
                       for m in inventory['control_groups'][group]['macros'])
    differences = [{'master':m,'expected':expected[m],'elaborated':actual[m]}
                   for m in sorted(set(actual) | set(expected)) if expected[m] != actual[m]]
    return {'group':group, 'xml':str(xml_path), 'instances':instances,
            'differences':differences, 'accepted':not differences,
            'scope':'Source elaboration instance census, not synthesis area; control arithmetic and memories require separate audit.'}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p-xml',type=Path,required=True)
    parser.add_argument('--u-xml',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    inventory=build()
    result={'contract_revision':inventory['contract_revision'],
            'results':[audit(args.p_xml,'P0',inventory),audit(args.u_xml,'U0',inventory)],
            'other_groups':'not elaborated in this receipt; no inferred pass',
            'accepted':False}
    result['accepted']=all(x['accepted'] for x in result['results'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for row in result['results']:
        print(row['group'],json.dumps(row['differences']))
