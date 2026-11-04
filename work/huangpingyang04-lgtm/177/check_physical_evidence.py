"""Check received original reports and Git inputs; optionally reread six files.

Large artifacts and the complete raw archive stay outside Git. The repository
contains the closed acceptance-report subset. Pass --raw-root to reread all
original small files and --files-root to reread the six files and layout images.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent/'physical-evidence'


def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):h.update(block)
 return h.hexdigest()


def blobs(commit,names):
 raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
   input=''.join(commit+':'+n+'\n' for n in names).encode())
 result={};pos=0
 for name in names:
  end=raw.index(b'\n',pos);head=raw[pos:end].split();assert head[1]==b'blob'
  length=int(head[2]);pos=end+1;result[name]=raw[pos:pos+length];pos+=length
  assert raw[pos:pos+1]==b'\n';pos+=1
 assert pos==len(raw)
 return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--files-root',type=Path);p.add_argument('--raw-root',type=Path);args=p.parse_args()
 index=json.loads((HERE/'remote-index.json').read_text())
 reception=json.loads((HERE/'LOCAL_RECEPTION.json').read_text())
 assert index['passed'] and reception['passed']
 assert sha(HERE/'remote-index.json')==reception['remote_index_sha256']
 subset=json.loads((HERE/'COMMITTED_SUBSET.json').read_text())
 assert sha(HERE/'COMMITTED_SUBSET.json')==reception['committed_subset_sha256']
 indexed={row['path']:row for row in index['raw_files']}
 assert all(indexed[row['path']]==row for row in subset['files'])
 selected=index['raw_files'] if args.raw_root else subset['files']
 raw_folder=args.raw_root or HERE/'raw'
 raw={}
 for row in selected:
  f=raw_folder/row['member']
  assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256'],str(f)
  raw[row['path']]=f
 for name,key in [('sacct.txt','sacct_sha256'),('tools.json','tools_sha256')]:
  assert sha(HERE/name)==index[key]
 snapshots=0;rejected=[]
 rejected_root='/public/home/yuzelu/PingyangHuang/issue177-s-physical-20261103T160312Z'
 for name,file in raw.items():
  if name.endswith('/source/source-snapshot.json'):
   snapshot=json.loads(file.read_text());names=list(snapshot['files'])
   source=blobs(snapshot['source_commit'],names)
   mismatch=[n for n,h in snapshot['files'].items() if hashlib.sha256(source[n]).hexdigest()!=h]
   if mismatch:
    # This exact pre-execution archive was rejected by sbatch for CRLF. Keep
    # its failure evidence; never treat it as a canonical or qualified input.
    assert name==rejected_root+'/source/source-snapshot.json',name
    assert sha(file)=='6fb931f725ea31e68e6e7b59c958ecbd17f197b87f5f89932bc40eb8f37c94bb'
    assert snapshot['source_commit']=='301ea4b673cb7074f2cec6621faa82d347ce6e3d'
    assert len(mismatch)==7 and all(hashlib.sha256(source[n].replace(b'\n',b'\r\n')).hexdigest()==snapshot['files'][n] for n in mismatch)
    assert [r['path'] for r in index['raw_files'] if r['path'].startswith(rejected_root+'/')]==[name]
    rejected.append(rejected_root);continue
   snapshots+=1
 assert snapshots>0 and rejected==[rejected_root]
 def qualified(value):
  assert all(root not in json.dumps(value) for root in rejected),'Rejected CRLF archive referenced by qualified evidence'
 root=index['accepted_root'];assert set(index['accepted'])=={'p4','n4','n5'}
 required={'6_final.'+s for s in ('v','sdc','def','odb','spef','gds')}
 reports={'physical':'five-macro-physical.json','drc':'five-macro-drc.json',
          'function':'final-function.json','formal':'formal.json'}
 accepted_snapshot=json.loads(raw[root+'/source/source-snapshot.json'].read_text())
 qualified(accepted_snapshot)
 names=list(accepted_snapshot['files']);current=blobs('HEAD',names)
 assert all(hashlib.sha256(current[n]).hexdigest()==h for n,h in accepted_snapshot['files'].items()),'Current implementation inputs differ'
 file_count=0;total=0
 for variant,accepted in index['accepted'].items():
  delivery=json.loads(raw[root+'/delivery/'+variant+'/delivery.json'].read_text())
  qualified(delivery)
  assert delivery==accepted and delivery['passed'] and delivery['native_leaf_accepted']
  assert set(delivery['final_files'])==required
  drun=json.loads(raw[root+'/delivery/'+variant+'/run.json'].read_text())
  qualified(drun)
  assert drun['passed'] and drun['source_unchanged']
  assert sha(raw[root+'/delivery/'+variant+'/delivery.json'])==drun['outputs']['delivery.json']
  candidates=[name for name,file in raw.items()
              if name.endswith('/sealed/'+variant+'/receipt.json') and sha(file)==delivery['source_receipt_sha256']]
  assert candidates,'No actual sealed receipt matches the four gates'
  sealed=candidates[0].rsplit('/',1)[0]
  sr=json.loads(raw[sealed+'/receipt.json'].read_text())
  assert sr['passed'] and sha(raw[sealed+'/final-source.json'])==sr['outputs']['final-source.json']
  source=json.loads(raw[sealed+'/final-source.json'].read_text())
  qualified([sr,source])
  assert source['passed'] and source['pipeline_completed']
  if source.get('postroute_repair'):
   file=raw[sealed+'/route-repair-proof.json']
   assert sha(file)==source['postroute_repair']['proof_sha256']
   eco=json.loads(file.read_text())
   qualified(eco)
   assert eco['passed'] and eco['native_whole_drc_zero']
   assert eco['identical_non_target_geometry'] and eco['identical_target_terminal_connections']
   assert eco['pin_contacts']['passed'] and eco['unchanged_routes_ports_placement']
   assert sha(raw[eco['source']+'/receipt.json'])==eco['source_receipt_sha256']
   original_receipt=json.loads(raw[eco['source']+'/receipt.json'].read_text())
   original_flow=raw[eco['source']+'/final-source.json']
   qualified([original_receipt,json.loads(original_flow.read_text())])
   assert original_receipt['passed'] and sha(original_flow)==original_receipt['outputs']['final-source.json']
   assert eco['source_files']==json.loads(original_flow.read_text())['final_files']
  for name,row in source['final_files'].items():assert row['sha256']==delivery['final_files'][name]['sha256']
  for name,digest in source['rtl_sha256'].items():assert hashlib.sha256(current[name]).hexdigest()==digest
  for mode,name in reports.items():
   link=delivery['gate_receipts'][mode]
   rfile=raw[link['path']];proof=raw[link['report_path']]
   assert sha(rfile)==link['sha256'] and sha(proof)==link['report_sha256']
   run=json.loads(rfile.read_text());report=json.loads(proof.read_text())
   qualified([run,report])
   assert run['passed'] and run['source_unchanged'] and report['passed']
   assert report['top']==delivery['top']
   assert sha(proof)==run['outputs'][name]
   assert report['source_receipt_sha256']==delivery['source_receipt_sha256']
   if mode=='physical':assert all(report['checks'].values())
   elif mode=='drc':
    assert report['full_deck']['total_items']==0 and not report['native_report'].strip()
    assert report['gds']['sha256']==delivery['final_files']['6_final.gds']['sha256']
    database=proof.parent/'full-deck.lyrdb'
    assert sha(database)==report['full_deck']['report_sha256']
    assert database.stat().st_size==report['full_deck']['report_bytes']
    drc=ET.parse(database).getroot();items=drc.find('items');categories=drc.find('categories')
    assert drc.tag=='report-database' and drc.findtext('top-cell')==delivery['top']
    assert items is not None and len(items)==0 and categories is not None and len(categories)>0
   elif mode=='function':
    assert len(report['initial_runs'])==3 and {x['mode'] for x in report['initial_runs']}=={0,1,2}
    assert all(x['result']['passed'] for x in report['initial_runs'])
    assert report['checks']==sum(x['result']['checks'] for x in report['initial_runs'])
    assert all(x['result']==report['initial_runs'][0]['result'] for x in report['initial_runs'])
   else:
    assert all(report['strict_native_lec']['checks'].values())
    assert report['function_receipt_sha256']==delivery['gate_receipts']['function']['sha256']
    assert sha(proof.parent/'kepler.log')==report['log_sha256']
  for name,row in list(delivery['final_files'].items())+[('layout.png',delivery['image'])]:
   received=reception['files'][variant+'/'+name]
   assert received['sha256']==row['sha256']
   if 'bytes' in row:assert received['bytes']==row['bytes']
   if args.files_root:
    path=args.files_root/variant/name
    assert path.stat().st_size==received['bytes'] and sha(path)==received['sha256']
   file_count+=1;total+=received['bytes']
 suffix=('reread '+str(file_count)+' physical files/images ('+str(total)+' bytes)' if args.files_root
         else 'recorded reception only; large files not reread (pass --files-root to verify them)')
 raw_scope='all original raw files' if args.raw_root else 'committed original report/log subset (full raw archive not reread; pass --raw-root)'
 print('PASS: '+str(len(raw))+' '+raw_scope+'; '+str(snapshots)+' canonical Git source snapshots; 1 known rejected CRLF archive retained and excluded from every qualified receipt; '
       '3 variants x 4 bound final gates; '+suffix+'.')


if __name__=='__main__':main()
