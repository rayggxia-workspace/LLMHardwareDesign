"""Build and audit a relocatable, SHA-locked bounded control synthesis handoff."""
from pathlib import Path
import argparse, hashlib, json, re, shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BANK_SHA = '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
LIB_SHA = '8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
STAGE_INDEX_SHA = '4fd2e7e6b1e5d65f5a0cb359460325b064e54d1e7ebeea144cb0d0ade00afe0c'
LEF_SHA = {'NangateOpenCellLibrary.tech.lef':'834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2',
           'NangateOpenCellLibrary.macro.mod.lef':'a43aea339f12a57a63497783e508ba16f3da2dc056d3247dec7d99707c2dedef'}
CONTROL = ('mc_min_controller', 'lc_min_controller', 'two_local_link')
GROUPS = ('pu_p_group', 'pu_u_group', 'block_cfj_cf', 'block_cfj_j')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def targets():
    registry = json.loads((REPO/'project/control_task_compiler_v1/targets.json').read_text())['targets']
    expected = [{k:v for k,v in x.items() if k not in ('top','parameters')} for x in json.loads((HERE/'freeze.json').read_text())['synthesis_profiles']]
    assert registry == expected, 'target registry drift'
    return registry

def source_lists(profile, stage):
    family, kind = profile['family'], profile['kind']
    c = REPO/'project/control_rtl_min_v0_1'
    b = REPO/'project/control_boot_v1'
    f = REPO/'project/control_five_boot_v1'
    sources = [c/(x+'.sv') for x in CONTROL]
    sources += [b/(x+'.sv') for x in ('control_pm', 'control_boot_manager')]
    if family == 'five':
        sources += [f/(x+'.sv') for x in ('native_result_fifo', 'native_control_endpoint', 'five_control_top', 'typed_boot_front', 'five_boot_top')]
    else:
        sources += [f/'native_result_fifo.sv', REPO/'project/control_hetero_boot_v1/hetero_boot_front.sv']
        sources += [REPO/'project/control_recovery_boot_v1'/(x+'.sv') for x in ('draining_transport', 'draining_word_link', 'recovery_endpoint', 'recovery_control_top', 'recovery_engine', 'recovery_supervisor', 'recovery_boot_top')]
    sources += [REPO/'project/control_native_v1'/(x+'.sv') for x in ('pj_native_service', 'ucf_native_service')]
    base = stage/('cfj' if kind in (1, 2, 4) else 'native-p')
    native = base/'staged/native'
    control = sources + [native/'block_feed_s16k_sram.sv']
    full = sources + [stage/'native-p/design'/(x+'.sv') for x in ('pu_p_group', 'pu_p_store_control', 'pu_u_group', 'pu_compact_e_service')]
    full += [stage/'cfj/design'/(x+'.sv') for x in ('block_cfj_cf', 'block_cfj_j', 'cfj_s_port', 'cfj_e_port')]
    full += sorted(p for p in native.glob('*.sv') if not p.name.startswith('tb_'))
    if family == 'recovery' and kind != 0:
        full += [stage/'native-p/staged/native/local_s_p.sv']
    rtl = base/'staged/pj/project/rtl'
    full += sorted(p for p in (rtl/'block_pj_v1').glob('*.sv') if not p.name.startswith('tb_'))
    full += [rtl/'block_v2/block_v2_m.sv', rtl/'block_v1/transaction6k.sv']
    return control, list(dict.fromkeys(full)), [c, native]

def build(name, stage, bank, platform, out):
    stage, bank, platform, out = map(lambda x: x.resolve(), (stage, bank, platform, out))
    profile = next((x for x in targets() if x['name'] == name), None)
    if profile is None:
        raise ValueError('unknown profile')
    if out.exists():
        raise ValueError('package output must be new; never overwrite frozen evidence')
    assert sha(bank) == BANK_SHA
    assert sha(stage/'source-sha256.json') == STAGE_INDEX_SHA
    stage_index = json.loads((stage/'source-sha256.json').read_text())
    qualified = json.loads((HERE/'freeze.json').read_text())['qualified_control_source_sha256']
    lib = platform/'lib/NangateOpenCellLibrary_typical.lib'
    assert sha(lib) == LIB_SHA
    out.mkdir(parents=True)
    copied = {}
    def copy(path):
        path = path.resolve()
        if path.is_relative_to(REPO):
            source_name = path.relative_to(REPO).as_posix()
            assert sha(path) == qualified[source_name], source_name
            rel = Path('src/repo')/source_name
        elif path.is_relative_to(stage):
            source_name = path.relative_to(stage).as_posix()
            assert sha(path) == stage_index[source_name], source_name
            rel = Path('src/stage')/source_name
        else:
            raise ValueError('source outside declared roots')
        dst = out/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dst)
        copied[rel.as_posix()] = sha(path)
        return rel.as_posix()
    control, full, incdirs = source_lists(profile, stage)
    for path in set(control + full):
        assert not path.name.startswith('tb_')
        copy(path)
    # Include closures are copied explicitly, with no repository-wide scan.
    pending = list(set(control + full))
    for incdir in incdirs:
        for path in incdir.glob('*.svh'):
            copy(path)
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        for include in re.findall(r'^\s*`include\s+"([^"]+)"', path.read_text(), re.M):
            candidates = [path.parent/include] + [p/include for p in incdirs]
            target = next((p for p in candidates if p.is_file()), None)
            if target is None:
                raise ValueError('missing include: '+include)
            copy(target)
            pending.append(target)
    bank_model = 'models/bank.behavioral.v'
    (out/'models').mkdir()
    shutil.copyfile(bank, out/bank_model)
    (out/'boundaries').mkdir()
    boundary_paths = []
    for group in GROUPS:
        path = stage/('native-p/design' if group.startswith('pu_') else 'cfj/design')/(group+'.sv')
        dst = out/'boundaries'/(group+'.sv')
        dst.write_text(path.read_text().split(');', 1)[0]+');\nendmodule\n')
        boundary_paths.append(dst.relative_to(out).as_posix())
    dst = out/'boundaries/bank.v'
    dst.write_text(bank.read_text().split('  reg [DATA_WIDTH-1:0]    mem', 1)[0]+'endmodule\n')
    boundary_paths.append(dst.relative_to(out).as_posix())
    for path in (lib, platform/'lef/NangateOpenCellLibrary.tech.lef', platform/'lef/NangateOpenCellLibrary.macro.mod.lef'):
        if path.suffix == '.lef':
            assert sha(path) == LEF_SHA[path.name]
        dst = out/'technology'/path.relative_to(platform)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dst)
    shutil.copyfile(HERE/'constraints.sdc', out/'constraints.sdc')
    relative_control = [copy(p) for p in control]
    relative_full = [copy(p) for p in full] + [bank_model]
    include_dirs = [('src/repo/'+p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else 'src/stage/'+p.relative_to(stage).as_posix()) for p in incdirs]
    for file, paths in [('control.f', relative_control), ('full.f', relative_full), ('boundaries.f', boundary_paths)]:
        (out/file).write_text('\n'.join(json.dumps(x) for x in paths)+'\n')
    native = ['pu_u_group', 'block_cfj_cf', 'block_cfj_cf', 'pu_p_group', 'block_cfj_j'][profile['kind']]
    groups = {native: 2} if profile['family'] == 'five' else {native: 1, 'pu_p_group': 1}
    metadata = dict(schema='control-synthesis-package/1', profile=profile,
        top='five_boot_top' if profile['family']=='five' else 'recovery_boot_top',
        parameters={'KIND':profile['kind'], 'PM_USE_SRAM':1},
        hierarchy_expected={'mc_min_controller':1, 'lc_min_controller':2, 's_sram_256x128_freepdk45':12, **groups},
        control_sources=relative_control, full_sources=relative_full, boundaries=boundary_paths,
        include_dirs=include_dirs, copied_source_sha256=copied,
        boundaries_contract={'native_groups':'Logical synthesis partitions, not combined hard macros or group LEF. Computational macros and private S/T remain inside; real full RTL separately provided.',
            'PM':'3 x 16KiB, each four 256x128 1RW banks; USE_SRAM=1 only. No inferred PM backend in synthesis.',
            'bank':'Port-only synthesis declaration; behavioral model is full-RTL simulation only.',
            'physical_models':'Native-group and SRAM Liberty/LEF not provided by this control-side package; required for combined timing/physical integration.',
            'power_pins':'USE_POWER_PINS undefined; logical interface, no new power gating/UPF.',
            'reset':'Single-clock cohort; asynchronous assertion, synchronized release. Do not false-path rst_ni.'},
        parent_pr180='d8e443369e443568b31645df198e3ba749ec60a5',
        input_sha256={'stage_index':STAGE_INDEX_SHA,'bank':BANK_SHA},
        functional_evidence='work/Melodydt/179/control-matrix-validation.json',
        library={'sha256':LIB_SHA, 'corner':'Nangate45 typical 1.1V/25C'},
        scope='Source/parameter/boundary/SDC freeze and structural validation; not mapped combined timing, physical or model-level acceptance.')
    dump(out/'profile.json', metadata)
    # Paths are relative to the package, so the same script survives relocation.
    quote = json.dumps
    script = 'read_verilog -sv -lib '+' '.join(map(quote,boundary_paths))+'\n'
    script += 'read_verilog -sv '+' '.join('-I'+x for x in include_dirs)+' '+' '.join(map(quote,relative_control))+'\n'
    script += f'chparam -set KIND {profile["kind"]} -set PM_USE_SRAM 1 {metadata["top"]}\nhierarchy -check -top {metadata["top"]}\nsynth -top {metadata["top"]} -noabc\ncheck -assert\n'
    (out/'synth.ys').write_text(script)
    inputs = {p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    dump(out/'manifest.json', dict(schema='control-synthesis-manifest/1', files=inputs))
    return audit(out)

def audit(package):
    package = package.resolve()
    manifest = json.loads((package/'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        path = (package/name).resolve()
        assert path.is_relative_to(package), 'escaping manifest path'
        assert sha(path) == digest, name
    m = json.loads((package/'profile.json').read_text())
    assert m['parameters'] == {'KIND':m['profile']['kind'], 'PM_USE_SRAM':1}
    assert m['profile'] == next(x for x in targets() if x['name'] == m['profile']['name'])
    for filename, key in [('control.f','control_sources'),('full.f','full_sources'),('boundaries.f','boundaries')]:
        paths = [json.loads(x) for x in (package/filename).read_text().splitlines()]
        assert paths == m[key] and len(paths) == len(set(paths))
        assert all(p in manifest['files'] for p in paths)
        assert not any(Path(p).name.startswith('tb_') for p in paths)
    assert 'models/bank.behavioral.v' not in m['control_sources']
    assert sha(package/'models/bank.behavioral.v') == BANK_SHA
    assert sha(package/'technology/lib/NangateOpenCellLibrary_typical.lib') == LIB_SHA
    sdc = (package/'constraints.sdc').read_text()
    commands = '\n'.join(x for x in sdc.splitlines() if not x.lstrip().startswith('#'))
    assert not re.search(r'set_(false_path|multicycle_path|disable_timing|case_analysis)', commands)
    assert '3.333333333' in commands and 'all_inputs -no_clocks' in commands
    return dict(passed=True, profile=m['profile']['name'], files=len(manifest['files']), manifest_sha256=sha(package/'manifest.json'))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--stage',type=Path);p.add_argument('--bank',type=Path);p.add_argument('--platform',type=Path);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:
        result=audit(a.audit)
    else:
        if any(x is None for x in (a.profile,a.stage,a.bank,a.platform,a.out)):
            p.error('build requires profile/stage/bank/platform/out')
        result=build(a.profile,a.stage,a.bank,a.platform,a.out)
    print(json.dumps(result))
