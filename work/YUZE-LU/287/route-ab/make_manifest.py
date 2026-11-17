import pathlib,json,hashlib,platform
p=pathlib.Path(__file__).resolve().parent
old=P=pathlib.Path('/public/home/yuzelu/project-circuit/issue287-route-ab-20261117')
def digest(f):
 h=hashlib.sha256()
 with f.open('rb') as stream:
  for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
sources=[old/'A-mapped.json',old/'field-A/field.in',old/'field-B/field.in',old/'C-ports.tsv',old/'U-ports.tsv',pathlib.Path('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json'),pathlib.Path('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/spec.json')]
for f in ['C','U']:
 sources.append(pathlib.Path('/public/home/yuzelu/project-circuit/algo2-current-blocks-20261116/physical-binding/endpoint-handoff/stress/blocks')/f/'4_cts.odb')
sources += [pathlib.Path('/public/home/yuzelu/project-circuit/yzl-c-segment-250mhz-20261116/flow/results/nangate45/c-native-frame/base/6_final.odb'),pathlib.Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.odb'),pathlib.Path('/public/home/yuzelu/PingyangHuang/issue-199-field-xXrAwSOn/job-98267/field_row')]
out=dict(scope='All 646 non-P scheme/net rows; static upper geometry field loads and real endpoints, not complete STA',python=platform.python_version(),jobs=[119532,119540],source_sha256={str(f):digest(f) for f in sources},artifact_sha256={f.name:digest(f) for f in p.iterdir() if f.is_file() and f.suffix in ['.py','.sbatch','.csv','.tsv','.json'] and not f.name.endswith('.summary.json') and f.name!='manifest-all.json'})
(p/'manifest-all.json').write_text(json.dumps(out,indent=2));print('MANIFEST_COMPLETE')
