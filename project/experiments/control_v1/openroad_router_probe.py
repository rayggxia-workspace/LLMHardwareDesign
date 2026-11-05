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


def landing_markers(parity_aware=False):
    """Keep legacy pins byteexact; odd masters duplicate existing cut keepouts."""
    text = 'VERSION 5.6 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'
    for direction in ('INPUT', 'OUTPUT'):
        for parity in ((0, 1) if parity_aware else (None,)):
            name = 'search_landing_' + direction.lower()
            if parity is not None:
                name += '_odd' if parity else '_even'
            text += (f'MACRO {name}\n CLASS BLOCK ;\n ORIGIN 0 0 ;\n SIZE 2 BY 2 ;\n'
                     f' PIN P\n  DIRECTION {direction} ;\n  USE SIGNAL ;\n  PORT\n   LAYER metal11 ;\n'
                     '   RECT 0 0 2 2 ;\n  END\n END P\n')
            if parity == 1:
                # The instance origin is landing_center minus1um. At2000DBU/um
                # this is exactly the same center+/-1DBU forbidden cut already
                # present in the block. Encode it in the master as well so PA
                # need not share a via-capable master across both parities.
                text += (' OBS\n  LAYER via11 ;\n'
                         '  RECT 0.9995 0.9995 1.0005 1.0005 ;\n END\n')
            text += 'END ' + name + '\n'
    return text + 'END LIBRARY\n'


def load_empty_region(path):
    """Read a source-bound real region without native upper obstacles."""
    import re
    with path.open() as f:
        x0, y0, x1, y1, blocked, count = map(int, f.readline().split())
        assert blocked == 0 and 1 <= count <= 700
        assert 4 <= x0 <= x1 and 4 <= y0 <= y1 and x1-x0 < 1200 and y1-y0 < 1200
        ox, oy = 4+(x0+y0)%2, 4
        nx, ny = x1-x0+1+ox+4, y1-y0+1+oy+4
        terminals, owned = {}, set()
        for _ in range(count):
            name, k, *values = f.readline().split()
            assert re.fullmatch(r'net_[a-zA-Z0-9_]+', name) and name not in terminals
            k = int(k)
            assert 2 <= k <= 400 and len(values) == 3*k
            numbers = list(map(int, values))
            row = []
            for x, y, l in zip(numbers[::3], numbers[1::3], numbers[2::3]):
                assert x0 <= x <= x1 and y0 <= y <= y1 and l in (0, 1)
                assert (x, y, l) not in owned
                owned.add((x, y, l))
                q = (x-x0+ox, y-y0+oy, l)
                assert (x+y)%2 == (q[0]+q[1])%2
                row.append(q)
            terminals[name] = row
        assert not f.read().strip()
    return dict(terminals=terminals, nx=nx, ny=ny, layer_markers=True,
                absolute_bounds=[x0,y0,x1,y1], local_offset=[ox,oy])


def verify_empty_region(scene, placement, portals_path, native_path):
    x0,y0,x1,y1=scene['absolute_bounds']
    ox,oy=scene['local_offset']
    def inside(pt):
        return x0<=pt[0]<=x1 and y0<=pt[1]<=y1
    real={}
    for name, ends in placement['terminals'].items():
        for x,y in ends:
            q=(x,y,0)
            assert q not in real
            real[q]=name
    expected={q:n for q,n in real.items() if inside(q)}
    portals=json.loads(portals_path.read_text())
    cross=0
    for name, pairs in portals.items():
        assert name in placement['terminals']
        for a,b in pairs:
            a,b=tuple(a),tuple(b)
            assert len(a)==len(b)==3 and a[2]==b[2] and a[2] in (0,1)
            assert abs(a[0]-b[0])+abs(a[1]-b[1])==1
            if not inside(a) and not inside(b):
                continue
            assert inside(a)!=inside(b) and a not in real and b not in real
            q=a if inside(a) else b
            assert q not in expected
            expected[q]=name
            cross+=1
    actual={(x+x0-ox,y+y0-oy,l):n for n,points in scene['terminals'].items() for x,y,l in points}
    assert actual==expected, 'Region differs from true source landings and exact boundary edges'
    with native_path.open() as f:
        count=int(f.readline())
        assert 0<count<len(placement['terminals'])
        for _ in range(count):
            n,k=f.readline().split()
            assert n in placement['terminals']
            for _ in range(int(k)):
                size,*coords=map(int,f.readline().split())
                assert len(coords)==3*size
                assert not any(inside(q) for q in zip(coords[::3],coords[1::3],coords[2::3])), 'Native prefix enters empty region'
        assert not f.read().strip()
    return dict(real_landings=len(actual)-cross, artificial_boundary_landings=cross,
                checked_native_trees=count, native_upper_obstacles=0)

def upper_landing_markers(parity_aware):
    original = landing_markers(parity_aware)
    upper = original[original.index('MACRO '):original.rindex('END LIBRARY')]
    upper = upper.replace('search_landing_', 'search_m12_landing_').replace('LAYER metal11 ;', 'LAYER metal12 ;')
    return original[:original.rindex('END LIBRARY')] + upper + 'END LIBRARY' + chr(10)

def run(out, scene=None, congestion_iterations=5, global_router='cugr',guide_pitch=4,parity_aware_markers=False):
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
    layered = scene is not None and scene.get('layer_markers', False)
    marker_lef.write_text((upper_landing_markers if layered else landing_markers)(parity_aware_markers))
    records = []
    for mode in (range(5 if parity_aware_markers else 3) if scene is None else [0]):
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
        elif mode == 2:
            terminals = {'bus_' + str(i): [(8+2*i+i%2, 8+(i//2)%2),
                          (38-2*i+i%2, 38+(i//2)%2), (8+2*i+i%2, 40+(i//2)%2)] for i in range(10)}
        elif mode == 3:
            terminals = {'odd_horizontal': [(8, 9), (38, 9)]}
        else:
            assert mode == 4
            terminals = {'odd_vertical': [(9, 8), (9, 38)]}
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
            for index, point in enumerate(ends):
                x, y = point[:2]
                level = point[2] if layered else 0
                xx, yy = 190+8000*x, 140+8000*y
                master_name = ('search_m12_landing_' if level else 'search_landing_') + ('output' if index == 0 else 'input')
                if parity_aware_markers:
                    master_name += '_odd' if (x+y)%2 else '_even'
                lines.extend([
                    'set master [$db findMaster ' + master_name + ']',
                    f'set inst [odb::dbInst_create $block $master {name}_p{index}]',
                    f'$inst setLocation {xx-2000} {yy-2000}',
                    '$inst setPlacementStatus FIRM',
                    'set term [$inst findITerm P]',
                    '$term connect $net',
                ])
        # Same four-grid-cell margin as the existing C++/Python acceptance.
        # Keepouts restrict the search; they add no final conductors or cells.
        x_margin, y_margin = scene['local_offset'] if layered else (4, 4)
        lo_x, lo_y = 190+8000*x_margin-6000, 140+8000*y_margin-6000
        hi_x, hi_y = 190+8000*(nx-5)+6000, 140+8000*(ny-5)+6000
        for layer in ('metal11', 'metal12'):
            lines.append(f'set guard_layer [[$db getTech] findLayer {layer}]')
            for x0, y0, x1, y1 in ((0, 0, lo_x, height), (hi_x, 0, width, height),
                                   (0, 0, width, lo_y), (0, hi_y, width, height)):
                lines.append(f'odb::dbObstruction_create $block $guard_layer {x0} {y0} {x1} {y1}')
        # Original mode retains minimal1nm keepouts byteexact. Parity-aware
        # mode uses1um keepouts: nearest legal4um center has2.5um edge clearance
        # (4-1um cut halfwidth-.5um guard), above original2.2um cut spacing.
        # Both modes exclude the same original forbidden grid sites only.
        # This is search geometry; no final/native mask shape is added.
        cut_guard_dbu = 1000 if parity_aware_markers else 1
        lines.extend([
            'set cut_layer [[$db getTech] findLayer via11]',
            f'for {{set x 4}} {{$x < {nx-4}}} {{incr x}} {{ for {{set y 4}} {{$y < {ny-4}}} {{incr y}} {{',
            ' if {($x+$y)%2} { set xx [expr {190+8000*$x}]; set yy [expr {140+8000*$y}];',
            f' odb::dbObstruction_create $block $cut_layer [expr {{$xx-{cut_guard_dbu}}}] [expr {{$yy-{cut_guard_dbu}}}] [expr {{$xx+{cut_guard_dbu}}}] [expr {{$yy+{cut_guard_dbu}}}] }}',
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
            + ('-via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal12 -verbose 1' if layered else
             '-via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1'),
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
        if layered:
            x0,y0,x1,y1=scene['absolute_bounds']
            ox,oy=scene['local_offset']
            branches={n:[[(x+x0-ox,y+y0-oy,l) for x,y,l in row] for row in rows]
                      for n,rows in branches.items()}
            assert all(x0<=x<=x1 and y0<=y<=y1 for rows in branches.values()
                       for row in rows for x,y,l in row), 'OpenROAD escaped the selected region'
            proof.update(region_absolute_bounds=scene['absolute_bounds'], absolute_tree_coordinates=True)
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
    if layered:
        result['region_absolute_bounds'] = scene['absolute_bounds']
        result['region_local_offset'] = scene['local_offset']
        result['scope'] += ' Isolated real region with exact M11/M12 terminals and no fixed native upper vertices; complete original geometry, PG and timing are untested.'
    if parity_aware_markers:
        result['parity_aware_search_landing_markers'] = True
        result['parity_aware_odd_cut_keepout_um'] = 1.0
        result['scope'] += ' Search masters split by original via parity; odd master cut obstruction exactly duplicates an already forbidden site, global1um cut keepouts preserve all original legal via centers with2.5um minimum clearance, native masks and all original gates unchanged.'
    (out / 'openroad-probe.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def route(terminals, nx, ny, seed, out, wire_limits, congestion_iterations=5, global_router='cugr',guide_pitch=4,parity_aware_markers=False):
    """Return only independently checked trees; unchanged downstream gates apply."""
    folder = out / 'openroad-search'
    folder.mkdir(exist_ok=False)
    result = run(folder, dict(terminals=terminals, nx=nx, ny=ny), congestion_iterations,global_router,guide_pitch,parity_aware_markers)
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
