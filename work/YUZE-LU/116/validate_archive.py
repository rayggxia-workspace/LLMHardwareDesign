"""Validate document relocation and the frozen, lightweight graph archive."""
import hashlib,json,pathlib,re,urllib.parse,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[3]
HERE=pathlib.Path(__file__).resolve().parent
DOC=ROOT/'docs/model-analysis';GRAPH=DOC/'graphs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((HERE/'archive-manifest.json').read_text(encoding='utf-8'))
for path,expected in record['byte_identical_imports'].items():
 assert sha(ROOT/path)==expected['sha256'],path
for path,expected in record['historical_issue114_files'].items():assert sha(ROOT/path)==expected,path
moved=(DOC/'MODEL_EXPERIMENT_ANALYSIS.md').read_text(encoding='utf-8')
restored=re.sub(r'\]\(([^)]+)\)',lambda m:']('+m[1][3:]+')' if m[1].startswith('../../') else m[0],moved)
assert hashlib.sha256(restored.encode()).hexdigest()==record['analysis_migration']['original_sha256'],'Report changed beyond URL rebasing'
checked=[]
def link(base,target):
 if not target or target.startswith(('#','http:','https:','mailto:','data:','javascript:')):return
 if '${' in target:return
 value=urllib.parse.unquote(target.split('#',1)[0].split('?',1)[0])
 if value:
  dest=(base/value).resolve();assert dest.exists(),str(dest);checked.append(str(dest.relative_to(ROOT)))
documents=list(DOC.rglob('*.md'))+[ROOT/x for x in ['README.md','研究资料导读.md','docs/ARCHITECTURE.md','docs/MODEL_EXPERIMENT_ANALYSIS.md','progress/YUZE-LU/STATUS.md','work/YUZE-LU/116/README.md']]
for p in documents:
 s=p.read_text(encoding='utf-8');assert s.count('```')%2==0,str(p)
 for target in re.findall(r'\]\(([^)]+)\)',s):link(p.parent,target)
page=(GRAPH/'operator-graphs.html').read_text(encoding='utf-8')
for target in re.findall(r'href="([^"]+)"',page):link(GRAPH,target)
data=json.loads(re.search('<script id="data" type="application/json">(.*?)</script>',page,re.S)[1])
assert len(data)==10
svg_count=0
for item in data:
 assert item['receipt']['status']=='pass'
 for target in item['paths'].values():link(GRAPH,target)
 for mode in ['raw.graph.json','simplified.graph.json','config.json','receipt.json']:link(GRAPH,item['relative']+'/'+mode)
 for text in item['svgs'].values():ET.fromstring(text);svg_count+=1
 for g in item['graphs'].values():
  ids={n['id'] for n in g['nodes']};assert len(ids)==len(g['nodes'])
  assert all(e['source'] in ids and e['target'] in ids for e in g['edges'])
for path,entry in json.loads((GRAPH/'delivery-manifest.json').read_text(encoding='utf-8')).items():assert sha(GRAPH/path)==entry['sha256'],path
manifest=json.loads((GRAPH/'results/render01/manifest.json').read_text(encoding='utf-8'))
for item in manifest:
 d=GRAPH/'results'/pathlib.PurePosixPath(item['result']).parent.name/item['model']
 receipt=json.loads((d/'receipt.json').read_text(encoding='utf-8'));assert receipt['status']=='pass'
 assert len(receipt['validation'])==3
 for name,entry in receipt['artifacts'].items():
  if name.endswith('.onnx'):continue
  assert sha(d/name)==entry['sha256'],str(d/name)
assert not any(p.suffix in {'.onnx','.whl','.tgz','.pyc'} for p in GRAPH.rglob('*') if p.is_file())
result={'status':'pass','source':'existing experiment archive; no numerical rerun','imported_files_verified':len(record['byte_identical_imports']),'historical_files_unchanged':len(record['historical_issue114_files']),'analysis_body_preserved_except_relative_links':True,'local_links_checked':len(checked),'embedded_svg_xml_valid':svg_count,'successful_layer_receipts':len(manifest),'original_delivery_sha_preserved':True,'weights_or_dependency_packages_imported':False}
(HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
