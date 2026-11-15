"""Integer contracts of the declared E32/N32/G32 macros, independent of graph names."""
from functools import lru_cache
from math import isqrt
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
def rne(value,shift):
 if shift<=0:return int(value)<<-shift
 q,r=divmod(int(value),1<<shift);h=1<<(shift-1)
 return q+int(r>h or r==h and q&1)
def quotient_rne(value,denominator):
 q,r=divmod(value,denominator)
 return q+int(2*r>denominator or 2*r==denominator and q&1)
def checked_s32(value):
 if not -(1<<31)<=value<1<<31:raise ValueError('declared S32 macro reported clipping')
 return value
@lru_cache(maxsize=1)
def exp_lut():
 with localcontext() as ctx:
  ctx.prec=60
  return tuple(int(((Decimal(i)/128-16).exp()*65536).to_integral_value(rounding=ROUND_HALF_EVEN)) for i in range(2049))
def exponents(scores):
 peak=max(scores);lut=exp_lut();result=[]
 for value in scores:
  offset=value-peak+1048576
  if offset<=0:result.append(0)
  elif offset>=1048576:result.append(65536)
  else:
   index,fraction=divmod(offset,512);lo,hi=lut[index:index+2]
   result.append(lo+rne((hi-lo)*fraction,9))
 return result
def rms_factor(values,epsilon,baseline,epsilon_shift):
 shift=baseline
 while any(not -32768<=rne(v,shift)<=32767 for v in values):
  shift+=1
  if shift>31:raise ValueError('N32 RMS range overflow')
 extra=shift-baseline
 epsilon=max(1,rne(epsilon,2*extra-epsilon_shift))
 if not 0<epsilon<1<<32:raise ValueError('N32 epsilon overflow')
 square=sum(rne(v,shift)**2 for v in values)
 root=isqrt((square<<16)//len(values)+(epsilon<<16))
 factor=rne((1<<38)//root,extra)
 if not 0<=factor<1<<31:raise ValueError('N32 factor overflow')
 return factor,shift,extra
