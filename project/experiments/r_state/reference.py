"""Independent scalar bigint R definition, not imported by RTL/input producer."""
I64=(1<<63)-1;LO32=-(1<<31);HI32=(1<<31)-1
class Guard(Exception):pass
def rne(v,s):
 if abs(v)>I64:raise Guard('I64 abs')
 if s<0:
  q=v<<(-s)
  if abs(q)>I64:raise Guard('I64 left')
  return q
 if s>63:return 0
 if s==0:return v
 a=abs(v);q,r=divmod(a,1<<s);h=1<<(s-1);q+=int(r>h or r==h and q&1)
 return -q if v<0 else q
def s32(v):
 if not LO32<=v<=HI32:raise Guard('I32')
 return v
def step(old,unit,epoch,x,b,c,dt,alpha,skip):
 if not 0<=alpha<=1<<31:raise Guard('alpha')
 trial=list(old);retries=0
 while True:
  try:
   dtb=[s32(rne(dt*v,12)) for v in b];dec=[rne(v*alpha,31) for v in trial]
   inj=[rne(xx*bb,32+unit) for xx in x for bb in dtb]
   if max(map(abs,dec))+max(map(abs,inj))>I64:raise Guard('I64 add')
   proposal=[a+b for a,b in zip(dec,inj)]
   if min(proposal)<LO32 or max(proposal)>HI32:raise Guard('range')
   break
  except Guard:
   if retries==8:raise Guard('retry_limit')
   if unit>=127:raise Guard('unit_limit')
   if epoch>=0xffffffff:raise Guard('epoch_limit')
   trial=[rne(v,1) for v in trial];unit+=1;epoch+=1;retries+=1
 prod=[v*c[i%256] for i,v in enumerate(proposal)]
 if max(map(abs,prod))*256>I64:raise Guard('readout_guard')
 scan=[rne(sum(prod[d*256:(d+1)*256]),-unit) for d in range(128)]
 sk=[rne(v*skip,20) for v in x]
 if max(map(abs,scan))+max(map(abs,sk))>I64:raise Guard('readout_add')
 return proposal,[s32(a+b) for a,b in zip(scan,sk)],unit,epoch,retries
