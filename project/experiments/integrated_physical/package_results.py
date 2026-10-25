"""Immutable whole-task artifact index and archive; never labels experiments accepted."""
import argparse,os,tarfile,time
from common import *
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root.resolve();need(str(root)=='/public/home/yuzelu/RuizhiLiang/issue98-integrated-physical-20261025','only own fixed experiment root');need(a.out.parent.resolve()==root,'direct own-root archive');a.out.mkdir(exist_ok=False);src=sources();resources=resource_snapshot();current_log=os.environ['SLURM_JOB_NAME'].removeprefix('lrz-i98-')+'-'+os.environ['SLURM_JOB_ID']+'.log';included=[];excluded=[];inodes={}
for f in sorted(root.rglob('*')):
 if f==a.out or a.out in f.parents:continue
 rel=f.relative_to(root);parts=rel.parts
 if 'tmp'in parts or '__pycache__'in parts:continue
 need(not f.is_symlink(),'no symbolic links in declared artifact package '+str(rel))
 if not f.is_file():continue
 if str(rel)==current_log:continue
 st=f.stat()
 if 'obj'in parts and f.name not in ('Vchain93','Vchain97'):
  excluded.append({'path':rel.as_posix(),'bytes':st.st_size,'reason':'regenerable build intermediate; executed binary retained with SHA'});continue
 inode=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
 h=inodes.get(inode)
 if h is None:h=sha(f);inodes[inode]=h
 need((st.st_size,st.st_mtime_ns)==(f.stat().st_size,f.stat().st_mtime_ns),'immutable source while hashing '+str(rel));included.append({'path':rel.as_posix(),'bytes':st.st_size,'sha256':h,'mtime_ns':st.st_mtime_ns})
index={'schema':'physical98-whole-task-artifact-index-v1','status':'EXACT_BYTES_ARCHIVED_NOT_EXPERIMENT_ACCEPTANCE','source':src,'resources':resources,'source_root':str(root),'included':included,'excluded_build_intermediates':excluded,'excluded_scope':['own tmp/cache, archive directory and current packaging log','No source/result/output/log exclusions beyond regenerable build intermediates and temporary cache; original failures retained.'],'total_file_bytes':sum(x['bytes']for x in included)};put(a.out/'index.json',index)
with tarfile.open(a.out/'artifacts.tar.gz','w:gz',compresslevel=3)as t:
 for q in included:
  f=root/q['path'];need(f.stat().st_size==q['bytes'] and f.stat().st_mtime_ns==q['mtime_ns'],'still immutable before archive '+q['path']);t.add(f,arcname=q['path'],recursive=False)
put(a.out/'archive.json',{'status':'ARCHIVE_CREATED_RECEPTION_PENDING','index_sha256':sha(a.out/'index.json'),'archive_sha256':sha(a.out/'artifacts.tar.gz'),'archive_bytes':(a.out/'artifacts.tar.gz').stat().st_size,'files':len(included),'total_file_bytes':index['total_file_bytes'],'source':src});print('ARCHIVE_CREATED_RECEPTION_PENDING')
