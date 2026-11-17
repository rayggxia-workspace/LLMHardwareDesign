import json,re,hashlib
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
old=Path('/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=json.loads((old/'sources.json').read_text())
expected={x['path']:x['sha256'] for x in records}
for path,h in expected.items():assert sha(path)==h,(path,'baseline drift')
def files(cfg):return re.findall(r'^export VERILOG_FILES\s*=\s*(.*)$',cfg.read_text(),re.M)[-1].split()
oldfiles=files(old/'config.mk')
missing=set(oldfiles)-set(expected);extra=set(expected)-set(oldfiles)
assert len(missing)==len(extra)==1
normalized=next(iter(missing));raw=next(iter(extra))
assert Path(normalized).name==Path(raw).name=='ucf_r256_service.sv'
assert Path(normalized).read_text()==Path(raw).read_text().replace('r_stream_local #(.WORDS(256)) leaf','r_stream_local leaf')
expected[normalized]=sha(normalized)
result={'original_sources_manifest_sha':sha(old/'sources.json'),'all_original_sources_match_recorded_hashes':True,'original_files':records,'original_r_binding_normalization':{'raw':raw,'normalized':normalized,'normalized_sha':sha(normalized),'change':'remove fixed WORDS256 override for qualified hardmacro Liberty blackbox'},'runs':{}}
known={'C-v14-genericadder-distributed':'2c0c51de8d1dd776a295cd3221b38c21b66f8191a93ebcfcaed4c41cff3e35c2','C-v14-genericadder-distributed-parallel':'2aaa6e239aa20b50c7ab3703531263146527e04046f1bdf8fe439d66e6161a0e','C-v15-genericadder-onehot-v2':'020538508ff7db6461afab28f73726867e5900fde2255a4a311789b105040567'}
for name,h in known.items():
 run=base/'cu/runs'/name
 newfiles=files(run/'config.mk')
 assert len(newfiles)==len(oldfiles)
 delta=[]
 for a,b in zip(oldfiles,newfiles):
  if a==b:assert sha(b)==expected[a]
  else:
   assert Path(a).name=='e32_tiled_dot_loader.sv' and Path(b).name=='loader-candidate.sv'
   assert sha(b)==h,(b,sha(b),h)
   delta.append({'old':a,'old_sha':sha(a),'new':b,'new_sha':sha(b)})
 assert len(delta)==1
 result['runs'][name]={'only_rtl_change':delta,'config_sha':sha(run/'config.mk'),'manifest_sha':sha(run/'inputs-manifest.json')}
(base/'audit/C-rtl-input-chain.json').write_text(json.dumps(result,indent=2));print('PASS original manifest exact and all3 candidates only reviewed loader differs')
