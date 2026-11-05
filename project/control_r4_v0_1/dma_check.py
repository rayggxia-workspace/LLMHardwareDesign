"""Cross actual DMA descriptors, native S, both CDC boundaries and completions."""
import copy
def check(log):
 from run import check_cycles
 need=check_cycles.need
 desc={}; tags={0:set(),1:set()};native={};ram={};physical={};completed={};facts=[]
 qreq=[];qrsp=[];ereq=[];ersp=[];ext={i:int.from_bytes(bytes(range(16)),'little')^int.from_bytes(((i//4-6)&0xffffffff).to_bytes(4,'little')*4,'little') for i in range(64)}
 services=0;writes=0;reads=0
 for line in log.splitlines():
  a=line.split()
  if line.startswith('B '):
   b,t=int(a[1]),int(a[2]);k=a[3];tag=int(a[4]);ctx=int(a[7],16)
   if k=='DESC':
    need(b not in desc and tag not in tags[b] and tag>0,'DMA descriptor owner/tag reuse')
    tags[b].add(tag);desc[b]=dict(tag=tag,write=int(a[5]),address=int(a[6]),ctx=ctx,begin=t,native=None,external=None)
    need(ctx>>(133)==b,'DMA full identity block')
   else:
    need(b in desc,'completion without mapped identity');d=desc[b]
    need(tag==d['tag'] and ctx==d['ctx'] and int(a[5])==0 and int(a[6])==1,'DMA completion tag/context/status/words')
    need(d['native'] is not None and d['external'] is not None and max(d['native'],d['external'])<t,'DMA completion before real S/external ACK')
    completed[b]=dict(d,done=t);desc.pop(b);services+=1
  elif line.startswith('S '):
   b,t,k=int(a[1]),int(a[2]),a[3]
   if k=='REQ':
    need(b in desc and b not in native,'native S without DMA descriptor/duplicate')
    wr,addr,data=int(a[4]),int(a[5]),int(a[6],16);need(wr==1-desc[b]['write'],'DMA/S direction mismatch');native[b]=(wr,addr,data,t)
   elif k=='RSP':
    need(b in native,'native response before accept');wr,addr,data,begin=native.pop(b);got=int(a[6],16)
    need((int(a[4]),int(a[5]))==(wr,addr) and begin<t,'native S response owner/address')
    if wr:need(got==data,'native S write ACK');ram[b,addr]=got;writes+=1
    else:need((b,addr) in ram and got==ram[b,addr],'DMA STORE did not read actual S');reads+=1
    desc[b]['native']=t;desc[b]['payload']=got
   elif k!='HOLD':raise ValueError('unknown S observation')
  elif line.startswith('Q '):
   t,k,p=int(a[1]),a[2],int(a[3],16)
   if k=='REQ':
    wr=(p>>184)&1;rid=(p>>168)&65535;address=(p>>128)&((1<<40)-1);data=p&((1<<128)-1);b=(rid>>3)&15
    need(b in desc and rid not in physical,'DMA physical identity collision');d=desc[b]
    need(wr==d['write'] and address==d['address'],'DMA descriptor/native external address mismatch')
    if wr:need(d.get('payload')==data and d['native']<t,'DMA external STORE before S read/changed payload')
    physical[rid]=(b,t);qreq.append(p)
   else:
    rid=(p>>128)&65535;need(rid in physical and p>>144==0,'unexpected/status external response');b,begin=physical.pop(rid)
    need(b in desc and begin<t,'external response identity');desc[b]['external']=t;qrsp.append(p)
  elif line.startswith('E '):
   k,p=a[2],int(a[3],16)
   if k=='REQ':
    wr=p>>184;rid=(p>>168)&65535;addr=(p>>128)&((1<<40)-1);data=p&((1<<128)-1);need(addr%16==0 and addr//16 in ext,'finite external address')
    if wr:ext[addr//16]=data
    expected=(rid<<128)|ext[addr//16];ereq.append(p);ersp.append(expected)
   else:need(p==ersp[len([x for x in facts if x=='E'])],'external memory data/ACK differs');facts.append('E')
  elif line.startswith('D '):
   b,t,k=int(a[1]),int(a[2]),int(a[3])
   if k in (1,2):
    need(b in completed,'service data fact before real DMA completion');d=completed.pop(b)
    need(d['done']<t and int(a[5],16)==d['payload'] and k==(2 if d['write'] else 1),'service data differs from real DMA native result')
    job,epoch,task,seq=int(a[6]),int(a[7]),int(a[8]),int(a[9]);ctx=d['ctx']
    need((ctx&0xffffffff,(ctx>>32)&0xffffffff,(ctx>>64)&0xffffffff,(ctx>>96)&0xffffffff)==(task,epoch,job,seq),'full 32bit service identity truncated')
 need(not desc and not native and not physical and not completed,'DMA outstanding ownership left')
 need(qreq==ereq and qrsp==ersp and len(facts)==len(qrsp),'CDC packet lost/duplicated/changed')
 return dict(descriptors=services,physical_requests=len(qreq),native_write_ACKs=writes,native_reads=reads,request_response_CDC_checked=True)
def mutations(log):
 names=['bad_DMA_tag','lost_external_ACK','truncated_context','early_service_fact'];out=[]
 for name in names:
  rows=log.splitlines()
  for i,line in enumerate(rows):
   a=line.split()
   if name=='bad_DMA_tag' and line.startswith('B ') and a[3]=='DONE':a[4]=str(int(a[4])+1)
   elif name=='lost_external_ACK' and line.startswith('Q ') and a[2]=='RSP':rows[i]='';break
   elif name=='truncated_context' and line.startswith('B ') and a[3]=='DONE':a[7]=hex(int(a[7],16)&65535)[2:]
   elif name=='early_service_fact' and line.startswith('D ') and a[3]=='1':a[2]='0'
   else:continue
   rows[i]=' '.join(a);break
  try:check('\n'.join(rows))
  except (ValueError,KeyError,IndexError):out.append(dict(name=name,rejected=True));continue
  raise ValueError('accepted DMA mutant '+name)
 return out
def fault(log,mode):
 from run import check_cycles
 need=check_cycles.need
 ds=[x.split() for x in log.splitlines() if x.startswith('B ') and x.split()[3]=='DESC']
 done=[x.split() for x in log.splitlines() if x.startswith('B ') and x.split()[3]=='DONE']
 responses=[int(x.split()[3],16) for x in log.splitlines() if x.startswith('Q ') and x.split()[2]=='RSP']
 need(len(ds)==1 and len(responses)==1,'DMA fault was not actually exercised')
 need(not any(x.startswith('D ') and x.split()[3] in ('1','2','3') for x in log.splitlines()),'DMA fault fabricated service/data/ACK')
 need(not any(x.startswith('S ') for x in log.splitlines()),'failed LOAD touched native S')
 if mode==5:
  need(responses[0]>>144!=0 and len(done)==1 and done[0][5]=='3' and done[0][6]=='0','external error did not become DMA error3/zero confirmed words')
  need(ds[0][4]==done[0][4] and ds[0][7]==done[0][7],'error completion lost full mapped identity')
 else:need(not done and responses[0]>>144==0,'bad physical ID fabricated completion')
 return dict(injected_external_error=mode,service_completion_fabricated=False,requires_cohort_reset=True)
