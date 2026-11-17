from pathlib import Path
import hashlib,json
p=Path(__file__).parent
source=p/'loader-onehot-v2.sv'
s=source.read_text()
changes=[]
def replace(old,new,count=1):
 global s
 assert s.count(old)==count,(old,s.count(old))
 s=s.replace(old,new)
 changes.append({'old':old,'new':new,'count':count})
replace(' reg [8:0] pi[0:1];',' reg [8:0] pi[0:1];\n reg [63:0] cached_addr[0:7];')
replace("lane_address[j]=addr(pi[j/4],2'(j%4));",'lane_address[j]=cached_addr[j];')
replace("addr(pi[p],2'(l))",'cached_addr[4*p+l]',2)
reset='   for(integer p=0;p<2;p=p+1)begin pi[p]<=0;pd[p]<=0;pm[p]<=0;tags[p]<=0;lines[p]<=0;caches[p]<=0;end'
replace(reset,reset+"\n   for(integer k=0;k<8;k=k+1)cached_addr[k]<=64'd0;")
alloc='    pwriting[!pv[0]?0:1]<=0;allocated_words<=allocated_words+1;'
replace(alloc,alloc+"\n    for(integer l=0;l<4;l=l+1)cached_addr[4*(!pv[0]?0:1)+l]<=addr(allocated_words,2'(l));")
out=p/'loader-cached.sv';out.write_text(s)
sha=lambda b:hashlib.sha256(b).hexdigest()
r={'source_raw_sha256':sha(source.read_bytes()),'candidate_raw_sha256':sha(out.read_bytes()),'added_address_register_bits':512,'observable_cycles_added':0,'required_invariant':'pv[p] implies cached_addr[4*p+l] == addr(pi[p],l), and pv[p] implies active','changes':changes,'qualification':'Requires independent lifecycle induction and source binding; not accepted by construction'}
(p/'loader-cached-transform.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
