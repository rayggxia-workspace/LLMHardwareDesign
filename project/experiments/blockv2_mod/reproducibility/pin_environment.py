"""Record source roots and transitive Python imports for the current deployment."""
import json,ast,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=(root/'evidence/reference-directory.txt').read_text().strip()
framework=(Path(p)/'../../../../..').resolve()
native=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments')
codecs=Path('/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project')
tlm=Path('/public/home/yuzelu/project-circuit/issue260-tlm-request-Xuwu5O')
roots=[root/'compiler',root/'algo1',root/'tlm',framework,native/'block_local_native',
       native/'mother_control_native',codecs/'control_image_v0_1',codecs/'control_isa_v0_1',
       native/'native_s32_n',tlm]
pending=[root/'compile_graph_input.py',root/'tlm/run_native_package.py']
files={};imports={}
def locate(name):
    for directory in roots:
        path=directory/(name.split('.')[0]+'.py')
        if path.is_file():return path.resolve()
    return None
while pending:
    path=pending.pop().resolve()
    if str(path) in files:continue
    raw=path.read_bytes();tree=ast.parse(raw)
    files[str(path)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    names=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):names.update(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:names.add(node.module)
    imports[str(path)]={}
    for name in sorted(names):
        target=locate(name)
        imports[str(path)][name]=str(target) if target else 'python environment or package'
        if target:pending.append(target)
for directory in [native/'block_local_native',native/'w8a16_g',native/'native_s32_n']:
    for path in directory.glob('*.json'):
        raw=path.read_bytes();files[str(path)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
for path in [native/'w8a16_g/reference.py',root/'hardware/blockv2-mod-nine.json']:
    raw=path.read_bytes();files[str(path)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
config={'schema':'blockv2-mod-runtime-environment/1','module_roots':list(map(str,roots)),
        'python':'/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python',
        'extra_python_roots':[str(root.parent/'chip-state-replay-20261113/deps'),str(root.parent.parent/'operator-graphs-20261026/deps')],
        'dram_library':'/public/home/yuzelu/project-circuit/issue260-tlm-joint-9BiJdfEg/dram-106937.so',
        'dram_config':'/public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini',
        'g_reference':str(native/'w8a16_g/reference.py'),'files':files,'imports':imports,
        'scope':'pinned Python sources and schemas; third-party packages and RTL have separate provenance'}
(root/'reproducibility/environment.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps({'source_and_schema_files':len(files),'bytes':sum(r['bytes'] for r in files.values())}))
