from pathlib import Path
import hashlib,json
p=Path(__file__).parent
src=p/'loader-onehot-v2.sv';cand=p/'loader-cached-reviewed.sv'
s=src.read_text();c=cand.read_text();original=c
changes=[
(' reg [8:0] pi[0:1];',' reg [8:0] pi[0:1];\n reg [63:0] cached_addr[0:7];',1),
("lane_address[j]=addr(pi[j/4],2'(j%4));",'lane_address[j]=cached_addr[j];',1),
("addr(pi[p],2'(l))",'cached_addr[4*p+l]',2),
('   for(integer p=0;p<2;p=p+1)begin pi[p]<=0;pd[p]<=0;pm[p]<=0;tags[p]<=0;lines[p]<=0;caches[p]<=0;end','   for(integer p=0;p<2;p=p+1)begin pi[p]<=0;pd[p]<=0;pm[p]<=0;tags[p]<=0;lines[p]<=0;caches[p]<=0;end\n   for(integer k=0;k<8;k=k+1)cached_addr[k]<=64\'d0;',1),
('    pwriting[!pv[0]?0:1]<=0;allocated_words<=allocated_words+1;',"    pwriting[!pv[0]?0:1]<=0;allocated_words<=allocated_words+1;\n    for(integer l=0;l<4;l=l+1)cached_addr[4*(!pv[0]?0:1)+l]<=addr(allocated_words,2'(l));",1)]
for old,new,n in reversed(changes):assert c.count(new)==n;(None);c=c.replace(new,old)
assert c==s
assert 'if(active&&!stop&&allocated_words<total_words&&pv!=3)begin' in original
assert 'if(start&&ready)begin' in original and 'assign ready=!reset&&!active&&!report;' in original
assert "if(pv[p]&&!pwriting[p]&&!is_pad(pi[p],2'(l))&&((cached_addr[4*p+l]>>6)==(lines[response_slot]>>6)))begin" in original
assert 'lane_exam[j]=pv[j/4]&&!pwriting[j/4]&&!pm[j/4][j%4];' in original
sha=lambda a:hashlib.sha256(a.read_bytes()).hexdigest()
r={'passed':True,'source_sha256':sha(src),'candidate_sha256':sha(cand),'induction_model_sha256':sha(p/'cache-key-induction.sv'),'induction_script_sha256':sha(p/'cache-key-induction.ys'),'induction_job':119717,'induction_result':'SAT SUCCESS both bad_induction=0 and bad_reset=0','address_configuration_bits':252,'address_configuration_fields':['f:16','cols:3','aa:64','bb:64','ast:32','bst:32','cst:32','a_words:9'],'cache_bits_added':512,'binding':'Exactly five reviewed substitutions; entire inverse source equal to previously proven onehot v2. No original state update changed. Every replaced use is observed only if its slot pv is true.','scope':'Two-state, from reset (or state relation satisfying invariant); preserves all original state and outputs every cycle, adds no observable cycle. Not whole-module SAT or physical signoff.'}
(p/'C-cached-loader-proof-binding.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
