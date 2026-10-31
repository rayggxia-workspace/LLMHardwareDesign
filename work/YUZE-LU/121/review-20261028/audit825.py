from pathlib import Path
import json,hashlib,subprocess
p=Path('work/YUZE-LU/121/review-20261028/r-404-grt-failure-825');d=json.loads((p/'index.json').read_bytes())
paths=[(p/n).as_posix()for n in d['files']]
raw=subprocess.check_output(['git','cat-file','--batch'],input=''.join('HEAD:'+n+'\n'for n in paths).encode());pos=0
for name,row in d['files'].items():
 f=p/name;assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']
 end=raw.index(b'\n',pos);head=raw[pos:end].split();assert head[1]==b'blob';n=int(head[2]);pos=end+1
 assert hashlib.sha256(raw[pos:pos+n]).hexdigest()==row['sha256']and n==row['bytes'],name;pos+=n+1
assert pos==len(raw)
print('825 exact local and Git bytes PASS',len(paths),'files;37 large files actual server hash indexed')
