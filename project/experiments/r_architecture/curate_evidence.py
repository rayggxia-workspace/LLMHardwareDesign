"""Archive complete partition certificates without thousands of Git review files."""
from pathlib import Path
import io,tarfile,gzip,json,hashlib,subprocess
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'
def main():
 archives=[]
 for n,k in [(35,'A1'),(51,'A2h')]:
  root=E/f'attempt{n:03d}/results/{k}-full-proof';members={}
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   rel=p.relative_to(root)
   if p.name not in ['receipt.json','PARTS.json','COVERAGE.json','COVERAGE.json.gz','complete.log','complete.log.gz']:continue
   name=rel.as_posix();data=p.read_bytes()
   if p.suffix=='.gz':data=gzip.decompress(data);name=name[:-3]
   members[name]=data
  stream=io.BytesIO()
  with tarfile.open(fileobj=stream,mode='w')as t:
   for name,data in sorted(members.items()):
    ti=tarfile.TarInfo(name);ti.mtime=0;ti.size=len(data);t.addfile(ti,io.BytesIO(data))
  archive=root/'PARTITION_CERTIFICATES.tar.gz';archive.write_bytes(gzip.compress(stream.getvalue(),mtime=0));archives.append(dict(path=str(archive.relative_to(D)),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=len(members),scope='complete per-part proof receipts, original SAT logs, full exact coverage and aggregate receipt'))
 (D/'PROOF_ARCHIVES.json').write_text(json.dumps(archives,indent=2)+'\n')
 collection=E/'FINAL_COLLECTED.json'
 if collection.exists():(E/'COLLECTION_MANIFEST.json.gz').write_bytes(gzip.compress(collection.read_bytes(),mtime=0))
 # Preserve old tracked stage1 evidence; ignore new uncurated raw snapshots.
 (D/'evidence/.gitignore').write_text('*\n!.gitignore\n')
 selected=[]
 for p in E.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(E);parts=rel.parts
  if p.name=='STATE_DIAGNOSTIC.json'or parts[0]=='attempt047':continue
  if any(s.startswith('part')and len(s)==8 and s[4:].isdigit()for s in parts):continue
  if len(parts)>=2 and parts[0].startswith('attempt'):
   if any(s in parts for s in ['same-full-proof','wrong-full-proof','controls','A1-proof','A2-proof','A2g-proof','proof-route-selftest']):continue
   if p.name in ['complete.log','complete.log.gz','prepare.log','prepare.log.gz','COVERAGE.json','COVERAGE.json.gz','PARTS.json','receipt.json','PARTITION_CERTIFICATES.tar.gz','STATE_RELATION_RULE.json','INVENTORY.json','COST.json','RESULTS.json','MANIFEST.json','REAL_CONFIG.json','BINARY.json','BINARY_VERSIONS.json','GEOMETRY.json','STA_RECEIPTS.json','ODB_RECEIPTS.json','FLOW_RECEIPT.json','PARTITION_SELFTEST.json']or p.name.endswith(('.trace.csv','.trace.csv.gz','.webp','.tsv.gz'))or len(parts)==3 and parts[1]=='results'and p.suffix=='.json':selected.append(p)
   elif '/physical/'in p.as_posix()and p.name in ['receipt.json','NETLIST_NORMALIZATION.json','config.mk','input.sdc','pins.tcl','6_report.json','5_2_route.json','5_1_grt.json','3_3_place_gp.json','5_2_route.log.gz','5_1_grt.log.gz']:selected.append(p)
   elif p.name=='sta.log.gz'and parts[0]in['attempt047','attempt052']:selected.append(p)
  elif p.name.startswith(('deployment','superseded-proof-jobs'))or p.name in ['PHYSICAL_METRICS_SNAPSHOT.json','COLLECTION_MANIFEST.json.gz']:selected.append(p)
 # Add only selected files; the complete raw artifacts remain locally/remotely.
 names=[str(p.relative_to(R))for p in selected]
 for i in range(0,len(names),100):subprocess.run(['git','add','-f','--']+names[i:i+100],cwd=R,check=True)
 (D/'FINAL_EVIDENCE.json').write_text(json.dumps([dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)for p in selected],indent=2)+'\n')
 print(json.dumps(dict(curated_files=len(selected),archives=archives),indent=2))
if __name__=='__main__':main()
