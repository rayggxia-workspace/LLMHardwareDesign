"""Mapped-netlist CDC allow-list, independent of the SDC delay exceptions."""
import collections,json
def check(mapping_dir,out):
 mod=json.loads((mapping_dir/'mapped.json').read_text())['modules']['dram_m_direct']
 regs=json.loads((mapping_dir/'registers.json').read_text())
 bycell={r['cell']:r for r in regs};drivers={};memo={};visiting=set()
 ports=mod['ports'];mem_in={'mem_req_ready','mem_rsp_valid','mem_rsp_data','mem_rsp_error'}
 labels={}
 for p,v in ports.items():
  if v['direction']=='input':
   if p in ('core_clk','mem_clk','reset'):continue
   for b in v['bits']:labels[b]=frozenset({('mem'if p in mem_in else'core','input:'+p)})
 def kind(r):
  ns=r['names']
  for f in ('requests','responses'):
   for k in ('wg','rg','wg1','wg2','rg1','rg2','payload'):
    if any(n.startswith('loader.'+f+'.'+k+'[')for n in ns):return f+'.'+k
  return 'other'
 for n,c in mod['cells'].items():
  if n in bycell:
   r=bycell[n]
   for p,d in c['port_directions'].items():
    if d=='output':
     for b in c['connections'][p]:
      if isinstance(b,int):labels[b]=frozenset({(r['clock'],kind(r))})
  else:
   ins=tuple(b for p,d in c['port_directions'].items()if d=='input'for b in c['connections'][p])
   for p,d in c['port_directions'].items():
    if d=='output':
     for b in c['connections'][p]:
      if isinstance(b,int):drivers[b]=ins
 def origins(b):
  if not isinstance(b,int):return frozenset()
  if b in labels:return labels[b]
  if b in memo:return memo[b]
  assert b not in visiting,('combinational loop',b)
  visiting.add(b);v=frozenset().union(*(origins(x)for x in drivers.get(b,())))
  visiting.remove(b);memo[b]=v;return v
 crossings=[];bad=[]
 def accept(name,domain,foreign,names):
  allowed=False
  # A Gray source may reach only the corresponding first-stage synchronizer.
  for f in ('requests','responses'):
   for k in ('wg','rg'):
    if any(s.startswith('loader.'+f+'.'+k+'1[')for s in names):
     allowed=all(x[1]==f+'.'+k for x in foreign)
  if domain=='mem'and any(s.startswith('loader.return_tag[')for s in names):
   allowed=all(x[1]=='requests.payload'for x in foreign)
  if domain=='core'and any(s.startswith('loader.'+p+'[')for s in names
     for p in ('a_valid','a_data','a_bank','a_wide','a_row','a_tile','b_valid','b_data','b_bank','b_wide','b_tile','b_half','gather','fault')):
   allowed=all(x[1]=='responses.payload'for x in foreign)
  if name=='port:mem_req_address':
   allowed=all(x[1]=='requests.payload'for x in foreign)
  row={'sink':name,'domain':domain,'foreign':sorted(foreign),'aliases':names,'allowed':allowed}
  crossings.append(row)
  if not allowed:bad.append(row)
 for r in regs:
  foreign={x for x in origins(r['D'])if x[0]!=r['clock']}
  if foreign:accept(r['cell']+'/D',r['clock'],foreign,r['names'])
 mem_out={'mem_req_valid','mem_req_address','mem_rsp_ready','response_fifo_full'}
 for p,v in ports.items():
  if v['direction']=='output':
   dom='mem'if p in mem_out else'core'
   foreign=set().union(*(origins(b)for b in v['bits']))
   foreign={x for x in foreign if x[0]!=dom}
   if foreign:accept('port:'+p,dom,foreign,[p])
 result={'passed':not bad,'crossing_sinks':len(crossings),'crossings':crossings,'unexpected':bad,
 'scope':'Combinational clock-origin allow-list on mapped graph; not analog metastability proof'}
 (out/'cdc-structure.json').write_text(json.dumps(result,indent=2)+'\n')
 assert not bad,('unexpected CDC cone',bad[:5])
 return result
