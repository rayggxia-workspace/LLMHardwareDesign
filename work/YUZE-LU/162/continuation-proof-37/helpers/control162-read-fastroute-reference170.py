"""Read official upstream source for diagnosis; never claim installed-version identity."""
import urllib.request,json,concurrent.futures,hashlib
from pathlib import Path
root=Path(r'D:\Data\电路实验\control162-openroad-fastroute-reference170');assert not root.exists()
url='https://api.github.com/repos/The-OpenROAD-Project/OpenROAD/contents/src/grt/src/fastroute/src'
def read(url):
 req=urllib.request.Request(url,headers={'User-Agent':'LLMHardwareDesign-Issue162-reference'})
 with urllib.request.urlopen(req,timeout=15)as r:return r.read()
items=json.loads(read(url));files=[r for r in items if r['type']=='file'and r['name'].endswith(('.cpp','.h'))];root.mkdir();rows=[]
def fetch(item):
 data=read(item['download_url']);(root/item['name']).write_bytes(data);return dict(name=item['name'],upstream_git_blob=item['sha'],url=item['download_url'],sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 for r in pool.map(fetch,files):rows.append(r)
(root/'index.json').write_text(json.dumps(dict(repository='The-OpenROAD-Project/OpenROAD',listing_url=url,files=rows,installed_version_equivalence=False),indent=2))
for r in rows:
 lines=(root/r['name']).read_text(encoding='utf-8').splitlines()
 for i,line in enumerate(lines):
  if 'maximum allowed'in line or '228,'in line:print(r['name'],i+1,'\n'.join(lines[max(0,i-5):i+9]))
print('Official reference files',len(rows),'installed version correspondence unverified')
