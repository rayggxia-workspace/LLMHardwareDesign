from pathlib import Path
import json,hashlib,subprocess,shlex,collections,time
h=Path(__file__).parent;out=h/'control162-order-window687';assert out.is_dir()and not(out/'source-digest-correction-688.json').exists()
q=r'''from pathlib import Path
import hashlib,json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');blocks=[];sources=[]
for n in [537,633]:
 p=b/('source-'+str(n)+'/project/experiments/control_v1/tree_router.cpp');raw=p.read_bytes();text=raw.decode();block=text.split(' vector<vector<int>>trees(count)',1)[1].split(' bool complete=false',1)[0];blocks.append(block);sources.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()))
assert blocks[0]==blocks[1];print(json.dumps(dict(passed=True,source_initial_order_bytes_exact=True,source_initial_order_block_sha256=hashlib.sha256(blocks[0].encode()).hexdigest(),source_initial_order_block_bytes=len(blocks[0].encode()),sources=sources)))
'''
r=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=20));r['time']=time.time();r['correction']='687 remote comparison assertion was correct, but its initial_order_source_sha256 field hashed the last candidate header after variable reuse. Preserve original687 bytes; this new688 receipt provides exact source-block digest. All input/order-window comparisons and nonqualification scope unchanged.';(out/'source-digest-correction-688.json').write_bytes((json.dumps(r,indent=2)+'\n').encode())
d=json.loads((out/'receipt.json').read_text());extra=[]
for window in d['windows']:
 seed=window['seed'];rows={}
 for line in(out/(str(seed)+'-input.txt')).read_text().splitlines()[1:]:
  fields=line.split();n=int(fields[1]);xy=[tuple(map(int,fields[2+2*i:4+2*i]))for i in range(n)];rows[fields[0]]=xy
 lengths=[]
 for name in window['next_at_most100_names']:
  xy=rows[name];lengths.append(4*(max(x for x,y in xy)-min(x for x,y in xy)+max(y for x,y in xy)-min(y for x,y in xy)))
 extra.append(dict(seed=seed,count=len(lengths),sum_hpwl_um=sum(lengths),max_hpwl_um=max(lengths),mean_hpwl_um=sum(lengths)/len(lengths),scope='Endpoint XY bounding-box distances, not actual routed length or per-net time.'))
(out/'window-distance-688.json').write_bytes((json.dumps(dict(passed=True,whole_system_qualified=False,windows=extra),indent=2)+'\n').encode());print(json.dumps(dict(corrected_source_digest=True,windows=extra)))
