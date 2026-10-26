"""Prepare native ten-layer flow inputs; does not launch physical implementation."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from pin_plan import generate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root, out):
    base = out.parents[2]
    config=json.loads((root/'project/experiments/block_v1/native_pipeline.json').read_text())
    source = base/config['physical_inputs_run']/'tasks'/config['physical_inputs_task']
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is True
    budget = json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    native = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
    technology = json.loads((root/'project/experiments/block_v1/technology.json').read_text())
    assert sha(native) == technology['native_tech_sha256']
    m10 = re.search(r'(?ms)^LAYER metal10\s*\n(.*?)^END metal10\s*$', native.read_text()).group(1)
    for key, value in [('WIDTH', .8), ('PITCH', 1.6)]:
        assert float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;', m10).group(1)) == value
    trackfile=native.parents[1]/'make_tracks.tcl'
    tracks={}
    for metal in ['metal9','metal10']:
        line=re.search(r'(?m)^make_tracks '+metal+r' (.+)$',trackfile.read_text()).group(1)
        values=line.split();assert len(values)==8
        tracks[metal]={values[i]:float(values[i+1])for i in range(0,len(values),2)}
    assert tracks['metal9']==tracks['metal10'],'Via access needs explicit two-layer track-grid intersection'
    via9=re.search(r'(?ms)^LAYER via9\s*\n(.*?)^END via9\s*$',native.read_text()).group(1)
    def cut(key):return float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;',via9).group(1))
    grid=dict(pitch_x=tracks['metal10']['-x_pitch'],pitch_y=tracks['metal10']['-y_pitch'],
        offset_x=tracks['metal10']['-x_offset'],offset_y=tracks['metal10']['-y_offset'],
        width=.8,cut_width=cut('WIDTH'),cut_spacing=cut('SPACING'),
        track_file_sha256=sha(trackfile),native_tech_sha256=sha(native))
    candidates = []
    for top, leaf in budget['leaves'].items():
        inputs = out/'inputs'/top
        inputs.mkdir(parents=True)
        for suffix in ['.v', '.sdc', '-ports.json']:
            name = top+suffix
            assert sha(source/name) == receipt['outputs'][name]
            shutil.copyfile(source/name, inputs/name)
        proof=source/(top+'-structural-proof.json')
        assert sha(proof)==receipt['outputs'][proof.name]
        checked=json.loads(proof.read_text())
        assert checked['passed']is True and checked['single_pin_bit_negative_rejected']is True
        from constraints import generate as constraints
        previous_sdc_sha256=sha(inputs/(top+'.sdc'))
        (inputs/(top+'.sdc')).write_text(constraints(budget))
        bits = json.loads((inputs/(top+'-ports.json')).read_text())
        for policy in ['A', 'C']:
            folder = out/(top+'-'+policy)
            folder.mkdir()
            plan = generate(bits, leaf, policy,grid)
            (folder/'pins.json').write_text(json.dumps(plan, indent=2)+'\n')
            def tcl_string(s):
                assert not any(c in s for c in '{}\\\n\r')
                return '{'+s+'}'
            script = '# Exact current-source M10 candidate; all IO geometry is prefabricated.\n'
            script += 'set planned_pins [dict create]\n'
            for pin in plan['pins']:
                name = tcl_string(pin['pin']); x, y = pin['xy_um']; w, h = pin['size_um']
                script += 'dict set planned_pins '+name+' 1\n'
                script += 'place_pin -pin_name '+name+' -layer metal10 -location {%.9f %.9f} -pin_size {%.9f %.9f}\n' % (x,y,w,h)
            script += r'''
set actual_pins {}
foreach pin [[ord::get_db_block] getBTerms] {
  if {[$pin getSigType] ni {POWER GROUND}} { lappend actual_pins [$pin getName] }
}
if {[lsort $actual_pins] ne [lsort [dict keys $planned_pins]]} {
  error "Physical IO inventory differs from exact mapped input"
}
'''
            (folder/'pins.tcl').write_text(script)
            width, height = leaf['die_um']; margin = leaf['core_margin_um']
            config = 'export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\n'
            config += 'export DESIGN_NICKNAME = bv1_'+top+'_'+policy+'\n'
            config += 'export VERILOG_FILES = '+str(inputs/(top+'.v'))+'\n'
            config += 'export SDC_FILE = '+str(inputs/(top+'.sdc'))+'\n'
            config += 'export DIE_AREA = 0 0 %g %g\n' % (width,height)
            config += 'export CORE_AREA = %g %g %g %g\n' % (margin,margin,width-margin,height-margin)
            config += 'export PLACE_DENSITY = 0.45\n'
            # Standard ORFS manual-footprint path: place fixed pins after
            # floorplan initialization; the ordinary IO placer copies them.
            config += 'export FOOTPRINT_TCL = '+str(folder/'pins.tcl')+'\n'
            config += 'override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
            # The stock IO step checks FOOTPRINT_TCL after stage filtering.
            # Preserve the configured manual footprint across those stages.
            config += 'export KEEP_VARS = 1\n'
            (folder/'config.mk').write_text(config)
            candidates.append(dict(top=top,policy=policy,ports=plan['ports'],internal_ports=plan['internal_ports'],
                folder=str(folder),config_sha256=sha(folder/'config.mk'),pins_sha256=sha(folder/'pins.json'),
                netlist_sha256=sha(inputs/(top+'.v')),sdc_sha256=sha(inputs/(top+'.sdc')),
                original_sdc_sha256=previous_sdc_sha256,structural_proof_sha256=sha(proof),
                command_capacitance_unit='fF',output_load_ff=budget['output_load_pf']*1000,
                budget=leaf,physical_implementation_started=False))
    (out/'native-preparation.json').write_text(json.dumps(dict(schema='block-v1-native-preparation/1',
        candidates=candidates,source_receipt_sha256=sha(source/'receipt.json'),native_tech_sha256=sha(native),
        qualification='Source-bound A/C* pin and flow configuration preparation only; no P&R/STA/DRC pass'),indent=2)+'\n')
