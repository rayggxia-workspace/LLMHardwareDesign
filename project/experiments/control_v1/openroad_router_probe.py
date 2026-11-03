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


def run(out, scene=None, congestion_iterations=5, global_router='cugr',guide_pitch=4):
    assert congestion_iterations in (5, 20, 50)
    assert global_router in ('cugr','fastroute')
    assert guide_pitch in (1.6,4)
    from openroad_grid import regression
    guards = regression(out / 'parser-regression')
    tools = ROOT / 'project/experiments/block_v1'
    sys.path.insert(0, str(tools))
    from overlay import generate
    spec_path = tools / 'technology-2um-v1.json'
    spec = json.loads(spec_path.read_text())
    platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    generate(platform / 'lef/NangateOpenCellLibrary.tech.lef', spec, out / 'technology')
    search_tracks = out / 'search-custom-tracks.tcl'
    search_tracks.write_text(''.join(
        f'make_tracks metal{i} -x_offset 0.095 -x_pitch 4 -y_offset 0.070 -y_pitch 4\n'
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
    for mode in (range(3) if scene is None else [0]):
        folder = out / ('case-' + str(mode))
        folder.mkdir()
        nx, ny = (48, 48) if scene is None else (scene['nx'], scene['ny'])
        assert nx >= 16 and ny >= 16
        width, height = nx*8000, ny*8000
        if scene is not None:
            terminals = scene['terminals']
        elif mode == 0:
            terminals = {'bus_' + str(i): [(8, 8 + 2*i), (38, 34 - 2*i)] for i in range(12)}
        elif mode == 1:
            terminals = {
                'VDD': [(8, 8)] + [(12+4*i, 12+4*j) for i in range(7) for j in range(7) if (i+j) % 2 == 0],
                'VSS': [(40, 40)] + [(12+4*i, 14+4*j) for i in range(7) for j in range(7) if (i+j) % 2 == 1]}
        else:
            terminals = {'bus_' + str(i): [(8+2*i+i%2, 8+(i//2)%2),
                          (38-2*i+i%2, 38+(i//2)%2), (8+2*i+i%2, 40+(i//2)%2)] for i in range(10)}
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
            f'set die [odb::new_Rect 0 0 {width} {height}]',
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
        # Same four-grid-cell margin as the existing C++/Python acceptance.
        # Keepouts restrict the search; they add no final conductors or cells.
        lo_x, lo_y = 190+8000*4-6000, 140+8000*4-6000
        hi_x, hi_y = 190+8000*(nx-5)+6000, 140+8000*(ny-5)+6000
        for layer in ('metal11', 'metal12'):
            lines.append(f'set guard_layer [[$db getTech] findLayer {layer}]')
            for x0, y0, x1, y1 in ((0, 0, lo_x, height), (hi_x, 0, width, height),
                                   (0, 0, width, lo_y), (0, hi_y, width, height)):
                lines.append(f'odb::dbObstruction_create $block $guard_layer {x0} {y0} {x1} {y1}')
        # One-nanometer search-only cut keepouts exclude exactly the original
        # forbidden checkerboard sites. Adjacent legal centers remain 4um away,
        # exceeding cut half-width + 2.2um spacing. No final mask shape is added.
        lines.extend([
            'set cut_layer [[$db getTech] findLayer via11]',
            f'for {{set x 4}} {{$x < {nx-4}}} {{incr x}} {{ for {{set y 4}} {{$y < {ny-4}}} {{incr y}} {{',
            ' if {($x+$y)%2} { set xx [expr {190+8000*$x}]; set yy [expr {140+8000*$y}];',
            ' odb::dbObstruction_create $block $cut_layer [expr {$xx-1}] [expr {$yy-1}] [expr {$xx+1}] [expr {$yy+1}] }',
            '} }',
        ])
        lines.extend([
            # GRT derives GCell dimensions from otherwise unused M2-M4 track
            # grids. Native submicron grids make GCells smaller than a single
            # legal M11/M12 track. These *search-only, unroutable* lower grids
            # set a 60um guide tile; no technology rules or native views change.
            f'for {{set i 1}} {{$i <= 10}} {{incr i}} {{ make_tracks metal$i -x_offset 0.095 -x_pitch {guide_pitch} -y_offset 0.070 -y_pitch {guide_pitch} }}',
            f'source {{{search_tracks}}}',
            'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
            'help global_route', 'help detailed_route',
            f'write_db {{{folder / "before.odb"}}}',
            f'global_route {"-use_cugr " if global_router=="cugr" else ""}{"-grid_origin {190 140} " if guide_pitch==1.6 else ""}-congestion_iterations {congestion_iterations} -congestion_report_file {{{folder / "congestion.rpt"}}} -congestion_report_iter_step {congestion_iterations} -guide_file {{{folder / "route.guide"}}} -verbose',
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
        assert (folder / 'drc.rpt').read_text().strip() == '', 'Actual router DRC report is nonempty'
        from openroad_grid import read
        branches, proof = read(folder / 'routed.def', terminals, nx, ny)
        (folder / 'trees.json').write_text(json.dumps(branches) + '\n')
        (folder / 'grid-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        records[-1]['outputs'] = {name: sha(folder/name) for name in
                                 ('routed.def', 'routed.odb', 'geometry.tsv', 'drc.rpt', 'trees.json', 'grid-proof.json')}
    result = dict(passed=True, execution_passed=True, whole_system_qualified=False,
                  congestion_iterations=congestion_iterations,
                  global_router=global_router,
                  unused_lower_search_track_pitch_um=guide_pitch,
                  global_guide_origin_dbu=[190,140]if guide_pitch==1.6 else[0,0],
                  parser_regression=guards,
                  independent_grid_verification_passed=True, independent_physical_verification_passed=False, cases=records,
                  source_sha256=sha(__file__), technology_sha256=sha(spec_path),
                  scope='Actual small OpenROAD search, empty router DRC, and strict independent original edge/grid/checkerboard/margin/flood verification. Full native/actual geometry, PG and RC acceptance remain mandatory; no leaf or system qualification.')
    (out / 'openroad-probe.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def route(terminals, nx, ny, seed, out, wire_limits, congestion_iterations=5, global_router='cugr',guide_pitch=4):
    """Return only independently checked trees; unchanged downstream gates apply."""
    folder = out / 'openroad-search'
    folder.mkdir(exist_ok=False)
    result = run(folder, dict(terminals=terminals, nx=nx, ny=ny), congestion_iterations,global_router,guide_pitch)
    assert result['passed'] and result['independent_grid_verification_passed']
    branches = json.loads((folder / 'case-0/trees.json').read_text())
    proof = json.loads((folder / 'case-0/grid-proof.json').read_text())
    for name, limit in wire_limits.items():
        edges = {tuple(sorted((tuple(v), tuple(w)))) for path in branches[name]
                 for v, w in zip(path, path[1:]) if v[2] == w[2]}
        assert len(edges) <= limit, ('Original optimistic source wire budget exceeded', name, len(edges), limit)
    proof.update(seed=seed, placement_seed=seed, backend='OpenROAD CUGR/TritonRoute',
                 whole_system_qualified=False, search_only_passive_markers=True,
                 optimistic_locked_wire_limits_grid_edges=wire_limits,
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 actual_search=result)
    return branches, proof
