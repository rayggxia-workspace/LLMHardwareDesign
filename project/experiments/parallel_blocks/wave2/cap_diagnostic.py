"""Compute-node evidence for tolerance, ACT address loading, and selected view gaps."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

source = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06')
platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
standard = platform/'lib/NangateOpenCellLibrary_typical.lib'
binary = Path('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad')
inputs = set([standard, binary])


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


disassembly = subprocess.check_output(['objdump','-d','--disassemble=_ZN3sta10fuzzyEqualEff',str(binary)],text=True)
Path('fuzzy-disassembly.txt').write_text(disassembly)
address = int(re.search(r'movss[^\n]+# ([0-9a-f]+)',disassembly)[1],16)
constant = subprocess.check_output(['objdump','-s','--start-address='+hex(address),'--stop-address='+hex(address+4),str(binary)],text=True)
Path('fuzzy-constant.txt').write_text(constant)
hexbytes = re.search(r'^\s*'+format(address,'x')+r'\s+([0-9a-f]{8})',constant,re.M)[1]
tolerance = struct.unpack('<f',bytes.fromhex(hexbytes))[0]
assert abs(tolerance/1e-15-1)<1e-6
unit = re.search(r'capacitive_load_unit\s*\(([^)]+)\)',standard.read_text())[1]
assert unit.replace(' ','').lower() == '1,ff'


def group(text, match):
    start = text.index('{', match.start())
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|[{}]',text[start:],re.S):
        if token[0] == '{': depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0: return text[start+1:start+token.start()]
    raise AssertionError('Unbalanced Liberty group')


def logical_signature(name):
    liberty = standard.read_text()
    cell = re.search(r'\bcell\s*\(\s*'+re.escape(name)+r'\s*\)\s*{',liberty)
    assert cell is not None, name
    body = group(liberty,cell)
    pins = {}
    for match in re.finditer(r'\bpin\s*\(\s*([^)]*)\)\s*{',body):
        pin = group(body,match)
        pins[match[1].strip()] = {key:re.sub(r'\s+','',m[1]) for key in ('direction','function','clock','three_state')
            for m in [re.search(r'\b'+key+r'\s*:\s*([^;]+);',pin)] if m}
    sequential = []
    for match in re.finditer(r'\b(ff|latch)\s*\(\s*([^)]*)\)\s*{',body):
        ff = group(body,match)
        sequential.append(dict(kind=match[1],state_variables=re.sub(r'\s+','',match[2]),
            attributes={key:re.sub(r'\s+','',m[1]) for key in ('clocked_on','next_state','enable','data_in','clear','preset','clear_preset_var1','clear_preset_var2')
                for m in [re.search(r'\b'+key+r'\s*:\s*([^;]+);',ff)] if m}))
    return dict(pins=pins,sequential=sequential)


cell_checks = {}
for before, after in [('MUX2_X1','MUX2_X2'),('BUF_X1','BUF_X2'),('DFF_X1','DFF_X2')]:
    sig = logical_signature(before)
    assert sig == logical_signature(after), (before,after)
    cell_checks[before+'->'+after] = dict(logical_signatures_equal=True,signature=sig,
        scope='Liberty port functions and sequential state equations match; not whole-netlist formal equivalence')
address_rows = {}
target = 'u_act.g_row[1].g_pc[0].u_act.ra[4]'
for case in ('act-cap00','act-cap10','act-cap20'):
    root = source/case
    result = root/'flow/results/nangate45/parallel_opentpu_act/base'
    path = result/'6_final.spef'
    inputs.add(path)
    text = path.read_text()
    assert '*C_UNIT 1 PF' in text
    names = dict(re.findall(r'^\*(\d+) (.+)$',text.split('*D_NET')[0],re.M))
    block = next(b for b in re.findall(r'\*D_NET.*?\*END',text,re.S)
        if names[b.splitlines()[0].split()[1][1:]].replace('\\','') == target)
    connections = [re.sub(r'\*(\d+)',lambda m:names.get(m[1],m[0]),line)
        for line in block.split('*CAP')[0].splitlines()[2:]]
    address_rows[case] = dict(wire_cap_fF=1000*float(block.splitlines()[0].split()[2]),connections=connections)
    stages = {}
    for stage in ('3_resizer','4_cts_final','5_global_route','6_finish'):
        report = root/'flow/reports/nangate45/parallel_opentpu_act/base'/(stage+'.rpt')
        inputs.add(report)
        match = re.search(r'max_capacitance_check_slack\s*\n-+\s*\n([^\n]+)',report.read_text())
        stages[stage] = float(match[1])
    address_rows[case]['stage_worst_cap_slack_fF'] = stages
for path in (source/'act-cap10/memory-model/macros').glob('*.lib'):
    inputs.add(path)
    assert 'capacitance : 5.000;' in path.read_text()
row = address_rows['act-cap10']
assert len([l for l in row['connections'] if 'r_addr_in[4]' in l]) == 3
row.update(sink_cap_total_fF=15.0,driver_limit_fF=60.5011,
    recomputed_total_fF=row['wire_cap_fF']+15.0,
    recomputed_slack_fF=60.5011-row['wire_cap_fF']-15.0)
assert abs(row['recomputed_slack_fF']-row['stage_worst_cap_slack_fF']['6_finish'])<1e-4

views = {}
for case, nickname, top in [('act-cap20','opentpu_act','llhd_opentpu_act'),
        ('mxu-cap20','opentpu_mxu','llhd_opentpu_mxu'),
        ('gemm-cap20','llaccel_gemm','gemm_engine')]:
    result = source/case/'flow/results/nangate45'/('parallel_'+nickname)/'base'
    paths = {suffix:result/(top+suffix) for suffix in ('.lef','_typ.lib','.detailed.lef')}
    assert all(path.is_file() for path in paths.values())
    inputs.update(paths.values())
    liberty = paths['_typ.lib'].read_text()
    lef = paths['.lef'].read_text()
    detailed = paths['.detailed.lef'].read_text()
    signal_pins = set(re.findall(r'^\s*PIN\s+(\S+)',lef,re.M))-{'VDD','VSS'}
    views[case] = dict(top=top,source_paths={k:str(v) for k,v in paths.items()},
        signal_pin_count=len(signal_pins),
        liberty_timing_groups=len(re.findall(r'\btiming\s*\(',liberty)),
        liberty_timing_types=sorted(set(re.findall(r'timing_type\s*:\s*([^;]+);',liberty))),
        minimum_period_present=bool(re.search(r'\bminimum_period\b|\bmin_period\b',liberty)),
        detailed_obs_count=len(re.findall(r'^\s*OBS\s*$',detailed,re.M)),
        qualified_hard_macro=False,
        scope='Existence, counts and model-gap inventory only; not exhaustive arc, timing or PG qualification')
Path('diagnostic.json').write_text(json.dumps(dict(capacitance_unit=unit,
    binary_zero_tolerance_SI=tolerance,binary_zero_tolerance_fF=tolerance*1e15,
    address_net=target,act_rows=address_rows,selected_views=views,replacement_cell_checks=cell_checks,
    count_zero_is_not_nonnegative_slack=True,
    scope='Static final-netlist/SPEF/library reconstruction and actual executable constant; no new STA run'),indent=2)+'\n')
Path('diagnostic-inputs.sha256').write_text(''.join(digest(p)+'  '+str(p)+'\n' for p in sorted(inputs)))
Path('validation.json').write_text(json.dumps(dict(passed=True,diagnostic='diagnostic.json',
    physical_or_system_signoff=False,qualified_hard_macro=False),indent=2)+'\n')
