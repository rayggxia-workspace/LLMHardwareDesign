from pathlib import Path
import json,hashlib,xml.etree.ElementTree as E
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-physical');cases={}
for typ,directory in [('OAI221_X4','oai221-isolated'),('OAI221_X2','oai221-x2-isolated')]:
 p=r/directory;result={}
 for n in ('merged','library'):
  q=p/(n+'.lyrdb');rows=[dict(category=i.findtext('category'),cell=i.findtext('cell'),values=[v.text for v in i.findall('values/value')]) for i in E.parse(q).findall('.//items/item')];result[n]=dict(count=len(rows),markers=rows,report_sha256=hashlib.sha256(q.read_bytes()).hexdigest())
 assert result['merged']['markers']==result['library']['markers']
 if typ.endswith('X4'):assert result['library']['count']==1 and result['library']['markers'][0]['category']=="'METAL1.5'"
 else:assert result['library']['count']==0
 cases[typ]=dict(reports=result,source_binding=json.loads((p/'export-binding.json').read_text()),deck_identity=(p/'deck-identity.txt').read_text())
v=dict(passed=True,scope='Isolated actual merged cell and original platform library cell each checked with complete unchanged FreePDK45 deck. X4 intrinsic M1.5 failure confirmed; X2 physical source clean. Does not imply parent timing or replacement placement/routing passes.',cases=cases);(r/'oai221-source-qualification.json').write_text(json.dumps(v,indent=2));print(json.dumps({n:{k:x['count'] for k,x in v['cases'][n]['reports'].items()} for n in cases}));print(hashlib.sha256((r/'oai221-source-qualification.json').read_bytes()).hexdigest())
