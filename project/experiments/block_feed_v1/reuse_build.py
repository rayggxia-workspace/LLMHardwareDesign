"""Reuse a successful exact-input gate build, but rerun every final test."""
import json
from pathlib import Path
import shutil
from io_slots import file_sha as sha


def receive(out,previous,compiler,top,inputs):
    previous=previous.resolve()
    r=json.loads((previous/'receipt.json').read_text());assert r['passed']
    f=json.loads((previous/'final-function.json').read_text())
    assert f['passed'] and len(f['initial_runs'])==3
    assert all(x['result']['passed'] for x in f['initial_runs'].values())
    assert sha(previous/'final-function.json')==r['outputs']['final-function.json']
    commands=[c for c in r['commands'] if c['command'][0]==compiler and '--build' in c['command']]
    assert len(commands)==1 and commands[0]['returncode']==0
    command=commands[0]
    assert sha(previous/command['log'])==command['sha256']
    before=list(map(Path,command['command'][-len(inputs):]))
    producer_root=previous.parents[1]
    manifest=json.loads((producer_root/'source-manifest.json').read_text())
    bindings=[]
    for old,new in zip(before,inputs):
        digest=sha(old);assert sha(new)==digest
        if previous in old.parents:assert digest==r['outputs'][str(old.relative_to(previous))]
        else:assert digest==manifest['files'][str(old.relative_to(producer_root))]
        bindings.append(dict(original=str(old),current=str(new),sha256=digest))
    original=previous/'obj'/('V'+top)
    digest=sha(original);assert digest==r['outputs'][str(original.relative_to(previous))]
    target=out/'obj';target.mkdir();target=target/original.name
    shutil.copy2(original,target);assert sha(target)==digest
    for name,new in [('receipt.json','build-reuse-receipt.json'),('final-function.json','build-reuse-function.json')]:
        shutil.copyfile(previous/name,out/new)
    return dict(passed=True,receipt=str(previous/'receipt.json'),receipt_sha256=sha(previous/'receipt.json'),
        function_sha256=sha(previous/'final-function.json'),inputs=bindings,binary_sha256=digest,
        original_compile_command=command,all_inputs_byte_identical=True,
        scope='Successful complete physical gate build with every ordered compiler input byte-identical; binary copied byte-exactly, all three final simulations rerun for current sealed candidate')
