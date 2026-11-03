"""Receive all qualified leaf six-files as independently verified local ZIPs.

Remote work is read-only uncompressed streaming, with no EDA or new allocation.
Compression and complete archive readback happen on this machine. No system
acceptance is inferred. Partial transfers are preserved under unique names.
"""
from pathlib import Path,PurePosixPath
import base64,concurrent.futures,hashlib,json,re,shlex,shutil,subprocess,tarfile,threading,time,zipfile
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control')
source=repo/'work/YUZE-LU/162/block-delivery-r256-r296/index.json';source_bytes=source.read_bytes();source_sha=hashlib.sha256(source_bytes).hexdigest();index=json.loads(source_bytes)
root=repo.parent.parent/'LLMHardwareDesign-deliveries/issue-162/blocks-r256-r296';root.mkdir(parents=True,exist_ok=True)
total=sum(f['bytes']for r in index['leaves']for f in r['final_files'].values());assert total==867399835 and len(index['leaves'])==1
assert shutil.disk_usage(root).free>total+4*1024**3,'Insufficient local space for declared files and4GiB guard'
lock=threading.Lock();results=[]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for data in iter(lambda:f.read(4*1024**2),b''):h.update(data)
 return h.hexdigest()
def emit(value):
 with lock:print(json.dumps(value,ensure_ascii=True),flush=True)
def receive(row):
 top=row['top'];assert re.fullmatch('[a-zA-Z0-9_]+',top)
 expected=dict(row['final_files']);assert set(expected)=={'6_final.'+s for s in ['v','sdc','def','odb','spef','gds']}
 expected['pins.json']=row['pins']
 for name,field in [('delivery.json','delivery'),('receipt.json','receipt')]:expected['evidence/'+name]=row[field]
 for name,field in [('original-delivery.json','original_delivery'),('fresh-physical-receipt.json','fresh_physical_receipt'),('fresh-timing-receipt.json','fresh_timing_receipt')]:expected['evidence/'+name]=dict(path=row[field],sha256=row[field+'_sha256'])
 # Original accepted M/N/E/G/T provenance lives in the common project tree;
 # every read is still restricted to the exact committed source-index paths.
 for entry in expected.values():assert PurePosixPath('/public/home/yuzelu/project-circuit')in PurePosixPath(entry['path']).parents
 local={}
 image=source.parent/row['image']['path'];assert sha(image)==row['image']['sha256'];local['layout.png']=image.read_bytes()
 local['leaf-index.json']=(json.dumps(row,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 known={n:r['sha256']for n,r in expected.items()};known.update({n:hashlib.sha256(v).hexdigest()for n,v in local.items()})
 output=root/(top+'.zip');temporary=root/(top+'.partial-'+str(time.time_ns()))
 if not output.exists():
  encoded=base64.b64encode(json.dumps({n:v['path']for n,v in expected.items()}).encode()).decode()
  program="import tarfile,sys,json,base64;rows=json.loads(base64.b64decode('"+encoded+"'));t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|');"+"[t.add(path,arcname=name,recursive=False)for name,path in rows.items()];t.close()"
  log=root/(top+'.transport-'+str(time.time_ns())+'.log');received=0;stamp=time.monotonic()
  with log.open('wb')as errors:
   process=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','yuzelu@10.129.166.172','python3 -c '+shlex.quote(program)],stdout=subprocess.PIPE,stderr=errors)
   try:
    with tarfile.open(fileobj=process.stdout,mode='r|')as stream,zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True)as archive:
     seen=set()
     for member in stream:
      name=member.name;assert member.isfile()and name in expected and name not in seen;seen.add(name)
      if 'bytes'in expected[name]:assert member.size==expected[name]['bytes']
      h=hashlib.sha256();count=0
      with stream.extractfile(member)as incoming,archive.open(name,'w',force_zip64=True)as outgoing:
       for data in iter(lambda:incoming.read(4*1024**2),b''):
        outgoing.write(data);h.update(data);count+=len(data);received+=len(data)
        if time.monotonic()-stamp>15:emit(dict(top=top,transfer_bytes=received,pending=True));stamp=time.monotonic()
      assert count==member.size and h.hexdigest()==expected[name]['sha256'],(top,name,'remote byte hash mismatch')
     assert seen==set(expected)
     for name,data in local.items():archive.writestr(name,data)
    assert process.wait(timeout=45)==0,(top,log)
   finally:
    if process.poll()is None:process.terminate();process.wait(timeout=15)
    if process.stdout:process.stdout.close()
  archive_path=temporary
 else:archive_path=output
 # Read every delivered member back through ZIP/CRC and SHA, not just headers.
 with zipfile.ZipFile(archive_path)as archive:
  assert set(archive.namelist())==set(known)and len(archive.namelist())==len(known)
  for name,digest in known.items():
   h=hashlib.sha256()
   with archive.open(name)as stream:
    for data in iter(lambda:stream.read(4*1024**2),b''):h.update(data)
   assert h.hexdigest()==digest,(top,name,'local archive readback mismatch')
 if archive_path!=output:assert not output.exists();temporary.rename(output)
 result=dict(top=top,path=str(output),bytes=output.stat().st_size,sha256=sha(output),six_file_uncompressed_bytes=sum(e['bytes']for e in row['final_files'].values()),members_sha256=known,all_six_files_and_archive_crc_sha_readback_passed=True)
 with lock:
  results.append(result);state=dict(passed=False,whole_system_qualified=False,source_index_sha256=source_sha,completed=results,expected_types=1)
  p=root/'transfer-state.tmp';p.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');p.replace(root/'transfer-state.json')
 emit(dict(top=top,local_zip_bytes=result['bytes'],verified=True,completed_types=len(results)))
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:completed=list(pool.map(receive,index['leaves']))
assert len(completed)==1 and sum(r['six_file_uncompressed_bytes']for r in completed)==total
receipt=dict(passed=True,individually_qualified_types=1,six_file_count=6,six_file_uncompressed_bytes=total,local_zip_bytes=sum(r['bytes']for r in completed),source_index_sha256=source_sha,source_index=str(source),whole_system_qualified=False,all_archives_readback_passed=True,completed_at=time.time(),blocks=completed,scope='Local readback of actual newly qualified R256 computation physical type, actual six-files/layout/evidence. No upper combination/RC/300MHz acceptance inferred.')
(root/'RECEPTION.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');(root/'SOURCE_INDEX.json').write_bytes(source_bytes)
(root/'README.md').write_text('# Issue162 已验收单块文件\n\n1种R256计算物理块，每种ZIP含V/SDC/DEF/ODB/SPEF/GDS、真实版图、逐块索引和5份源绑定验收回执。RECEPTION.json记录每个ZIP及成员SHA，全部成员已从ZIP重新解压读取并逐SHA核对。\n\n这些是单块合格结果；完整组合M11/M12、PG、三个RC角点与300MHz仍单独执行，不能从此包推断系统通过。完整组合继续独立验收。\n',encoding='utf-8')
emit({k:receipt[k]for k in ['passed','individually_qualified_types','six_file_count','six_file_uncompressed_bytes','local_zip_bytes','whole_system_qualified']})
