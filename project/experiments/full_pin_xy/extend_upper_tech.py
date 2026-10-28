"""Explicit research-only M11/M12 extrapolation; preserve original ten layers.

No foundry, SRAM, full-rule, extraction calibration or manufacturing claim.
Existing Nangate45 M9/M10 geometry is the assumption source, not evidence that
Nangate45 has these extra layers. Original source files remain immutable.
"""
from pathlib import Path
import argparse, hashlib, json, re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def block(text, kind, name):
    pattern = r'^'+kind+r'[ \t]+'+re.escape(name)+r'[^\n]*\n.*?^END[ \t]+'+re.escape(name)+r'[ \t]*$'
    matches = list(re.finditer(pattern, text, re.M | re.S))
    assert len(matches) == 1, (kind, name, len(matches))
    return matches[0]


def renamed(text, mapping):
    return re.sub(r'\b(?:'+ '|'.join(map(re.escape, sorted(mapping, key=len, reverse=True)))+r')\b',
                  lambda m: mapping[m.group()], text)


def extend(source, rc_source, output):
    source, rc_source, output = Path(source), Path(rc_source), Path(output)
    assert not output.exists(), 'Refuse existing technology output'
    raw = source.read_bytes()
    assert digest(raw) == '834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2'
    s = raw.decode()
    assert not re.search(r'^LAYER\s+(?:metal11|metal12|via10|via11)\s*$', s, re.M)
    originals = {name: digest(block(s, 'LAYER', name).group().encode())
                 for name in ['metal'+str(i) for i in range(1, 11)] + ['via'+str(i) for i in range(1, 10)]}
    additions = []
    for cut, metal, donor, height in [(10, 11, 9, 14.09), (11, 12, 10, 18.09)]:
        additions.append(renamed(block(s, 'LAYER', 'via9').group(), {'via9': 'via'+str(cut)}))
        layer = renamed(block(s, 'LAYER', 'metal'+str(donor)).group(), {'metal'+str(donor): 'metal'+str(metal)})
        layer = re.sub(r'HEIGHT\s+[\d.]+\s*;', 'HEIGHT '+str(height)+' ;', layer)
        additions.append(layer)
    at = block(s, 'LAYER', 'metal10').end()
    extended = s[:at]+'\n\n'+'\n\n'.join(additions)+'\n'+s[at:]
    via_additions = []
    for cut in [10, 11]:
        mapping = {'via9': 'via'+str(cut), 'via9_0': 'via'+str(cut)+'_0',
                   'metal9': 'metal'+str(cut), 'metal10': 'metal'+str(cut+1),
                   'Via9Array-0': 'Via'+str(cut)+'Array-0'}
        for kind, name in [('VIA', 'via9_0'), ('VIARULE', 'Via9Array-0')]:
            via_additions.append(renamed(block(s, kind, name).group(), mapping))
    assert extended.count('END LIBRARY') == 1
    extended = extended.replace('END LIBRARY', '\n\n'.join(via_additions)+'\n\nEND LIBRARY')
    assert all(digest(block(extended, 'LAYER', name).group().encode()) == h for name, h in originals.items())
    rc = rc_source.read_text()
    for new, donor in [(11, 9), (12, 10)]:
        lines = [line for line in rc.splitlines() if re.match(r'set_layer_rc\s+-layer\s+metal'+str(donor)+r'\s', line)]
        assert len(lines) == 1
        rc += '\n# RESEARCH EXTRAPOLATION; uncalibrated upper layer\n'+renamed(lines[0], {'metal'+str(donor): 'metal'+str(new)})+'\n'
    output.mkdir(parents=True)
    with (output/'research12.tech.lef').open('w', encoding='utf-8', newline='\n') as f:
        f.write(extended)
    with (output/'research12.setRC.tcl').open('w', encoding='utf-8', newline='\n') as f:
        f.write(rc)
    manifest = {'scope': 'RESEARCH_ASSUMPTIONS_ONLY; not original Nangate45 M11/M12 or manufacturing qualification',
                'source_tech_sha256': digest(raw), 'source_RC_sha256': digest(rc_source.read_bytes()),
                'original_M1_M10_and_via1_via9_layer_blocks_identical': True, 'original_layer_block_hashes': originals,
                'upper_layers': {'metal11': {'donor': 'metal9', 'direction': 'HORIZONTAL', 'width_um': .8, 'pitch_um': 1.6, 'height_um': 14.09},
                                 'metal12': {'donor': 'metal10', 'direction': 'VERTICAL', 'width_um': .8, 'pitch_um': 1.6, 'height_um': 18.09}},
                'spacing': 'Complete original M9/M10 parallel-run-length spacing tables cloned; not just one uniform spacing',
                'via10_via11': {'donor': 'via9/via9_0/Via9Array-0', 'cut_size_um': [.8, .8], 'cut_spacing_um': .88,
                               'array_pitch_um': [1.68, 1.68], 'landing_size_um': [.8, .8], 'enclosure_um': [0, 0],
                               'resistance_ohm_per_cut': .5, 'note': 'Original research LEF zero enclosure copied explicitly; no claim of process validity'},
                'RC': 'M11/M12 clone platform setRC M9/M10 estimates; original 10-layer OpenRCX patterns are NOT a calibrated 12-layer extraction model',
                'required_RC_sensitivity_multipliers': [.5, 1., 2.],
                'not_checked': ['manufacturability', '12-layer full rule deck', 'antenna', 'LVS', 'coupling calibration', 'SRAM GDS', 'system functionality', 'system STA'],
                'files': {p.name: {'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size} for p in output.iterdir()}}
    (output/'model.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('RESEARCH_12_LAYER_MODEL_CREATED_NOT_QUALIFIED', output)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--rc-source', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    extend(a.source, a.rc_source, a.out)
