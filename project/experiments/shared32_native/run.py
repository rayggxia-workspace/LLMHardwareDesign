"""Slurm-only native shared-A RTL validation; no token/s extrapolation."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import time
import traceback

HERE = Path(__file__).resolve().parent
VERILATOR = Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA = '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
BANK_LIB = BANK.with_name('s_sram_256x128_freepdk45_TT_1p1V_25C.lib')
BANK_LIB_SHA = '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189'
LIBERTY = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
MACRO = 's_sram_256x128_freepdk45'
MACRO_AREA_MM2 = 0.092462050025
SEEDS = ((1, 247), (2, 247), (2, 248))
POOL = 'project/rtl/shared_s/shared_a_pool32.sv'
MEMORY = 'project/rtl/s_sram/block_feed_s16k_1r1w.sv'
PAIR = 'project/rtl/shared_s/pu_p_shared_pair.sv'
GROUP_SOURCES = [
    'project/rtl/block_local_s/block_local_s_arbiter.sv',
    'project/rtl/block_local_s/popt_s_policy_arbiter.sv',
    'project/rtl/s_sram/block_feed_s16k_sram.sv',
    'project/rtl/s_sram/block_feed_s16k_bank_rw.sv', MEMORY,
    'project/rtl/s_sram/local_s_p.sv',
    'project/rtl/block_feed_v1/block_feed_loader.sv',
    'project/rtl/block_v2/block_v2_m.sv',
    'project/rtl/block_v2/block_v2_m_context.sv',
    'project/rtl/block_v2/block_v2_g.sv',
    *['project/rtl/pu_leaf_base/' + name + '.sv' for name in
      ('pu_p_group', 'pu_p_store_control', 'pj_feed_hold', 'pj_mem_port', 'pj_sram_client')],
]
COMPONENTS = {
    'pool': ('tb_shared_pool', 'shared_a_pool32', [POOL]),
    'memory': ('tb_s16k_1r1w', 'block_feed_s16k_1r1w', [MEMORY]),
    'pair': ('tb_shared_pair', 'pu_p_shared_pair', [PAIR, POOL, *GROUP_SOURCES]),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fields(line):
    result = {}
    for field in line.split()[1:]:
        if '=' not in field:
            raise ValueError('unstructured receipt field: ' + field)
        key, value = field.split('=', 1)
        if key in result:
            raise ValueError('duplicate receipt key: ' + key)
        result[key] = int(value) if re.fullmatch(r'-?\d+', value) else value
    return result


def parse_receipts(output, component):
    prefix = {'pool': 'POOL', 'memory': 'S16K_1R1W', 'pair': 'SHARED_PAIR'}[component]
    passes = re.findall(r'^' + prefix + r'_PASS(?: .*)?$', output, re.M)
    measurements = re.findall(r'^' + prefix + r'_MEASURE .+$', output, re.M)
    if len(passes) != 1 or not measurements:
        raise ValueError(component + ' missing/duplicate pass or missing measurement')
    result = dict(checks=fields(passes[0]), measurements=[fields(line) for line in measurements])
    if any(not isinstance(row.get('cycles'), int) or row['cycles'] <= 0 for row in result['measurements']):
        raise ValueError(component + ' requires positive measured cycles')
    if component == 'pool':
        for key in ('checks', 'reads', 'writes', 'a_words', 'errors'):
            if not isinstance(result['checks'].get(key), int) or result['checks'][key] <= 0:
                raise ValueError('pool missing positive coverage count: ' + key)
        scenarios = {row.get('scenario') for row in result['measurements']}
        if not {'fill', 'simultaneous', 'boundary', 'invalid', 'release_hold', 'reset_refill'} <= scenarios:
            raise ValueError('pool scenario coverage missing')
        for row in result['measurements']:
            if row.get('scenario') == 'invalid' and (row.get('reads') != 0 or row.get('a_words') != 0):
                raise ValueError('invalid pool descriptor performed a data transfer')
    if component == 'memory':
        for key in ('simultaneous_rw', 'reads', 'writes'):
            if sum(row.get(key, 0) for row in result['measurements']) <= 0:
                raise ValueError('memory missing positive coverage count: ' + key)
        throughput = re.findall(r'^S16K_1R1W_THROUGHPUT .+$', output, re.M)
        if len(throughput) != 1:
            raise ValueError('memory missing/duplicate simultaneous throughput probe')
        result['throughput'] = fields(throughput[0])
        for key in ('cycles', 'reads', 'writes', 'simultaneous_rw'):
            if result['throughput'].get(key) != 256:
                raise ValueError('memory steady-state one-read/one-write service failed: ' + key)
        for key in ('read_bytes', 'write_bytes'):
            if result['throughput'].get(key) != 256*64:
                raise ValueError('memory steady-state byte conservation failed: ' + key)
        for row in result['measurements']:
            for key, value in (('logical_bytes', 16384), ('physical_bytes', 32768), ('macros', 8), ('live_bits', 1024)):
                if row.get(key) != value:
                    raise ValueError('memory capacity receipt mismatch: ' + key)
    if component == 'pair':
        checks = result['checks']
        shared, rw = checks.get('shared'), checks.get('true_rw')
        if shared not in (0, 1) or rw not in (0, 1) or checks.get('numeric') != 3456 or checks.get('contexts') != 288:
            raise ValueError('pair native numeric/context coverage mismatch')
        scenarios = {row.get('scenario'): row for row in result['measurements']}
        if set(scenarios) != ({0, 1, 2, 'lease'} if rw else {0, 1, 2}):
            raise ValueError('pair scenario coverage mismatch')
        for case in range(3):
            row = scenarios[case]
            expected_shared = (36 if case == 1 else 72) if shared else 0
            if row.get('A') != 72 or row.get('shared_A') != expected_shared:
                raise ValueError('pair local/shared A work conservation')
            if not 0 < row.get('compute_cycles', 0) < row['cycles']:
                raise ValueError('pair end-to-end cost omitted')
        if rw:
            for key in ('protected_stalls', 'concurrent_writes', 'simultaneous_rw'):
                if scenarios['lease'].get(key, 0) <= 0:
                    raise ValueError('pair lease/concurrency coverage missing: ' + key)
    return result


def validate_manifest(repo, manifest, required):
    commit = manifest.get('source_commit', '')
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('deployment requires real 40-hex source commit')
    sources = manifest.get('code_sha256', {})
    if not set(required) <= sources.keys():
        raise ValueError('manifest omits required sources: ' + str(sorted(set(required) - sources.keys())))
    for name, digest in sources.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or 'ref-project' in rel.parts or rel.name == '.env':
            raise ValueError('unsafe source path: ' + name)
        path = repo / name
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise ValueError('deployment source mismatch: ' + name)
    return commit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--components', choices=('units', 'pool', 'memory', 'pair', 'all'), default='all')
    parser.add_argument('--area', action='store_true', help='Map new modules only after requested functional tests pass')
    parser.add_argument('--build-timeout', type=int, default=1800)
    parser.add_argument('--run-timeout', type=int, default=300)
    args = parser.parse_args()
    args.repo = args.repo.resolve(); args.out = args.out.resolve(); args.manifest = args.manifest.resolve()
    if not re.fullmatch(r'\d+', os.environ.get('SLURM_JOB_ID', '')) or not 1 <= args.workers <= min(4, int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))):
        raise ValueError('requires actual Slurm job and 1..4 allocated workers')
    if not 1 <= args.run_timeout <= 1800 or not 30 <= args.build_timeout <= 7200:
        raise ValueError('finite timeout outside allowed range')
    selected = ['pool', 'memory'] if args.components == 'units' else list(COMPONENTS) if args.components == 'all' else [args.components]
    if args.area and not {'pool', 'memory'} <= set(selected):
        raise ValueError('--area requires units or all, ensuring both new modules passed first')
    args.out.mkdir(parents=True, exist_ok=False)
    report = dict(passed=False, functional_passed=False, source_commit=None,
                  scope='Native S8/S16 A128, B512 and S40/S64 arithmetic. RTL microbench cycles only; no full-model token/s, STA or physical qualification.',
                  job=os.environ['SLURM_JOB_ID'], node=platform.node(), workers=args.workers,
                  affinity=sorted(os.sched_getaffinity(0)), requested_components=selected,
                  manifest_sha256=sha(args.manifest), versions={'python': platform.python_version()},
                  commands=[], components={}, mapped_area={'status': 'not_requested'}, errors=[])

    def save():
        dump(args.out / 'result.json', report)

    def execute(command, log, timeout=None):
        command = list(map(str, command)); target = args.out / log
        target.parent.mkdir(parents=True, exist_ok=True)
        before = time.monotonic(); timed_out = False
        with target.open('wb') as stream:
            process = subprocess.Popen(command, cwd=args.repo, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                returncode = process.wait(timeout=timeout or args.build_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
                returncode = process.returncode
        report['commands'].append(dict(command=command, exit_code=returncode, timed_out=timed_out,
                                       seconds=time.monotonic()-before, log=log, sha256=sha(target)))
        save()
        output = target.read_text(encoding='utf-8', errors='replace')
        if returncode or timed_out:
            raise RuntimeError(log + ' failed: ' + output[-2500:])
        # Legacy closure may retain its historical warnings, but never silently
        # leave a newly added production input floating.
        if re.search(r'%Warning-(?:PINMISSING|PINNOTFOUND)', output):
            raise ValueError(log + ' has incomplete port connections')
        return output

    def run_component(name):
        top, dut, sources = COMPONENTS[name]
        bench = HERE / (top + '.sv')
        includes = ['-I' + str(args.repo / 'project/rtl/block_v2')]
        if name != 'pair':
            execute([VERILATOR, '--lint-only', '--timing', '--timescale', '1ns/1ps',
                     '--top-module', dut, *includes, *[args.repo / path for path in sources], BANK], name + '-strict-lint.log')
        legacy_warnings = ['-Wno-fatal'] if name == 'pair' else []
        runs = []
        report['components'][name] = dict(passed=False, runs=runs)
        variants = [('default', [], SEEDS)]
        if name == 'memory':
            variants = [('echo1', ['-GECHO_WRITE_DATA=1'], SEEDS),
                        ('echo0', ['-GECHO_WRITE_DATA=0'], SEEDS[:1])]
        if name == 'pair':
            variants = [(f'share{s}-rw{w}', [f'-GSHARED={s}', f'-GTRUE_RW={w}'], SEEDS)
                        for s, w in ((0, 0), (1, 0), (0, 1), (1, 1))]
        for variant, params, seeds in variants:
            obj = args.out / ('obj-' + name + '-' + variant)
            execute([VERILATOR, '--binary', '--timing', '--assert', '--timescale', '1ns/1ps',
                     *legacy_warnings, '--x-initial', 'unique', '--x-assign', 'unique', '-j', args.workers,
                     '--top-module', top, '--Mdir', obj, *params, *includes, bench,
                     *[args.repo / path for path in sources], BANK], name + '-' + variant + '-build.log')
            for reset_mode, seed in seeds:
                log = f'{name}-{variant}-run-{reset_mode}-{seed}.log'
                output = execute([obj / ('V' + top), f'+verilator+rand+reset+{reset_mode}',
                                  f'+verilator+seed+{seed}', f'+SEED={seed}'], log, args.run_timeout)
                runs.append(dict(variant=variant, reset_mode=reset_mode, seed=seed, log=log, **parse_receipts(output, name)))
                save()
        report['components'][name]['passed'] = True

    def map_area():
        yosys = shutil.which('yosys')
        if yosys is None or not LIBERTY.is_file():
            raise ValueError('requested area mapping requires Yosys and Nangate45 library')
        bank_lib = BANK_LIB
        if sha(bank_lib) != BANK_LIB_SHA:
            raise ValueError('SRAM liberty identity drift')
        report['versions']['yosys'] = execute([yosys, '-V'], 'yosys-version.log', 30).strip()
        result = dict(status='running', scope='New-module standard-cell synthesis; SRAM blackboxes reported separately. No placement, routing, timing or chip-area qualification.',
                      yosys_binary_sha256=sha(yosys), standard_liberty=dict(path=str(LIBERTY), sha256=sha(LIBERTY)),
                      bank_liberty=dict(path=str(bank_lib), sha256=sha(bank_lib)), modules={})
        report['mapped_area'] = result; save()
        def q(path):
            return '"' + str(path).replace('\\', '/').replace('"', '\\"') + '"'
        for source, top, expected_banks in ((POOL, 'shared_a_pool32', 8), (MEMORY, 'block_feed_s16k_1r1w', 8),
                                            ('project/rtl/s_sram/block_feed_s16k_sram.sv', 'block_feed_s16k_sram', 4)):
            directory = args.out / ('synth-' + top); directory.mkdir()
            flow = directory / 'synth.ys'
            flow.write_text('\n'.join([
                'read_liberty -lib ' + q(LIBERTY), 'read_liberty -lib ' + q(bank_lib),
                'read_verilog -sv ' + q(args.repo/source), 'hierarchy -check -top ' + top,
                'synth -top ' + top + ' -flatten -noabc', 'dfflibmap -liberty ' + q(LIBERTY),
                'abc -liberty ' + q(LIBERTY), 'clean', 'check -assert',
                'tee -o ' + q(directory/'stat.json') + ' stat -json -liberty ' + q(LIBERTY),
                'write_json ' + q(directory/'mapped.json'),
                'write_verilog -noattr ' + q(directory/'mapped.v')]) + '\n', encoding='utf-8')
            execute([yosys, '-Q', '-s', flow], str(directory.relative_to(args.out)/'synthesis.log'))
            stats = json.loads((directory/'stat.json').read_text())
            module_stats = next(value for key, value in stats['modules'].items() if key.lstrip('\\') == top)
            mapped = json.loads((directory/'mapped.json').read_text())['modules'][top]
            counts = {}
            for cell in mapped.get('cells', {}).values():
                kind = cell['type']; counts[kind] = counts.get(kind, 0) + 1
            if counts.get(MACRO) != expected_banks or any(kind.startswith('$') for kind in counts if kind != '$scopeinfo'):
                raise ValueError(top + ' bank count mismatch or unmapped cells')
            area = module_stats.get('area', stats.get('design', {}).get('area'))
            if not isinstance(area, (int, float)) or area <= 0:
                raise ValueError(top + ' missing positive mapped standard-cell area')
            result['modules'][top] = dict(standard_cell_area_um2=area, physical_4KiB_banks=expected_banks,
                macro_area_proxy_mm2=expected_banks * MACRO_AREA_MM2, physical_KiB=4*expected_banks,
                logical_KiB=32 if top=='shared_a_pool32' else 16, cell_types=counts,
                stat_sha256=sha(directory/'stat.json'), netlist_sha256=sha(directory/'mapped.v'))
            save()
        result['status'] = 'passed'

    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        required = {str(HERE.relative_to(args.repo)/name) for name in ('run.py', 'job.sh', 'analyze.py')}
        for name in selected:
            top, _, sources = COMPONENTS[name]; required.update(sources)
            required.add(str(HERE.relative_to(args.repo)/(top+'.sv')))
        if args.area:
            required.add('project/rtl/s_sram/block_feed_s16k_sram.sv')
        # All path keys use the package's POSIX convention.
        required = {name.replace('\\', '/') for name in required}
        report['source_commit'] = validate_manifest(args.repo, manifest, required)
        report['source_sha256'] = {name: sha(args.repo/name) for name in sorted(required)}
        if sha(BANK) != BANK_SHA:
            raise ValueError('real SRAM behavior identity drift')
        report['bank'] = dict(path=str(BANK), sha256=BANK_SHA)
        report['verilator_binary_sha256'] = sha(VERILATOR)
        report['versions']['verilator'] = execute([VERILATOR, '--version'], 'verilator-version.log', 30).strip()
        report['versions']['gcc'] = execute(['g++', '--version'], 'gcc-version.log', 30).splitlines()[0]
        for name in selected:
            try:
                run_component(name)
            except Exception as error:
                report['errors'].append(dict(component=name, error=repr(error), traceback=traceback.format_exc()))
                save()
        report['functional_passed'] = not report['errors'] and all(report['components'].get(name, {}).get('passed') for name in selected)
        if args.area:
            if not report['functional_passed']:
                report['mapped_area'] = dict(status='not_executed', reason='requested functional gate failed')
            else:
                map_area()
        report['passed'] = report['functional_passed'] and (not args.area or report['mapped_area']['status'] == 'passed')
    except Exception as error:
        report['errors'].append(dict(component='setup_or_area', error=repr(error), traceback=traceback.format_exc()))
    finally:
        report['output_files_sha256'] = {str(path.relative_to(args.out)): sha(path) for path in sorted(args.out.rglob('*'))
            if path.is_file() and path.name != 'result.json' and not any(part.startswith('obj-') for part in path.relative_to(args.out).parts)}
        save()
        print(json.dumps(dict(passed=report['passed'], functional_passed=report['functional_passed'],
                              errors=report['errors'], result=str(args.out/'result.json'))), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
