"""Run inside the pinned ORFS container on an allocated compute node.
Physical checks and regenerated views; functional equivalence remains a separate gate.
"""
import sys, os, shutil, subprocess, hashlib, json
from pathlib import Path
from xml.etree import ElementTree as ET

role, candidate_arg = sys.argv[1:]
candidate = Path(candidate_arg).resolve()
assert role in ('G', 'S')
assert 'GS_CANDIDATE_COMPLETE_NOT_QUALIFIED' in (candidate/'implementation.log').read_text()
out = candidate/'qualification'
out.mkdir()
os.chdir(out)
platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
repo = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign')
gconfig = repo/'issue-201-compact-ge/e44ef51ee/audit-followup/g-220-bands2/sealed/config.mk'
sroot = repo/'issue-200-compact-local-s/run08-base0/results/0'
config = gconfig if role == 'G' else sroot/'config.mk'
top = 'block_v2_g' if role == 'G' else 'local_s_base'
nickname = 'bv1_block_v2_g' if role == 'G' else 'local_s_base'
lib = platform/'lib/NangateOpenCellLibrary_typical.lib'
sram = repo/'issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib'
cpus = os.environ.get('OMP_NUM_THREADS', '8')
commands = []
def run(args, log):
    args = list(map(str, args))
    with open(log, 'w') as f:
        rc = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT).returncode
    commands.append(dict(args=args, log=log, returncode=rc))
    (out/'commands.json').write_text(json.dumps(commands, indent=2))
    assert rc == 0, (log, rc)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# Give ORFS a private, immutable-source-free output tree for streamout.
results = out/'flow/results/nangate45'/nickname/'base'
results.mkdir(parents=True)
for ext in ('odb', 'def', 'v', 'sdc', 'spef'):
    shutil.copyfile(candidate/f'candidate.{ext}', results/f'6_final.{ext}')
(out/'config.mk').write_text(config.read_text()+f'\nexport DESIGN_NICKNAME = {nickname}\n')
run(['make', '-C', '/OpenROAD-flow-scripts/flow', f'DESIGN_CONFIG={out}/config.mk',
     f'WORK_HOME={out}/flow', f'NUM_CORES={cpus}', 'do-gds'], 'gds.log')
gds = results/'6_final.gds'
assert gds.is_file()
deck = platform/'drc/FreePDK45.lydrc'
assert sha(deck) == '4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
run(['klayout', '-b', '-r', deck, '-rd', f'in_gds={gds}', '-rd', f'report_file={out}/full-deck.lyrdb'], 'full-deck.log')
items = len(ET.parse(out/'full-deck.lyrdb').findall('.//items/item'))
body = f'set_thread_count {cpus}\nread_liberty {{{lib}}}\n'
if role == 'S': body += f'read_liberty {{{sram}}}\n'
body += f'''read_db {{{candidate}/candidate.odb}}
read_sdc {{{candidate}/candidate.sdc}}
read_spef {{{candidate}/candidate.spef}}
set_propagated_clock [all_clocks]
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 gs_whole_drc
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > electrical.rpt
report_parasitic_annotation -report_unannotated > annotation.rpt
write_timing_model -library_name {top}_tt -cell_name {top} {top}.lib
write_abstract_lef -bloat_occupied_layers {top}.lef
'''
(out/'verify.tcl').write_text(body)
run(['openroad', '-no_init', '-exit', out/'verify.tcl'], 'verify.log')
report = dict(full_deck_items=items, native_drc_empty=(out/'native-whole-drc.rpt').stat().st_size==0,
              formal_passed=False, parent_passed=False, qualified=False,
              hashes={str(p):sha(p) for p in [candidate/'candidate.odb',gds,deck,out/'full-deck.lyrdb']})
(out/'physical-receipt.json').write_text(json.dumps(report,indent=2))
assert items == 0 and report['native_drc_empty'], report
print('GS_PHYSICAL_CHECK_COMPLETE_FUNCTION_STA_PARENT_GATES_REMAIN')
