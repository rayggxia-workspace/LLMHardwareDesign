"""Resume verified S route plus one exact M2 RECT through fresh native finish."""
import hashlib
import json
import shutil
from pathlib import Path


def partition_def(path):
    """Bind every byte outside the single target net, including other nets."""
    digest = hashlib.sha256()
    selected = []
    active = False
    hits = 0
    with path.open('rb') as stream:
        for line in stream:
            if line.lstrip().startswith(b'- words\\[674\\][3] '):
                assert not active
                active = True
                hits += 1
            if active:
                selected.append(line)
                if b';' in line:
                    active = False
            else:
                digest.update(line)
    assert hits == 1 and not active
    return digest.hexdigest(), b''.join(selected).split()


def implement(root, out, cpus, run):
    from io_slots import file_sha, slot
    assert cpus == 16 and out.name == 'revision300-route-s'
    policy = json.loads((root/'project/experiments/block_v1/revision300-s-patch-resume.json').read_text())
    assert policy == dict(schema='revision300-s-patch-resume/1',
        source='block-v1-20261028-246/tasks/revision300-route-s',
        patch_probe='block-v1-20261029-279/tasks/revision300-s-patch-probe',
        same_net_metal2_rect_dbu=[362260,1806770,362460,1806830],
        requires_fresh_final_acceptance=True)
    base = out.parents[2]
    probe = base/'block-v1-20261029-279/tasks/revision300-s-patch-probe'
    pr = json.loads((probe/'receipt.json').read_text())
    assert pr['passed']
    proof = probe/'revision300-s-patch-probe.json'
    assert file_sha(proof) == pr['outputs'][proof.name]
    patch = json.loads(proof.read_text())
    assert patch['passed'] and patch['native_drc_count'] == 0
    source = base/'block-v1-20261028-246/tasks/revision300-route-s'
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed']
    pp = source/'revision300-native-flow.json'
    assert file_sha(pp) == receipt['outputs'][pp.name]
    original = json.loads(pp.read_text())
    assert original['pipeline_completed'] and original['stages'] == [
        'do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
    for name, digest in original['rtl_sha256'].items():
        assert file_sha(root/name) == digest
    original_odb = Path(patch['input_odb'])
    assert file_sha(original_odb) == patch['input_odb_sha256']
    # Independently serialize the original with the same pinned writer. All
    # non-target DEF bytes must be identical; target tokens may only gain RECT.
    (out/'original-def.tcl').write_text('read_db {'+str(original_odb)+'}\nwrite_def original.def\n')
    run(['openroad','-no_init','-exit',out/'original-def.tcl'],'original-def.log')
    patched_def = probe/'patched.def'
    assert file_sha(patched_def) == pr['outputs']['patched.def']
    before_hash, before_tokens = partition_def(out/'original.def')
    after_hash, after_tokens = partition_def(patched_def)
    extra = b'NEW metal2 ( 362260 1806770 ) RECT ( 0 0 200 60 )'.split()
    assert before_hash == after_hash, 'Non-target DEF changed'
    assert before_tokens[-1] == b';'
    assert after_tokens == before_tokens[:-1]+extra+[b';'], 'Unexpected target edit'
    (out/'patch-diff.json').write_text(json.dumps(dict(passed=True,
        outside_target_def_sha256=before_hash, added_tokens=[x.decode() for x in extra],
        original_target_sha256=hashlib.sha256(b' '.join(before_tokens)).hexdigest(),
        patched_target_sha256=hashlib.sha256(b' '.join(after_tokens)).hexdigest()),indent=2)+'\n')
    relative = 'flow/results/nangate45/bv1_block_v1_s16k/base'
    results = out/relative
    results.mkdir(parents=True)
    copied = {}
    for name in ('pins.json','pins.tcl','input.sdc','config.mk'):
        assert file_sha(source/name) == receipt['outputs'][name]
        shutil.copyfile(source/name,out/name)
    # The config still names immutable, hash-bound synthesis/placement inputs.
    # No early stage is invoked. Record this explicitly rather than claiming
    # synthesis/CTS/detail-route were run again.
    for name in ('1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc',
                 '5_1_grt.sdc','bv1-input-diodes.tsv','bv1-input-delay.tsv'):
        p = source/relative/name
        if name == 'bv1-input-delay.tsv' and not p.exists():
            continue
        digest = file_sha(p)
        assert digest == receipt['outputs'][str(p.relative_to(source))]
        with slot(base):
            shutil.copyfile(p,results/name)
        copied[name] = digest
    patched_odb = probe/'patched.odb'
    assert file_sha(patched_odb) == pr['outputs']['patched.odb'] == patch['patched_odb_sha256']
    with slot(base):
        shutil.copyfile(patched_odb,results/'5_2_route.odb')
    result = dict(original)
    result.update(passed=False,pipeline_completed=False,qualified_hard_macro=False,
        stages=original['stages'][:-1],final_files={},
        inherited_stages=original['stages'][:-1],fresh_finish_commands=[],
        source_route_task=str(source),source_route_receipt_sha256=file_sha(source/'receipt.json'),
        patch_probe_receipt_sha256=file_sha(probe/'receipt.json'),
        patch_diff_sha256=file_sha(out/'patch-diff.json'),inherited_files_sha256=copied,
        requires_fresh_final_acceptance=True,
        scope='Same RTL/constraints, inherited sealed synthesis through detailed routing plus exactly one same-net M2 RECT; fresh fill, route aliases and native finish/RCX. No previous final gate transfers.')
    def save():
        (out/'revision300-native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    command = ['make','-C','/OpenROAD-flow-scripts/flow',
               'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    for stage in ('do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish'):
        run(command+[stage],stage+'.log')
        result['fresh_finish_commands'].append(stage)
        save()
    result['stages'].append('do-finish')
    for suffix in ('v','sdc','def','odb','spef'):
        p = results/('6_final.'+suffix)
        assert p.is_file() and p.stat().st_size
        result['final_files'][p.name] = dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    assert file_sha(original_odb) == patch['input_odb_sha256']
    assert all(file_sha(results/name) == digest for name,digest in copied.items())
    result.update(passed=True,pipeline_completed=True,regenerated_rc=True)
    save()
