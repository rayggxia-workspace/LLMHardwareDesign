"""Slurm-only matched Nangate45 mapping of shared-A one/two-word modules.

The parent runner must pass its functional gate before calling run_area().
This maps complete standalone M modules, not an estimated operand sub-block.
No local P memory, P glue, placement, routing, or timing is included.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import time


BANK_LIB = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib')
BANK_LIB_SHA = '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189'
LIBERTY = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
LIBERTY_SHA = '8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
MACRO = 's_sram_256x128_freepdk45'
MACRO_AREA_MM2 = 0.092462050025
SOURCES = {
    'pool': ('shared_a_pool32', 'project/rtl/shared_s/shared_a_pool32.sv', 8),
    'm': ('block_v2_m', 'project/rtl/block_v2/block_v2_m.sv', 0),
    'm_context8': ('block_v2_m_context', 'project/rtl/block_v2/block_v2_m_context.sv', 0),
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def quote(path):
    value = str(path)
    if '\n' in value or '\r' in value:
        raise ValueError('newline in synthesis path')
    return '"' + value.replace('\\', '/').replace('"', '\\"') + '"'


def run_area(repo, out, environment=None):
    """Return a persisted receipt; raise on any setup, mapping, or audit failure.

    API: run_area(repo: Path, out: Path, environment: dict | None) -> dict.
    Output directory must not exist. Source commits belong to the caller's
    locked run manifest; this receipt hashes every actual RTL and tool input.
    """
    job = os.environ.get('SLURM_JOB_ID', '')
    cpus_text = os.environ.get('SLURM_CPUS_PER_TASK', '')
    if not re.fullmatch(r'\d+', job) or not re.fullmatch(r'[1-4]', cpus_text):
        raise RuntimeError('area mapping requires an actual Slurm job with 1..4 CPUs per task')
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if not repo.is_dir():
        raise ValueError('missing source repository')
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    if environment is not None:
        env.update(environment)
    # All six tools run sequentially; no nested synthesis concurrency is used.
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env[key] = '1'
    report = dict(status='running', scope='Matched standalone standard-cell synthesis only; no P/pair glue, local-S, placement, routing, timing, or whole-chip qualification.',
                  source_commit=None, source_commit_status='Refer to parent locked run manifest; actual input SHA-256 values are recorded here.',
                  job=job, node=platform.node(), allocated_cpus=int(cpus_text),
                  synthesis_concurrency=1, threads_per_tool=1,
                  commands=[], modules={}, tools={}, artifacts={})

    def save():
        dump(out / 'result.json', report)

    def execute(command, log_path, timeout, accepted_codes=(0,)):
        command = [str(part) for part in command]
        log_path = Path(log_path)
        entry = dict(command=command, cwd=str(repo), log=str(log_path.relative_to(out)), timeout_seconds=timeout)
        report['commands'].append(entry)
        save()
        started = time.monotonic()
        with log_path.open('w', encoding='utf8') as log:
            process = subprocess.Popen(command, cwd=repo, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                entry.update(exit_code=process.returncode, timed_out=True,
                             elapsed_seconds=time.monotonic() - started)
                save()
                raise RuntimeError('area tool timeout: ' + str(log_path)) from None
        entry.update(exit_code=code, elapsed_seconds=time.monotonic() - started,
                     log_sha256=sha(log_path))
        save()
        if code not in accepted_codes:
            raise RuntimeError('area tool failed with exit ' + str(code) + ': ' + str(log_path))
        return log_path.read_text(encoding='utf8', errors='replace')

    try:
        yosys = shutil.which('yosys', path=env.get('PATH'))
        if yosys is None:
            raise ValueError('Yosys is not available in the locked run environment')
        yosys = Path(yosys).resolve()
        sibling_abc = yosys.with_name('yosys-abc')
        abc_path = str(sibling_abc) if sibling_abc.is_file() else (
            shutil.which('yosys-abc', path=env.get('PATH')) or shutil.which('abc', path=env.get('PATH')))
        if abc_path is None:
            raise ValueError('ABC executable is required and must be explicitly recorded')
        abc = Path(abc_path).resolve()
        for name, library, expected in (('standard_liberty', LIBERTY, LIBERTY_SHA),
                                        ('bank_liberty', BANK_LIB, BANK_LIB_SHA)):
            actual = sha(library)
            if actual != expected:
                raise ValueError(name + ' identity drift')
            report[name] = dict(path=str(library), sha256=actual)
        yosys_version = execute([yosys, '-V'], out / 'yosys-version.log', 30).strip()
        # ABC help prints its release/build banner; exit 1 is its normal usage status.
        abc_banner = execute([abc, '-h'], out / 'abc-version.log', 30, (0, 1)).strip()
        if not abc_banner:
            raise ValueError('ABC version banner is empty')
        report['tools'] = dict(
            yosys=dict(path=str(yosys), sha256=sha(yosys), version=yosys_version),
            abc=dict(path=str(abc), sha256=sha(abc), version_banner=abc_banner))
        report['sources'] = {source: sha(repo / source) for _, source, _ in SOURCES.values()}
        cells = re.findall(r'\bcell\s*\(\s*(?:"([^"]+)"|([^\s)]+))\s*\)', LIBERTY.read_text(encoding='utf8'))
        allowed_cells = {quoted or plain for quoted, plain in cells}
        if not allowed_cells:
            raise ValueError('standard-cell library contains no recognized cell definitions')
        save()
        for kind, (top, source, expected_banks) in SOURCES.items():
            for words in (1, 2):
                key = kind + '_a' + str(words)
                directory = out / key
                directory.mkdir()
                config = dict(A_WORDS_PER_BEAT=words)
                if kind == 'm_context8':
                    config['CONTEXTS'] = 8
                flow = directory / 'synth.ys'
                parameters = 'chparam ' + ' '.join('-set ' + name + ' ' + str(value) for name, value in config.items()) + ' ' + top
                flow.write_text('\n'.join([
                    'read_liberty -lib ' + quote(LIBERTY),
                    'read_liberty -lib ' + quote(BANK_LIB),
                    'read_verilog -sv ' + quote(repo / source),
                    parameters, 'hierarchy -check -top ' + top,
                    'synth -top ' + top + ' -flatten -noabc',
                    'dfflibmap -liberty ' + quote(LIBERTY),
                    'abc -exe ' + quote(abc) + ' -liberty ' + quote(LIBERTY),
                    'clean', 'check -assert',
                    'tee -o ' + quote(directory / 'stat.json') + ' stat -json -liberty ' + quote(LIBERTY),
                    'write_json ' + quote(directory / 'mapped.json'),
                    'write_verilog -noattr ' + quote(directory / 'mapped.v'),
                ]) + '\n', encoding='utf8')
                execute([yosys, '-Q', '-s', flow], directory / 'synthesis.log', 1200)
                stats = json.loads((directory / 'stat.json').read_text(encoding='utf8'))
                matches = [value for name, value in stats['modules'].items() if name.lstrip('\\') == top]
                if len(matches) != 1:
                    raise ValueError(key + ' missing unique mapped top statistics')
                mapped = json.loads((directory / 'mapped.json').read_text(encoding='utf8'))['modules'][top]
                counts = Counter(cell['type'] for cell in mapped.get('cells', {}).values())
                unmapped = sorted(set(counts) - allowed_cells - {MACRO, '$scopeinfo'})
                if counts.get(MACRO, 0) != expected_banks or unmapped:
                    raise ValueError(key + ' bank count mismatch or non-library cells: ' + repr(unmapped))
                area = matches[0].get('area', stats.get('design', {}).get('area'))
                if not isinstance(area, (int, float)) or not math.isfinite(area) or area <= 0:
                    raise ValueError(key + ' missing positive mapped standard-cell area')
                report['modules'][key] = dict(top=top, configuration=config, source=source,
                    source_sha256=report['sources'][source], standard_cell_area_um2=area,
                    physical_4KiB_banks=expected_banks, physical_SRAM_KiB=4 * expected_banks,
                    macro_area_proxy_mm2=expected_banks * MACRO_AREA_MM2,
                    no_unmappedcells=True, unmapped_cell_types=[], cell_types=dict(sorted(counts.items())),
                    artifacts={name: dict(path=str((directory / name).relative_to(out)), sha256=sha(directory / name))
                               for name in ('synth.ys', 'synthesis.log', 'stat.json', 'mapped.json', 'mapped.v')})
                save()
        modules = report['modules']
        deltas = {kind: modules[kind + '_a2']['standard_cell_area_um2'] - modules[kind + '_a1']['standard_cell_area_um2']
                  for kind in SOURCES}
        report['deltas_standard_cell_um2'] = deltas
        report['aggregate'] = dict(
            expression='pool_a2 - pool_a1 + 2 * (m_context8_a2 - m_context8_a1)',
            standard_cell_delta_um2=deltas['pool'] + 2 * deltas['m_context8'],
            standard_cell_delta_mm2=(deltas['pool'] + 2 * deltas['m_context8']) / 1_000_000,
            SRAM_macro_delta=0, SRAM_macro_delta_mm2=0,
            scope='Only one pool and two complete context8 M modules; excludes unchanged/local SRAM and unmeasured P/pair glue. Not whole-P, pair, placed, or chip area.')
        report['status'] = 'passed'
        return report
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        for path in sorted(out.rglob('*')):
            if path.is_file() and path != out / 'result.json':
                report['artifacts'][str(path.relative_to(out))] = dict(bytes=path.stat().st_size, sha256=sha(path))
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    receipt = run_area(args.repo, args.out)
    print(json.dumps(dict(status=receipt['status'], modules=len(receipt['modules']), aggregate=receipt['aggregate'])))
