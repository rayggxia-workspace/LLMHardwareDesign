"""Exact binary identity except GDSII BGNLIB/BGNSTR timestamp payloads."""
import hashlib,json,mmap,struct
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030')
suffix='gds-flow/results/nangate45/bv1_block_v1_r/base/6_final.gds'
a=base/'outputs/138'/suffix;b=base/'outputs/142'/suffix
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
 return h.hexdigest()
old_source=base/'outputs/123/pnr/r';new_source=base/'outputs/139/pnr/r'
assert (new_source/'config.mk').read_bytes()==(old_source/'config.mk').read_bytes().replace(str(old_source).encode(),str(new_source).encode())
definition=new_source/'flow/results/nangate45/bv1_block_v1_r/base/6_final.def'
defhash=digest(definition)
assert defhash==digest(base/'outputs/129/after.def')==digest(base/'outputs/142/gds-flow/results/nangate45/bv1_block_v1_r/base/6_final.def')
stats=[p.stat() for p in (a,b)];assert stats[0].st_size==stats[1].st_size
ha=hashlib.sha256();hb=hashlib.sha256();hc=hashlib.sha256();timestamps=[];records=0
with a.open('rb') as fa,b.open('rb') as fb:
 with mmap.mmap(fa.fileno(),0,access=mmap.ACCESS_READ) as ma,mmap.mmap(fb.fileno(),0,access=mmap.ACCESS_READ) as mb:
  n=len(ma);pos=0;start=0
  def equal_segment(lo,hi):
   for k in range(lo,hi,8*1024**2):
    x=ma[k:min(k+8*1024**2,hi)];y=mb[k:min(k+8*1024**2,hi)]
    assert x==y,('Non-timestamp GDS bytes differ',k)
    ha.update(x);hb.update(y);hc.update(x)
  while pos<n:
   assert n-pos>=4
   length,record_type,data_type=struct.unpack_from('>HBB',ma,pos)
   assert length>=4 and length%2==0 and pos+length<=n,(pos,length)
   records+=1
   if record_type in (1,5):
    assert length==28 and data_type==2,('Not a GDS timestamp record',pos)
    equal_segment(start,pos+4)
    x=ma[pos+4:pos+28];y=mb[pos+4:pos+28]
    ha.update(x);hb.update(y);hc.update(bytes(24))
    timestamps.append(dict(offset=pos,record_type=record_type,changed=x!=y,before=list(struct.unpack('>12h',x)),after=list(struct.unpack('>12h',y))))
    start=pos+28
   pos+=length
  equal_segment(start,n)
assert ha.hexdigest()==digest(a) and hb.hexdigest()==digest(b)
assert [(v.st_size,v.st_mtime_ns) for v in stats]==[(p.stat().st_size,p.stat().st_mtime_ns) for p in (a,b)]
result=dict(passed=True,qualified=False,native_leaf_accepted=False,only_gds_timestamp_payloads_differ=True,
 source_gds=dict(path=str(a),sha256=ha.hexdigest()),final_generated_gds=dict(path=str(b),sha256=hb.hexdigest()),
 canonical_all_non_timestamp_bytes_sha256=hc.hexdigest(),bytes=stats[0].st_size,records=records,
 timestamp_records=len(timestamps),changed_timestamps=sum(v['changed'] for v in timestamps),timestamps=timestamps,
 actual_final_def_sha256=defhash,old_candidate_and_actual_final_def_bytes_identical=True,
 config_only_output_directory_prefix_differs=True,source_config_sha256=digest(old_source/'config.mk'),final_config_sha256=digest(new_source/'config.mk'),
 scope='Binary comparison ignores only 24-byte BGNLIB/BGNSTR timestamps; every other GDS byte, header, structure and geometry is identical. This is input identity, not a DRC pass or native producer acceptance.')
(base/'r-gds-identity-138-142.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('passed','bytes','records','timestamp_records','changed_timestamps','canonical_all_non_timestamp_bytes_sha256','actual_final_def_sha256')}))
