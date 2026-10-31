"""Extend the actual platform's KLayout mapping without native mask changes."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def generate(platform,spec,out):
    original=platform/'FreePDK45.lyt'
    assert hashlib.sha256(original.read_bytes()).hexdigest()=='45382e7c1ad2c3727fec79fc0249dceff8ce8fab8ef815017ad5de3350a87a12'
    tree=ET.parse(original);technology=tree.getroot()
    layer_map=technology.find('reader-options/lefdef/layer-map')
    existing={name:(int(layer),int(datatype))for name,layer,datatype in re.findall(r"'([^']+)\s+:\s+(\d+)/(\d+)'",layer_map.text)}
    assert existing['metal10']==(29,0) and existing['via9']==(28,0)
    custom={name:tuple(pair)for name,pair in spec['gds'].items()}
    # The native .lyt already reserves via10=30 even though no via10 exists
    # in the actual ten-layer tech LEF. Replace this unused placeholder only.
    retained={name:pair for name,pair in existing.items()if name.split('.')[0]not in custom}
    assert not set(retained.values()) & set(custom.values()),'native declared mapping collision'
    entries=dict(retained)
    for name,pair in custom.items():
        for suffix in ['', '.LABEL','.PIN']:
            entries[name+suffix]=pair
    layer_map.text='layer_map('+ ';'.join("'%s : %d/%d'"%(name,*pair)for name,pair in entries.items())+')'
    technology.find('name').text=spec['name']
    technology.find('description').text='Nangate45 research twelve-layer extension; explicit assumptions'
    technology.find('base-path').text='.'
    technology.find('original-base-path').text='.'
    # Actual LEFs are explicitly passed to each standalone read, preventing
    # the original relative .mod.lef path from resolving to another version.
    for child in list(technology.find('reader-options/lefdef')):
        if child.tag=='lef-files':technology.find('reader-options/lefdef').remove(child)
    connectivity=technology.find('connectivity')
    for name in ['metal10,via10,metal11','metal11,via11,metal12']:
        ET.SubElement(connectivity,'connection').text=name
    for name,pair in custom.items():ET.SubElement(connectivity,'symbols').text="%s='%d/%d'"%(name,*pair)
    out.mkdir(exist_ok=False)
    tree.write(out/'research12.lyt',encoding='utf-8',xml_declaration=True)
    (out/'mapping.json').write_text(json.dumps(dict(native_lyt_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        native_routing_layers_1_to_10_preserved=True,native_cut_layers_1_to_9_preserved=True,
        replaced_unused_placeholder={'via10':[30,0]},custom=custom,
        qualification='Mapping overlay only; geometry/extraction qualification separate'),indent=2)+'\n')

