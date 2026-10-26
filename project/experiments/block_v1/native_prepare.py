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
    source = base/'block-v1-20261027-010/tasks/physical-inputs'
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is True
    budget = json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    native = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
    technology = json.loads((root/'project/experiments/block_v1/technology.json').read_text())
    assert sha(native) == technology['native_tech_sha256']
    m10 = re.search(r'(?ms)^LAYER metal10\s*\n(.*?)^END metal10\s*$', native.read_text()).group(1)
    for key, value in [('WIDTH', .8), ('PITCH', 1.6)]:
        assert float(re.search(r'(?m)^\s*'+key+r'\s+([\d.]+)\s*;', m10).group(1)) == value
    candidates = []
    for top, leaf in budget['leaves'].items():
        inputs = out/'inputs'/top
        inputs.mkdir(parents=True)
        for suffix in ['.v', '.sdc', '-ports.json']:
            name = top+suffix
            assert sha(source/name) == receipt['outputs'][name]
            shutil.copyfile(source/name, inputs/name)
        bits = json.loads((inputs/(top+'-ports.json')).read_text())
        for policy in ['A', 'C']:
            folder = out/(top+'-'+policy)
            folder.mkdir()
            plan = generate(bits, leaf, policy)
            (folder/'pins.json').write_text(json.dumps(plan, indent=2)+'\n')
            def tcl_string(s):
                assert not any(c in s for c in '{}\\\n\r')
                return '{'+s+'}'
            script = '# Exact current-source M10 candidate; all IO geometry is prefabricated.\n'
            script += 'set planned_pins [dict create]\n'
            for pin in plan['pins']:
                name = tcl_string(pin['pin']); x, y = pin['xy_um']; w, h = pin['size_um']
                script += 'dict set planned_pins '+name+' 1\n'
                script += 'place_pin -pin_name '+name+' -layer metal10 -location {%g %g} -pin_size {%g %g}\n' % (x,y,w,h)
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
            config += 'export MIN_ROUTING_LAYER = metal1\nexport MAX_ROUTING_LAYER = metal10\n'
            (folder/'config.mk').write_text(config)
            candidates.append(dict(top=top,policy=policy,ports=plan['ports'],internal_ports=plan['internal_ports'],
                folder=str(folder),config_sha256=sha(folder/'config.mk'),pins_sha256=sha(folder/'pins.json'),
                netlist_sha256=sha(inputs/(top+'.v')),sdc_sha256=sha(inputs/(top+'.sdc')),
                budget=leaf,physical_implementation_started=False))
    (out/'native-preparation.json').write_text(json.dumps(dict(schema='block-v1-native-preparation/1',
        candidates=candidates,source_receipt_sha256=sha(source/'receipt.json'),native_tech_sha256=sha(native),
        qualification='Source-bound A/C* pin and flow configuration preparation only; no P&R/STA/DRC pass'),indent=2)+'\n')
