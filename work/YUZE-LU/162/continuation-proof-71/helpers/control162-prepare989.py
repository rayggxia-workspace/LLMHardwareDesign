from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-audit961.py').read_text(encoding='utf-8').replace('r256-pin-release-active-pool-audit-961','r256-native-warm-active-pool-audit-989')
a=s.index(' for seed,baseline in');z=s.index(' for job,node,folder',a)
s=s[:a]+''' for seed in [9810,9811]:
  manifest=b/'r256-composition-453'/('warm-seed-'+str(seed)+'.json');cfg=json.loads(manifest.read_text());original=Path(cfg['input']);prefix=Path(cfg['prefix']);assert sha(original)==cfg['input_sha256']and sha(prefix)==cfg['prefix_sha256']
  h,body=original.read_bytes().split(b'\\n',1)
  for i in range(16):
   p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes().split(b'\\n',1)[1]==body
   snapshot=p.parent/'output.txt.native-prefix-paths.txt';assert sha(snapshot)==cfg['prefix_sha256']
   log=p.parent/'output.txt.native-prefix.log';lines=[json.loads(x)for x in log.read_text().splitlines()if x.startswith('{')];rows=[x for x in lines if'conflict_nodes'in x];assert len(rows)==1 and rows[0]['conflict_nodes']==0 and rows[0]['round']==0
   r['comparisons'].append(dict(candidate=seed,trial=i,input_sha256=sha(p),seed_manifest=str(manifest),seed_manifest_sha256=sha(manifest),seed_native_prefix_sha256=sha(prefix),actual_imported_prefix_sha256=sha(snapshot),native_rounds=rows,original_input_body_byte_exact=True,actual_warm_zero_prefix_byte_exact=True))
'''+s[z:]
s=s.replace("[9490],[6360,8301,9280,9490]","[9810],[6360,8301,9280,9810]").replace("[9491],[9060,9061,9281,9491]","[9811],[9060,9061,9281,9811]")
s=s.replace("'--pin-access=ordinary-first','--native-batch-ripup','--release-pin-reservations'","'--pin-access=none','--native-prefix-flexible'")
s=s.replace("assert ('--native-refresh=8'in cmd)==(seed==9491);", "assert '--native-prefix-input='+json.loads((b/'r256-composition-453'/('warm-seed-'+str(seed)+'.json')).read_text())['prefix']in cmd;assert not any(x.startswith('--native-refresh=')for x in cmd);")
a=s.index("scope='");z=s.index("')\nexcept",a)
s=s[:a]+"scope='Actual9810/9811 each16 owned source972 children.32actualinputs bodies match source seeds;32actual zero-native snapshot files byte-identical to validated imported prefixes. Independent16CPU masks and all4active slots pernode disjoint, actual224/256GiB memory admissions checked. Every native M11/M12 wire remains movable under original finite wire budgets; actualM11landings and M1-M10 interiors unchanged. Actual973/980/984 tests/source/14strictfuturefullstage bindings required; originalgeometry/PG/currentfunctions/events/3RC300MHz gates unchanged. No fullroute or physical acceptance inferred"+s[z:]
compile(s,'audit989','exec');(h/'control162-audit989.py').write_text(s,encoding='utf-8');print('prepared989 real32child/prefix/CPU/memory audit')
