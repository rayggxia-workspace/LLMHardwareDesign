"""Transport immutable public registry bytes using upstream lockfile SHA values.

This stages network data only. It does not alter modules, versions or C++ rules.
"""
from pathlib import Path
import argparse,base64,concurrent.futures,hashlib,json,urllib.parse,urllib.request

p=argparse.ArgumentParser();p.add_argument('--lock',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--supplements',action='store_true');a=p.parse_args()
a.out.mkdir(exist_ok=a.supplements)
entries=json.loads(a.lock.read_text())['registryFileHashes']
if a.supplements:
 supplements={}
 for url,expected in entries.items():
  if not url.endswith('/source.json'):continue
  relative=Path(urllib.parse.urlsplit(url).path.lstrip('/'))
  source=a.out/relative
  assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
  definition=json.loads(source.read_text())
  for kind in ('overlay','patches'):
   for name,integrity in definition.get(kind,{}).items():
    assert '..'not in Path(name).parts and not Path(name).is_absolute()
    algorithm,encoded=integrity.split('-',1);assert algorithm=='sha256'
    suffix='/overlay/'if kind=='overlay'else'/patches/'
    supplements[url[:-len('/source.json')]+suffix+name]=base64.b64decode(encoded,validate=True).hex()
 entries=supplements
def fetch(item):
 url,expected=item;u=urllib.parse.urlsplit(url)
 assert u.scheme=='https'and u.netloc=='bcr.bazel.build'and len(expected)==64
 parts=Path(u.path.lstrip('/')).parts;assert '..'not in parts
 error=None
 for _ in range(3):
  try:
   with urllib.request.urlopen(url,timeout=45)as response:data=response.read()
   assert hashlib.sha256(data).hexdigest()==expected,('Registry bytes differ from pinned lockfile',url)
   dest=a.out.joinpath(*parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   return dict(url=url,sha256=expected,bytes=len(data))
  except Exception as ex:error=ex
 raise error
with concurrent.futures.ThreadPoolExecutor(16)as pool:rows=list(pool.map(fetch,entries.items()))
record={'passed':True,'lock_sha256':hashlib.sha256(a.lock.read_bytes()).hexdigest(),'files':rows,'scope':'Transport of every immutable registry byte from the pinned upstream lockfile; no module/rule/version substitution.'}
(a.out.parent/(a.out.name+('-supplements'if a.supplements else'')+'-receipt.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'passed':True,'files':len(rows),'bytes':sum(r['bytes']for r in rows)}))
