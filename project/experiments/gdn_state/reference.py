"""Independent exact Python integers; no producer/RTL import, clipping, partial RNE."""
import numpy as np
MAX=(1<<63)-1;LO=-(1<<31);HI=32767<<16

def absolute(a):return max((abs(int(x))for x in np.asarray(a,dtype=object).flat),default=0)
def require(c,s):
 if not c:raise ValueError(s)
def rne_scalar(v,shift):
 v=int(v);shift=int(shift)
 if not -62<=shift<=62:raise ValueError('E_FORMAT shift')
 if abs(v)>MAX:raise OverflowError('RNE magnitude')
 if shift<=0:
  v=v<<-shift
  if abs(v)>MAX:raise OverflowError('RNE left')
  return v
 q,r=divmod(abs(v),1<<shift);q+=r>(1<<(shift-1))or(r==(1<<(shift-1))and q%2==1)
 return -q if v<0 else q

def rne(a,shift):return np.frompyfunc(lambda v:rne_scalar(v,shift),1,1)(np.asarray(a,dtype=object))
def multiply(a,b):
 if absolute(a)*absolute(b)>MAX:raise OverflowError('conservative product')
 return np.asarray(a,dtype=object)*np.asarray(b,dtype=object)
def add(a,b):
 if absolute(a)+absolute(b)>MAX:raise OverflowError('conservative add')
 return np.asarray(a,dtype=object)+np.asarray(b,dtype=object)
def fmt(su,vu):
 # Literal original bounds, independent of RTL's algebraically equivalent threshold.
 sh=int(vu)-int(su);vb=32767<<sh if sh>=0 else (32767+(1<<-sh)-1)//(1<<-sh)
 pp=128*(1<<31)*32767;pred=(pp+32767)//32768;r=vb+pred
 bounds=[(1<<31)*(1<<31),pp,pred,vb,r,r*32768,r*32767,(1<<31)+(r*32767+32767)//32768,pp]
 if max(bounds)>MAX:raise OverflowError('conservative format')

def step(state,q,k,v,d,b,units,value_units,epoch):
 s=np.asarray(state,dtype=object).copy();q,k,v=[np.asarray(x,dtype=object)for x in(q,k,v)];d,b=[np.asarray(x,dtype=object)for x in(d,b)]
 require(s.shape==(2,128,128)and q.shape==k.shape==v.shape==(2,128),'shape')
 require(all(LO<=int(x)<=HI for x in s.flat),'E_STATE')
 require(all(absolute(x)<=32767 for x in(q,k,v)),'QKV symmetric S16')
 require(all(0<=int(x)<=1<<31 for x in d)and all(0<=int(x)<=32768 for x in b),'gates')
 require(all(-128<=int(x)<=127 for x in(*units,*value_units)),'I8')
 units=list(map(int,units));attempts=[]
 for attempt in range(9):
  stages={};bad=[True,True]
  try:
   for h in range(2):fmt(units[h],value_units[h])
   dec=rne(multiply(s,d[:,None,None]),31)
   pp=multiply(dec,k[:,:,None])
   if 128*absolute(pp)>MAX:raise OverflowError('prediction dot')
   pred=rne(pp.sum(axis=1),15)
   aligned=np.stack([rne(v[h],units[h]-int(value_units[h]))for h in range(2)])
   residual=add(aligned,-pred);correction=rne(multiply(residual,b[:,None]),15)
   proposed=add(dec,rne(multiply(k[:,:,None],correction[:,None,:]),15))
   stages={'prediction':pred,'residual':residual,'correction':correction,'proposal':proposed,'aligned':aligned}
   bad=[any(int(x)<LO or int(x)>HI for x in proposed[h].flat)for h in range(2)]
   if not any(bad):
    op=multiply(proposed,q[:,:,None])
    if 128*absolute(op)>MAX:raise OverflowError('output dot')
    y=rne(op.sum(axis=1),15);stages['output']=y;attempts.append({'attempt':attempt,'bad':bad,'stages':stages,'width':False})
    return np.asarray(proposed,dtype=np.int32),np.asarray(y,dtype=np.int64),units,epoch,attempts
   attempts.append({'attempt':attempt,'bad':bad,'stages':stages,'width':False})
  except OverflowError as e:attempts.append({'attempt':attempt,'bad':[True,True],'stages':stages,'width':True,'reason':str(e)});bad=[True,True]
  if attempt==8:raise ValueError('E_RETRIES')
  if any(bad[h]and units[h]==127 for h in range(2)):raise ValueError('E_UNIT')
  if epoch==(1<<32)-1:raise ValueError('E_EPOCH')
  for h in range(2):
   if bad[h]:s[h]=rne(s[h],1);units[h]+=1
  epoch+=1
 raise AssertionError('unreachable')

def observations(attempts):
 for row in attempts:
  a=row['attempt'];s=row['stages']
  if not s:continue
  for h in range(2):
   for p in range(64):
    j=2*p
    for kind,key in enumerate(('prediction','residual','correction')):yield(a,kind,h,p,127 if kind<2 else 0,int(s[key][h,j]),int(s[key][h,j+1]))
    for i in range(128):yield(a,3,h,p,i,int(s['proposal'][h,i,j]),int(s['proposal'][h,i,j+1]))
  if 'output'in s:
   for h in range(2):
    for p in range(64):yield(a,4,h,p,127,int(s['output'][h,2*p]),int(s['output'][h,2*p+1]))
