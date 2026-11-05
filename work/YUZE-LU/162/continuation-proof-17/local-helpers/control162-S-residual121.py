import subprocess, shlex

q = r'''from pathlib import Path
import hashlib,json,os,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
s=b/'source-121';assert(s/'freeze-import.json').exists()
base=b/'s-internal-composition-01/1182'
config=b/'route-selection-102/s1182-native-residual-config121.json'
spec_path=b/'dynamic-02/node26/pending/00-j-s1182-native-residual.json'
out=base/'native-cap-residual'
assert base.is_dir()and not config.exists()and not spec_path.exists()and not out.exists()
config.write_text(json.dumps(dict(native_sta=str(base/'native-sta'),placements=[str(base/'cap-preflight')]),indent=2))
spec=dict(script='system_upper.py',source_root=str(s),forecast_gib=32,
 requires=[str(base/'native-sta/native-system-audit.json'),str(base/'cap-preflight/receipt.json')],
 args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json',
 '--native-cap-residual-config',config,'--out',out])))
temp=spec_path.with_suffix('.tmp');temp.write_text(json.dumps(spec));os.rename(str(temp),str(spec_path))
record=b/'route-selection-102/s1182-native-residual-source121.json'
assert not record.exists()
record.write_text(json.dumps(dict(time=time.time(),path=str(spec_path),sha256=hashlib.sha256(spec_path.read_bytes()).hexdigest(),
 config=str(config),config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),spec=spec,
 scope='Fresh new-S actual joined native SPEF ground capacitance plus optimistic upper-wire diagnostic. Waits for new S native and fixed-PG qualification, new actual graph and native STA. Zero violations are necessary only. No old335 acceptance or stale native cap reused.'),indent=2))
print('Appended one immutable source121 residual-cap diagnostic behind newS1182 native/fixed-PG qualification and exact new native STA. No active or existing queued task changed.')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
