"""Actual OpenROAD two-layer search preflight; never a system qualification.

The abstract search database has only passive M11 landing markers, no logic.
Native leaves, technology thresholds, geometry/PG/RC acceptors are untouched.
See official grt/drt README documentation for the search commands used here.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(out):
    tools = ROOT / 'project/experiments/block_v1'
    sys.path.insert(0, str(tools))
    from overlay import generate
    spec_path = tools / 'technology-2um-v1.json'
    spec = json.loads(spec_path.read_text())
    platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    generate(platform / 'lef/NangateOpenCellLibrary.tech.lef', spec, out / 'technology')
    search_tracks = out / 'search-custom-tracks.tcl'
    search_tracks.write_text(''.join(
        f'make_tracks metal{i} -x_offset 0.095 -x_pitch 8 -y_offset 0.070 -y_pitch 8\n'
        for i in (11, 12)))
    executable = shutil.which('openroad')
    assert executable
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    marker_lef = out / 'search-landing-markers.lef'
    # Top-level BTerms are boundary ports to FastRoute and cannot model the
    # internal landings faithfully. Passive pin-only masters model their exact
    # locations instead. They are search objects, never final native cells.
    marker_lef.write_text('VERSION 5.6 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + ''.join(
        f'MACRO search_landing_{direction.lower()}\n CLASS BLOCK ;\n ORIGIN 0 0 ;\n SIZE 2 BY 2 ;\n'
        f' PIN P\n  DIRECTION {direction} ;\n  USE SIGNAL ;\n  PORT\n   LAYER metal11 ;\n'
        '   RECT 0 0 2 2 ;\n  END\n END P\nEND search_landing_' + direction.lower() + '\n'
        for direction in ('INPUT', 'OUTPUT')) + 'END LIBRARY\n')
    records = []
    for mode in range(3):
        folder = out / ('case-' + str(mode))
        folder.mkdir()
        if mode == 0:
            terminals = {'bus_' + str(i): [(8, 8 + 2*i), (38, 34 - 2*i)] for i in range(12)}
        elif mode == 1:
            terminals = {
                'VDD': [(8, 8)] + [(12+4*i, 12+4*j) for i in range(7) for j in range(7) if (i+j) % 2 == 0],
                'VSS': [(40, 40)] + [(12+4*i, 14+4*j) for i in range(7) for j in range(7) if (i+j) % 2 == 1]}
        else:
            terminals = {'bus_' + str(i): [(8+2*i, 8), (38-2*i, 38), (8+2*i, 40)] for i in range(10)}
        (folder / 'terminals.json').write_text(json.dumps(terminals, indent=2) + '\n')
        # The same grid phase and physical landing size as system_geometry.py.
        # Supply-named fixture nets are SIGNAL only in this search abstraction;
        # actual system PG connectivity is checked separately, without waiver.
        lines = [
            f'read_lef {{{out / "technology/research12.tech.lef"}}}',
            f'read_lef {{{marker_lef}}}',
            'set db [ord::get_db]',
            'set chip [odb::dbChip_create $db [$db getTech]]',
            'set block [odb::dbBlock_create $chip search_probe]',
            '$block setDefUnits 2000',
            'set die [odb::new_Rect 0 0 384000 384000]',
            '$block setDieArea $die',
            'set layer [[$db getTech] findLayer metal11]',
            'set_thread_count 16',
        ]
        for name, ends in terminals.items():
            lines.append(f'set net [odb::dbNet_create $block {name}]')
            for index, (x, y) in enumerate(ends):
                xx, yy = 190+8000*x, 140+8000*y
                lines.extend([
                    'set master [$db findMaster search_landing_' + ('output' if index == 0 else 'input') + ']',
                    f'set inst [odb::dbInst_create $block $master {name}_p{index}]',
                    f'$inst setLocation {xx-2000} {yy-2000}',
                    '$inst setPlacementStatus FIRM',
                    'set term [$inst findITerm P]',
                    '$term connect $net',
                ])
        lines.extend([
            # GRT derives GCell dimensions from otherwise unused M2-M4 track
            # grids. Native submicron grids make GCells smaller than a single
            # legal M11/M12 track. These *search-only, unroutable* lower grids
            # set a 60um guide tile; no technology rules or native views change.
            'for {set i 1} {$i <= 10} {incr i} { make_tracks metal$i -x_offset 0.095 -x_pitch 4 -y_offset 0.070 -y_pitch 4 }',
            f'source {{{search_tracks}}}',
            # Search a strict subset of the physical stack: preferred wires
            # only, and every other custom track. This retains the original
            # checkerboard-via acceptance; no accepted geometry is broadened.
            'foreach name {metal11 metal12} { [[$db getTech] findLayer $name] setRightWayOnGridOnly true }',
            'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
            'help global_route', 'help detailed_route',
            f'write_db {{{folder / "before.odb"}}}',
            f'global_route -use_cugr -guide_file {{{folder / "route.guide"}}} -verbose',
            f'detailed_route -output_drc {{{folder / "drc.rpt"}}} -output_maze {{{folder / "maze.log"}}} '
            '-via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1',
            f'write_db {{{folder / "routed.odb"}}}',
            f'write_def {{{folder / "routed.def"}}}',
            f'source {{{tools / "odb_geometry.tcl"}}}',
            f'bvgeom::export {{{folder / "geometry.tsv"}}}',
        ])
        script = folder / 'run.tcl'
        script.write_text('\n'.join(lines) + '\n')
        command = [executable, '-exit', str(script)]
        with (folder / 'openroad.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=folder)
        records.append(dict(case=mode, command=command, returncode=result.returncode,
                            inputs_sha256=sha(folder / 'terminals.json'), script_sha256=sha(script),
                            log_sha256=sha(folder / 'openroad.log')))
        (out / 'probe-progress.json').write_text(json.dumps(records, indent=2) + '\n')
        assert result.returncode == 0, str(folder / 'openroad.log')
        assert (folder / 'geometry.tsv').stat().st_size > 0
    result = dict(passed=True, execution_passed=True, whole_system_qualified=False,
                  independent_physical_verification_passed=False, cases=records,
                  source_sha256=sha(__file__), technology_sha256=sha(spec_path),
                  scope='Actual small OpenROAD search execution only. Routed geometry still requires independent edge/grid/via/spacing/flood verification before any real-scene admission; no leaf or system qualification.')
    (out / 'openroad-probe.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
