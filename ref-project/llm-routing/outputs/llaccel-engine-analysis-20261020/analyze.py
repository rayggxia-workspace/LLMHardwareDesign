"""Exclusive cell labels and whole-net layer accounting from final physical endpoints.

No geometry-based ownership; never propagate through a source anchor or a flop.
The anonymous cone label denotes downstream service, not recovered RTL ownership.
"""
from pathlib import Path
from collections import Counter, defaultdict, deque
from array import array
import csv, gzip, hashlib, json, re, time
import numpy as np

P=Path(__file__).resolve().parent
DATA=P/'compact_physical_evidence.jsonl.gz'
GROUPS={
 'GEMM.WEIGHT':('权重双缓冲与装载','#247a85'),
 'GEMM.MULTIPLY':('乘法级及输入选择','#2357a0'),
 'GEMM.REDUCE':('求和归约级','#6a5bac'),
 'GEMM.ACC':('累加状态、选择与反馈','#a44c88'),
 'GEMM.EPILOGUE':('偏置与再量化流水','#c67522'),
 'GEMM.OUTPUT':('输出 FIFO 与写回','#56823b'),
 'GEMM.CONTROL':('指令、地址与调度','#8b6c4a'),
 'ATTENTION.Q':('Q 输入与保持','#247a85'),
 'ATTENTION.KV':('K/V 请求、拼接与保持','#2357a0'),
 'ATTENTION.DOT':('Q·K 点积及分组求和','#6a5bac'),
 'ATTENTION.SCORE':('分数／概率缓冲及读写选择','#a44c88'),
 'ATTENTION.SOFTMAX':('最大值、指数近似与归一化','#c67522'),
 'ATTENTION.VALUE':('V 加权与累加状态','#b3414b'),
 'ATTENTION.OUTPUT':('输出再量化、队列与写回','#56823b'),
 'ATTENTION.CONTROL':('指令、循环与地址控制','#8b6c4a'),
 'VECTOR.READ':('读响应缓冲与拆分','#247a85'),
 'VECTOR.NORM':('共享归约、开方与除法','#6a5bac'),
 'VECTOR.LANES':('共享通道计算与结果保持','#b3414b'),
 'VECTOR.ADDRESS':('读写遍历与地址控制','#56823b'),
 'VECTOR.CONTROL':('指令与流水控制','#8b6c4a'),
 'COMMAND_PROCESSOR':('命令处理','#777777'),
 'DMA':('DMA','#777777'),
 'DRAM_ARBITER':('DRAM 仲裁','#777777'),
 'SRAM_CROSSBAR':('SRAM 互连','#777777'),
 'PERFORMANCE_COUNTERS':('性能计数','#777777'),
 'OTHER_SOURCE':('其他保留来源','#999999'),
 'EXTERNAL':('顶层端口','#999999'),
 'UNRESOLVED':('未解析终点','#999999'),
}
KEYS=list(GROUPS); BIT={k:1<<i for i,k in enumerate(KEYS)}
BAD=BIT['UNRESOLVED']; EXTERNAL=BIT['EXTERNAL']
ENGINES=['GEMM','ATTENTION','VECTOR']
EMASK={e:sum(BIT[k] for k in KEYS if k.startswith(e+'.')) for e in ENGINES}

def norm(s):return s.replace('\\','')
def classify(name):
 s=norm(name)
 if s.startswith('u_gemm.'):
  t=re.split(r'\[|\$',s[7:])[0]
  if t.startswith('u_out.') or t in 'wr_ph out_count out_out out_ptr out_nt_base'.split():g='OUTPUT'
  elif t in 'wbuf wbuf_valid w_ptr ld_active ld_inflight ld_par ld_nt ld_kt'.split():g='WEIGHT'
  elif t in 'prod p_valid p_m'.split():g='MULTIPLY'
  elif t in 'psum s_valid s_m'.split():g='REDUCE'
  elif t=='acc':g='ACC'
  elif re.match(r'd[1-4]_',t) or t in 'bias_v rq_m rq_s dr_m dr_idx'.split():g='EPILOGUE'
  else:g='CONTROL'
  return 'GEMM.'+g
 if s.startswith('u_attn.'):
  t=re.split(r'\[|\$',s[7:])[0]
  if t.startswith('u_dram_tags.') or t.startswith('dram_') or t in 'key_row row_asm rd_ph rsp_cross rsp_last rsp_ph row_addr wide_pending'.split():g='KV'
  elif t in 'qv qrow q_issued'.split():g='Q'
  elif t in 'dot dot_partial s_reg s_valid s_t k_group k_active'.split():g='DOT'
  elif t in 'sbuf s_rd sbuf_raddr'.split():g='SCORE'
  elif t.startswith('u_udiv.') or t in 'mx z_big z_lo sum inv_r va vz ta_q tz_q Ms_r Ss_r p_val p_prod'.split():g='SOFTMAX'
  elif t in 'o pn_q v_q vv v_group pn_prod'.split():g='VALUE'
  elif t.startswith('u_wq.') or t in 'wdata_acc og Mo_r So_r wr_ph dst_cur dst_m dst_pending write_piece'.split():g='OUTPUT'
  else:g='CONTROL'
  return 'ATTENTION.'+g
 if s.startswith('u_vec.'):
  t=re.split(r'\[|\$',s[6:])[0]
  if t.startswith(('u_f0.','u_f1.','u_s0.','u_s1.')):g='READ'
  elif t.startswith(('u_isqrt.','u_udiv.')) or t in 'ss r_r inv_r norm_state isqrt_a'.split():g='NORM'
  elif t in 'x1_r c_r y2_r wr_data_r'.split():g='LANES'
  elif t.startswith(('u_w0.','u_w1.','u_wc.')) or t.startswith(('wr_addr','wr_size')) or t=='wr_ph':g='ADDRESS'
  else:g='CONTROL'
  return 'VECTOR.'+g
 for prefix,g in [('u_cp.','COMMAND_PROCESSOR'),('u_dma.','DMA'),('u_arb.','DRAM_ARBITER'),('u_xbar.','SRAM_CROSSBAR'),('u_perf.','PERFORMANCE_COUNTERS')]:
  if s.startswith(prefix):return g
 return None

# Only internal arithmetic signals, not module input aliases or interface handshakes.
NET_ANCHORS={
 'u_attn.dot':'ATTENTION.DOT',
 'u_attn.p_prod':'ATTENTION.SOFTMAX',
 'u_attn.p_val':'ATTENTION.SOFTMAX',
 'u_attn.pn_prod':'ATTENTION.VALUE',
 'u_vec.isqrt_a':'VECTOR.NORM',
}
def rows():
 with gzip.open(DATA,'rt',encoding='utf8') as f:
  for line in f:yield json.loads(line)
def isseq(master):return bool(re.match(r'(?:SDFF|DFF|DLH|DLL|LATCH)',master))
def serial(d):return json.dumps(d,ensure_ascii=False,indent=2)
def write_csv(path,rows):
 rows=list(rows)
 if not rows:return
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 t0=time.time();cells=[];idx={};header=None
 for a in rows():
  if isinstance(a,dict):header=a;continue
  if a[0]!='c':break
  # Name, master, footprint; no filler/tap/antenna cells.
  idx[a[2]]=len(cells);cells.append(a[2:])
 n=len(cells);print('cells',n,flush=True)
 masks=[0]*n;fixed=bytearray(n);origin=bytearray(n)
 predecessors=[None]*n;has_out=bytearray(n)
 named_counts=Counter();netanchor_audit=[];external_drivers=set();clock_cells=set()
 for i,(name,master,box) in enumerate(cells):
  g=classify(name)
  if g:masks[i]=BIT[g];fixed[i]=1;origin[i]=1;named_counts[g]+=1
  elif isseq(master):masks[i]=BAD;fixed[i]=1;origin[i]=4
 net_total=0;dedicated=Counter();missing_endpoints=Counter()
 for a in rows():
  if not isinstance(a,list) or a[0]!='n':continue
  _,nid,name,cat,ds,ls,bs,layers,attrs=a;net_total+=1
  if cat in ('CLOCK','RESET') or any(x in ('clock','reset') for x in attrs):
   dedicated[cat]+=sum(layers.values())
   for cn,pin in ds:
    if cn in idx and not fixed[idx[cn]]:clock_cells.add(idx[cn])
   continue
  # A multi-output primitive may be constrained by several anchors: preserve conflicts.
  key=re.split(r'\[',norm(name))[0];g=NET_ANCHORS.get(key)
  if g:
   assert re.search(r'\b'+re.escape(key.split('.')[-1])+r'\b',(P/'sources'/('vec_engine.sv' if key.startswith('u_vec.') else 'attn_engine.sv')).read_text()),key
   for cn,pin in ds:
    if cn not in idx:continue
    j=idx[cn]
    if origin[j]==1:
     assert masks[j]==BIT[g],(cn,g)
    elif origin[j]!=4:
     masks[j]|=BIT[g];fixed[j]=1;origin[j]=2
     netanchor_audit.append([nid,name,cn,pin,g])
  drivers=[idx[cn] for cn,pin in ds if cn in idx]
  loads=[idx[cn] for cn,pin in ls if cn in idx and pin not in ('CK','CLK','RN','SN','RESET_B')]
  for j in drivers:has_out[j]=1
  if bs:
   for j in drivers:external_drivers.add(j)
  for cn,pin in ds+ls:
   if cn not in idx:missing_endpoints[cn]+=1
  for v in loads:
   arr=predecessors[v]
   if arr is None:arr=array('I');predecessors[v]=arr
   arr.extend(drivers)
 print('graph built',net_total,'nets',round(time.time()-t0,1),'s',flush=True)
 # Anonymous leaf, output and clock cells are explicit barriers.
 for j in clock_cells:
  if not fixed[j]:masks[j]=BAD;fixed[j]=1;origin[j]=5
 for j in external_drivers:
  if not fixed[j]:masks[j]|=EXTERNAL
 # Zero-outdegree combinational nodes do not silently disappear from a fanout cone.
 successors_count=array('I',[0])*n
 for a in predecessors:
  if a:
   for j in a:successors_count[j]+=1
 for j in range(n):
  if not masks[j] and (successors_count[j]==0 or not has_out[j]):masks[j]=BAD
 q=deque(j for j,m in enumerate(masks) if m);inqueue=bytearray(1 if m else 0 for m in masks);updates=0
 while q:
  v=q.popleft();inqueue[v]=0
  for u in predecessors[v] or ():
   if fixed[u]:continue
   new=masks[u]|masks[v]
   if new!=masks[u]:
    masks[u]=new;updates+=1
    if not inqueue[u]:q.append(u);inqueue[u]=1
 labels=[];tiers=[];cellcounts=Counter();seedcounts=Counter();unknown_types=Counter();mask_counts=Counter()
 for i,m in enumerate(masks):
  if origin[i]==5:
   g='DEDICATED_CLOCK_RESET';tier='DEDICATED'
  elif m and m&(m-1)==0 and m not in (BAD,EXTERNAL):
   g=KEYS[m.bit_length()-1];tier='SOURCE' if origin[i]==1 else ('NAMED_NET' if origin[i]==2 else 'RECEIVER')
  else:
   e=next((e for e in ENGINES if m and m&EMASK[e] and not m&~EMASK[e]),None)
   g=(e+'.SHARED') if e else ('UNRESOLVED' if not m or m&BAD else 'CROSS_ENGINE_OR_EXTERNAL')
   tier='SHARED' if e else 'UNRESOLVED'
  labels.append(g);tiers.append(tier);cellcounts[g]+=1;seedcounts[(g,tier)]+=1;mask_counts[m]+=1
  if g in ('UNRESOLVED','CROSS_ENGINE_OR_EXTERNAL'):unknown_types[cells[i][1]]+=1
 print('propagated',updates,'updates',round(time.time()-t0,1),'s',flush=True)
 # Compressed, auditable cell assignment; masks retain evidence of shared destinations.
 with gzip.open(P/'cell_assignments.jsonl.gz','wt',encoding='utf8') as f:
  for i,(name,master,box) in enumerate(cells):
   f.write(json.dumps([name,master,box,labels[i],tiers[i],masks[i]],separators=(',',':'))+'\n')
 # Integer DBU statistics; each whole net is counted once in the global partition.
 totals=Counter();stats={};pairs=defaultdict(Counter);relations=Counter();partial=Counter();audit=[]
 signal_internal=Counter();engine_touched=Counter();top_nets=[]
 def accumulate(scope,g,nid,lengths):
  for layer,length in lengths.items():
   key=(scope,g,layer);s=stats.setdefault(key,[0,0,0,None,0])
   s[0]+=length;s[1]+=1;s[2]+=length*length;s[3]=length if s[3] is None else min(s[3],length);s[4]=max(s[4],length)
 for a in rows():
  if not isinstance(a,list) or a[0]!='n':continue
  _,nid,name,cat,ds,ls,bs,layers,attrs=a;length=sum(layers.values());ends=ds+ls
  groups={labels[idx[cn]] for cn,pin in ends if cn in idx};hasmissing=any(cn not in idx for cn,pin in ends)
  touched={g.split('.')[0] for g in groups if g.split('.')[0] in ENGINES}
  for e in touched:engine_touched[e]+=length
  isded=cat in ('CLOCK','RESET') or any(x in ('clock','reset') for x in attrs)
  if isded:bucket='DEDICATED';group=cat
  elif not ends or hasmissing or any(g in ('UNRESOLVED','CROSS_ENGINE_OR_EXTERNAL','DEDICATED_CLOCK_RESET') for g in groups):bucket='PARTIAL';group='unresolved_endpoint'
  elif bs:bucket='EXTERNAL';group='top_port'
  elif len(groups)==1:
   group=next(iter(groups));e=group.split('.')[0]
   bucket='INTERNAL' if e in ENGINES and not group.endswith('.SHARED') else ('SHARED' if e in ENGINES else 'OTHER')
  else:
   es={g.split('.')[0] for g in groups}
   if len(es)==1 and next(iter(es)) in ENGINES:bucket='BETWEEN_GROUPS';group=next(iter(es))
   else:bucket='CROSS_ENGINE';group='cross_engine'
  totals[bucket]+=length
  accumulate('GLOBAL',bucket,nid,layers)
  if bucket=='INTERNAL':
   accumulate('INTERNAL',group,nid,layers);signal_internal[group]+=length
  if bucket in ('INTERNAL','SHARED','BETWEEN_GROUPS'):
   e=group.split('.')[0];accumulate('ENGINE',e,nid,layers)
   relation='within_group' if bucket=='INTERNAL' else ('contains_shared' if any(g.endswith('.SHARED') for g in groups) else 'between_groups')
   accumulate(e,relation,nid,layers)
   if len(groups)==2 and not any(g.endswith('.SHARED') for g in groups):
    pair=' ↔ '.join(sorted(groups));relations[(e,pair)]+=length
    for layer,ln in layers.items():pairs[(e,pair)][layer]+=ln
  elif not isded:
   for e in touched:partial[(e,bucket)]+=length
  if touched and len(top_nets)<300 and length>400000:audit.append([nid,name,bucket,sorted(groups),length/2000])
  if bucket=='INTERNAL' and len(top_nets)<300:top_nets.append([nid,name,group,length/2000])
 # Exact physical length conservation, including all unknown and boundary categories.
 observed=sum(totals.values());expected=header['extraction']['totals']['dbwire_centerline_length_dbu']
 assert observed==expected,(observed,expected)
 table=[]
 for (scope,group,layer),s in sorted(stats.items()):
  table.append({'scope':scope,'group':group,'layer':layer,'net_layer_entries':s[1], 'length_dbu':s[0],'length_um':s[0]/2000,'mean_net_layer_length_um':s[0]/s[1]/2000,'min_net_layer_length_um':s[3]/2000,'max_net_layer_length_um':s[4]/2000})
 write_csv(P/'layer_lengths.csv',table)
 write_csv(P/'cell_counts.csv',[{'group':g,'zh':GROUPS.get(g,('',))[0] if g in GROUPS else ('多个内部组共享' if g.endswith('.SHARED') else '未确定归属'),'tier':tier,'cells':v} for (g,tier),v in sorted(seedcounts.items())])
 write_csv(P/'group_connections.csv',[{'engine':e,'pair':pair,'layer':layer,'length_dbu':ln,'length_um':ln/2000} for (e,pair),v in sorted(pairs.items()) for layer,ln in sorted(v.items())])
 result={'schema':1,'source':header,'groups':GROUPS,'bits':BIT,'cells':n,'nets':net_total,'cell_counts':dict(cellcounts),'tier_counts':{g:dict((tier,seedcounts[(g,tier)]) for tier in ('SOURCE','NAMED_NET','RECEIVER','SHARED','UNRESOLVED','DEDICATED')) for g in cellcounts},'unknown_master_types':dict(unknown_types.most_common()),'net_anchor_count':len(netanchor_audit),'source_cell_count':sum(named_counts.values()),'missing_endpoints':dict(missing_endpoints),'global_length_dbu':dict(totals),'conservation':{'expected_dbu':expected,'observed_dbu':observed,'pass':True},'engine_internal_group_length_dbu':dict(signal_internal),'engine_touched_length_dbu':dict(engine_touched),'partial_touched_nonadditive_dbu':{e:dict((b,v) for (ee,b),v in partial.items() if ee==e) for e in ENGINES},'group_pair_totals_dbu':{e:dict((p,v) for (ee,p),v in relations.items() if ee==e) for e in ENGINES},'elapsed_seconds':time.time()-t0,'clock_reset_excluded_from_inference':True,'whole_net_no_branch_allocation':True}
 (P/'summary.json').write_text(serial(result),encoding='utf8')
 (P/'net_anchor_evidence.json').write_text(serial(netanchor_audit),encoding='utf8')
 (P/'sample_net_assignments.json').write_text(serial({'internal':top_nets,'large_touched':audit[:100]}),encoding='utf8')
 print(serial({'cell_counts':cellcounts,'global_length_dbu':totals,'conservation':result['conservation'],'elapsed':result['elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
