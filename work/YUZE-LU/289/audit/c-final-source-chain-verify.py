from pathlib import Path
import json,hashlib
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117'); checked={}; checks=[]; container_bound={}
def digest(p):
    p=Path(p); d=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):d.update(b)
    checked[str(p)]=d.hexdigest();return d.hexdigest()
def check(p,h): assert digest(p)==h,(str(p),h)
def read(p): p=Path(p);digest(p);return p.read_text()
def j(p): return json.loads(read(p))
def yes(name,test): assert test,name;checks.append(name)
def recorded_dependency(p,h):
    if Path(p).is_file():check(p,h)
    else:
        assert p.startswith('/OpenROAD-flow-scripts/'),('missing non-container input',p)
        container_bound[p]=h
digest(__file__)
indexpath=R/'audit/C-final-source-proof-chain-index.json'; index=j(indexpath)
entries={e['stage']:e for e in index['entries']}
for e in entries.values():check(e['path'],e['sha256'])
def stage(name):return j(entries[name]['path'])
o=stage('original-source-set');yes('Original source receipt pass',o['all_original_sources_match_recorded_hashes'])
for f in o['original_files']:check(f['path'],f['sha256'])
raw=stage('parallel-selector-inputs')
for n,v in raw['files'].items():check(R/'cu'/n,v['raw_sha256'])
ob=stage('parallel-selector-obligations')
yes('Parallel structural equalities and 77 outputs',ob['selector_formal_equivalence_bits']==77 and all(ob[k] for k in ['pure_lane_evaluator_functions_byte_equal','all_sequential_always_blocks_byte_equal','ports_state_and_continuous_assigns_byte_equal']))
yes('Normalized parallel hash explicitly resolves to raw999948',ob['parallel_sha256']==raw['files']['loader-parallel.sv']['normalized_text_sha256'] and raw['files']['loader-parallel.sv']['raw_sha256']==index['source_hash_chain'][1])
sel=read(R/'cu/select-proof-recovery.log');yes('Actual selector 77 proven /0 unproven', '77 are proven and 0 are unproven' in sel and 'Equivalence successfully proven!' in sel)
div=j(R/'cu/div3-exhaustive.json');yes('Div3 all2048 inputs',div['tested_inputs']==2048 and div['failures']==0 and div['input_width']==11)
yes('Actual div3 SAT SUCCESS','SAT proof finished - no model found: SUCCESS!' in read(R/'cu/div3-proof.log'))
arith=stage('arithmetic-inverse-binding'); a=arith['candidates']['loader-distributed-parallel-reviewed.sv']
yes('Exact arithmetic inverse to parallel raw source',a['inverse_substitution_exact_to_reference'] and a['raw_sha256']==index['source_hash_chain'][2] and a['reference_raw_sha256']==index['source_hash_chain'][1] and arith['div3_failures']==0)
check(R/'audit/loader-distributed-parallel-reviewed.sv',a['raw_sha256'])
one=stage('onehot-binding');yes('Onehot direct proof receipt',one['proof_result']=='direct SAT all outputs SUCCESS')
for n,h in one['hashes'].items():check(R/'audit'/n,h)
yes('Actual onehot SAT SUCCESS','SAT proof finished - no model found: SUCCESS!' in read(entries['onehot-actual-solver']['path']))
cache=stage('cache-transform-binding');yes('Cache source/candidate/512bits/252key',cache['passed'] and cache['source_sha256']==index['source_hash_chain'][3] and cache['candidate_sha256']==index['source_hash_chain'][4] and cache['cache_bits_added']==512 and cache['address_configuration_bits']==252)
check(entries['cache-induction-model']['path'],cache['induction_model_sha256']);check(entries['cache-induction-script']['path'],cache['induction_script_sha256'])
log=read(entries['cache-induction-actual-solver']['path'])
yes('Joint cache base and inductive-step SAT SUCCESS', all(x in log for x in ["Import proof-constraint: \\bad_induction = 1'0","Import proof-constraint: \\bad_reset = 1'0",'SAT proof finished - no model found: SUCCESS!']))
generic=stage('generic523');yes('Actual generic523 EQY PASS',generic['passed'] and generic['total_partitions']==523 and generic['EQY_status']=='PASS')
for key in ['source_hashes','hashes']:
    for p,h in generic[key].items():
        recorded_dependency(p,h)
part=Path(entries['generic523']['path']).parent/'proof-work/partition.list'
yes('Actual partition list523',len([l for l in read(part).splitlines() if l.strip()])==523)
eqlog=read(part.parent/'logfile.txt');yes('Actual EQY log pass','PASS' in eqlog and 'Successfully proved equivalence' in eqlog)
ff=stage('ff-lowering');yes('Actual FF22119 exhaustive semantics',ff['passed'] and ff['flipflops']==22119 and ff['truth_table_assignments']==255955 and ff['other_cells_exact']==206522)
for p,h in ff['hashes'].items():
    recorded_dependency(p,h)
binding=stage('actual-ff-abc-binding');yes('Actual FF byte-isolated netlist binding',binding['passed'] and binding['ff_stage_passed'] and binding['actual_netlists_byte_identical']['1_synth_lec.v']==index['source_hash_chain'][-2] and binding['actual_netlist_state_count']==21095)
check(entries['ff-lowering']['path'],binding['ff_receipt_sha'])
cec=stage('actual-abc-cec');yes('Actual ABC allgroups CEC',cec['passed'] and len(cec['groups'])>0 and all(g['passed'] for g in cec['groups']))
for g in cec['groups']:
    p=Path(g['directory']);check(p/'input.blif',g['input_sha']);check(p/'output.blif',g['output_sha']);check(p/'cec.log',g['log_sha'])
    yes('ABC retained actual combinational networks equivalent','Networks are equivalent' in read(p/'cec.log'))
    yes('ABC input binds isolated FF stage',g['input_sha']==binding['abc_input_byte_identical_to_proven_cec119786'])
final=stage('actual-final');yes('Actual final complete proof receipt',final['passed'])
for p,h in final['receipts'].items():
    check(p,h);v=j(p);yes('Actual final subreceipt '+Path(p).parent.name,v['passed'])
    if 'proof' in v:yes('Final exact boundary solver checks '+Path(p).parent.name,all(v['proof']['checks'].values()))
    if 'state_count' in v:yes('Final control21095 states',v['state_count']==21095)
exp=stage('actual-odb-export');yes('Actual ODB fresh export binds saved final',exp['export_verified'] and exp['saved_final_verilog_exact'])
for p,h in final['hashes'].items():
    if p.endswith('/gold.v') or p.endswith('/gate.v'):check(p,h)
manual=[entries[k] for k in ['parallel-manual-proof','arithmetic-inverse-binding','distribution-bitwidth','cache-invariant-manual-bridge']]
out=dict(passed=True,automatic_obligation_receipts_verified=True,checks=checks,manual_compositional_bridges=manual,manual_bridges_automatically_proven=False,container_dependencies_previously_verified_in_frozen_proof_jobs=container_bound,scope='Machine verification of source-bound finite proof obligations and actual generic/FF/ABC/final equivalence receipts. Complete correctness also relies on the explicitly listed exact-source manual compositional bridges and trusted frontend normalizations. Container-only library bytes retain the actual proof-job hash binding and are not re-opened by this login-host metadata check. This does not promote whole-module SAT timeouts to success.',whole_module_RTL_SAT_claimed=False,four_state_X_equivalence_claimed=False,physical_acceptance=False,source_hash_chain=index['source_hash_chain'],input_sha256=checked)
outpath=R/'audit/C-final-source-chain-semantic-verification.json';outpath.write_text(json.dumps(out,indent=2)+'\n');print(outpath,digest(outpath))
