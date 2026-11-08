"""Independent native S ownership/data facts cross-checked with LC facts."""
import copy
def native(log):
 from run import check_cycles
 need=check_cycles.need; pending={};memory={};held={}; facts=[];edges=0
 for line in log.splitlines():
  if not line.startswith('S '):continue
  a=line.split();b=int(a[1]);t=int(a[2]);kind=a[3]
  if kind=='REQ':
   need(b not in pending,'native S duplicate ownership');pending[b]=(int(a[4]),int(a[5]),int(a[6],16),t)
  elif kind=='HOLD':
   need(b in pending,'S response without request');data=int(a[5],16)
   if b in held:need(data==held[b],'S held result changed')
   held[b]=data;edges+=int(not int(a[4]))
  elif kind=='RSP':
   need(b in pending,'S response without accepted native request');wr,addr,data,begin=pending.pop(b)
   need((int(a[4]),int(a[5]))==(wr,addr) and begin<t,'S ownership/address/latency')
   got=int(a[6],16)
   if wr:need(got==data,'write ACK differs from stored payload');memory[b,addr]=data
   else:need((b,addr) in memory and got==memory[b,addr],'TX did not read actual prior S write')
   facts.append((b,t,1 if wr else 2,got));held.pop(b,None)
  else:raise ValueError('unknown native S event')
 # The intentionally poisoned missing-ACK case has no native S obligations;
 # only a transport ACK remains. Unclosed RX has never issued a storage write.
 need(not pending and not held,'native S unresolved obligation')
 d=[]
 for line in log.splitlines():
  if not line.startswith('D '):continue
  a=line.split()
  if int(a[3]) in (1,2):d.append((int(a[1]),int(a[2]),int(a[3]),int(a[5],16)))
 need(d==facts,'LC data facts are not exactly native S response handshakes')
 return dict(native_requests=len(facts),native_write_ACKs=sum(f[2]==1 for f in facts),native_reads=sum(f[2]==2 for f in facts),held_response_edges=edges)
def mutations(log):
 result=[]
 for mode in ['erase_native_ACK','bad_write_ACK','changed_held_response','early_store_fact']:
  rows=log.splitlines(); changed=False
  for i,line in enumerate(rows):
   a=line.split()
   if mode=='erase_native_ACK' and line.startswith('S ') and a[3]=='RSP':rows[i]='';changed=True;break
   if mode=='bad_write_ACK' and line.startswith('S ') and a[3]=='RSP' and a[4]=='1':a[6]='0';rows[i]=' '.join(a);changed=True;break
   if mode=='changed_held_response' and line.startswith('S ') and a[3]=='HOLD' and a[4]=='0':a[5]='0';rows[i]=' '.join(a);changed=True;break
   if mode=='early_store_fact' and line.startswith('D ') and a[3]=='1':a[2]=str(int(a[2])-1);rows[i]=' '.join(a);changed=True;break
  if not changed:raise ValueError('mutation not exercised '+mode)
  try:native('\n'.join(rows))
  except ValueError:result.append(dict(name=mode,rejected=True));continue
  raise ValueError('accepted native S mutant '+mode)
 return result
