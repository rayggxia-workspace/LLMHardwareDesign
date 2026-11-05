"""Replay immutable search inputs for bounded DRC diagnosis, never qualification."""
import json
import shutil
import subprocess
from pathlib import Path


def inspect(config, out, bind):
    cfg = json.loads(config.read_text())
    assert cfg['schema'] == 'control162-openroad-search-snapshot-v1'
    assert cfg['iterations'] in (1, 3)
    files = cfg['inputs']
    assert set(files) == {'before.odb', 'route.guide', 'terminals.json', 'run.tcl'}
    resolved = {}
    for name, row in files.items():
        path = Path(row['path'])
        assert path.is_file() and path.name == name
        assert path.parent == Path(files['before.odb']['path']).parent
        bind(path, row['sha256'])
        resolved[name] = path
    assert cfg['nx'] >= 16 and cfg['ny'] >= 16
    tool = shutil.which('openroad')
    assert tool
    bind(Path(tool))
    script = out / 'snapshot.tcl'
    script.write_text('\n'.join([
        f'read_db {{{resolved["before.odb"]}}}',
        'set_thread_count 16',
        'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
        'help read_guides',
        f'read_guides {{{resolved["route.guide"]}}}',
        f'detailed_route -droute_end_iter {cfg["iterations"]} -drc_report_iter_step 1 '
        f'-output_drc {{{out / "drc.rpt"}}} '
        '-via_in_pin_bottom_layer metal11 -via_in_pin_top_layer metal11 -verbose 1',
        f'write_def {{{out / "snapshot.def"}}}',
        f'write_db {{{out / "snapshot.odb"}}}',
    ]) + '\n')
    with (out / 'openroad.log').open('w') as log:
        result = subprocess.run([tool, '-exit', str(script)], stdout=log, stderr=subprocess.STDOUT, cwd=out)
    assert result.returncode == 0, 'Snapshot execution failed; inspect actual openroad.log'
    assert (out / 'snapshot.def').is_file() and (out / 'snapshot.odb').is_file()
    drc = out / 'drc.rpt'
    assert drc.is_file()
    grid = dict(passed=False)
    try:
        from openroad_grid import read
        _, proof = read(out / 'snapshot.def', json.loads(resolved['terminals.json'].read_text()), cfg['nx'], cfg['ny'])
        grid = dict(passed=True, proof=proof)
    except AssertionError as error:
        grid['error'] = str(error)
    report = dict(execution_passed=True, whole_system_qualified=False,
                  bounded_search_iterations=cfg['iterations'], actual_router_drc_empty=not drc.read_text().strip(),
                  independent_original_grid_check=grid,
                  scope='Bounded replay of SHA-bound pre-route search ODB and original global guides. '
                        'Diagnostic only, including when DRC is empty; no final native geometry, PG, RC or 300MHz qualification.')
    (out / 'snapshot.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
