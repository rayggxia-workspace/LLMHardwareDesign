from pathlib import Path
import json,hashlib,ast,datetime,re
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/publication-runtime-680-682';assert out.exists()
src=(h/'control162-delivery-status683.py').read_text(encoding='utf-8')
old='continuation-proof-54/r256-padding-final-function-audit-472/receipt.json';new='continuation-proof-55/final-program-supplement/r256-padding-final-function-audit-472/receipt.json';assert(r/'work/YUZE-LU/162'/new).is_file()
tree=ast.parse(src.replace(old,new));node=[x for x in tree.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='s'for t in x.targets)][-1]
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds');s=eval(compile(ast.Expression(node.value),'program-header','eval'),{'now':now});p=r/'docs/CONTROL_V1_REAL_PROGRAMS.md'
assert not p.read_text(encoding='utf-8').startswith('# 当前真实程序证据：453');p.write_bytes((s+p.read_text(encoding='utf-8')).encode())
for name in ['CONTROL_V1_BLOCK_DELIVERY.md','CONTROL_V1_REAL_PROGRAMS.md']:
 p=r/'docs'/name;header=p.read_text(encoding='utf-8').split('\n# ',1)[0]
 for target in re.findall(r'\]\(([^)]+)\)',header):assert(p.parent/target).resolve().is_file(),target
(out/'helper684.py').write_bytes(Path(__file__).read_bytes());d=json.loads((out/'index.json').read_text(encoding='utf-8'));d['rows'].append(dict(relative='helper684.py',bytes=(out/'helper684.py').stat().st_size,sha256=hashlib.sha256((out/'helper684.py').read_bytes()).hexdigest()));d['metadata_failure']='683 preserved first header/raw evidence, then asserted incorrectly guessed local472 location before writing program header. Actual rg inventory located472 in proof55/final-program-supplement;684 wrote corrected header and checked all new header links. No remote jobs, sources, specifications or acceptance gates changed.';(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(new_header_links_verified=True,preserved_metadata_failure=True)))
