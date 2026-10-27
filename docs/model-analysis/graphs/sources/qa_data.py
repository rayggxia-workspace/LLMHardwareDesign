import json,pathlib,re,xml.etree.ElementTree as ET
p=pathlib.Path(__file__).resolve().parent.parent
s=(p/'operator-graphs.html').read_text(encoding='utf-8');m=re.search('<script id="data" type="application/json">(.*?)</script>',s,re.S);data=json.loads(m[1]);total=0
for item in data:
 for k,svg in item['svgs'].items():
  ET.fromstring(svg);g=item['graphs'][k];ids={n['id'] for n in g['nodes']}
  assert len(ids)==len(g['nodes'])
  assert all(e['source'] in ids and e['target'] in ids for e in g['edges'])
  total+=1
 assert item['receipt']['status']=='pass'
print(json.dumps({'embedded_svg_count':total,'model_variants':len(data),'svg_xml_valid':True,'graph_edges_valid':True}))
