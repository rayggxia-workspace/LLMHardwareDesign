from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
r=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-461');expected={'source.tar': '2919ca01229084967c08740b6de077e6f5d2e5224ef41f5604d872dc19288f2c', 'node-queue.json': '24121f01cbc002dcbf249c96213ea544bbd9f1154b496c534fbf9ba1799ea623', 'manifest.json': '8296aa455f49c5825ad21d4ad6cb67304170ce54ce8203937b29811d619ad538'}
for n,h in expected.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
m=json.loads((r/'manifest.json').read_text());q=json.loads((r/'node-queue.json').read_text());assert r.name==m['run_id'] and m['source_commit']=='074923df01c2980d9fb4c08f765a0d557ee145bd' and m['source_archive_sha256']==expected['source.tar']
assert m['tasks'][0]['argv']==['bash',str(r/'src/project/experiments/block_v1/worker.sh'),str(r/'src'),'native-node-queue']
assert q['state_path']==str(r/'node-queue-state.json') and all(t['source']==str(r/'src')and t['cwd']==str(r/'tasks'/t['id'])for t in q['tasks'])
with tarfile.open(str(r/'source.tar'))as t:assert json.load(t.extractfile('bundle-manifest.json'))['source_commit']==m['source_commit'];t.extractall(str(r/'src'))
sys.path.insert(0,str(r/'src/project/experiments/block_v1'));from native_node_queue import validate;validate(q,r.parent)
proof=dict(passed=True,actual_remote_sha256=expected,run_directory_and_manifest_same=True,actual_archive_source_commit_matches=True,queue_and_argv_paths_exact=True,source_commit=m['source_commit'],scope='Crossfile source/run/argv identity guard before any dispatch;460 wrong manifest is not reused.')
(r/'stage-identity-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('IDENTITY_GUARD_PASS',r.name,flush=True)
subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'],check=True,cwd=str(r))
